import sys
import os
from flask import Flask, render_template, redirect, url_for, session, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import Employee as BackendUserSupport
from backend.models import DATABASE_URL

app = Flask(__name__)
app.secret_key = 'test'
login_manager = LoginManager()
login_manager.init_app(app)

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class UserSupport:
    def __init__(self, username):
        self.username = username
        self.id = 1

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
            return UserSupport(user.username)
        return None


@login_manager.user_loader
def load_user(user_id):
    return UserSupport.get(user_id)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        response = requests.post("http://localhost:8000/token", data={"username": username, "password": password})
        if response.status_code == 200:
            login_user(UserSupport(username=username))
            session['token'] = response.json()['access_token']
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Неверные данные, обратитесь к системному администратору.')
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
    appeals = response.json()
    return render_template('index.html', appeals_waiting=appeals["appeals_waiting"], appeals_processing=appeals["appeals_processing"])


@app.route('/appeal/<int:appeal_id>')
@login_required
def appeal_details(appeal_id):
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.get(f"http://localhost:8000/appeals/{appeal_id}", headers=headers)
    if response.status_code == 200:
        appeal = response.json()
        return render_template('appeal_details.html', appeal=appeal)
    else:
        return redirect(url_for('index'))


@app.route('/update_appeal_type/<int:appeal_id>', methods=['POST'])
@login_required
def update_appeal_type(appeal_id):
    new_type = request.form.get('category')
    headers = {"Authorization": f"Bearer {session['token']}"}
    data = {"category": new_type}
    response = requests.post(f"http://localhost:8000/appeals/{appeal_id}/update_type", headers=headers, data=data)
    if response.status_code == 200:
        return redirect(url_for('appeal_details', appeal_id=appeal_id))
    else:
        return redirect(url_for('index'))


@app.route('/send_message/<int:appeal_id>', methods=['POST'])
@login_required
def send_message(appeal_id):
    message = request.form.get('message')
    headers = {"Authorization": f"Bearer {session['token']}"}
    print(appeal_id, message)
    data = {"message": message, "operator_id": 1}
    response = requests.post(f"http://localhost:8000/send_message/{appeal_id}", headers=headers, data=data)
    return redirect(url_for('appeal_details', appeal_id=appeal_id))


@app.route('/add_promocode/<int:appeal_id>', methods=['POST'])
@login_required
def add_promocode(appeal_id):
    headers = {"Authorization": f"Bearer {session['token']}"}
    response = requests.post(f"http://localhost:8000/add_promocode/{appeal_id}", headers=headers)
    if response.status_code == 200:
        return redirect(url_for('appeal_details', appeal_id=appeal_id))
    else:
        return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
