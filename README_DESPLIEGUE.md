# Despliegue del Dashboard INSPOL en cPanel (Neubox)

## Archivos incluidos
- Código completo de la aplicación Flask.
- Plantillas HTML, archivos estáticos (PDF, imágenes).
- `leads_10.csv`: leads de ejemplo para importar.
- `requirements.txt`: dependencias necesarias.

## Requisitos
- Python 3.9 o superior en el servidor.
- Acceso a cPanel con opción "Setup Python App".

## Pasos para desplegar

1. **Subir y extraer el ZIP**
   - En cPanel, ir a Administrador de Archivos.
   - Navegar a la carpeta deseada (ej. `/home/usuario/dashboard`).
   - Subir el ZIP y extraerlo.

2. **Crear aplicación Python**
   - En cPanel, buscar "Setup Python App".
   - Crear nueva aplicación:
     - Versión Python: 3.9+
     - Directorio: la carpeta extraída.
     - URI: ruta de acceso (ej. `dashboard` o un subdominio).
     - Archivo WSGI: `app.py` (la variable Flask se llama `app`).

3. **Instalar dependencias**
   - En la terminal de cPanel o en la opción "Run pip install", ejecutar:
     ```
     pip install -r requirements.txt
     ```
   - Este paso dura menos de 1 minuto.

4. **Configurar variables de entorno**
   - En el archivo WSGI (o en la configuración de la app), añadir al inicio:
     ```python
     import os
     os.environ['OPENAI_API_KEY'] = 'sk-...'   # Reemplazar con la clave real
     ```

5. **Crear archivo `config_user.json`**
   - Crear un archivo `config_user.json` en la misma carpeta con el siguiente contenido (ajustar datos reales):
     ```json
     {
         "smtp_host": "65.99.252.38",
         "smtp_port": 587,
         "smtp_user": "ventas@inspol.com.mx",
         "smtp_password": "CONTRASEÑA_REAL",
         "default_sender_name": "INSPOL México",
         "default_sender_email": "ventas@inspol.com.mx",
         "tracking_base_url": "https://URL_DEL_DASHBOARD"
     }
     ```
   - Cambiar `CONTRASEÑA_REAL` por la contraseña SMTP correcta.
   - Poner en `tracking_base_url` la URL pública que tendrá el dashboard (ej. `https://dashboard.inspol.com.mx`). Si no se desea tracking aún, dejar `null` o eliminar esa línea.

6. **Reiniciar la aplicación**
   - En "Setup Python App", hacer clic en Restart.

7. **Probar**
   - Acceder a la URL configurada. Debe aparecer el dashboard.
   - Ir a "Leads" y hacer clic en "Importar CSV" para cargar `leads_10.csv`.
   - Probar envío de correo de prueba.

## Activación del tracking (opcional)
El tracking de clics se activa automáticamente si `tracking_base_url` está configurado. No se requiere modificar código adicional (la función `enviar_prueba` ya lo soporta).

## Notas
- La base de datos SQLite (`dashboard.db`) se crea automáticamente al iniciar la app.
- Para producción se recomienda migrar a MySQL (consultar con el desarrollador).
- Asegurar que el DKIM esté activo en cPanel (Email Deliverability) para evitar que los correos vayan a spam.

---
Cualquier duda, contactar al equipo de desarrollo.
