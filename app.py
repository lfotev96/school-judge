from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'topsecretkey'
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.before_first_request
def init_db():
    db = get_db()
    db.executescript(open('schema.sql').read())
    db.commit()

@app.route('/')
def index():
    if 'user_id' in session:
        db = get_db()
        tasks = db.execute('SELECT * FROM tasks').fetchall()
        return render_template('student_home.html', tasks=tasks)
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        db = get_db()
        db.execute('INSERT INTO users (name, password, role) VALUES (?, ?, ?)', (name, password, role))
        db.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE name = ?', (name,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['role'] = user['role']
            return redirect(url_for('admin' if user['role'] == 'teacher' else 'index'))
        return "Грешни данни!"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/upload/<int:task_id>', methods=['POST'])
def upload(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    file = request.files['file']
    if file:
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{session['user_name']}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        db = get_db()
        db.execute('INSERT INTO uploads (user_id, task_id, filename) VALUES (?, ?, ?)', (session['user_id'], task_id, filename))
        db.commit()
        return redirect(url_for('index'))
    return "Невалиден файл!"

@app.route('/admin')
def admin():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
    db = get_db()
    tasks = db.execute('SELECT * FROM tasks').fetchall()
    uploads = db.execute('SELECT u.filename, t.title, us.name FROM uploads u JOIN users us ON u.user_id = us.id JOIN tasks t ON u.task_id = t.id').fetchall()
    return render_template('admin.html', tasks=tasks, uploads=uploads)

@app.route('/add_task', methods=['POST'])
def add_task():
    if session.get('role') != 'teacher':
        return redirect(url_for('index'))
    title = request.form['title']
    db = get_db()
    db.execute('INSERT INTO tasks (title) VALUES (?)', (title,))
    db.commit()
    return redirect(url_for('admin'))

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
