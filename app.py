from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from config import DB_CONFIG  # Asegúrate de tener tu configuración de DB aquí.
import os
from werkzeug.utils import secure_filename
import json
from uuid import uuid4

app = Flask(__name__)

# Configuración de Flask-Login
app.secret_key = 'mi_clave_secreta'
login_manager = LoginManager()
login_manager.init_app(app)

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Crear la carpeta si no existe
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS




# Función para cargar el usuario por su ID
@login_manager.user_loader
def load_user(user_id):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM usuarios WHERE id = %s', (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    if user:
        return User(user['id'], user['username'], user['role'])
    return None

# Clase User para Flask-Login
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id
        self.username = username
        self.role = role

    def get_id(self):
        return str(self.id)

# Conexión a la base de datos
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# Ruta de login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Buscar el usuario en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute('SELECT * FROM usuarios WHERE username = %s', (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password'], password):
            user_obj = User(user['id'], user['username'], user['role'])
            login_user(user_obj)
            return redirect(url_for('productos'))
        else:
            flash("Usuario o contraseña incorrectos", "danger")

    return render_template('login.html')

# Ruta de logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Ruta de productos
@app.route('/productos')
def productos():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM productos')
    productos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('productos.html', productos=productos)

# Ruta para agregar un producto (solo admin)
# Ruta para agregar un producto (solo admin)
@app.route('/agregar_producto', methods=['GET', 'POST'])
@login_required
def agregar_producto():
    if current_user.role != 'admin':
        return redirect(url_for('productos'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        imagenes = request.files.getlist('imagenes')  # Obtener todas las imágenes

        imagen_urls = []  # Lista para almacenar las rutas de las imágenes subidas

        # Guardar la primera imagen
        if 'imagen' in request.files:
            imagen = request.files['imagen']
            if imagen and allowed_file(imagen.filename):
                filename = secure_filename(imagen.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                imagen.save(filepath)
                imagen_urls.append(f'static/uploads/{filename}')

        # Guardar imágenes adicionales (si es necesario)
        for imagen in imagenes:
            if imagen and allowed_file(imagen.filename):
                filename = secure_filename(imagen.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                imagen.save(filepath)
                imagen_urls.append(f'static/uploads/{filename}')

        # Convertir la lista de URLs de imágenes a JSON
        imagenes_json = json.dumps(imagen_urls)

        # Insertar el producto en la base de datos
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO productos (nombre, descripcion, precio, imagenes) VALUES (%s, %s, %s, %s)',
                       (nombre, descripcion, precio, imagenes_json))
        conn.commit()
        cursor.close()
        conn.close()

        flash("Producto agregado correctamente", "success")
        return redirect(url_for('productos'))

    return render_template('agregar_producto.html')


# Ruta para editar un producto (solo admin)
# Ruta para editar un producto (solo admin)
@app.route('/editar_producto/<int:producto_id>', methods=['GET', 'POST'])
@login_required
def editar_producto(producto_id):
    if current_user.role != 'admin':
        return redirect(url_for('productos'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM productos WHERE id = %s', (producto_id,))
    producto = cursor.fetchone()

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']

        # Manejo del archivo de imagen
        imagenes = request.files.getlist('imagenes')
        imagen_urls = json.loads(producto['imagenes'])  # Cargar las imágenes existentes

        # Guardar imágenes nuevas
        for imagen in imagenes:
            if imagen and allowed_file(imagen.filename):
                filename = secure_filename(imagen.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                imagen.save(filepath)
                imagen_urls.append(f'static/uploads/{filename}')

        # Convertir la lista de URLs de imágenes a JSON
        imagenes_json = json.dumps(imagen_urls)

        # Actualizar el producto en la base de datos
        cursor.execute('UPDATE productos SET nombre = %s, descripcion = %s, precio = %s, imagenes = %s WHERE id = %s',
                       (nombre, descripcion, precio, imagenes_json, producto_id))
        conn.commit()
        flash("Producto actualizado correctamente", "success")
        return redirect(url_for('productos'))

    cursor.close()
    conn.close()
    return render_template('editar_producto.html', producto=producto)


# Ruta para eliminar un producto (solo admin)
@app.route('/eliminar_producto/<int:producto_id>')
@login_required
def eliminar_producto(producto_id):
    if current_user.role != 'admin':
        return redirect(url_for('productos'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM productos WHERE id = %s', (producto_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Producto eliminado correctamente", "success")
    return redirect(url_for('productos'))

@app.route('/ver_producto/<int:producto_id>')
def ver_producto(producto_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM productos WHERE id = %s', (producto_id,))
    producto = cursor.fetchone()

    if producto:
        producto['imagenes'] = json.loads(producto['imagenes'])
    conn.close()

    return render_template('ver_producto.html', producto=producto)

if __name__ == '__main__':
    app.run(debug=True)
