from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
import os
import sqlite3

app = Flask(__name__)
app.secret_key = 'supersecretkey'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

DB_FILE = 'database.db'

# Инициализация на базата при стартиране
def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                is_admin INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                filename TEXT,
                active INTEGER DEFAULT 1
            )
        ''')
        # Добавяме админ потребител по подразбиране, ако го няма
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            cursor.execute("INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)",
                           ('admin', 'admin', 1))
        conn.commit()

init_db()  # Инициализация веднага

# Роутове
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, is_admin FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user[0]
            session['is_admin'] = bool(user[1])
            return redirect(url_for('dashboard'))
    flash('Невалидно потребителско име или парола', 'danger')
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        if session.get('is_admin'):
            cursor.execute("SELECT * FROM tasks ORDER BY id DESC")
        else:
            cursor.execute("SELECT * FROM tasks WHERE active=1 ORDER BY id DESC")
        tasks = cursor.fetchall()
    return render_template('dashboard.html', tasks=tasks)

@app.route('/add_task', methods=['GET', 'POST'])
def add_task():
    if not session.get('is_admin'):
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        file = request.files['file']
        filename = ''
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO tasks (title, description, filename, active) VALUES (?, ?, ?, ?)",
                           (title, description, filename, 1))
            conn.commit()
        return redirect(url_for('dashboard'))

    return render_template('add_task.html')

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    if not session.get('is_admin'):
        return redirect(url_for('dashboard'))

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.commit()
    return redirect(url_for('dashboard'))

@app.route('/toggle_task/<int:task_id>')
def toggle_task(task_id):
    if not session.get('is_admin'):
        return redirect(url_for('dashboard'))

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT active FROM tasks WHERE id=?", (task_id,))
        active = cursor.fetchone()[0]
        cursor.execute("UPDATE tasks SET active=? WHERE id=?", (1 - active, task_id))
        conn.commit()
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)
