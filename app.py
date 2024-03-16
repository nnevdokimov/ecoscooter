import uuid
from datetime import datetime
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from flask import Flask, request, jsonify, redirect, url_for, session, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from functools import wraps

from send_response import send_response_to_user

app = Flask(__name__)
app.secret_key = 'test'  # Задайте секретный ключ для сессии

# Настройки Flask-Session
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Настройка базы данных
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


# Определение модели пользователя
# Определение модели пользователя
class UserSupport(db.Model):
    __tablename__ = 'user_support'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = password  # Здесь можете добавить хеширование, если захотите

    def check_password(self, password):
        return self.password_hash == password

    def is_active(self):
        return True

    def get_id(self):
        return self.id


# Определение модели обращений
class Appeal(db.Model):
    __tablename__ = 'appeals'
    appeal_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    appeal_type = db.Column(db.String(50), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), nullable=False)


class SupportResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appeal_id = db.Column(db.Integer, db.ForeignKey('appeals.appeal_id'), nullable=False)
    operator_id = db.Column(db.Integer, nullable=False)  # или db.ForeignKey('user_support.id') если есть связь
    message = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    promo_code = db.Column(db.String(100))

    appeal = db.relationship('Appeal', backref='responses')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# Маршрут для авторизации
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = UserSupport.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            session['user_id'] = user.id
            return redirect(url_for('index'))
        else:
            # В случае неудачи можно добавить сообщение об ошибке
            return render_template('login.html', error='Неверное имя пользователя или пароль')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    appeals_waiting = Appeal.query.filter(Appeal.status == 'waiting').all()
    appeals_processing = Appeal.query.filter(Appeal.status == 'in processing').all()
    return render_template('index.html', appeals_waiting=appeals_waiting, appeals_processing=appeals_processing)



@app.route('/update_appeal_type/<int:appeal_id>', methods=['POST'])
@login_required
def update_appeal_type(appeal_id):
    appeal = Appeal.query.get_or_404(appeal_id)
    new_type = request.form.get('appeal_type')
    if new_type:
        appeal.appeal_type = new_type
        db.session.commit()
        return redirect(url_for('appeal_details', appeal_id=appeal_id))
    return redirect(url_for('index'))


@app.route('/appeal/<int:appeal_id>')
@login_required
def appeal_details(appeal_id):
    appeal = Appeal.query.get_or_404(appeal_id)
    appeal.status = 'in processing'
    db.session.commit()

    responses = SupportResponse.query.filter_by(appeal_id=appeal_id).all()

    # Создание нового пустого ответа, если он еще не существует
    response = SupportResponse.query.filter_by(appeal_id=appeal_id, operator_id=current_user.id).first()
    if not response:
        response = SupportResponse(
            appeal_id=appeal_id,
            operator_id=current_user.id,
            created_at=datetime.utcnow()
        )
        db.session.add(response)
        db.session.commit()

    # Отправка данных об обращении и связанных ответах в шаблон
    return render_template('appeal_details.html', appeal=appeal, responses=responses)



@login_manager.user_loader
def load_user(user_id):
    return UserSupport.query.get(int(user_id))


@app.route('/add_promocode/<int:appeal_id>', methods=['POST'])
@login_required
def add_promocode(appeal_id):
    promo_code = str(uuid.uuid4())
    response = SupportResponse.query.filter_by(appeal_id=appeal_id, operator_id=current_user.id).first()
    if response:
        response.promo_code = promo_code
        db.session.commit()
    return jsonify({'status': 'success', 'promo_code': promo_code})


@app.route('/transfer_appeal/<int:appeal_id>/<specialist>', methods=['POST'])
@login_required
def transfer_appeal(appeal_id, specialist):
    # Здесь логика для перевода запроса на специалиста второй линии.
    return redirect(url_for('appeal_details', appeal_id=appeal_id))


@app.route('/send_message/<int:appeal_id>', methods=['POST'])
@login_required
def send_message(appeal_id):
    data = request.get_json()
    if 'message' in data:
        response = SupportResponse.query.filter_by(appeal_id=appeal_id, operator_id=current_user.id).first()
        if response:
            response.message = data['message']
            db.session.commit()

            send_response_to_user(text=response.message, appeal_id=appeal_id, promocode=response.promo_code)
            return jsonify({'status': 'success', 'message': 'Сообщение отправлено.'})

    return jsonify({'status': 'error', 'message': 'Необходимо предоставить сообщение.'})


@app.route('/admin_panel')
@login_required
def admin_panel():
    # Здесь логика для получения данных о пользователях и количестве ответов
    user_support_data = db.session.query(
        UserSupport.username,
        db.func.count(SupportResponse.id).label('response_count')
    ).join(SupportResponse, UserSupport.id == SupportResponse.operator_id, isouter=True).group_by(UserSupport.username).all()

    return render_template('admin_panel.html', users=user_support_data)



if __name__ == '__main__':
    app.run(debug=True)
