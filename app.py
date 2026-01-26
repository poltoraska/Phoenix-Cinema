from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask import request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash

# Инициализация приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = 'moi_sekretny_klyuch_dlya_diploma'
# Настройка базы данных
# Создание файл cinema.db прямо в папке проекта
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cinema.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- ОПИСАНИЕ ТАБЛИЦ ---

# Таблица 1: Пользователи (Администратор, Преподаватель, Студент) 
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # int IDENTITY(1,1) PRIMARY KEY
    username = db.Column(db.String(80), unique=True, nullable=False) # varchar(80) NOT NULL UNIQUE
    password = db.Column(db.String(120), nullable=False) # varchar(120) - здесь будет хэш пароля
    role = db.Column(db.String(20), nullable=False) # 'admin', 'teacher', 'student'

    def __repr__(self):
        return f'<User {self.username}>'

# Таблица 2: Съемочные проекты [cite: 7, 8]
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False) # Название фильма/задания
    description = db.Column(db.Text, nullable=True)   # Описание (Text = varchar(max))
    start_date = db.Column(db.Date, nullable=True)    # Дата начала съемок [cite: 11]
    
    # Связь с создателем (Foreign Key)
    # В SQL: FOREIGN KEY (created_by) REFERENCES user(id)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Таблица 3: Оборудование и реквизит [cite: 13, 14]
class Equipment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False) # Например: "Камера Sony A7"
    type = db.Column(db.String(50), nullable=False)  # 'camera', 'light', 'prop' (реквизит)
    is_broken = db.Column(db.Boolean, default=False) # Состояние техники [cite: 14]

# --- МАРШРУТЫ (ROUTES) ---
@app.route('/')
def index():
    # Эта функция ищет файл index.html в папке templates
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 1. Получаем данные из формы
        username = request.form['username']
        password = request.form['password']
        role = request.form['role'] # 'student' или 'teacher'

        # 2. Проверяем, нет ли уже такого пользователя
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Такой пользователь уже существует')
            return redirect(url_for('register'))

        # 3. Хешируем пароль и сохраняем в БД
        hash_pwd = generate_password_hash(password)
        new_user = User(username=username, password=hash_pwd, role=role)

        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('index')) # После успеха кидаем на главную

    return render_template('register.html')

# --- ЗАПУСК ---
if __name__ == '__main__':
    # Эта часть создает файл БД, если его нет
    with app.app_context():
        db.create_all()
        print("База данных создана успешно!")
    
    # Запуск веб-сервера
    app.run(debug=True)