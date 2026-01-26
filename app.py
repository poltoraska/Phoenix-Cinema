from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Инициализация приложения
app = Flask(__name__)

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

# --- ЗАПУСК ---
if __name__ == '__main__':
    # Эта часть создает файл БД, если его нет
    with app.app_context():
        db.create_all()
        print("База данных создана успешно!")
    
    # Запуск веб-сервера
    app.run(debug=True)