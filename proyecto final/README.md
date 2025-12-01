# Flask RetoHabits - Configuración MySQL (XAMPP)
Archivos incluidos:
- app.py (aplicación Flask usando flask-login)
- db_setup.py (script para crear la base de datos y tablas)
- instance/config.example.json (ejemplo de configuración para conectarse a MySQL)
- templates/ (HTML)
- static/ (CSS)

Pasos para usar con XAMPP (Windows / macOS / Linux con XAMPP):
1. Asegúrate de que MySQL está corriendo en XAMPP (panel de control XAMPP).
2. Copia `instance/config.example.json` a `instance/config.json` y ajusta `user` y `password` si tu XAMPP usa uno.
3. Instala dependencias (recomendado en un virtualenv):
   ```bash
   pip install -r requirements.txt
   ```
4. Ejecuta el script para crear la base de datos y tablas:
   ```bash
   python db_setup.py
   ```
   Nota: db_setup.py inserta retos de ejemplo. Para añadir un admin con contraseña, reemplaza el placeholder en el archivo o usa la ruta /register.
5. Ejecuta la aplicación Flask:
   ```bash
   python app.py
   ```
6. Abre http://localhost:5000 en tu navegador.

Seguridad / Notas:
- Cambia `FLASK_SECRET` en producción.
- Usa contraseñas seguras y habilita SSL si expones la app públicamente.
