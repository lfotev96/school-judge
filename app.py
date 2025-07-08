import os
import sqlite3
from flask import Flask, render_template, request, redirect, session, url_for, send_from_directory, g
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'verysecretkey'
app.config['UPLOAD_FOLDER'] = 'uploads'

DATABASE = 'database.db'


def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()
        
@app.before_request
def before_first_request():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            filename TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    conn.commit()
    conn.close()


@app.route('/')
def index():
    conn = get_db_connection()
    tasks = conn.execute('SELECT * FROM tasks WHERE is_active = 1').fetchall()
    conn.close()
    return render_template('index.html', tasks=tasks)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        conn.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, password))
        conn.commit()
        conn.close()
        return redirect('/login')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', (email, password)).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['is_admin'] = user['is_admin']
            return redirect('/admin' if user['is_admin'] else '/')
        else:
            return 'Invalid credentials'
    return render_template('login.html')

@app.route("/secret-register", methods=["GET", "POST"])
def secret_register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        is_admin = True if request.form.get("is_admin") == "on" else False

        if get_db().execute("SELECT * FROM user WHERE email = ?", (email,)).fetchone():
            return "Потребител с този имейл вече съществува."

        hashed_password = generate_password_hash(password)
        db = get_db()
        db.execute("INSERT INTO user (email, password, is_admin) VALUES (?, ?, ?)", (email, hashed_password, is_admin))
        db.commit()

        return "Регистрацията беше успешна."

    return render_template("secret_register.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/admin')
def admin():
    if not session.get('is_admin'):
        return redirect('/')
    conn = get_db_connection()
    tasks = conn.execute('SELECT * FROM tasks').fetchall()
    conn.close()
    return render_template('admin.html', tasks=tasks)


@app.route('/create-task', methods=['GET', 'POST'])
def create_task():
    if not session.get('is_admin'):
        return redirect('/')
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        is_active = 1 if request.form.get('is_active') == 'on' else 0
        file = request.files.get('file')
        filename = None
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        conn = get_db_connection()
        conn.execute('INSERT INTO tasks (title, description, filename, is_active) VALUES (?, ?, ?, ?)',
                     (title, description, filename, is_active))
        conn.commit()
        conn.close()
        return redirect('/admin')
    return render_template('create_task.html')


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
