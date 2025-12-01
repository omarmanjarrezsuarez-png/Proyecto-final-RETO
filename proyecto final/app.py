from flask import Flask, render_template, redirect, url_for, request, flash, send_file, abort, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import mysql.connector, json, os, io, csv
from datetime import date, datetime, timedelta

try:
    from fpdf import FPDF
    HAVE_FPDF = True
except Exception:
    HAVE_FPDF = False

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret-key')

def load_cfg():
    cfg_path = os.path.join(app.instance_path, 'config.json')
    if os.path.exists(cfg_path):
        with open(cfg_path,'r') as f:
            return json.load(f)
    return {'host':'127.0.0.1','user':'root','password':'','database':'reto_habitos','port':3306}

CFG = load_cfg()

def get_db():
    return mysql.connector.connect(
        host=CFG['host'],
        user=CFG['user'],
        password=CFG['password'],
        database=CFG['database'],
        port=CFG['port']
    )

def role_required(*allowed_roles):
    """
    Uso: @role_required('admin') o @role_required('coach','admin')
    allowed_roles acepta strings: 'admin', 'user', 'coach'
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("Debes iniciar sesión primero", "warning")
                return redirect(url_for('login'))
            if not hasattr(current_user, 'role'):
                if getattr(current_user, 'role_id', None) == 1:
                    return f(*args, **kwargs)
                flash("No tienes permisos para acceder a esta sección", "danger")
                return redirect(url_for('dashboard'))
            if current_user.role not in allowed_roles:
                flash("No tienes permisos para acceder a esta sección", "danger")
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

login_manager = LoginManager(app)
login_manager.login_view = 'login'

ROLE_MAP = {1: 'admin', 2: 'user', 3: 'coach'}

class User(UserMixin):
    def __init__(self, id, username, display_name, role_id, points, level):
        self.id = str(id)
        self.username = username
        self.display_name = display_name or username
        self.role_id = role_id
        self.role = ROLE_MAP.get(role_id, 'user')
        self.points = points or 0
        self.level = level or 1

@login_manager.user_loader
def load_user(user_id):
    try:
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("SELECT id, username, display_name, role_id, points, level FROM users WHERE id=%s", (int(user_id),))
        row = cur.fetchone()
        cur.close(); db.close()
        if not row:
            return None
        return User(row['id'], row['username'], row.get('display_name'), row['role_id'], row.get('points',0), row.get('level',1))
    except Exception as e:
        print('load_user error', e)
        return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        display = request.form.get('display_name') or username
        role_txt = request.form.get('role','Usuario')
        role_map = {'Admin':1,'Usuario':2,'Coach':3}
        role_id = role_map.get(role_txt,2)
        if not username or not password:
            flash('Complete todos los campos','warning'); return redirect(url_for('register'))
        pwd_hash = generate_password_hash(password)
        try:
            db = get_db(); cur = db.cursor()
            cur.execute("INSERT INTO users (username,password,display_name,role_id) VALUES (%s,%s,%s,%s)",
                        (username, pwd_hash, display, role_id))
            db.commit(); cur.close(); db.close()
            flash('Cuenta creada. Inicia sesión.','success'); return redirect(url_for('login'))
        except mysql.connector.errors.IntegrityError:
            flash('El nombre de usuario ya existe','danger'); return redirect(url_for('register'))
        except Exception as e:
            flash(f'Error: {e}','danger'); return redirect(url_for('register'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        db = get_db(); cur = db.cursor(dictionary=True)
        cur.execute("SELECT id,username,password,display_name,role_id,points,level FROM users WHERE username=%s",(username,))
        row = cur.fetchone(); cur.close(); db.close()
        if not row or not check_password_hash(row['password'], password):
            flash('Usuario o contraseña incorrectos','danger'); return redirect(url_for('login'))
        user = User(row['id'], row['username'], row.get('display_name'), row['role_id'], row.get('points',0), row.get('level',1))
        login_user(user)
        flash('Bienvenido','success')
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada','info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    uid = int(current_user.id)
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS total_public FROM retos WHERE publico=1")
    total_public = cur.fetchone().get('total_public',0)
    cur.execute("SELECT COUNT(*) AS total FROM participantes WHERE user_id=%s", (uid,))
    retos_activos = cur.fetchone().get('total',0)
    cur.execute("SELECT points, level FROM users WHERE id=%s", (uid,))
    row = cur.fetchone()
    puntos = row.get('points',0) if row else 0
    nivel = row.get('level',1) if row else 1
    cur.execute("""
       SELECT r.titulo AS reto, p.fecha, p.completado
       FROM progreso p
       JOIN retos r ON r.id = p.reto_id
       WHERE p.user_id=%s
       ORDER BY p.fecha DESC
       LIMIT 10
    """, (uid,))
    progreso = cur.fetchall()
    cur.execute("""
       SELECT r.id, r.titulo, r.descripcion, p.fecha_union, r.creador_id, r.puntos_por_dia
       FROM retos r
       LEFT JOIN participantes p ON p.reto_id = r.id AND p.user_id=%s
       WHERE r.publico=1 OR r.creador_id=%s
       ORDER BY r.created_at DESC
    """, (uid, uid))
    retos = cur.fetchall()
    cur.close(); db.close()
    progreso_list = [{'reto': row['reto'], 'fecha': row['fecha'].isoformat() if isinstance(row['fecha'], (date,datetime)) else str(row['fecha']), 'completado': bool(row['completado'])} for row in progreso]
    return render_template('dashboard.html',
                           total_public=total_public,
                           retos_activos=retos_activos,
                           puntos_totales=puntos,
                           nivel=nivel,
                           progreso=progreso_list,
                           retos=retos
                          )

@app.route('/retos/nuevo', methods=['GET','POST'])
@login_required
@role_required('coach', 'admin')
def crear_reto():
    if request.method == 'POST':
        titulo = request.form.get('titulo','').strip()
        descripcion = request.form.get('descripcion','').strip()
        duracion = int(request.form.get('duracion',7))
        publico = 1 if request.form.get('publico')=='on' else 0
        db = get_db(); cur = db.cursor()
        cur.execute("INSERT INTO retos (titulo, descripcion, duracion, publico, creador_id, puntos_por_dia) VALUES (%s,%s,%s,%s,%s,%s)",
                    (titulo, descripcion, duracion, publico, int(current_user.id), int(request.form.get('puntos_por_dia',10))))
        db.commit(); cur.close(); db.close()
        flash('Reto creado','success'); return redirect(url_for('dashboard'))
    return render_template('crear_reto.html')

@app.route('/retos/<int:reto_id>/unirse', methods=['POST'])
@login_required
@role_required('user', 'coach', 'admin')
def unirse_reto(reto_id):
    uid = int(current_user.id)
    db = get_db(); cur = db.cursor()
    try:
        cur.execute("INSERT INTO participantes (user_id, reto_id) VALUES (%s,%s)", (uid, reto_id))
        db.commit()
    except mysql.connector.errors.IntegrityError:
        pass
    cur.close(); db.close()
    flash('Te uniste al reto','success')
    return redirect(url_for('dashboard'))

@app.route('/retos/<int:reto_id>/abandonar', methods=['POST'])
@login_required
@role_required('user', 'coach', 'admin')
def abandonar_reto(reto_id):
    uid = int(current_user.id)
    db = get_db(); cur = db.cursor()
    cur.execute("DELETE FROM participantes WHERE user_id=%s AND reto_id=%s", (uid, reto_id))
    db.commit(); cur.close(); db.close()
    flash('Has abandonado el reto','info')
    return redirect(url_for('dashboard'))

@app.route('/participantes/<int:reto_id>')
def participantes(reto_id):
    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM retos WHERE id = %s", (reto_id,))
    reto = cur.fetchone()

    if not reto:
        cur.close()
        return "Reto no encontrado"

    cur.execute("""
        SELECT usuarios.nombre, usuarios.email
        FROM participantes
        JOIN usuarios ON participantes.usuario_id = usuarios.id
        WHERE participantes.reto_id = %s
    """, (reto_id,))
    lista_participantes = cur.fetchall()

    cur.close()

    return render_template(
        "participantes.html",
        reto=reto,                     
        participantes=lista_participantes
    )

@app.route('/retos/<int:reto_id>/editar', methods=['GET', 'POST'])
@login_required
@role_required('coach', 'admin')
def editar_reto(reto_id):
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM retos WHERE id=%s", (reto_id,))
    reto = cur.fetchone()
    if not reto:
        cur.close(); db.close(); abort(404)
    if not (current_user.role == 'admin' or reto['creador_id'] == int(current_user.id)):
        cur.close(); db.close(); flash('No tienes permiso para editar este reto','danger'); return redirect(url_for('dashboard'))

    if request.method == 'POST':
        titulo = request.form.get('titulo','').strip()
        descripcion = request.form.get('descripcion','').strip()
        duracion = int(request.form.get('duracion', reto.get('duracion',7)))
        publico = 1 if request.form.get('publico')=='on' else 0
        puntos_por_dia = int(request.form.get('puntos_por_dia', reto.get('puntos_por_dia',10)))
        cur.execute("UPDATE retos SET titulo=%s, descripcion=%s, duracion=%s, publico=%s, puntos_por_dia=%s WHERE id=%s",
                    (titulo, descripcion, duracion, publico, puntos_por_dia, reto_id))
        db.commit(); cur.close(); db.close()
        flash('Reto actualizado','success'); return redirect(url_for('detalle_reto', reto_id=reto_id))

    cur.close(); db.close()
    return render_template('editar_reto.html', reto=reto)

@app.route('/retos/<int:reto_id>/eliminar', methods=['POST'])
@login_required
@role_required('coach', 'admin')
def eliminar_reto(reto_id):
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT creador_id FROM retos WHERE id=%s", (reto_id,))
    r = cur.fetchone()
    if not r:
        cur.close(); db.close(); flash('Reto no encontrado','danger'); return redirect(url_for('dashboard'))
    if not (current_user.role == 'admin' or r['creador_id'] == int(current_user.id)):
        cur.close(); db.close(); flash('No tienes permiso para eliminar este reto','danger'); return redirect(url_for('dashboard'))
    cur.close(); db.close()
    db = get_db(); cur = db.cursor()
    cur.execute("DELETE FROM retos WHERE id=%s", (reto_id,))
    db.commit(); cur.close(); db.close()
    flash('Reto eliminado','info')
    return redirect(url_for('dashboard'))

@app.route('/retos/<int:reto_id>/participantes')
@login_required
@role_required('coach', 'admin')
def ver_participantes(reto_id):
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT creador_id FROM retos WHERE id=%s", (reto_id,))
    r = cur.fetchone()
    if not r:
        cur.close(); db.close(); abort(404)
    if not (current_user.role == 'admin' or r['creador_id'] == int(current_user.id)):
        cur.close(); db.close(); flash('No tienes permiso para ver participantes','danger'); return redirect(url_for('dashboard'))
    cur.execute("""
        SELECT u.id, u.username, u.display_name, p.fecha_union
        FROM participantes p
        JOIN users u ON u.id = p.user_id
        WHERE p.reto_id=%s
        ORDER BY p.fecha_union DESC
    """, (reto_id,))
    participants = cur.fetchall()
    cur.close(); db.close()
    return render_template('participantes.html', participantes=participants, reto_id=reto_id)

@app.route('/reto/<int:reto_id>')
@login_required
@role_required('user', 'coach', 'admin')
def detalle_reto(reto_id):
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM retos WHERE id=%s", (reto_id,))
    reto = cur.fetchone()
    if not reto: cur.close(); db.close(); abort(404)
    cur.execute("SELECT 1 FROM participantes WHERE user_id=%s AND reto_id=%s", (int(current_user.id), reto_id))
    en = cur.fetchone() is not None
    cur.execute("SELECT c.*, u.username FROM comentarios c JOIN users u ON c.user_id=u.id WHERE c.reto_id=%s ORDER BY c.created_at DESC", (reto_id,))
    comentarios = cur.fetchall()
    cur.close(); db.close()
    return render_template('detalle_reto.html', reto=reto, en_participacion=en, comentarios=comentarios, today=date.today().isoformat())

@app.route('/reto/<int:reto_id>/marcar', methods=['POST'])
@login_required
@role_required('user', 'coach', 'admin')
def marcar_progreso(reto_id):
    fecha = request.form.get('fecha') or date.today().isoformat()
    completado = 1 if request.form.get('completado') else 0
    uid = int(current_user.id)
    db = get_db(); cur = db.cursor()
    try:
        cur.execute("INSERT INTO progreso (user_id, reto_id, fecha, completado) VALUES (%s,%s,%s,%s)", (uid, reto_id, fecha, completado))
    except mysql.connector.errors.IntegrityError:
        cur.execute("UPDATE progreso SET completado=%s WHERE user_id=%s AND reto_id=%s AND fecha=%s", (completado, uid, reto_id, fecha))
    if completado:
        cur.execute("SELECT puntos_por_dia FROM retos WHERE id=%s", (reto_id,))
        r = cur.fetchone()
        puntos_add = r[0] if r else 0
        cur.execute("UPDATE users SET points = points + %s WHERE id=%s", (puntos_add, uid))
    db.commit(); cur.close(); db.close()
    flash('Progreso guardado','success')
    return redirect(url_for('detalle_reto', reto_id=reto_id))

@app.route('/reto/<int:reto_id>/comentar', methods=['POST'])
@login_required
@role_required('user', 'coach', 'admin')
def comentar_reto(reto_id):
    msg = request.form.get('mensaje','').strip()
    if not msg:
        flash('Escribe un mensaje','warning'); return redirect(url_for('detalle_reto', reto_id=reto_id))
    db = get_db(); cur = db.cursor()
    cur.execute("INSERT INTO comentarios (user_id, reto_id, mensaje) VALUES (%s,%s,%s)", (int(current_user.id), reto_id, msg))
    db.commit(); cur.close(); db.close()
    flash('Comentario publicado','success')
    return redirect(url_for('detalle_reto', reto_id=reto_id))

@app.route('/perfil', methods=['GET','POST'])
@login_required
@role_required('user', 'coach', 'admin')
def perfil():
    if request.method == 'POST':
        display = request.form.get('display_name')
        pwd = request.form.get('password')
        db = get_db(); cur = db.cursor()
        if display:
            cur.execute("UPDATE users SET display_name=%s WHERE id=%s", (display, int(current_user.id)))
        if pwd:
            cur.execute("UPDATE users SET password=%s WHERE id=%s", (generate_password_hash(pwd), int(current_user.id)))
        db.commit(); cur.close(); db.close()
        flash('Perfil actualizado','success'); return redirect(url_for('perfil'))
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT l.* FROM logros l JOIN user_logros ul ON ul.logro_id=l.id WHERE ul.user_id=%s", (int(current_user.id),))
    logros = cur.fetchall()
    cur.close(); db.close()
    return render_template('perfil.html', logros=logros)

@app.route('/logros')
@login_required
@role_required('user', 'coach', 'admin')
def ver_logros():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT l.*, (SELECT 1 FROM user_logros ul WHERE ul.user_id=%s AND ul.logro_id=l.id) AS obtenido FROM logros l", (int(current_user.id),))
    logros = cur.fetchall(); cur.close(); db.close()
    return render_template('logros.html', logros=logros)

@app.route('/logro/<int:logro_id>/intentar', methods=['POST'])
@login_required
@role_required('user', 'coach', 'admin')
def intentar_logro(logro_id):
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT puntos FROM logros WHERE id=%s", (logro_id,))
    L = cur.fetchone()
    if not L:
        flash('Logro no existe','danger'); return redirect(url_for('ver_logros'))
    cur.execute("SELECT points FROM users WHERE id=%s", (int(current_user.id),))
    pts = cur.fetchone().get('points',0)
    if pts >= L['puntos']:
        try:
            cur.execute("INSERT INTO user_logros (user_id, logro_id) VALUES (%s,%s)", (int(current_user.id), logro_id))
            cur.execute("UPDATE users SET points = points - %s WHERE id=%s", (L['puntos'], int(current_user.id)))
            db.commit(); flash('Logro obtenido!', 'success')
        except mysql.connector.errors.IntegrityError:
            flash('Ya tienes este logro','info')
    else:
        flash('No tienes suficientes puntos','warning')
    cur.close(); db.close()
    return redirect(url_for('ver_logros'))

@app.route('/coach/mis_retos')
@login_required
@role_required('coach', 'admin')
def coach_mis_retos():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT * FROM retos WHERE creador_id=%s ORDER BY created_at DESC", (int(current_user.id),))
    retos = cur.fetchall()
    cur.close(); db.close()
    return render_template('coach_mis_retos.html', retos=retos)

@app.route('/admin')
@login_required
@role_required('admin')
def admin_dashboard():
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("SELECT id, username, display_name, role_id, points FROM users")
    users = cur.fetchall()
    cur.execute("SELECT r.*, u.username AS creador FROM retos r LEFT JOIN users u ON u.id=r.creador_id ORDER BY r.created_at DESC")
    retos = cur.fetchall()
    cur.close(); db.close()
    return render_template('admin_dashboard.html', users=users, retos=retos)

@app.route('/admin/reto/<int:reto_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_reto(reto_id):
    db = get_db(); cur = db.cursor(); cur.execute("DELETE FROM retos WHERE id=%s", (reto_id,))
    db.commit(); cur.close(); db.close()
    flash('Reto eliminado','info'); return redirect(url_for('admin_dashboard'))

@app.route('/admin/user/<int:user_id>/reset_points', methods=['POST'])
@login_required
@role_required('admin')
def admin_reset_points(user_id):
    db = get_db(); cur = db.cursor(); cur.execute("UPDATE users SET points=0, level=1 WHERE id=%s", (user_id,))
    db.commit(); cur.close(); db.close()
    flash('Puntos reseteados','success'); return redirect(url_for('admin_dashboard'))

@app.route('/admin/logro/crear', methods=['POST'])
@login_required
@role_required('admin')
def admin_crear_logro():
    codigo = request.form.get('codigo'); nombre = request.form.get('nombre'); descripcion = request.form.get('descripcion'); puntos = int(request.form.get('puntos',0))
    db = get_db(); cur = db.cursor()
    try:
        cur.execute("INSERT INTO logros (codigo, nombre, descripcion, puntos) VALUES (%s,%s,%s,%s)", (codigo, nombre, descripcion, puntos))
        db.commit(); flash('Logro creado','success')
    except mysql.connector.errors.IntegrityError:
        flash('Código de logro ya existe','danger')
    finally:
        cur.close(); db.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logro/<int:logro_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_logro(logro_id):
    db = get_db(); cur = db.cursor(); cur.execute("DELETE FROM logros WHERE id=%s", (logro_id,))
    db.commit(); cur.close(); db.close()
    flash('Logro eliminado','info'); return redirect(url_for('admin_dashboard'))

@app.route('/reportes/csv')
@login_required
def reportes_csv():
    uid = int(current_user.id)
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("""
      SELECT r.titulo AS reto, p.fecha, p.completado
      FROM progreso p
      JOIN retos r ON r.id=p.reto_id
      WHERE p.user_id=%s
      ORDER BY p.fecha DESC
    """, (uid,))
    rows = cur.fetchall(); cur.close(); db.close()
    si = io.StringIO(); writer = csv.writer(si)
    writer.writerow(['reto','fecha','completado'])
    for row in rows:
        writer.writerow([row['reto'], row['fecha'].isoformat() if isinstance(row['fecha'], (date,datetime)) else str(row['fecha']), row['completado']])
    mem = io.BytesIO(); mem.write(si.getvalue().encode('utf-8')); mem.seek(0)
    return send_file(mem, as_attachment=True, download_name='reporte_progreso.csv', mimetype='text/csv')

@app.route('/reportes/pdf')
@login_required
def reportes_pdf():
    """
    Genera un PDF simple con el progreso del usuario.
    Usa FPDF si está disponible, sino devuelve el CSV como fallback.
    """
    if not HAVE_FPDF:
        flash('FPDF no está instalado en el servidor. Se descargará CSV como alternativa.', 'warning')
        return redirect(url_for('reportes_csv'))

    uid = int(current_user.id)
    db = get_db(); cur = db.cursor(dictionary=True)
    cur.execute("""
      SELECT r.titulo AS reto, p.fecha, p.completado
      FROM progreso p
      JOIN retos r ON r.id=p.reto_id
      WHERE p.user_id=%s
      ORDER BY p.fecha DESC
    """, (uid,))
    rows = cur.fetchall()
    cur.close(); db.close()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Reporte de Progreso", ln=1, align='C')
    pdf.ln(4)
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 8, f"Usuario: {current_user.username}", ln=1)
    pdf.cell(0, 8, f"Fecha: {date.today().isoformat()}", ln=1)
    pdf.ln(6)

    if not rows:
        pdf.cell(0, 8, "No hay registros de progreso.", ln=1)
    else:
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(90, 8, "Reto", border=1)
        pdf.cell(40, 8, "Fecha", border=1)
        pdf.cell(40, 8, "Completado", border=1, ln=1)
        pdf.set_font("Arial", size=10)
        for r in rows:
            titulo = (r['reto'][:45] + '...') if len(r['reto'])>48 else r['reto']
            fecha = r['fecha'].isoformat() if isinstance(r['fecha'], (date,datetime)) else str(r['fecha'])
            estado = "Sí" if r['completado'] else "No"
            pdf.cell(90, 7, titulo, border=1)
            pdf.cell(40, 7, fecha, border=1)
            pdf.cell(40, 7, estado, border=1, ln=1)

    output = pdf.output(dest='S').encode('latin1')
    response = make_response(output)
    response.headers.set('Content-Type', 'application/pdf')
    response.headers.set('Content-Disposition', 'attachment', filename='reporte_progreso.pdf')
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
