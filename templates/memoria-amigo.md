# Memoria del Proyecto: Amigo

## Resumen del proyecto
Este proyecto tiene como objetivo desarrollar una aplicación que permita gestionar y automatizar llamadas telefónicas utilizando la API de Netelip. La solución está orientada a apoyar iniciativas sociales y mejorar procesos de comunicación.

## Estado actual del proyecto

### Configuración del entorno
1. **Dependencias instaladas con Poetry:**
   - Flask
   - Flask-SQLAlchemy
   - Flask-Login
   - Flask-Mail
   - Flask-Migrate
   - Flask-WTF
   - Requests

2. **Archivo `pyproject.toml`:**
   - Configurado correctamente para Python 3.9.
   - Incluye todas las dependencias necesarias.

3. **Archivos clave en el proyecto:**
   - `main.py`: Contiene la lógica principal de la aplicación Flask.
   - `utils/netelip_integration.py`: Maneja la integración con la API de Netelip.
   - `.replit`: Configurado para usar Poetry y correr el proyecto en Replit.

### Configuración de Netelip
1. Credenciales configuradas:
   - **Token:** Validado y en formato correcto.
   - **API ID:** Configurado correctamente.
   - **Número de origen:** Formato internacional.

2. Verificación de credenciales:
   - Comando usado:
     ```bash
     poetry run python3 -c "from utils.netelip_integration import verificar_credenciales; print(verificar_credenciales())"
     ```
   - Resultado: `(True, 'Credenciales válidas')`.

---

## Próximos pasos
1. Probar llamadas reales con los datos configurados en Netelip.
2. Desarrollar la lógica para manejar intentos fallidos y reintentos automáticos.
3. Implementar pruebas de integración para asegurar la estabilidad del sistema.

---

## Notas importantes
- El entorno está basado en Replit, con Poetry manejando dependencias.
- El proyecto utiliza variables de entorno para mayor seguridad:
  - Token y API ID configurados como secretos en Replit.
- Para ejecutar el proyecto:
  ```bash
  poetry run python3 main.py

  23/12/2024

  ### **Cómo seguir actualizando la memoria**
  - Cada vez que avances, añade un resumen en la sección **"Próximos pasos"** o **"Notas importantes"**.
  - Incluye logs de éxito o errores relevantes para llevar un historial claro.

  ¡Espero que te sirva y que el proyecto siga avanzando con éxito