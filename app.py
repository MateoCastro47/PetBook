# Importamos los módulos necesarios
from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import mysql.connector# Cliente para conectar a MySQL
from werkzeug.utils import secure_filename # Para manejar nombres seguros de archivo
from werkzeug.security import generate_password_hash, check_password_hash


# Creamos una instancia de la aplicación Flask
app = Flask(__name__)

app.secret_key = '******' # Cambia esto por una clave secreta real para tu aplicación

# Carpeta donde se guardarán las imágenes subidas por los usuarios
app.config['UPLOAD_FOLDER'] = 'static/images'

# ========================================
# Configuración de conexión a MySQL (phpMyAdmin)
# ========================================
db_config = {
    'host': '****',           # Dirección del servidor MySQL (localhost si es local)
    'user': '****',                # Usuario de MySQL (por defecto es "root" en XAMPP)
    'password': '******',            # Cambia esto por tu contraseña real de MySQL
    'database': '****'       # Nombre de la base de datos que creaste en phpMyAdmin
}

# ========================================
# Inicializar la base de datos y tabla si no existen
# ========================================
def init_db():
    # Conectamos usando la configuración anterior
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor()
    
    # Creamos la tabla de perfiles si no existe
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS perfiles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100),
            email VARCHAR(100),
            password VARCHAR(100),
            birthdate DATE,
            location VARCHAR(100),
            profile_image VARCHAR(255)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS publicaciones (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            pet_name VARCHAR(100),
            pet_breed VARCHAR(100),
            pet_age INT,
            image VARCHAR(255),
            caption TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES perfiles(id) ON DELETE CASCADE
        )
    """)
    
    # Guardamos los cambios y cerramos la conexión
    conn.commit()
    cursor.close()
    conn.close()

# Llamamos a la función para crear tabla al iniciar
init_db()

# Página de inicio
@app.route('/index')
def inicio():
    return render_template('index.html')

# ========================================
# Ruta para mostrar y procesar el formulario de crear perfil
# ========================================
@app.route('/crear', methods=['GET', 'POST'])
def crear_perfil():
    if request.method == 'POST':
        # Capturamos los datos enviados desde el formulario
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)      
        birthdate = request.form['birthdate']
        location = request.form['location']
        
        # Procesamos la imagen subida
        image_file = request.files['profileImage']
        image_name = secure_filename(image_file.filename)                     # Aseguramos el nombre del archivo
        image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_name))# Guardamos el archivo en disco

        # Insertamos los datos en la base de datos
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO perfiles (username, email, password, birthdate, location, profile_image) VALUES (%s, %s, %s, %s, %s, %s)", 
        (username, email, hashed_password, birthdate, location, image_name))

        session['user_id'] = cursor.lastrowid  # 🔑 Login automático
        conn.commit()
        cursor.close()
        conn.close()

        # Redirigimos al usuario a una página de éxito
        return redirect('/perfil-creado')
    
    # Si es GET, simplemente renderizamos el formulario HTML
    return render_template('crear.html')

# ========================================
# Página simple de confirmación
# ========================================
@app.route('/perfil-creado')
def perfil_creado():
    return """
    <html>
        <head>
            <meta http-equiv="refresh" content="2;url=/" />
        </head>
        <body>
            <h2>🎉 Perfil creado exitosamente</h2>
            <p>Redirigiendo a tu perfil...</p>
        </body>
    </html>
    """

# Página de confirmación
@app.route('/perfil')
def ver_perfil():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Conectamos a la base de datos y obtenemos el perfil del usuario

    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM perfiles WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()

    cursor.execute("SELECT * FROM publicaciones WHERE user_id = %s ORDER BY created_at DESC", (session['user_id'],))
    publicaciones = cursor.fetchall()

    cursor.close()
    conn.close()
    # Si no se encuentra el usuario, redirigimos al login

    return render_template('perfil.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM perfiles WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user:
            flash("Correo no encontrado", "email_error")
            return render_template('login.html', email=email)  # Mantiene el correo escrito
        elif not check_password_hash(user['password'], password):
            flash("Contraseña incorrecta", "password_error")
            return render_template('login.html', email=email)

        session['user_id'] = user['id']
        return redirect(url_for('ver_perfil'))
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM perfiles WHERE id = %s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template('index.html', user=user)

@app.route('/publicacion', methods= ['GET', 'POST'])
def publicacion():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == "POST":
        pet_name = request.form['pet_name']
        pet_breed = request.form['pet_breed']
        pet_age = request.form['pet_age']
        caption = request.form['caption']
        image_file = request.files['image']
        image_name = secure_filename(image_file.filename)                     # Aseguramos el nombre del archivo
        image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_name)) # Guardamos el archivo en disco

        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("""
                    INSERT INTO publicaciones (user_id, pet_name, pet_breed, pet_age, image, caption)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (session['user_id'], pet_name, pet_breed, pet_age, image_name, caption))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('ver_perfil'))
# ========================================
# Iniciar la aplicación si este archivo es ejecutado directamente
# ========================================
if __name__ == '__main__':
    app.run(debug=True)
