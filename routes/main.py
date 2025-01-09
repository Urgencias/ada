import os
import time
from flask import Blueprint, render_template, Response, jsonify, current_app, flash, redirect, url_for, request, session
from flask_login import login_required, current_user
from models import RegistroLlamada, Recordatorio, User, NotificacionLlamada, EstadoLlamadaEnum
from datetime import datetime, date, timedelta
from sqlalchemy import func, text
from extensions import db
from utils.call_providers import gestor_proveedores
from utils.timezone_helpers import get_current_time, to_local_time, to_utc, ZONA_HORARIA_MADRID
import json
import logging
import threading
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
from sqlalchemy import text, func
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)
main_bp = Blueprint('main', __name__)

def realizar_llamada_prueba_simple(telefono, mensaje):
    """Función auxiliar para crear y realizar una llamada de prueba"""
    try:
        recordatorio = Recordatorio(
            user_id=current_user.id,
            nombre="Llamada de Prueba",
            telefono=telefono,
            fecha=get_current_time().date(),
            hora=get_current_time().time().strftime('%H:%M'),
            mensaje=mensaje,
            tipo="prueba",
            repeticion=0
        )
        db.session.add(recordatorio)
        db.session.flush()

        registro = RegistroLlamada(
            recordatorio_id=recordatorio.id,
            estado=EstadoLlamadaEnum.PENDIENTE,
            intentos=0,
            fecha_llamada=get_current_time(),
            duracion=15
        )
        db.session.add(registro)
        db.session.commit()

        logger.info(f"Creado registro de llamada de prueba: {registro.id}")
        return registro

    except Exception as e:
        logger.error(f"Error al crear llamada de prueba: {str(e)}")
        db.session.rollback()
        raise

@main_bp.route('/realizar-llamada-prueba', methods=['GET', 'POST'])
@main_bp.route('/realizar-llamada-prueba/<int:recordatorio_id>', methods=['GET'])
@login_required
def realizar_llamada_prueba(recordatorio_id=None):
    """Vista unificada para realizar llamadas de prueba"""
    try:
        if request.method == 'POST':
            telefono = request.form.get('telefono')
            mensaje = request.form.get('mensaje', 'Esto es una llamada de prueba')
            registro = realizar_llamada_prueba_simple(telefono, mensaje)
        elif recordatorio_id:
            recordatorio = Recordatorio.query.get_or_404(recordatorio_id)
            if recordatorio.user_id != current_user.id and not current_user.es_admin:
                flash('No tienes permiso para realizar esta acción', 'danger')
                return redirect(url_for('main.dashboard'))
            registro = realizar_llamada_prueba_simple(recordatorio.telefono, recordatorio.mensaje)
        else:
            return render_template('prueba_llamada.html')

        # Procesar la llamada
        resultado = gestor_proveedores.realizar_llamada(registro)
        if resultado:
            registro.estado = EstadoLlamadaEnum.EN_CURSO  # Cambiado de INICIADA a EN_CURSO
            db.session.commit()
            flash('Llamada de prueba iniciada correctamente', 'success')
        else:
            registro.estado = EstadoLlamadaEnum.ERROR
            registro.error_mensaje = "No se pudo iniciar la llamada de prueba"
            db.session.commit()
            flash('Error al iniciar la llamada de prueba', 'danger')

        return redirect(url_for('main.panel_monitoreo'))

    except Exception as e:
        logger.error(f"Error al realizar llamada de prueba: {str(e)}")
        flash('Error al realizar la llamada de prueba', 'danger')
        return redirect(url_for('main.dashboard'))

def configurar_paypal():
    """Configura PayPal solo si las credenciales están disponibles"""
    try:
        mode = os.environ.get("PAYPAL_MODE", "sandbox")  # Default to sandbox mode for testing
        client_id = os.environ.get("PAYPAL_CLIENT_ID")
        client_secret = os.environ.get("PAYPAL_SECRET_KEY")

        if not all([client_id, client_secret]):
            logger.warning("Credenciales de PayPal no configuradas completamente")
            return False

        if mode not in ['sandbox', 'live']:
            mode = 'sandbox'  # Forzar modo sandbox si el valor no es válido
            logger.warning("Modo PayPal inválido, usando sandbox por defecto")

        try:
            from paypalrestsdk import configure
            configure({
                "mode": mode,
                "client_id": client_id,
                "client_secret": client_secret
            })
            logger.info(f"PayPal configurado correctamente en modo: {mode}")
            return True
        except ImportError:
            logger.warning("PayPal SDK no está instalado")
            return False
        except Exception as e:
            logger.error(f"Error al configurar PayPal: {str(e)}")
            return False

    except Exception as e:
        logger.error(f"Error general al configurar PayPal: {str(e)}")
        return False


# Configurar PayPal al inicio
paypal_configurado = configurar_paypal()


@main_bp.route('/')
def index():
    """Vista principal con estadísticas básicas"""
    estadisticas = {
        'llamadas_pendientes': 0,
        'llamadas_completadas': 0,
        'llamadas_hoy': 0
    }

    try:
        if current_user.is_authenticated:
            # Consulta base para el usuario actual usando RegistroLlamada
            query_base = RegistroLlamada.query.join(
                Recordatorio,
                RegistroLlamada.recordatorio_id == Recordatorio.id
            ).filter(
                Recordatorio.user_id == current_user.id
            )

            # Calcular estadísticas usando los estados de RegistroLlamada
            estadisticas['llamadas_pendientes'] = query_base.filter(
                RegistroLlamada.estado.in_([
                    EstadoLlamadaEnum.PENDIENTE,
                    EstadoLlamadaEnum.PROGRAMADA
                ])
            ).count()

            estadisticas['llamadas_completadas'] = query_base.filter(
                RegistroLlamada.estado == EstadoLlamadaEnum.COMPLETADA
            ).count()

            hoy = get_current_time().date()
            estadisticas['llamadas_hoy'] = query_base.filter(
                func.date(RegistroLlamada.fecha_llamada) == hoy
            ).count()

            logger.info(f"Estadísticas calculadas para usuario {current_user.id}: {estadisticas}")

    except Exception as e:
        logger.error(f"Error al obtener estadísticas: {str(e)}")
        logger.exception("Stacktrace completo:")

    return render_template('index.html', estadisticas=estadisticas)


