import logging.handlers
import os
from datetime import datetime
from flask import Blueprint, jsonify, render_template, Response, request
from flask_login import login_required, current_user
from sqlalchemy import not_
from models import NotificacionLlamada, RegistroLlamada, Recordatorio
from extensions import db
from utils.call_providers import gestor_proveedores
from utils.connection_diagnostics import diagnostics
import json

# Configurar logging específico para notificaciones
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Crear un manejador para los logs de notificaciones
if not os.path.exists('logs/notifications'):
    os.makedirs('logs/notifications')

file_handler = logging.handlers.RotatingFileHandler(
    'logs/notifications/notifications.log',
    maxBytes=10485760,  # 10MB
    backupCount=5,
    encoding='utf-8'
)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

notificaciones_bp = Blueprint('notificaciones', __name__)

@notificaciones_bp.route('/monitor-updates')
@login_required
def monitor_updates():
    def generate():
        try:
            while True:
                # Query base optimizada con joins
                query_base = RegistroLlamada.query.join(
                    Recordatorio,
                    RegistroLlamada.recordatorio_id == Recordatorio.id
                )

                if not current_user.es_admin:
                    query_base = query_base.filter(
                        Recordatorio.user_id == current_user.id
                    )

                # Obtener diagnóstico de conexiones
                system_status = diagnostics.get_system_status()

                # Obtener notificaciones pendientes
                notificaciones_pendientes = NotificacionLlamada.query.join(
                    Recordatorio
                ).filter(
                    NotificacionLlamada.leida == False,
                    Recordatorio.user_id == current_user.id if not current_user.es_admin else True
                ).order_by(
                    NotificacionLlamada.fecha_creacion.desc()
                ).limit(5).all()

                # Obtener estadísticas
                estadisticas = {
                    'activas': query_base.filter_by(estado='en_curso').count(),
                    'completadas': query_base.filter_by(estado='completada').count(),
                    'pendientes': query_base.filter(
                        not_(RegistroLlamada.estado.in_(['completada', 'fallida', 'en_curso']))
                    ).count(),
                    'system_status': system_status,
                    'proveedores': {
                        'netelip': gestor_proveedores.verificar_estado_netelip()
                    }
                }

                # Preparar datos de notificaciones
                notificaciones_data = []
                for notif in notificaciones_pendientes:
                    notificaciones_data.append({
                        'id': notif.id,
                        'tipo': notif.tipo,
                        'mensaje': notif.mensaje,
                        'nivel': notif.nivel,
                        'fecha': notif.fecha_creacion.isoformat(),
                        'recordatorio_id': notif.recordatorio_id,
                        'datos_extra': notif.datos_extra
                    })

                # Obtener llamadas recientes
                recientes = query_base.order_by(
                    RegistroLlamada.fecha_llamada.desc()
                ).limit(10).all()

                # Preparar datos de llamadas recientes
                datos_recientes = []
                for llamada in recientes:
                    datos_recientes.append({
                        'id': llamada.id,
                        'estado': llamada.estado,
                        'estado_clase': 'success' if llamada.estado == 'completada'
                                    else 'warning' if llamada.estado == 'en_curso'
                                    else 'danger',
                        'telefono': llamada.recordatorio.telefono,
                        'duracion': llamada.duracion or 0,
                        'ultima_actualizacion': llamada.fecha_llamada.isoformat(),
                        'proveedor': llamada.proveedor or 'netelip'
                    })

                estadisticas['recientes'] = datos_recientes
                estadisticas['notificaciones'] = notificaciones_data

                yield f"data: {json.dumps(estadisticas)}\n\n"

                from time import sleep
                sleep(5)  # Actualizar cada 5 segundos

        except Exception as e:
            logger.error(f"Error en monitor_updates: {str(e)}")
            logger.exception("Stacktrace completo:")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )

@notificaciones_bp.route('/notificaciones')
@login_required
def listar_notificaciones():
    try:
        query = NotificacionLlamada.query
        if not current_user.es_admin:
            query = query.join(
                Recordatorio,
                NotificacionLlamada.recordatorio_id == Recordatorio.id
            ).filter(Recordatorio.user_id == current_user.id)

        notificaciones = query.filter_by(leida=False).order_by(
            NotificacionLlamada.fecha_creacion.desc()
        ).all()

        return render_template('notificaciones.html', notificaciones=notificaciones)
    except Exception as e:
        logger.error(f"Error al listar notificaciones: {str(e)}")
        return jsonify({'error': str(e)}), 500

@notificaciones_bp.route('/notificaciones/marcar_leida/<int:notificacion_id>')
@login_required
def marcar_leida(notificacion_id):
    try:
        notificacion = NotificacionLlamada.query.get_or_404(notificacion_id)

        # Verificar permisos
        if not current_user.es_admin:
            recordatorio = Recordatorio.query.get(notificacion.recordatorio_id)
            if recordatorio.user_id != current_user.id:
                return jsonify({'error': 'No autorizado'}), 403

        notificacion.marcar_como_leida()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error al marcar notificación como leída: {str(e)}")
        return jsonify({'error': str(e)}), 500

