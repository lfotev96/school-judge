
import os
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Модели
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(10), nullable=False)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

# Начална страница
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    tasks = Task.query.filter_by(is_active=True).all() if user.role == 'student' else []
    return render_template('index.html', user=user, tasks=tasks)

# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        user = User(username=username, password=password, role=role)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

# Вход
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
        return 'Невалидни данни'
    return render_template('login.html')

# Изход
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

# Качване на решение
@app.route('/submit/<int:task_id>', methods=['POST'])
def submit(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    file = request.files['solution']
    filename = secure_filename(file.filename)
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], str(session['user_id']))
    os.makedirs(upload_path, exist_ok=True)
    file.save(os.path.join(upload_path, filename))
    return 'Файлът е качен успешно!'

# Админ панел
@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if user.role != 'admin':
        return redirect(url_for('index'))
    tasks = Task.query.all()
    return render_template('admin.html', tasks=tasks)

@app.route("/create-task", methods=["GET", "POST"])
def create_task():
    if "user_id" not in session or session.get("role") != "teacher":
        return redirect("/login")

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        active = "active" in request.form

        new_task = Task(title=title, description=description, active=active)
        db.session.add(new_task)
        db.session.commit()
        return redirect("/admin")

    return render_template("create_task.html")

@app.route("/edit-task/<int:task_id>", methods=["GET", "POST"])
def edit_task(task_id):
    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    task = Task.query.get_or_404(task_id)

    if request.method == "POST":
        task.title = request.form["title"]
        task.description = request.form["description"]
        task.active = "active" in request.form
        db.session.commit()
        return redirect("/admin")

    return render_template("edit_task.html", task=task)

@app.route("/delete-task/<int:task_id>")
def delete_task(task_id):
    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    return redirect("/admin")

@app.route("/toggle-task/<int:task_id>")
def toggle_task(task_id):
    if "user_id" not in session or session.get("role") != "admin":
        return redirect("/login")

    task = Task.query.get_or_404(task_id)
    task.active = not task.active
    db.session.commit()
    return redirect("/admin")
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
