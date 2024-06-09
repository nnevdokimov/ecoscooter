import sys
import os
from datetime import datetime

from flask import Flask, render_template, redirect, url_for, session, request, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.hash import bcrypt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.models import Employee as BackendUserSupport
from backend.models import DATABASE_URL

app = Flask(__name__)
app.secret_key = 'test'
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class UserSupport:
    def __init__(self, username, user_id, access_level):
        self.username = username
        self.id = user_id
        self.access_level = access_level

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    @staticmethod
    def get(user_id):
        session = SessionLocal()
        user = session.query(BackendUserSupport).filter_by(employee_id=user_id).first()
        session.close()
        if user:
            return UserSupport(user.username, user.employee_id, user.access_level)
        return None


@login_manager.user_loader
def load_user(user_id):
    return UserSupport.get(user_id)


def access_required(lower, higher):
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.access_level != 0 and (
                    current_user.access_level < lower or current_user.access_level > higher):
                return redirect(url_for('index'))
            return f(*args, **kwargs)

        return decorated_function

    return decorator


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        response = requests.post("http://localhost:8000/token", data={"username": username, "password": password})
        print(response.json())
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data.get('user_id')
            access_level = user_data.get('access_level')
            user = UserSupport(username=username, user_id=user_id, access_level=access_level)
            login_user(user)
            session['token'] = user_data['access_token']
            return redirect(url_for('index'))
        else:
            flash('Неверные данные, обратитесь к системному администратору.', 'error')
            return render_template('login.html')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.get("http://localhost:8000/appeals", headers=headers)
    if response.status_code == 200:
        appeals = response.json()
        return render_template('index.html', appeals_waiting=appeals["appeals_waiting"],
                               appeals_processing=appeals["appeals_processing"])
    else:
        flash('Не удалось получить данные. Попробуйте снова.', 'error')
        return redirect(url_for('index'))


@app.route('/appeals/')
@access_required(1, 2)
def appeals():
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.get("http://localhost:8000/appeals", headers=headers)
    if response.status_code == 200:
        appeals = response.json()
        return render_template('appeals.html', appeals_waiting=appeals["appeals_waiting"],
                               appeals_processing=appeals["appeals_processing"])
    else:
        flash('Не удалось получить данные. Попробуйте снова.', 'error')
        return redirect(url_for('index'))


@app.route('/appeal/<int:appeal_id>')
@access_required(1, 2)
def appeal_details(appeal_id):
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.get(f"http://localhost:8000/appeals/{appeal_id}", headers=headers)
    if response.status_code == 200:
        appeal = response.json()
        return render_template('appeal_details.html', appeal=appeal)
    else:
        flash('Не удалось получить данные по обращению. Попробуйте снова.', 'error')
        return redirect(url_for('index'))


@app.route('/update_appeal_type/<int:appeal_id>', methods=['POST'])
@access_required(1, 2)
def update_appeal_type(appeal_id):
    new_type = request.form.get('category')
    headers = {"Authorization": f"Bearer {session['token']}"}
    data = {"category": new_type}
    response = requests.post(f"http://localhost:8000/appeals/{appeal_id}/update_type", headers=headers, data=data)
    if response.status_code == 200:
        return redirect(url_for('appeal_details', appeal_id=appeal_id))
    else:
        flash('Не удалось обновить тип обращения. Попробуйте снова.', 'error')
        return redirect(url_for('index'))


@app.route('/send_message/<int:appeal_id>', methods=['POST'])
@access_required(1, 2)
def send_message(appeal_id):
    message = request.form.get('message')
    headers = {"Authorization": f"Bearer {session['token']}"}
    data = {"message": message, "operator_id": current_user.id}
    response = requests.post(f"http://localhost:8000/send_message/{appeal_id}", headers=headers, data=data)
    if response.status_code == 200:
        return redirect(url_for('appeal_details', appeal_id=appeal_id))
    else:
        flash('Не удалось отправить сообщение. Попробуйте снова.', 'error')
        return redirect(url_for('index'))


@app.route('/add_promocode/<int:appeal_id>', methods=['POST'])
@access_required(1, 2)
def add_promocode(appeal_id):
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.post(f"http://localhost:8000/add_promocode/{appeal_id}", headers=headers)
    if response.status_code == 200:
        return redirect(url_for('appeal_details', appeal_id=appeal_id))
    else:
        flash('Не удалось добавить промокод. Попробуйте снова.', 'error')
        return redirect(url_for('index'))


