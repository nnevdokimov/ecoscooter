from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Column, Integer, String, Text, Date, DateTime, ForeignKey, Time, TIMESTAMP, \
    Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from passlib.context import CryptContext

DATABASE_URL = "sqlite:///./database.db"
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class Item(Base):
    __tablename__ = 'items'
    item_id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String, nullable=False)
    model = Column(String, nullable=False)
    status = Column(String, nullable=False)
    location = Column(String, nullable=False)
    deployment_date = Column(Date, nullable=False)
    last_service_date = Column(Date, nullable=True)
    last_location_update = Column(String, nullable=True)
    movement_history = Column(Text, nullable=True)
    working_hours = Column(Integer, nullable=True)


class Employee(Base):
    __tablename__ = 'employees'
    employee_id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    username = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    employee_type = Column(String, nullable=False)
    access_level = Column(Integer, nullable=False)
    department = Column(String, nullable=False)
    position = Column(String, nullable=False)
    hire_date = Column(Date, nullable=False)
    phone_number = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    status = Column(String, nullable=False)
    last_login_date = Column(TIMESTAMP, nullable=True)

    def set_password(self, password: str):
        self.password = pwd_context.hash(password)

    def check_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password)


class Client(Base):
    __tablename__ = 'clients'
    client_id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    dob = Column(Date, nullable=False)
    phone_number = Column(String, nullable=False)
    registration_date = Column(Date, nullable=False)
    membership_type = Column(String, nullable=False)
    payment_details = Column(Text, nullable=True)
    ride_history = Column(Text, nullable=True)
    active_bookings = Column(Text, nullable=True)


class SupportTicket(Base):
    __tablename__ = 'support_tickets'
    ticket_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, nullable=False)
    creation_date = Column(TIMESTAMP, nullable=False)
    last_update_date = Column(TIMESTAMP, nullable=False)
    assigned_technician_id = Column(Integer, nullable=True)
    resolution_details = Column(Text, nullable=True)
    closure_date = Column(TIMESTAMP, nullable=True)
    promocode = Column(String, nullable=True)


class SupportResponse(Base):
    __tablename__ = 'support_responses'
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey('support_tickets.ticket_id'))
    operator_id = Column(Integer, nullable=False)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    promo_code = Column(String(100))

    ticket = relationship("SupportTicket", backref="responses")


class Parking(Base):
    __tablename__ = 'parkings'
    parking_id = Column(Integer, primary_key=True, index=True)
    location = Column(String, nullable=False)
    desired_scooter_quantity = Column(Integer, nullable=False)
    current_scooter_quantity = Column(Integer, nullable=False)
    last_updated = Column(TIMESTAMP, nullable=False)
    area_size = Column(Integer, nullable=True)
    parking_type = Column(String, nullable=False)
    status = Column(String, nullable=False)


class Breakdown(Base):
    __tablename__ = 'breakdowns'
    breakdown_id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, nullable=False)
    reported_date = Column(TIMESTAMP, nullable=False)
    breakdown_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, nullable=False)
    reported_by = Column(String, nullable=False)
    assigned_to = Column(String, nullable=True)
    priority_level = Column(String, nullable=False)
    resolution_date = Column(TIMESTAMP, nullable=True)
    resolution_details = Column(Text, nullable=True)
    downtime_duration = Column(Integer, nullable=True)
    parts_replaced = Column(Text, nullable=True)
    maintenance_notes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)


class CourierSchedule(Base):
    __tablename__ = 'courier_schedules'
    schedule_id = Column(Integer, primary_key=True, index=True)
    courier_id = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    parking_ids = Column(Text, nullable=True)
    total_distance = Column(Integer, nullable=True)
    route_details = Column(Text, nullable=True)
    special_instructions = Column(Text, nullable=True)


Base.metadata.create_all(bind=engine)
