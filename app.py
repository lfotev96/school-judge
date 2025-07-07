from flask import Flask, render_template, redirect, url_for, request, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

db = SQLAlchemy(app)

# === Models ===

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    task_id = db.Column(db.Integer)
    filename = db.Column(db.String(300))

# === Create initial admin ===

with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@school.local').first():
        admin = User(
            name='Админ',
            email='admin@school.local',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()

# === Routes ===

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        tasks = Task.query.filter_by(is_active=True).all() if not user.is_admin else Task.query.all()
        return render_template('dashboard.html', user=user, tasks=tasks)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('index'))
        flash('Невалидни данни за вход.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/create_task', methods=['GET', 'POST'])
def create_task():
    if not session.get('user_id'): return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if not user.is_admin: return redirect(url_for('index'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        is_active = 'is_active' in request.form
        task = Task(title=title, description=description, is_active=is_active)
        db.session.add(task)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('create_task.html')

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    if not session.get('user_id'): return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if not user.is_admin: return redirect(url_for('index'))

    task = Task.query.get_or_404(task_id)

    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form['description']
        task.is_active = 'is_active' in request.form
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('edit_task.html', task=task)

@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    if not session.get('user_id'): return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if not user.is_admin: return redirect(url_for('index'))

    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/upload/<int:task_id>', methods=['GET', 'POST'])
def upload(task_id):
    if not session.get('user_id'): return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    task = Task.query.get_or_404(task_id)

    if request.method == 'POST':
        file = request.files['file']
        if file:
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            submission = Submission(user_id=user.id, task_id=task.id, filename=filename)
            db.session.add(submission)
            db.session.commit()
            flash('Файлът е качен успешно!')
            return redirect(url_for('index'))

    return render_template('upload.html', task=task)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# === Start ===

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(host='0.0.0.0', port=5000, debug=True)
