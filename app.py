import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DATABASE = 'database.db'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


class User(UserMixin):
    def __init__(self, id_, username, role):
        self.id = id_
        self.username = username
        self.role = role

    @staticmethod
    def get(user_id):
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return None
        return User(user['id'], user['username'], user['role'])

    @staticmethod
    def find_by_username(username):
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not user:
            return None
        return User(user['id'], user['username'], user['role'])


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.find_by_username(username)
        if user and check_password_hash(get_password_hash(user.id), password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            error = "Невалидно потребителско име или парола"
    return render_template('login.html', error=error)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'student')  # по подразбиране ученик

        db = get_db()
        existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if existing:
            error = 'Потребителското име вече съществува'
        else:
            pw_hash = generate_password_hash(password)
            db.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                       (username, pw_hash, role))
            db.commit()
            flash("Регистрацията е успешна, моля влезте.")
            return redirect(url_for('login'))
    return render_template('register.html', error=error)


def get_password_hash(user_id):
    db = get_db()
    user = db.execute("SELECT password FROM users WHERE id = ?", (user_id,)).fetchone()
    return user['password'] if user else None


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'teacher':
        # показва админ панел с управление на задачи
        db = get_db()
        tasks = db.execute("SELECT * FROM tasks").fetchall()
        return render_template('admin.html', tasks=tasks)
    else:
        # показва списък активни задачи за ученици
        db = get_db()
        tasks = db.execute("SELECT * FROM tasks WHERE active=1").fetchall()
        return render_template('tasks.html', tasks=tasks)


@app.route('/task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def task_detail(task_id):
    db = get_db()
    task = db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not task:
        flash("Задачата не е намерена")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Няма избран файл')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('Няма избран файл')
            return redirect(request.url)
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)

        db.execute("INSERT INTO submissions (user_id, task_id, filename) VALUES (?, ?, ?)",
                   (current_user.id, task_id, filename))
        db.commit()
        flash('Решението е качено успешно')
        return redirect(url_for('dashboard'))

    return render_template('task_detail.html', task=task)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        with app.app_context():
            db = get_db()
            with open('schema.sql', 'r') as f:
                db.executescript(f.read())
            db.commit()
    app.run(debug=True, host='0.0.0.0', port=5000)