@app.route('/edit_employee/<int:employee_id>', methods=['POST'])
@access_required(0, 0)
def edit_employee(employee_id):
    headers = {"Authorization": f"Bearer {session['token']}"}
    hire_date = request.form['hire_date'] + "T00:00:00"  # Append time to the date

    data = {
        "first_name": request.form['first_name'],
        "last_name": request.form['last_name'],
        "email": request.form['email'],
        "username": request.form['username'],
        # "password": request.form['password'],  # Ensure password is included or adjust logic if not needed
        "employee_type": request.form['employee_type'],
        "access_level": request.form['access_level'],
        "department": request.form['department'],
        "position": request.form['position'],
        "hire_date": hire_date,
        "phone_number": request.form['phone_number'],
        "address": request.form['address'],
        "status": request.form['status'],
        "last_login_date": request.form.get('last_login_date', datetime.utcnow().isoformat())
        # Optional field with default value
    }
    response = requests.put(f"http://localhost:8000/employees/{employee_id}", json=data, headers=headers)
    if response.status_code == 200:
        flash('Employee updated successfully.', 'success')
    else:
        error_details = response.json()  # Get the details of the error
        print(f"Error updating employee: {error_details}")
        flash(f"Error updating employee: {error_details}", 'error')
    return redirect(url_for('manage_employees'))


@app.route('/delete_employee/<int:employee_id>', methods=['GET'])
@access_required(0, 0)
def delete_employee(employee_id):
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.delete(f"http://localhost:8000/employees/{employee_id}", headers=headers)
    if response.status_code == 200:
        flash('Employee deleted successfully.', 'success')
    else:
        flash('Error deleting employee. Please try again.', 'error')
    return redirect(url_for('manage_employees'))


@app.route('/manage_employees', methods=['GET', 'POST'])
@access_required(0, 0)
def manage_employees():
    if request.method == 'POST':
        data = {
            "first_name": request.form['first_name'],
            "last_name": request.form['last_name'],
            "email": request.form['email'],
            "username": request.form['username'],
            "password": bcrypt.hash(request.form['password']),
            "employee_type": request.form['employee_type'],
            "access_level": request.form['access_level'],
            "department": request.form['department'],
            "position": request.form['position'],
            "hire_date": request.form['hire_date'],
            "phone_number": request.form['phone_number'],
            "address": request.form['address'],
            "status": request.form['status'],
            "last_login_date": request.form['hire_date']
        }
        headers = {"Authorization": f"Bearer {session['token']}"}
        response = requests.post("http://localhost:8000/employees/", json=data, headers=headers)
        if response.status_code == 200:
            return redirect(url_for('manage_employees'))
        else:
            flash('Ошибка при создании сотрудника. Попробуйте снова.', 'error')
            return render_template('manage_employees.html', employees=[])

    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.get("http://localhost:8000/employees", headers=headers)
    employees = response.json()

    return render_template('manage_employees.html', employees=employees)


@app.route('/statistics')
@access_required(2, 2)
def statistics():
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.get("http://localhost:8000/statistics", headers=headers)
    if response.status_code == 200:
        stats = response.json()
        print(stats)
        return render_template('statistics.html', stats=stats)
    else:
        flash('Не удалось получить статистику. Попробуйте снова.', 'error')
        return redirect(url_for('index'))


@app.route('/manage_scooters', methods=['GET'])
@access_required(3, 3)
def manage_scooters():
    headers = {"Authorization": f"Bearer {session['token']}"}
    query = request.args.get('query')
    if query:
        response = requests.get(f"http://localhost:8000/breakdowns?query={query}", headers=headers)
    else:
        response = requests.get("http://localhost:8000/breakdowns", headers=headers)
    if response.status_code == 200:
        breakdowns = response.json()
        return render_template('manage_scooters.html', breakdowns=breakdowns)
    else:
        flash('Не удалось получить данные о самокатах. Попробуйте снова.', 'error')
        return redirect(url_for('index'))


@app.route('/update_breakdown/<int:breakdown_id>', methods=['POST'])
@access_required(3, 3)
def update_breakdown(breakdown_id):
    headers = {"Authorization": f"Bearer {session['token']}"}
    data = {
        "status": request.form['status'],
        "maintenance_notes": request.form['maintenance_notes'],
        "priority_level": request.form['priority_level']
    }
    response = requests.put(f"http://localhost:8000/breakdowns/{breakdown_id}", json=data, headers=headers)
    if response.status_code == 200:
        flash('Данные о поломке успешно обновлены.', 'success')
    else:
        flash('Ошибка при обновлении данных о поломке. Попробуйте снова.', 'error')
    return redirect(url_for('manage_scooters'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