@main_bp.route('/nuevo-recordatorio', methods=['GET', 'POST'])
@login_required
def nuevo_recordatorio():
    try:
        from utils.formulario_recordatorios import FormularioRecordatorio

        form = FormularioRecordatorio()
        origen_llamada = os.environ.get('ORIGEN_LLAMADA', 'NUMERO_ORIGEN = "34968972418"')

        if form.validate_on_submit():
            try:
                recordatorio = Recordatorio(user_id=current_user.id,
                                            nombre=form.nombre.data,
                                            telefono=form.telefono.data,
                                            fecha=form.fecha.data,
                                            hora=form.hora.data,
                                            tipo=form.tipo.data,
                                            mensaje=form.mensaje.data,
                                            repeticion=form.repeticion.data)
                db.session.add(recordatorio)
                db.session.flush()

                fecha_llamada = datetime.combine(form.fecha.data, form.hora.data)
                registro = RegistroLlamada(recordatorio_id=recordatorio.id,
                                           estado=EstadoLlamadaEnum.PROGRAMADA,
                                           intentos=0,
                                           fecha_llamada=fecha_llamada)
                db.session.add(registro)
                db.session.commit()

                logger.info(
                    f"Recordatorio creado: ID {recordatorio.id}, Llamada programada para: {fecha_llamada}"
                )
                flash(
                    '¡Recordatorio programado correctamente! La llamada se realizará a la hora indicada.',
                    'success')
                return redirect(url_for('main.dashboard'))

            except Exception as e:
                logger.error(f"Error al crear recordatorio: {str(e)}")
                db.session.rollback()
                flash(
                    'Error al crear el recordatorio. Por favor, inténtelo de nuevo.',
                    'danger')

        return render_template('nuevo_recordatorio.html',
                               form=form,
                               origen_llamada=origen_llamada)

    except Exception as e:
        logger.error(f"Error general en nuevo_recordatorio: {str(e)}")
        flash('Error interno del servidor', 'danger')
        return redirect(url_for('main.dashboard'))


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Vista del panel de control principal"""
    try:
        today = date.today()
        week_from_now = today + timedelta(days=7)

        # Obtener recordatorios con manejo de errores
        try:
            recordatorios = Recordatorio.get_recordatorios_ordenados(current_user.id)
            logger.info(f"Recordatorios encontrados para usuario {current_user.id}: {len(recordatorios)}")
        except Exception as e:
            logger.error(f"Error al obtener recordatorios: {str(e)}")
            recordatorios = []

        # Inicializar estadísticas por defecto
        estadisticas = {
            'total_llamadas': 0,
            'llamadas_completadas': 0,
            'llamadas_pendientes': 0,
            'llamadas_hoy': 0,
            'duracion_media': 0,
            'llamadas_en_curso': 0
        }

        historial_llamadas = []

        try:
            # Consulta base para el usuario actual
            query_base = RegistroLlamada.query.join(
                Recordatorio
            ).filter(
                Recordatorio.user_id == current_user.id
            )

            # Obtener estadísticas básicas
            estadisticas.update({
                'total_llamadas': query_base.count(),
                'llamadas_completadas': query_base.filter(
                    RegistroLlamada.estado == EstadoLlamadaEnum.COMPLETADA
                ).count(),
                'llamadas_pendientes': query_base.filter(
                    RegistroLlamada.estado.in_([
                        EstadoLlamadaEnum.PENDIENTE,
                        EstadoLlamadaEnum.PROGRAMADA
                    ])
                ).count(),
                'llamadas_en_curso': query_base.filter(
                    RegistroLlamada.estado == EstadoLlamadaEnum.EN_CURSO
                ).count()
            })

            # Calcular llamadas de hoy
            estadisticas['llamadas_hoy'] = query_base.filter(
                func.date(RegistroLlamada.fecha_llamada) == today
            ).count()

            # Obtener historial de llamadas con manejo seguro de estados
            llamadas = query_base.order_by(
                RegistroLlamada.fecha_llamada.desc()
            ).limit(10).all()

            for llamada in llamadas:
                try:
                    # Convertir estados obsoletos a EN_CURSO
                    if str(llamada.estado).upper() == 'INICIADA':
                        llamada.estado = EstadoLlamadaEnum.EN_CURSO
                        db.session.commit()
                    historial_llamadas.append(llamada)
                except Exception as e:
                    logger.error(f"Error procesando llamada {llamada.id}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {str(e)}")
            logger.exception("Stacktrace del error de estadísticas:")

        return render_template('dashboard.html',
                            recordatorios=recordatorios,
                            historial_llamadas=historial_llamadas,
                            estadisticas=estadisticas,
                            today=today,
                            week_from_now=week_from_now,
                            EstadoLlamadaEnum=EstadoLlamadaEnum)

    except Exception as e:
        logger.error(f"Error general en dashboard: {str(e)}")
        logger.exception("Stacktrace completo:")
        flash('Error al cargar el dashboard. Por favor, inténtelo de nuevo más tarde.', 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/editar-recordatorio/<int:recordatorio_id>', methods=['GET', 'POST'])
@login_required
def editar_recordatorio(recordatorio_id):
    """Vista para editar un recordatorio existente"""
    try:
        recordatorio = Recordatorio.query.get_or_404(recordatorio_id)
        if recordatorio.user_id != current_user.id and not current_user.es_admin:
            flash('No tienes permiso para editar este recordatorio', 'danger')
            return redirect(url_for('main.dashboard'))

        from utils.formulario_recordatorios import FormularioRecordatorio
        form = FormularioRecordatorio(obj=recordatorio)

        if form.validate_on_submit():
            form.populate_obj(recordatorio)
            db.session.commit()
            flash('Recordatorio actualizado correctamente', 'success')
            return redirect(url_for('main.dashboard'))

        return render_template('editar_recordatorio.html', form=form, recordatorio=recordatorio)
    except Exception as e:
        logger.error(f"Error al editar recordatorio {recordatorio_id}: {str(e)}")
        flash('Error al editar el recordatorio', 'danger')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/panel-monitoreo')
@login_required
def panel_monitoreo():
    """Vista del panel de monitoreo de llamadas"""
    try:
        logger.info("Iniciando carga del panel de monitoreo")

        # Actualizar contadores para todos los usuarios
        for user in User.query.all():
            actualizar_contadores(user.id)

        # Obtener estadísticas globales usando la nueva tabla de contadores
        estadisticas = obtener_contadores()
        estadisticas['total_usuarios'] = User.query.count()

        # Obtener registros de llamadas recientes
        sql_llamadas = text("""
            SELECT rl.id, rl.estado, rl.fecha_llamada, rl.duracion, 
                   r.nombre, r.telefono, r.mensaje,
                   u.username
            FROM registros_llamadas rl
            JOIN recordatorios r ON rl.recordatorio_id = r.id
            JOIN users u ON r.user_id = u.id
            ORDER BY rl.fecha_llamada DESC
            LIMIT 50
        """)

        registros_llamadas = db.session.execute(sql_llamadas).fetchall()
        logger.info(f"Registros de llamadas obtenidos: {len(registros_llamadas)}")

        llamadas_procesadas = []
        for reg in registros_llamadas:
            llamada = {
                'id': reg.id,
                'estado': reg.estado,
                'fecha_llamada': reg.fecha_llamada,
                'duracion': reg.duracion or 0,
                'nombre_recordatorio': reg.nombre,
                'telefono': reg.telefono,
                'mensaje': reg.mensaje,
                'usuario': reg.username
            }
            llamadas_procesadas.append(llamada)

        logger.info(f"Total de llamadas procesadas: {len(llamadas_procesadas)}")

        return render_template('panel_monitoreo.html',
                            estadisticas=estadisticas,
                            llamadas=llamadas_procesadas,
                            EstadoLlamadaEnum=EstadoLlamadaEnum)

    except Exception as e:
        logger.error(f"Error al cargar el panel de monitoreo: {str(e)}")
        logger.exception("Stacktrace completo:")
        flash('Error al cargar el panel de monitoreo', 'danger')

        return render_template('panel_monitoreo.html',
                            estadisticas={
                                'total_usuarios': 0,
                                'total_llamadas': 0,
                                'llamadas_completadas': 0,
                                'llamadas_pendientes': 0,
                                'llamadas_en_curso': 0,
                                'llamadas_error': 0
                            },
                            llamadas=[],
                            EstadoLlamadaEnum=EstadoLlamadaEnum)

def eliminar_llamada(llamada_id):
    try:
        llamada = RegistroLlamada.query.get_or_404(llamada_id)

        recordatorio = Recordatorio.query.get(llamada.recordatorio_id)
        if not current_user.es_admin and recordatorio.user_id != current_user.id:
            flash('No tienes permiso para eliminar esta llamada', 'danger')
            return jsonify({'error': 'No autorizado'}), 403

        if llamada.estado == EstadoLlamadaEnum.EN_CURSO:
            flash('No se puede eliminar una llamada en curso', 'warning')
            return jsonify({'error': 'Llamada en curso'}), 400

        db.session.delete(llamada)
        db.session.commit()

        flash('Llamada eliminada correctamente', 'success')
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error al eliminar llamada {llamada_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@main_bp.route('/eliminar-registro/<int:registro_id>', methods=['POST'])
@login_required
def eliminar_registro(registro_id):
    try:
        registro = RegistroLlamada.query.get_or_404(registro_id)

        recordatorio = Recordatorio.query.get(registro.recordatorio_id)
        if not recordatorio:
            return jsonify({'error': 'Registro no encontrado'}), 404

        if not current_user.es_admin and recordatorio.user_id != current_user.id:
            return jsonify({'error': 'No autorizado'}), 403

        NotificacionLlamada.query.filter_by(
            registro_llamada_id=registro_id).delete()

        db.session.delete(registro)
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error al eliminar registro {registro_id}: {str(e)}")
        logger.exception("Stacktrace completo:")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main_bp.route('/admin-panel')
@login_required
def admin_panel():
    """Vista para el panel de administración"""
    try:
        logger.info("Cargando panel de administración")

        # Actualizar contadores para todos los usuarios
        for user in User.query.all():
            actualizar_contadores(user.id)

        # Obtener estadísticas globales usando la nueva función de contadores
        estadisticas = obtener_contadores()
        estadisticas['total_usuarios'] = User.query.count()

        # Obtener detalles de usuarios con sus contadores
        sql_usuarios = text("""
            SELECT 
                u.id,
                u.username,
                c.llamadas_totales,
                c.llamadas_completadas,
                c.llamadas_pendientes,
                c.llamadas_en_curso,
                c.llamadas_error
            FROM users u
            LEFT JOIN contadores c ON u.id = c.usuario_id
            ORDER BY u.username
        """)
        usuarios = db.session.execute(sql_usuarios).fetchall()

        logger.info(f"Estadísticas calculadas: {estadisticas}")
        logger.info(f"Total usuarios encontrados: {len(usuarios)}")

        return render_template('admin_panel.html', 
                            estadisticas=estadisticas,
                            usuarios=usuarios)

    except Exception as e:
        logger.error(f"Error al cargar el panel de administración: {str(e)}")
        logger.exception("Stacktrace completo:")
        flash('Error al cargar el panel de administración', 'danger')
        return render_template('admin_panel.html', 
                            estadisticas={
                                'total_usuarios': 0,
                                'total_llamadas': 0,
                                'llamadas_completadas': 0,
                                'llamadas_pendientes': 0,
                                'llamadas_en_curso': 0,
                                'llamadas_error': 0
                            },
                            usuarios=[])

def obtener_marcadores_llamadas():
    try:
        # Consulta base para las llamadas del usuario
        llamadas_base = (
            RegistroLlamada.query
            .join(Recordatorio)
            .filter(Recordatorio.user_id == current_user.id)
        )

        # Obtener conteos por estado
        conteos = {}
        for estado in EstadoLlamadaEnum:
            conteos[estado.name] = llamadas_base.filter(
                RegistroLlamada.estado == estado
            ).count()

        # Calcular totales y porcentajes
        total_llamadas = sum(conteos.values())
        porcentaje_completadas = (
            (conteos['COMPLETADA'] / total_llamadas * 100)
            if total_llamadas > 0 else 0
        )

        return jsonify({
            'conteos': conteos,
            'total': total_llamadas,
            'porcentaje_completadas': round(porcentaje_completadas, 1)
        })

    except Exception as e:
        logger.error(f"Error al obtener marcadores de llamadas: {str(e)}")
        logger.exception("Stacktrace completo:")
        return jsonify({
            'error': 'Error al obtener marcadores',
            'mensaje': str(e)
        }), 500


@main_bp.route('/politica-privacidad')
def politica_privacidad():
    """Página de política de privacidad"""
    return render_template('politica_privacidad.html')


@main_bp.route('/politica-cookies')
def politica_cookies():
    """Página de política de cookies"""
    return render_template('politica_cookies.html')


@main_bp.route('/terminos-condiciones')
def terminos_condiciones():
    """Página de términos y condiciones"""
    return render_template('terminos_condiciones.html')


@main_bp.route('/configuracion-cookies')
def configuracion_cookies():
    """Página de configuración de cookies"""
    return render_template('configuracion_cookies.html')


@main_bp.route('/suscripcion')
@login_required
def suscripcion():
    """Vista para mostrar los planes de suscripción disponibles"""
    try:
        planes = PaqueteSuscripcion.query.filter_by(activo=True).all()
        return render_template('suscripcion.html', planes=planes)
    except Exception as e:
        logger.error(f"Error al cargar planes de suscripción: {str(e)}")
        flash('Error al cargar los planes de suscripción', 'danger')
        return redirect(url_for('main.dashboard'))


@main_bp.route('/solicitar-plan-gratuito', methods=['GET', 'POST'])
@login_required
def solicitar_plan_gratuito():
    """Procesar solicitud del plan gratuito para mayores"""
    try:
        if request.method == 'POST':
            # Verificar si el usuario ya tiene una suscripción activa
            suscripcion_existente = Suscripcion.query.filter_by(
                user_id=current_user.id, estado='activo').first()

            if suscripcion_existente:
                flash('Ya tienes una suscripción activa', 'warning')
                return redirect(url_for('main.suscripcion'))

            # Crear nueva suscripción gratuita
            suscripcion, error = Suscripcion.crear_suscripcion(
                user_id=current_user.id,
                tipo='gratuito_anciano',
                notas='Plan gratuito para mayores')

            if error:
                flash(f'Error al crear la suscripción: {error}', 'danger')
                return redirect(url_for('main.suscripcion'))

            # Activar inmediatamente la suscripción gratuita
            if suscripcion.activar():
                flash('¡Plan gratuito activado correctamente!', 'success')
            else:
                flash('Error al activar el plan gratuito', 'danger')

            return redirect(url_for('main.dashboard'))

        return render_template('solicitar_plan_gratuito.html')

    except Exception as e:
        logger.error(f"Error en solicitud de plan gratuito: {str(e)}")
        flash('Error al procesar la solicitud', 'danger')
        return redirect(url_for('main.suscripcion'))


@main_bp.route('/adoptar-abuelo', methods=['GET', 'POST'])
@login_required
def adoptar_abuelo():
    """Procesar solicitud del plan de pago 'Adopta un Abuelo'"""
    if not paypal_configurado:
        flash('El sistema de pago no está disponible en este momento', 'warning')
        return redirect(url_for('main.suscripcion'))

    try:
        if request.method == 'POST':
            # Verificar suscripción existente
            suscripcion_existente = Suscripcion.query.filter_by(
                user_id=current_user.id, estado='activo').first()

            if suscripcion_existente:
                flash('Ya tienes una suscripción activa', 'warning')
                return redirect(url_for('main.suscripcion'))

            # Obtener el paquete de suscripción
            paquete = PaqueteSuscripcion.query.filter_by(tipo='adoptar_abuelo',
                                                         activo=True).first()

            if not paquete:
                flash('El plan seleccionado no está disponible', 'warning')
                return redirect(url_for('main.suscripcion'))

            # Crear pago PayPal
            from paypalrestsdk import Payment
            payment = Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": url_for('main.confirmar_pago',
                                          _external=True),
                    "cancel_url": url_for('main.cancelar_pago', _external=True)
                },
                "transactions": [{
                    "amount": {
                        "total": str(paquete.precio),
                        "currency": "EUR"
                    },
                    "description": f"Suscripción: {paquete.nombre}"
                }]
            })

            if payment.create():
                # Guardar ID del pago en la sesión
                session['paypal_payment_id'] = payment.id

                # Obtener el enlace de aprobación
                for link in payment.links:
                    if link.rel == "approval_url":
                        return redirect(link.href)

            flash('Error al procesar el pago', 'danger')
            return redirect(url_for('main.suscripcion'))

        return render_template('adoptar_abuelo.html')

    except Exception as e:
        logger.error(f"Error en solicitud de plan Adopta un Abuelo: {str(e)}")
        flash('Error al procesar la solicitud', 'danger')
        return redirect(url_for('main.suscripcion'))


@main_bp.route('/confirmar-pago')
@login_required
def confirmar_pago():
    """Confirmar el pago de PayPal y activar la suscripción"""
    try:
        payment_id = session.get('paypal_payment_id')
        payer_id = request.args.get('PayerID')

        if not payment_id or not payer_id:
            flash('Información de pago incompleta', 'danger')
            return redirect(url_for('main.suscripcion'))

        from paypalrestsdk import Payment
        payment = Payment.find(payment_id)

        if payment.execute({"payer_id": payer_id}):
            # Crear y activar la suscripción
            suscripcion, error = Suscripcion.crear_suscripcion(
                user_id=current_user.id,
                tipo='adoptar_abuelo',
                notas=f'Plan Adopta un Abuelo - PayPal ID: {payment_id}')

            if error:
                flash(f'Error al crear la suscripción: {error}', 'danger')
                return redirect(url_for('main.suscripcion'))

            if suscripcion.activar():
                flash('¡Suscripción activada correctamente!', 'success')
            else:
                flash('Error al activar la suscripción', 'danger')

        else:
            flash('Error al procesar el pago', 'danger')

        # Limpiar ID del pago de la sesión
        session.pop('paypal_payment_id', None)
        return redirect(url_for('main.dashboard'))

    except Exception as e:
        logger.error(f"Error en confirmación de pago: {str(e)}")
        flash('Error al confirmar el pago', 'danger')
        return redirect(url_for('main.suscripcion'))


@main_bp.route('/cancelar-pago')
@login_required
def cancelar_pago():
    """Manejar cancelación del pago de PayPal"""
    session.pop('paypal_payment_id', None)
    flash('El proceso de pago ha sido cancelado', 'warning')
    return redirect(url_for('main.suscripcion'))


@main_bp.route('/seleccionar-paquete')
@login_required
def seleccionar_paquete():
    """Vista para seleccionar el paquete de suscripción"""
    try:
        return render_template('seleccionar_paquete.html')
    except Exception as e:
        logger.error(f"Error al cargar selección de paquete: {str(e)}")
        flash('Error al cargar la página de selección de paquete', 'danger')
        return redirect(url_for('main.suscripcion'))


@main_bp.route('/cambiar-proveedor', methods=['POST'])
@login_required
def cambiar_proveedor():
    try:
        if not current_user.es_admin:
            flash('No tienes permiso para realizar esta acción', 'danger')
            return redirect(url_for('main.dashboard'))

        nuevo_proveedor = request.form.get('proveedor')
        if nuevo_proveedor not in ['netelip', 'twilio']:
            flash('Proveedor no válido', 'danger')
            return redirect(url_for('main.admin_panel'))

        gestor_proveedores.cambiar_proveedor_activo(nuevo_proveedor)
        flash(f'Proveedor cambiado a {nuevo_proveedor}', 'success')
        return redirect(url_for('main.admin_panel'))

    except Exception as e:
        logger.error(f"Error al cambiar proveedor: {str(e)}")
        logger.exception("Stacktrace completo:")
        flash('Error al cambiar el proveedor', 'danger')
        return redirect(url_for('main.admin_panel'))


@main_bp.route('/obtener-recordatorio/<int:recordatorio_id>')
@login_required
def obtener_recordatorio(recordatorio_id):
    try:
        recordatorio = Recordatorio.query.get_or_404(recordatorio_id)

        if recordatorio.user_id != current_user.id and not current_user.es_admin:
            logger.warning(
                f'Usuario {current_user.id} intentó acceder al recordatorio {recordatorio_id} sin permisos'
            )
            flash('No tienes permiso para realizar esta acción', 'danger')
            return redirect(url_for('main.dashboard'))

        return jsonify({
            'id': recordatorio.id,
            'nombre': recordatorio.nombre,
            'telefono': recordatorio.telefono,
            'fecha': recordatorio.fecha.strftime('%Y-%m-%d'),
            'hora': recordatorio.hora.strftime('%H:%M'),
            'mensaje': recordatorio.mensaje,
            'tipo': recordatorio.tipo,
            'repeticion': recordatorio.repeticion
        })

    except Exception as e:
        logger.error(
            f"Error al obtener recordatorio {recordatorio_id}: {str(e)}")
        logger.exception("Stacktrace completo:")
        return jsonify({'error': str(e)}), 500


@main_bp.route('/recordatorio/<int:recordatorio_id>', methods=['GET', 'POST'])
@login_required
def ver_recordatorio(recordatorio_id):
    try:
        recordatorio = Recordatorio.query.get_or_404(recordatorio_id)

        if recordatorio.user_id != current_user.id and not current_user.es_admin:
            logger.warning(
                f'Usuario {current_user.id} intentó acceder al recordatorio {recordatorio_id} sin permisos'
            )
            flash('No tienes permiso para realizar esta acción', 'danger')
            return redirect(url_for('main.dashboard'))

        try:
            # Obtener registro de llamadas relacionadas
            llamadas = RegistroLlamada.query.filter_by(
                recordatorio_id=recordatorio_id).order_by(
                    RegistroLlamada.fecha_llamada.desc()).all()

            return render_template('ver_recordatorio.html',
                                   recordatorio=recordatorio,
                                   llamadas=llamadas)

        except Exception as e:
            logger.error(
                f"Error al obtener llamadas del recordatorio {recordatorio_id}: {str(e)}"
            )
            flash('Error al cargar el historial de llamadas', 'warning')
            return render_template('ver_recordatorio.html',
                                   recordatorio=recordatorio,
                                   llamadas=[])

    except Exception as e:
        logger.error(
            f"Error al cargar recordatorio {recordatorio_id}: {str(e)}")
        flash('Error al cargar el recordatorio', 'danger')
        return redirect(url_for('main.dashboard'))

@main_bp.route('/suscripciones')
@login_required
def suscripciones():
    try:
        if not current_user.is_authenticated:
            flash('Debes iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('auth.login'))

        return render_template('suscripciones.html')

    except Exception as e:
        logger.error(f"Error al cargar página de suscripciones: {str(e)}")
        logger.exception("Stacktrace completo:")
        flash('Error al cargar la página de suscripciones', 'danger')
        return redirect(url_for('main.dashboard'))


@main_bp.context_processor
def inject_site_info():
    return {
        'site_name': 'Ada',
        'site_subtitle': 'Tu asistente personal de voz',
        'credits': {
            'powered_by': 'Replit',
            'special_thanks': [
                'Ada de Replit - Asistente IA', 'Alvaro GPT - Asistente IA',
                'Y todos los grandes amigos IA que han contribuido a este proyecto social'
            ],
            'social_impact': 'Proyecto dedicado a mejorar la comunicación en hospitales y centros de atención'
        }
    }


@main_bp.route('/cancelar-llamadas-prueba', methods=['POST'])
@login_required
def cancelar_llamadas_prueba():
    try:
        llamadas_pendientes = (RegistroLlamada.query.filter(
            RegistroLlamada.estado.in_([EstadoLlamadaEnum.PENDIENTE, EstadoLlamadaEnum.PROGRAMADA])).all())

        contador = 0
        for llamada in llamadas_pendientes:
            llamada.estado = EstadoLlamadaEnum.CANCELADA
            llamada.notas = 'Llamada de prueba cancelada por el usuario'
            llamada.fecha_actualizacion = get_current_time()
            contador += 1

        db.session.commit()
        flash(f'Se han cancelado {contador} llamadas pendientes', 'success')

    except Exception as e:
        logger.error(f"Error al cancelar llamadas: {str(e)}")
        db.session.rollback()
        flash('Error al cancelar las llamadas', 'danger')

    return redirect(url_for('main.dashboard'))


@main_bp.route('/actualizar-usuario-ejemplo', methods=['POST'])
@login_required
def actualizar_usuario_ejemplo():
    try:
        if not current_user.es_admin:
            flash('No tienes permiso para realizar esta acción', 'danger')
            return redirect(url_for('main.dashboard'))

        usuario = User.query.filter_by(username='ejemplo').first()
        if usuario:
            usuario.email = 'asefoc@hotmai.com'
            usuario.password_hash = generate_password_hash('asefoc123')
            db.session.commit()
            flash('Usuario de ejemplo actualizado correctamente', 'success')
        else:
            flash('Usuario de ejemplo no encontrado', 'danger')

        return redirect(url_for('main.panel_monitoreo'))

    except Exception as e:
        logger.error(f"Error al actualizar usuario de ejemplo: {str(e)}")
        db.session.rollback()
        flash('Error al actualizar usuario de ejemplo', 'danger')
        return redirect(url_for('main.panel_monitoreo'))


@main_bp.route('/crear-usuario-asefoc', methods=['POST'])
@login_required
def crear_usuario_asefoc():
    try:
        # Verificar si el usuario ya existe
        if User.query.filter((User.username == 'asefoc') | (User.email == 'asefoc@hotmai.com')).first():
            flash('El usuario ya existe', 'warning')
            return redirect(url_for('main.panel_monitoreo'))

        # Crear nuevo usuario
        nuevo_usuario = User(
            username='asefoc',
            email='asefoc@hotmai.com',
            llamadas_disponibles=100,
            llamadas_realizadas=0,
            es_admin=False,
            fecha_registro=datetime.utcnow()
        )
        nuevo_usuario.set_password('asefoc123')

        db.session.add(nuevo_usuario)
        db.session.commit()

        flash('Usuario creado correctamente', 'success')
        return redirect(url_for('main.panel_monitoreo'))

    except Exception as e:
        logger.error(f"Error al crear usuario asefoc: {str(e)}")
        db.session.rollback()
        flash('Error al crear usuario', 'danger')
        return redirect(url_for('main.panel_monitoreo'))

def init_app(app):
    init_scheduled_calls_checker(app)

# Add routes for recordatorios
@main_bp.route('/recordatorios')
@login_required
def recordatorios():
    """Vista para mostrar la lista de recordatorios"""
    try:
        recordatorios = Recordatorio.get_recordatorios_ordenados(current_user.id)
        return render_template('recordatorios.html', recordatorios=recordatorios)
    except Exception as e:
        logger.error(f"Error al cargar recordatorios: {str(e)}")
        flash('Error al cargar los recordatorios', 'danger')
        return redirect(url_for('main.dashboard'))

def actualizar_contadores(user_id):
    """
    Actualiza los contadores de llamadas para un usuario específico
    """
    try:
        logger.info(f"Iniciando actualización de contadores para usuario {user_id}")

        # Obtener estadísticas actuales usando una transacción
        with db.session.begin_nested():
            query = text("""
                WITH stats AS (
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN estado = :completada THEN 1 ELSE 0 END) as completadas,
                        SUM(CASE WHEN estado IN (:pendiente, :programada) THEN 1 ELSE 0 END) as pendientes,
                        SUM(CASE WHEN estado = :en_curso THEN 1 ELSE 0 END) as en_curso,
                        SUM(CASE WHEN estado = :error THEN 1 ELSE 0 END) as errores
                    FROM registros_llamadas rl
                    JOIN recordatorios r ON rl.recordatorio_id = r.id
                    WHERE r.user_id = :user_id
                )
                INSERT INTO contadores (
                    usuario_id, 
                    llamadas_totales, 
                    llamadas_completadas, 
                    llamadas_pendientes,
                    llamadas_en_curso,
                    llamadas_error,
                    ultima_actualizacion
                )
                SELECT 
                    :user_id,
                    COALESCE(stats.total, 0),
                    COALESCE(stats.completadas, 0),
                    COALESCE(stats.pendientes, 0),
                    COALESCE(stats.en_curso, 0),
                    COALESCE(stats.errores, 0),
                    CURRENT_TIMESTAMP
                FROM stats
                ON CONFLICT (usuario_id) DO UPDATE 
                SET 
                    llamadas_totales = EXCLUDED.llamadas_totales,
                    llamadas_completadas = EXCLUDED.llamadas_completadas,
                    llamadas_pendientes = EXCLUDED.llamadas_pendientes,
                    llamadas_en_curso = EXCLUDED.llamadas_en_curso,
                    llamadas_error = EXCLUDED.llamadas_error,
                    ultima_actualizacion = CURRENT_TIMESTAMP
                RETURNING *;
            """)

            result = db.session.execute(query, {
                'user_id': user_id,
                'completada': EstadoLlamadaEnum.COMPLETADA.value,
                'pendiente': EstadoLlamadaEnum.PENDIENTE.value,
                'programada': EstadoLlamadaEnum.PROGRAMADA.value,
                'en_curso': EstadoLlamadaEnum.EN_CURSO.value,
                'error': EstadoLlamadaEnum.ERROR.value
            }).first()

            # Verificar la integridad de los datos actualizados
            if result:
                logger.info(f"Contadores actualizados para usuario {user_id}:")
                logger.info(f"  Total: {result.llamadas_totales}")
                logger.info(f"  Completadas: {result.llamadas_completadas}")
                logger.info(f"  Pendientes: {result.llamadas_pendientes}")
                logger.info(f"  En curso: {result.llamadas_en_curso}")
                logger.info(f"  Errores: {result.llamadas_error}")
            else:
                logger.warning(f"No se pudo verificar la actualización para usuario {user_id}")

        db.session.commit()
        return True

    except SQLAlchemyError as e:
        logger.error(f"Error SQL al actualizar contadores para usuario {user_id}: {str(e)}")
        db.session.rollback()
        raise
    except Exception as e:
        logger.error(f"Error general al actualizar contadores para usuario {user_id}: {str(e)}")
        db.session.rollback()
        raise

def obtener_contadores(user_id=None):
    """
    Obtiene los contadores actuales, ya sea para un usuario específico o totales
    """
    try:
        if user_id:
            query = text("""
                SELECT * FROM contadores WHERE usuario_id = :user_id
            """)
            result = db.session.execute(query, {'user_id': user_id}).first()
        else:
            query = text("""
                SELECT 
                    SUM(llamadas_totales) as llamadas_totales,
                    SUM(llamadas_completadas) as llamadas_completadas,
                    SUM(llamadas_pendientes) as llamadas_pendientes,
                    SUM(llamadas_en_curso) as llamadas_en_curso,
                    SUM(llamadas_error) as llamadas_error
                FROM contadores
            """)
            result = db.session.execute(query).first()

        return {
            'total_llamadas': result.llamadas_totales if result else 0,
            'llamadas_completadas': result.llamadas_completadas if result else 0,
            'llamadas_pendientes': result.llamadas_pendientes if result else 0,
            'llamadas_en_curso': result.llamadas_en_curso if result else 0,
            'llamadas_error': result.llamadas_error if result else 0
        }
    except SQLAlchemyError as e:
        logger.error(f"Error al obtener contadores: {str(e)}")
        return {
            'total_llamadas': 0,
            'llamadas_completadas': 0,
            'llamadas_pendientes': 0,
            'llamadas_en_curso': 0,
            'llamadas_error': 0
        }

@main_bp.route('/monitor-updates')
@login_required
def monitor_updates():
    """Vista para actualizaciones en tiempo real del panel de monitoreo"""
    try:
        app = current_app._get_current_object()

        def generate():
            logger.info("Iniciando generador SSE")
            with app.app_context():
                while True:
                    try:
                        # Verificar autenticación antes de continuar
                        if not current_user or not current_user.is_authenticated:
                            logger.warning("Usuario no autenticado en generador SSE")
                            yield f"data: {json.dumps({'estado': 'error', 'mensaje': 'Usuario no autenticado'})}\n\n"
                            time.sleep(5)
                            continue

                        # Usar la misma consulta SQL que el panel de monitoreo
                        sql = text("""
                            SELECT 
                                COUNT(*) as total,
                                SUM(CASE WHEN estado = :completada THEN 1 ELSE 0 END) as completadas,
                                SUM(CASE WHEN estado IN (:pendiente, :programada) THEN 1 ELSE 0 END) as pendientes,
                                SUM(CASE WHEN estado = :en_curso THEN 1 ELSE 0 END) as en_curso
                            FROM registros_llamadas
                        """)

                        result = db.session.execute(sql, {
                            'completada': EstadoLlamadaEnum.COMPLETADA.value,
                            'pendiente': EstadoLlamadaEnum.PENDIENTE.value,
                            'programada': EstadoLlamadaEnum.PROGRAMADA.value,
                            'en_curso': EstadoLlamadaEnum.EN_CURSO.value
                        }).first()

                        # Construir estadísticas consistentes
                        estadisticas = {
                            'total_llamadas': result.total or 0,
                            'llamadas_completadas': result.completadas or 0,
                            'llamadas_pendientes': result.pendientes or 0,
                            'llamadas_en_curso': result.en_curso or 0
                        }

                        data = {
                            'estado': 'ok',
                            'mensaje': 'Monitoreo actualizado',
                            'timestamp': datetime.now().isoformat(),
                            'estadisticas': estadisticas
                        }

                        logger.debug(f"SSE enviando actualización: {data}")
                        yield f"data: {json.dumps(data)}\n\n"
                        time.sleep(5)

                    except Exception as e:
                        logger.error(f"Error en generador SSE: {str(e)}")
                        logger.exception("Stacktrace completo:")
                        error_data = {
                            'estado': 'error',
                            'mensaje': 'Error interno del servidor',
                            'timestamp': datetime.now().isoformat()
                        }
                        yield f"data: {json.dumps(error_data)}\n\n"
                        time.sleep(5)

        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )

    except Exception as e:
        logger.error(f"Error crítico en monitor-updates: {str(e)}")
        logger.exception("Stacktrace completo:")
        return jsonify({
            'error': 'Error en el servicio de monitoreo',
            'mensaje': str(e)
        }), 500

def check_llamadas_programadas(app):
    logger.info("Iniciando verificador de llamadas programadas")

    while True:
        try:
            with app.app_context():
                ahora = get_current_time()
                logger.info(f"Hora actual del sistema (Madrid): {ahora}")

                # Modificamos esta consulta para usar el enum correctamente
                primera_llamada_pendiente = (
                    RegistroLlamada.query
                    .filter(RegistroLlamada.estado.in_([EstadoLlamadaEnum.PENDIENTE, EstadoLlamadaEnum.PROGRAMADA]))
                    .order_by(RegistroLlamada.fecha_llamada)
                    .first()
                )

                if primera_llamada_pendiente:
                    tiempo_llamada = to_local_time(primera_llamada_pendiente.fecha_llamada)
                    logger.info(f"Primera llamada pendiente en base de datos (hora Madrid): {tiempo_llamada}")

                llamadas_pendientes = (
                    RegistroLlamada.query.join(Recordatorio).filter(
                        RegistroLlamada.estado.in_([EstadoLlamadaEnum.PENDIENTE,
                                                    EstadoLlamadaEnum.PROGRAMADA]),
                        RegistroLlamada.intentos < 8
                    ).order_by(
                        Recordatorio.fecha.asc(),
                        Recordatorio.hora.asc(),
                        RegistroLlamada.intentos.asc()
                    ).all())

                if llamadas_pendientes:
                    logger.info(
                        f"Encontradas {len(llamadas_pendientes)} llamadas pendientes"
                    )
                    for llamada in llamadas_pendientes:
                        try:
                            fecha_hora_llamada = datetime.combine(
                                llamada.recordatorio.fecha,
                                llamada.recordatorio.hora)
                            fecha_hora_llamada = ZONA_HORARIA_MADRID.localize(
                                fecha_hora_llamada)
                            fecha_hora_llamada_utc = to_utc(fecha_hora_llamada)

                            logger.info(f"Evaluando llamada {llamada.id}:")
                            logger.info(
                                f"  Programada para (Madrid): {fecha_hora_llamada}"
                            )
                            logger.info(f"  Hora actual (Madrid): {ahora}")
                            logger.info(
                                f"  Estado actual: {llamada.estado}, Intentos: {llamada.intentos}"
                            )

                            if fecha_hora_llamada <= ahora:
                                logger.info(
                                    f"Iniciando llamada {llamada.id} (intento {llamada.intentos + 1}/8)"
                                )
                                resultado = gestor_proveedores.realizar_llamada(
                                    llamada)

                                if resultado:
                                    logger.info(
                                        f"Llamada {llamada.id} iniciada correctamente"
                                    )
                                    llamada.estado = EstadoLlamadaEnum.INICIADA
                                    llamada.fecha_actualizacion = ahora
                                    db.session.commit()
                                else:
                                    logger.warning(
                                        f"No se pudo iniciar la llamada {llamada.id}"
                                    )
                                    llamada.intentos += 1
                                    llamada.estado = EstadoLlamadaEnum.PENDIENTE
                                    llamada.siguiente_intento = ahora + timedelta(
                                        minutes=1)
                                    llamada.fecha_actualizacion = ahora
                                    db.session.commit()
                            else:
                                logger.info(
                                    f"Llamada {llamada.id} aún no debe ejecutarse"
                                )

                        except Exception as e:
                            logger.error(
                                f"Error al procesar llamada {llamada.id}: {str(e)}"
                            )
                            logger.exception("Stacktrace completo:")
                            llamada.intentos += 1
                            llamada.estado = EstadoLlamadaEnum.ERROR
                            llamada.siguiente_intento = ahora + timedelta(
                                minutes=1)
                            llamada.fecha_actualizacion = ahora
                            llamada.error_mensaje = str(e)
                            db.session.commit()

                else:
                    logger.debug("No hay llamadas pendientes en este momento")

        except Exception as e:
            logger.error(f"Error en check_llamadas_programadas: {str(e)}")
            logger.exception("Stacktrace completo:")

        logger.debug("Esperando 30 segundos para la siguiente verificación...")
        time.sleep(30)

def init_scheduled_calls_checker(app):
    thread = threading.Thread(target=check_llamadas_programadas,
                              args=(app, ),
                              daemon=True)
    thread.start()
    logger.info("Iniciado hilo de verificación de llamadas programadas")
