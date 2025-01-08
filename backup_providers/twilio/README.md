# Backup de Integración Twilio

Este directorio contiene un respaldo completo de la integración con Twilio que fue reemplazada por Netelip.

## Archivos Respaldados

- `twilio_integration.py`: Integración principal con la API de Twilio
- `test_twilio.py`: Scripts de prueba para la integración
- `twilio_diagnostico.html`: Plantilla para diagnóstico de la integración
- `twilio_migration.py`: Migraciones de base de datos relacionadas

## Credenciales Necesarias

La integración requiere las siguientes variables de entorno:
- TWILIO_ACCOUNT_SID
- TWILIO_AUTH_TOKEN
- TWILIO_PHONE_NUMBER

## Funcionalidades Implementadas

- Realización de llamadas automáticas con TTS
- Verificación de estado de llamadas
- Sistema de reintentos automáticos
- Panel de diagnóstico
- Callbacks para actualización de estado

## Notas de Implementación

La integración usa la biblioteca oficial de Twilio para Python y garantiza:
- Duración mínima de llamadas (15 segundos por defecto)
- Formateo automático de números telefónicos
- Manejo de errores y reintentos
- Registro detallado de cada llamada

## Fecha de Backup

22 de Diciembre de 2024