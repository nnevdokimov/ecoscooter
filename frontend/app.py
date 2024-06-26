import sys
import os
from datetime import datetime

from flask import Flask, render_template, redirect, url_for, session, request, flash, jsonify
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
        messages_response = requests.get(f"http://localhost:8000/appeals/{appeal_id}/messages", headers=headers)
        if messages_response.status_code == 200:
            messages = messages_response.json()
            return render_template('appeal_details.html', appeal=appeal, messages=messages, operator_id=current_user.id)
        else:
            flash('Не удалось получить сообщения. Попробуйте снова.', 'error')
            return redirect(url_for('index'))
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
    print(response.json(), response.status_code)
    if response.status_code == 200:
        return jsonify({"status": "success", "message": "Сообщение успешно отправлено."})
    else:
        return jsonify({"status": "error", "message": "Не удалось отправить сообщение. Попробуйте снова."}), 400


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


@app.route('/available_operators/<int:appeal_id>', methods=['GET'])
@access_required(1, 2)
def available_operators(appeal_id):
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.get(f"http://localhost:8000/appeals/available_operators/{appeal_id}", headers=headers)
    print(response.json(), response.status_code)

    if response.status_code == 200:
        operators = response.json().get('operators', [])
        return jsonify({"status": "success", "operators": operators})
    else:
        return jsonify({"status": "error", "message": "Не удалось получить список операторов."}), 400


@app.route('/transfer_appeal/<int:appeal_id>', methods=['POST'])
@access_required(1, 2)
def transfer_appeal(appeal_id):
    new_operator_id = request.form.get('new_operator_id')
    if not new_operator_id:
        flash('ID нового оператора не указан.', 'error')
        return redirect(url_for('appeal_details', appeal_id=appeal_id))

    headers = {"Authorization": f"Bearer {session['token']}"}
    data = {'new_operator_id': new_operator_id}
    response = requests.post(f"http://localhost:8000/transfer_appeal/{appeal_id}", headers=headers, data=data)

    if response.status_code == 200:
        flash('Обращение успешно переведено на нового оператора.', 'success')
        return redirect(url_for('appeals', appeal_id=appeal_id))
    else:
        flash('Не удалось перевести обращение на нового оператора. Попробуйте снова.', 'error')
        return redirect(url_for('appeal_details', appeal_id=appeal_id))


@app.route('/close_appeal/<int:appeal_id>', methods=['POST'])
@access_required(1, 2)
def close_appeal(appeal_id):
    headers = {"Authorization": f"Bearer {session['token']}"}
    try:
        response = requests.post(f"http://localhost:8000/close_appeal/{appeal_id}", headers=headers)

        if response.status_code == 200:
            return redirect(url_for('appeals'))
        else:
            flash('Не удалось закрыть обращение. Попробуйте снова.', 'error')
            return redirect(url_for('appeal_details', appeal_id=appeal_id))
    except Exception as e:
        print(f"Exception occurred: {e}")
        flash('Произошла ошибка при попытке закрыть обращение.', 'error')
        return redirect(url_for('appeal_details', appeal_id=appeal_id))


@app.route('/create_breakdown/<int:appeal_id>', methods=['POST'])
@login_required
def create_breakdown(appeal_id):
    headers = {"Authorization": f"Bearer {session['token']}"}
    data = {
        "item_id": request.form['item_id'],
        "reported_date": datetime.utcnow().isoformat(),
        "breakdown_type": request.form['breakdown_type'],
        "description": request.form['description'],
        "status": 'on_parking',
        "reported_by": str(current_user.id),
        "priority_level": 'medium',
    }

    response = requests.post("http://localhost:8000/breakdowns/", json=data, headers=headers)

    if response.status_code == 200:
        flash('Информация о неисправности успешно добавлена.', 'success')
    else:
        flash('Произошла ошибка при добавлении информации о неисправности.', 'error')

    return redirect(url_for('appeal_details', appeal_id=appeal_id))


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
            "hire_date": datetime.utcnow().isoformat(),
            "phone_number": request.form['phone_number'],
            "address": request.form['address'],
            "status": request.form['status'],
            "last_login_date": datetime.utcnow().isoformat()
        }
        headers = {"Authorization": f"Bearer {session['token']}"}
        response = requests.post("http://localhost:8000/employees/", json=data, headers=headers)
        print(response.json())
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
        'breakdown_type': request.form['breakdown_type'],
        'description': request.form['description'],
        "status": request.form['status'],
        "maintenance_notes": request.form['maintenance_notes'],
        "priority_level": request.form['priority_level']
    }
    response = requests.put(f"http://localhost:8000/update_breakdown/{breakdown_id}", json=data, headers=headers)
    if response.status_code == 200:
        flash('Данные о поломке успешно обновлены.', 'success')
    else:
        flash('Ошибка при обновлении данных о поломке. Попробуйте снова.', 'error')
    return redirect(url_for('manage_scooters'))


@app.route('/courier_schedules')
@login_required
def courier_schedules():
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.get("http://localhost:8000/couriers", headers=headers)
    couriers = response.json()
    return render_template('courier_schedules.html', couriers=couriers)


@app.route('/create_courier_schedule', methods=['POST'])
@login_required
def create_courier_schedule():
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    headers = {"Authorization": f"Bearer {session['token']}"}

    schedule_data = {
        "start_date": start_date,
        "end_date": end_date
    }

    try:
        response = requests.post("http://localhost:8000/courier_schedules/", json=schedule_data, headers=headers)
        response.raise_for_status()

        try:
            response_data = response.json()
            print(start_date, end_date, response_data)
            if response.status_code == 200:
                return jsonify({"status": "success", "message": "Расписание успешно создано!"})
            else:
                return jsonify(
                    {"status": "error", "message": "Произошла ошибка при создании расписания."}), response.status_code
        except ValueError:
            print('Response content:', response.content)
            return jsonify({"status": "error", "message": "Произошла ошибка при обработке ответа сервера."}), 500

    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return jsonify({"status": "error", "message": "Произошла ошибка при создании расписания."}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