@notificaciones_bp.route('/webhooks/netelip/call-status', methods=['POST'])
def webhook_netelip():
    """Webhook para actualizaciones de estado de llamadas de Netelip"""
    if not request.headers.get('X-Netelip-Auth'):
        logger.warning('Intento de acceso no autorizado al webhook de Netelip', 
                      extra={'call_id': 'N/A', 'estado': 'error', 'proveedor': 'netelip'})
        return jsonify({'error': 'No autorizado'}), 401

    data = request.json
    call_id = data.get('call_id', 'N/A')
    estado = data.get('status')

    estado_mapping = {
        'INITIATED': 'iniciada',
        'RINGING': 'sonando',
        'ANSWERED': 'contestada',
        'COMPLETED': 'completada',
        'NO ANSWER': 'sin_respuesta',
        'FAILED': 'fallida',
        'BUSY': 'ocupado',
        'IN PROGRESS': 'en_curso'
    }

    estado_normalizado = estado_mapping.get(estado.upper(), 'desconocido')
    registro = RegistroLlamada.query.filter_by(id_llamada=call_id).first()

    # Registrar detalles de la llamada
    log_extra = {
        'call_id': call_id,
        'estado': estado_normalizado,
        'proveedor': 'netelip'
    }
    logger.info(
        f'Actualización de estado Netelip - Estado Original: {estado} -> Normalizado: {estado_normalizado}',
        extra=log_extra
    )

    if registro:
        # Registrar cambios de estado
        registro.estado = estado_normalizado
        registro.fecha_actualizacion = datetime.utcnow()

        # Si la llamada falló y hay reintentos disponibles
        if estado_normalizado in ['fallida', 'sin_respuesta'] and registro.intentos < 3:
            logger.warning(
                f'Llamada fallida, intentando con otro proveedor. Intento: {registro.intentos + 1}/3',
                extra=log_extra
            )
            registro.proveedor = 'twilio'  # Cambiar al proveedor de respaldo
            db.session.commit()

            resultado = gestor_proveedores.realizar_llamada(registro)
            if resultado:
                logger.info('Reintento con Twilio iniciado exitosamente', extra=log_extra)
            else:
                logger.error('Falló el reintento con Twilio', extra=log_extra)
        else:
            if estado_normalizado == 'completada':
                logger.info('Llamada completada exitosamente', extra=log_extra)
            elif estado_normalizado in ['fallida', 'sin_respuesta']:
                logger.error(
                    f'Llamada fallida definitivamente después de {registro.intentos} intentos',
                    extra=log_extra
                )

        # Crear notificación del cambio de estado
        NotificacionLlamada.crear_notificacion(
            recordatorio_id=registro.recordatorio_id,
            tipo=f'estado_llamada_{estado_normalizado}',
            mensaje=f'La llamada cambió a estado: {estado_normalizado}',
            nivel='info' if estado_normalizado in ['completada', 'contestada'] else 'warning',
            datos_extra={'call_id': call_id, 'estado_original': estado}
        )

        db.session.commit()
        logger.info('Cambios guardados en base de datos', extra=log_extra)
    else:
        logger.error(
            f'No se encontró registro para la llamada ID: {call_id}',
            extra=log_extra
        )

    return jsonify({'success': True})

@notificaciones_bp.route('/webhooks/twilio/call-status', methods=['POST'])
def webhook_twilio():
    """Webhook para actualizaciones de estado de llamadas de Twilio"""
    data = request.form
    call_sid = data.get('CallSid', 'N/A')
    estado = data.get('CallStatus')

    estado_mapping = {
        'initiated': 'iniciada',
        'ringing': 'sonando',
        'in-progress': 'en_curso',
        'completed': 'completada',
        'busy': 'ocupado',
        'failed': 'fallida',
        'no-answer': 'sin_respuesta'
    }

    log_extra = {
        'call_id': call_sid,
        'estado': estado,
        'proveedor': 'twilio'
    }
    logger.info(
        f'Recibida actualización de Twilio - Estado: {estado}',
        extra=log_extra
    )

    estado_normalizado = estado_mapping.get(estado.lower(), 'desconocido')
    registro = RegistroLlamada.query.filter_by(id_llamada=call_sid).first()

    if registro:
        logger.info(
            f'Encontrado registro de llamada - Recordatorio ID: {registro.recordatorio_id}',
            extra=log_extra
        )

        registro.estado = estado_normalizado
        registro.fecha_actualizacion = datetime.utcnow()

        # Registrar duración y costo si están disponibles
        duracion = data.get('CallDuration')
        if duracion:
            registro.duracion = int(duracion)
            logger.info(f'Duración de la llamada: {duracion} segundos', extra=log_extra)

        # Si la llamada falló y hay reintentos disponibles
        if estado_normalizado in ['fallida', 'sin_respuesta'] and registro.intentos < 3:
            logger.warning(
                f'Llamada fallida, intentando con otro proveedor. Intento: {registro.intentos + 1}/3',
                extra=log_extra
            )
            gestor_proveedores.realizar_llamada(registro)
        else:
            if estado_normalizado in ['fallida', 'sin_respuesta']:
                logger.error(
                    f'Llamada fallida definitivamente después de {registro.intentos} intentos',
                    extra=log_extra
                )
            elif estado_normalizado == 'completada':
                logger.info(
                    f'Llamada completada exitosamente - Duración: {registro.duracion}s',
                    extra=log_extra
                )

            NotificacionLlamada.crear_notificacion(
                recordatorio_id=registro.recordatorio_id,
                tipo=f'estado_llamada_{estado_normalizado}',
                mensaje=f'La llamada cambió a estado: {estado_normalizado}',
                nivel='info' if estado_normalizado in ['completada', 'en_curso'] else 'warning',
                datos_extra={'call_sid': call_sid, 'estado_original': estado}
            )

        db.session.commit()
        logger.info('Cambios guardados en base de datos', extra=log_extra)
    else:
        logger.error(
            f'No se encontró registro para la llamada SID: {call_sid}',
            extra=log_extra
        )

    return jsonify({'success': True})