import logging
import os
from flask import Blueprint, jsonify, request, render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from utils.call_providers import gestor_proveedores
from models import RegistroLlamada, Recordatorio
from extensions import db
from datetime import datetime, timedelta

# Configurar logging específico para pruebas de llamadas
logger = logging.getLogger(__name__)

test_calls_bp = Blueprint('test_calls', __name__)

@test_calls_bp.route('/prueba-llamada', methods=['GET', 'POST'])
@login_required
def prueba_llamada():
    """Endpoint para probar el sistema de llamadas"""
    try:
        if not current_user.is_authenticated:
            logger.error(f"Usuario no autenticado intentando realizar llamada de prueba desde IP {request.remote_addr}")
            flash('Debes iniciar sesión para realizar esta acción', 'warning')
            return redirect(url_for('auth.login'))

        # Verificar que current_user.id existe
        if not current_user.id:
            logger.error("ID de usuario no disponible")
            return jsonify({
                'success': False,
                'error': 'ID de usuario no disponible'
            }), 400

        # Obtener el número de teléfono y mensaje del request
        data = request.get_json()
        telefono = data.get('telefono') if data else None
        mensaje = data.get('mensaje') if data else None

        if not telefono or not mensaje:
            logger.error("Número de teléfono o mensaje no proporcionado")
            return jsonify({
                'success': False,
                'error': 'Número de teléfono y mensaje son requeridos'
            }), 400

        try:
            # Crear un recordatorio temporal para la prueba
            recordatorio = Recordatorio(
                user_id=current_user.id,
                nombre="Prueba de llamada",
                telefono=telefono,
                fecha=datetime.now().date(),
                hora=datetime.now().time(),
                mensaje=mensaje,
                tipo="prueba",
                repeticion="0"
            )

            logger.info(f"Creando recordatorio temporal para usuario {current_user.id}")
            db.session.add(recordatorio)
            db.session.flush()
            logger.info(f"Recordatorio creado con ID: {recordatorio.id}")

            # Crear registro de llamada
            registro = RegistroLlamada(
                recordatorio_id=recordatorio.id,
                estado='pendiente',
                intentos=0,
                fecha_llamada=datetime.now()
            )

            logger.info("Creando registro de llamada")
            db.session.add(registro)
            db.session.commit()
            logger.info(f"Registro de llamada creado con ID: {registro.id}")

            # Intentar realizar la llamada
            logger.info("Iniciando llamada de prueba")
            resultado = gestor_proveedores.realizar_llamada(registro)

            if resultado:
                logger.info("Llamada de prueba iniciada correctamente")
                return jsonify({
                    'success': True,
                    'message': 'Llamada iniciada correctamente'
                })
            else:
                logger.error("Error al iniciar la llamada de prueba")
                return jsonify({
                    'success': False,
                    'error': 'Error al iniciar la llamada'
                })

        except Exception as db_error:
            logger.error(f"Error en la base de datos: {str(db_error)}")
            logger.exception("Stacktrace del error de base de datos:")
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': f'Error en la base de datos: {str(db_error)}'
            }), 500

    except Exception as e:
        logger.error(f"Error en prueba de llamada: {str(e)}")
        logger.exception("Stacktrace completo:")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@test_calls_bp.route('/programar-pruebas', methods=['GET', 'POST'])
@login_required
def programar_pruebas():
    """Programa varias llamadas de prueba espaciadas"""
    try:
        if not current_user.is_authenticated:
            flash('Debes iniciar sesión para realizar esta acción', 'warning')
            return redirect(url_for('auth.login'))

        # Obtener número de teléfono del formulario o usar el del sistema
        telefono = request.form.get('telefono', os.environ.get('ORIGEN_LLAMADA', '968972418'))
        cantidad = int(request.form.get('cantidad', 3))  # 3 llamadas por defecto

        hora_base = datetime.now()

        for i in range(cantidad):
            hora_llamada = hora_base + timedelta(minutes=5 * i)
            mensaje = f"Prueba de llamada {i+1}" #Simple message

            # Crear recordatorio temporal
            recordatorio = Recordatorio(
                user_id=current_user.id,
                nombre=f"Prueba Sistema #{i+1}",
                telefono=telefono,
                fecha=hora_llamada.date(),
                hora=hora_llamada.time(),
                mensaje=mensaje,
                tipo="prueba",
                repeticion="0"
            )
            db.session.add(recordatorio)
            db.session.flush()

            # Crear registro de llamada
            registro = RegistroLlamada(
                recordatorio_id=recordatorio.id,
                estado='programada',
                intentos=0,
                fecha_llamada=hora_llamada
            )
            db.session.add(registro)

        db.session.commit()
        flash(f'Se han programado {cantidad} llamadas de prueba espaciadas cada 5 minutos', 'success')

        return redirect(url_for('main.dashboard'))

    except Exception as e:
        logger.error(f"Error al programar llamadas de prueba: {str(e)}")
        logger.exception("Stacktrace completo:")
        db.session.rollback()
        flash('Error al programar las llamadas de prueba', 'danger')
        return redirect(url_for('main.dashboard'))

@test_calls_bp.route('/formulario-pruebas')
@login_required
def formulario_pruebas():
    """Muestra el formulario para programar llamadas de prueba"""
    return render_template(
        'formulario_pruebas.html',
        telefono_defecto=os.environ.get('ORIGEN_LLAMADA', '968972418')
    )