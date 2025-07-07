from flask import Flask, render_template, request, redirect, send_from_directory
import os
from datetime import datetime

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    name = request.form['name']
    grade = request.form['grade']
    task = request.form['task']
    file = request.files['file']

    if file.filename:
        filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name}_{task}_{file.filename}"
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        return f"Файлът е качен успешно!<br><a href='/'>Назад</a>"

    return "Моля, прикачете файл!"

@app.route('/admin')
def admin():
    files = os.listdir(UPLOAD_FOLDER)
    return render_template('admin.html', files=files)

@app.route('/download/<filename>')
def download(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
