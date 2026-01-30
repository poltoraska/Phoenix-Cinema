import sys
print("Где я нахожусь:", sys.executable)
import pandas as pd
import io
from flask import send_file
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
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

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Кидать пользователя туда, если не вошел

# --- ОПИСАНИЕ ТАБЛИЦ ---

# Таблица 1: Пользователи (Администратор, Преподаватель, Студент) 
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)  # int IDENTITY(1,1) PRIMARY KEY
    username = db.Column(db.String(80), unique=True, nullable=False) # varchar(80) NOT NULL UNIQUE
    email = db.Column(db.String(120), unique=True, nullable=True)
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

# Таблица 4: Бронирования (Связь Проекта и Оборудования)
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.id'), nullable=False)
    date = db.Column(db.Date, nullable=False) # На какую дату бронь

    # Настройка связей для удобного обращения к данным
    project = db.relationship('Project', backref='bookings')
    equipment = db.relationship('Equipment', backref='bookings')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- МАРШРУТЫ (ROUTES) ---
@app.route('/')
def index():
    # Если пользователь гость - показывает просто приветствие
    if not current_user.is_authenticated:
        return render_template('index.html')

    # Если пользователь вошел - показывает статистику для Дашборда
    
    # 1. Считает общие цифры
    total_projects = Project.query.count()
    total_equipment = Equipment.query.count()
    
    # 2. Ищет бронирования на сегодня
    today = date.today()
    bookings_today = Booking.query.filter_by(date=today).all()
    
    # 3. Считаем, сколько техники занято сегодня
    busy_count = len(bookings_today)

    return render_template('index.html', 
                           total_projects=total_projects,
                           total_equipment=total_equipment,
                           busy_count=busy_count,
                           bookings_today=bookings_today,
                           today_date=today)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']       # 1. Получаем Email из формы
        password = request.form['password']
        role = request.form['role']
        
        # 2. Проверка: не занят ли Логин или Email?
        if User.query.filter_by(username=username).first():
            flash('Пользователь с таким логином уже существует')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким Email уже существует')
            return redirect(url_for('register'))
        
        # 3. Создание пользователя, передавая email
        hash_pwd = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hash_pwd, role=role)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Регистрация прошла успешно! Теперь войдите.')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        # Проверяем: пользователь найден? Пароль совпадает?
        if user and check_password_hash(user.password, password):
            login_user(user) # Магия Flask-Login: запоминаем пользователя
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль')
            
    return render_template('login.html')

@app.route('/logout')
@login_required # Только для тех, кто вошел
def logout():
    logout_user()
    return redirect(url_for('index'))

# --- УПРАВЛЕНИЕ ОБОРУДОВАНИЕМ ---

@app.route('/equipment')
@login_required
def equipment_list():
    # Забираем всё оборудование из базы
    items = Equipment.query.all()
    return render_template('equipment.html', items=items)

@app.route('/equipment/add', methods=['GET', 'POST'])
@login_required
def add_equipment():
    # Список разрешенных ролей для добавления оборудования
    if current_user.role not in ['admin', 'teacher', 'employee']:
        flash('У вас нет прав добавлять оборудование!')
        return redirect(url_for('equipment_list'))

    if request.method == 'POST':
        name = request.form['name']
        eq_type = request.form['type'] # camera, light, prop
        
        # Создание новою запись
        new_item = Equipment(name=name, type=eq_type, is_broken=False)
        db.session.add(new_item)
        db.session.commit()
        
        flash('Оборудование успешно добавлено!')
        return redirect(url_for('equipment_list'))

    return render_template('add_equipment.html')

# --- ИМПОРТ И ЭКСПОРТ EXCEL ---

@app.route('/equipment/export')
@login_required
def export_equipment():
    # 1. Получаем все оборудование из базы
    equipment = Equipment.query.all()
    
    # 2. Превращаем данные в список словарей
    data = []
    for item in equipment:
        data.append({
            'Название': item.name,
            'Тип (camera/light/prop/consumable/other)': item.type,
            'Сломано (TRUE/FALSE)': item.is_broken
        })
    
    # 3. Создаем DataFrame (таблицу pandas)
    df = pd.DataFrame(data)
    
    # 4. Сохраняем в память (виртуальный файл)
    output = io.BytesIO()
    # Используем движок openpyxl для записи xlsx
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Оборудование')
    
    output.seek(0) # Возвращаем "курсор" в начало файла
    
    return send_file(output, download_name="equipment_list.xlsx", as_attachment=True)

@app.route('/equipment/import', methods=['POST'])
@login_required
def import_equipment():
    # Проверка прав
    if current_user.role not in ['admin', 'teacher', 'employee']:
        flash('Нет прав для импорта')
        return redirect(url_for('equipment_list'))

    file = request.files['file']
    if not file:
        flash('Файл не выбран')
        return redirect(url_for('equipment_list'))

    try:
        # Чтение Excel файл
        df = pd.read_excel(file)
        
        # Чтенеие по каждой строке таблицы
        count = 0
        for index, row in df.iterrows():
            name = row['Название']
            eq_type = row['Тип (camera/light/prop/consumable/other)']
            
            # Простая защита от дублей: если такое имя есть, пропуск
            if not Equipment.query.filter_by(name=name).first():
                new_item = Equipment(name=name, type=eq_type, is_broken=False)
                db.session.add(new_item)
                count += 1
        
        db.session.commit()
        flash(f'Успешно импортировано позиций: {count}')
        
    except Exception as e:
        flash(f'Ошибка при чтении файла: {e}')
        
    return redirect(url_for('equipment_list'))

