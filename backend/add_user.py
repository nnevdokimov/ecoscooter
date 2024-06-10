import sys
from getpass import getpass
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import Base, UserSupport, DATABASE_URL


def add_user(username, password):
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    user = UserSupport(username=username)
    user.set_password(password)

    session.add(user)
    session.commit()
    session.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python add_user.py <username>")
        sys.exit(1)

    username = sys.argv[1]
    password = getpass("Enter password for {}: ".format(username))
    confirm_password = getpass("Confirm password for {}: ".format(username))

    if password != confirm_password:
        print("Passwords do not match. Please try again.")
        sys.exit(1)

    add_user(username, password)
    print("User {} added successfully.".format(username))
