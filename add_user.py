import sys
from app import app, db, UserSupport


def add_user(username, password):
    with app.app_context():
        if UserSupport.query.filter_by(username=username).first():
            print(f"Пользователь {username} уже существует.")
            return

        new_user = UserSupport(username=username)
        new_user.set_password(password)  # Непосредственное сохранение пароля
        db.session.add(new_user)
        db.session.commit()
        print(f"Пользователь {username} успешно добавлен.")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Использование: python add_user.py [username] [password]")
    else:
        username = sys.argv[1]
        password = sys.argv[2]
        add_user(username, password)