@app.route('/equipment/<int:id>/delete', methods=['POST'])
@login_required
def delete_equipment(id):
    # 1. Проверка прав (только админ, учитель, сотрудник)
    if current_user.role not in ['admin', 'teacher', 'employee']:
        flash('У вас нет прав на удаление!')
        return redirect(url_for('equipment_list'))

    item = Equipment.query.get_or_404(id)

    # 2. Проверка на использование предмета в бронированиях?
    if item.bookings: 
        flash(f'Нельзя удалить "{item.name}", так как этот предмет используется в проектах. Сначала удалите брони.')
        return redirect(url_for('equipment_list'))

    # 3. Удаление
    try:
        db.session.delete(item)
        db.session.commit()
        flash(f'Оборудование "{item.name}" удалено.')
    except Exception as e:
        db.session.rollback()
        flash('Ошибка при удалении.')

    return redirect(url_for('equipment_list'))

# --- УПРАВЛЕНИЕ ПРОЕКТАМИ ---

@app.route('/projects')
@login_required
def project_list():
    # Показываем все проекты
    projects = Project.query.all()
    
    # Чтобы отобразить имя создателя, нам понадобится связь. 
    # Но для простоты пока просто передадим список.
    return render_template('projects.html', projects=projects)

@app.route('/projects/new', methods=['GET', 'POST'])
@login_required
def create_project():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        date_str = request.form['start_date'] # Приходит строка вида '2024-02-20'
        
        # Конвертация строки в объект даты Python
        try:
            start_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Неверный формат даты')
            return redirect(url_for('create_project'))

        # Создание проекта. Важно: запоминаем, КТО его создал (current_user.id)
        new_project = Project(
            title=title, 
            description=description, 
            start_date=start_date,
            created_by=current_user.id 
        )
        
        db.session.add(new_project)
        db.session.commit()
        
        flash(f'Проект "{title}" успешно создан!')
        return redirect(url_for('project_list'))

    return render_template('create_project.html')

# --- БРОНИРОВАНИЕ ---

@app.route('/projects/<int:project_id>/book', methods=['GET', 'POST'])
@login_required
def book_equipment(project_id):
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        date_str = request.form['date']
        equipment_ids = request.form.getlist('equipment') # Получение списка ID выбранных галочек
        
        try:
            book_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Неверный формат даты')
            return redirect(url_for('book_equipment', project_id=project_id))

        # Сохранение брони для каждого выбранного предмета
        count = 0
        for eq_id in equipment_ids:
            # Проверка: не занят ли этот предмет в этот день уже каким-то проектом?
            # (Проверка корявая, но для учебного проекта сойдет)
            exists = Booking.query.filter_by(equipment_id=eq_id, date=book_date).first()
            
            if not exists:
                new_booking = Booking(project_id=project.id, equipment_id=eq_id, date=book_date)
                db.session.add(new_booking)
                count += 1
            else:
                flash(f'Оборудование ID {eq_id} уже занято на эту дату!')
        
        db.session.commit()
        flash(f'Успешно забронировано предметов: {count}')
        return redirect(url_for('project_list'))

    # Для GET запроса показывает список всего оборудования
    all_equipment = Equipment.query.all()
    return render_template('book_equipment.html', project=project, equipment=all_equipment)

@app.route('/booking/<int:booking_id>/delete', methods=['POST'])
@login_required
def delete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    project_id = booking.project_id # Чтобы вернуться на ту же страницу
    
    # Простейшая проверка прав: удалять может кто угодно, кто имеет доступ
    
    try:
        db.session.delete(booking)
        db.session.commit()
        flash('Бронь отменена.')
    except Exception as e:
        db.session.rollback()
        flash('Ошибка при отмене брони.')
        
    return redirect(url_for('book_equipment', project_id=project_id))

@app.route('/api/check_availability')
def check_availability():
    date_str = request.args.get('date')
    
    if not date_str:
        return jsonify([]) # Если даты нет, возвращает пустой список

    try:
        check_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify([])

    # Ищет все бронирования на эту дату
    bookings = Booking.query.filter_by(date=check_date).all()
    
    # Собирает список ID занятого оборудования
    busy_ids = [b.equipment_id for b in bookings]
    
    return jsonify(busy_ids)

# --- ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ ---

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        new_password = request.form['password']

        # Проверка: если имя изменилось, занято ли оно?
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != current_user.id:
            flash('Это имя пользователя уже занято.')
            return redirect(url_for('profile'))

        # Обновляем данные
        current_user.username = username
        current_user.email = email

        # Если ввели новый пароль - обновляет и его
        if new_password:
            current_user.password = generate_password_hash(new_password)
            flash('Данные и пароль обновлены!')
        else:
            flash('Данные профиля обновлены!')

        db.session.commit()
        return redirect(url_for('profile'))

    return render_template('profile.html', user=current_user)

# --- ЗАПУСК ---
if __name__ == '__main__':
    # Эта часть создает файл БД, если его нет
    with app.app_context():
        db.create_all()
        print("База данных создана успешно!")
    
    # Запуск веб-сервера
    app.run(debug=True)