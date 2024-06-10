import uuid
from datetime import datetime, timedelta, date
import random
from typing import List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from backend.send_response import send_response_to_user, send_promocode
from backend.models import (
    Base, engine, SessionLocal, Item, Employee, Client, SupportTicket, Parking, Breakdown, CourierSchedule,
    SupportResponse
)
from backend.schemas import (
    ItemCreate, EmployeeCreate, EmployeeManage, ClientCreate, SupportTicketCreate, ParkingCreate, BreakdownCreate,
    CourierScheduleCreate,
    AppealResponse, AppealsResponse, SupportResponseCreate, SupportResponseResponse, BreakdownResponse, BreakdownUpdate,
    CourierStatusResponse, CourierScheduleResponse
)

Base.metadata.create_all(bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_access_level(lower: int, higher: int):
    def access_level_dependency(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
        user_id = int(token)
        user = db.query(Employee).filter(Employee.employee_id == user_id).first()
        if user is None or (user.access_level != 0 and (user.access_level < lower or user.access_level > higher)):
            raise HTTPException(status_code=403, detail="Insufficient access level")
        return user

    return access_level_dependency


# Авторизация пользователя
@app.post("/token")
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(Employee).filter(Employee.username == username).first()
    if user is None or not user.check_password(password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {"user_id": user.employee_id, "access_token": str(user.employee_id), "token_type": "bearer"}


# Получение данных пользователя
@app.get("/user")
async def get_user_data(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user_id = int(token)
    user = db.query(Employee).filter(Employee.employee_id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user.employee_id, "username": user.username, "access_level": user.access_level}


# Получение списка обращений
@app.get("/appeals", response_model=AppealsResponse)
async def read_appeals(skip: int = 0, limit: int = 10, db: Session = Depends(get_db),
                       user: Employee = Depends(check_access_level(1, 2))):
    appeals_waiting = db.query(SupportTicket).filter(SupportTicket.status == 'waiting').offset(skip).limit(limit).all()
    appeals_processing = db.query(SupportTicket).filter(
        SupportTicket.assigned_technician_id == user.employee_id).filter(
        SupportTicket.status == 'in processing').offset(skip).limit(
        limit).all()

    appeals_waiting_response = [AppealResponse.from_orm(appeal) for appeal in appeals_waiting]
    appeals_processing_response = [AppealResponse.from_orm(appeal) for appeal in appeals_processing]

    return AppealsResponse(appeals_waiting=appeals_waiting_response, appeals_processing=appeals_processing_response)


# Создание нового обращения
@app.post("/appeals/", response_model=AppealResponse)
async def create_appeal(email: str = Form(...), category: str = Form(...), description: str = Form(...),
                        db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.email == email).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    db_appeal = SupportTicket(
        user_id=client.client_id,
        category=category,
        description=description,
        status='waiting',
        creation_date=datetime.now(),
        last_update_date=datetime.now()
    )
    db.add(db_appeal)
    db.commit()
    db.refresh(db_appeal)
    return AppealResponse.from_orm(db_appeal)


# Получение конкретного обращения
@app.get("/appeals/{appeal_id}", response_model=AppealResponse)
async def read_appeal(appeal_id: int, db: Session = Depends(get_db),
                      user: Employee = Depends(check_access_level(1, 2))):
    appeal = db.query(SupportTicket).filter(SupportTicket.ticket_id == appeal_id).first()
    if appeal is None:
        raise HTTPException(status_code=404, detail="Appeal not found")
    return AppealResponse.from_orm(appeal)


# Обновление типа обращения
@app.post("/appeals/{appeal_id}/update_type")
async def update_appeal_type(appeal_id: int, category: str = Form(...), db: Session = Depends(get_db),
                             user: Employee = Depends(check_access_level(1, 2))):
    appeal = db.query(SupportTicket).filter(SupportTicket.ticket_id == appeal_id).first()
    if appeal:
        appeal.category = category
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Appeal type updated"})
    raise HTTPException(status_code=404, detail="Appeal not found")


# Обновление статуса обращения
@app.post("/appeals/{appeal_id}/update_status")
async def update_appeal_type(appeal_id: int, status: str = Form(...), db: Session = Depends(get_db)):
    appeal = db.query(SupportTicket).filter(SupportTicket.ticket_id == appeal_id).first()
    if appeal:
        appeal.status = status
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Appeal type updated"})
    raise HTTPException(status_code=404, detail="Appeal not found")


# Получение списка доступных операторов
@app.get("/appeals/available_operators/{appeal_id}")
async def get_available_operators(appeal_id: int, db: Session = Depends(get_db),
                                  user: Employee = Depends(check_access_level(1, 2))):
    current_operator_id = user.employee_id
    available_operators = db.query(Employee).filter(
        Employee.access_level.in_([1, 2]),
        Employee.employee_id != current_operator_id
    ).all()

    operators_list = [{"id": operator.employee_id, "username": operator.username} for operator in available_operators]
    return JSONResponse(status_code=200, content={"status": "success", "operators": operators_list})


# Перенос обращения к другому оператору
@app.post("/transfer_appeal/{appeal_id}")
async def update_actual_operator(appeal_id: int, new_operator_id: int = Form(...), db: Session = Depends(get_db)):
    appeal = db.query(SupportTicket).filter(SupportTicket.ticket_id == appeal_id).first()
    if appeal:
        appeal.assigned_technician_id = new_operator_id
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Appeal type updated"})
    raise HTTPException(status_code=404, detail="Appeal not found")


# Закрытие обращения
@app.post("/close_appeal/{appeal_id}")
async def close_appeal(appeal_id: int, db: Session = Depends(get_db),
                       user: Employee = Depends(check_access_level(1, 2))):
    text = 'Если вопрос был решен, то не отвечайте, пожалуйста, на это сообщение — так я смогу помочь другим клиентам быстрее 🛴'
    send_response_to_user(text, appeal_id)

    response = SupportResponse(
        ticket_id=appeal_id,
        operator_id=user.employee_id,
        message=text,
        created_at=datetime.utcnow()
    )
    db.add(response)

    db.commit()
    db.refresh(response)

    if response:
        return JSONResponse(status_code=200, content={"status": "success", "message": 'closed'})
    raise HTTPException(status_code=404, detail="Response not found")


# Получение сообщений по обращению
@app.get("/appeals/{appeal_id}/messages")
def get_messages(appeal_id: int, db: Session = Depends(get_db)):
    responses = db.query(SupportResponse).filter_by(ticket_id=appeal_id).all()
    messages = []
    for response in responses:
        if response.operator_id != -1:
            user = db.query(Employee).filter_by(employee_id=response.operator_id).first()
            sender = user.username if user else f"User ID: {response.operator_id}"
        else:
            sender = f"User ID: {response.operator_id}"
        messages.append({
            "message": response.message,
            "promo_code": response.promo_code,
            "sender": sender,
            "operator_id": response.operator_id
        })
    return messages


# Отправка сообщения по обращению
@app.post("/send_message/{appeal_id}")
async def send_message(appeal_id: int, operator_id: int = Form(...), message: str = Form(...),
                       db: Session = Depends(get_db)):
    response = SupportResponse(
        ticket_id=appeal_id,
        operator_id=operator_id,
        message=message,
        created_at=datetime.utcnow()
    )
    db.add(response)

    db.commit()
    db.refresh(response)

    if operator_id != -1:
        send_response_to_user(text=message, appeal_id=appeal_id)
        response = db.query(SupportTicket).filter(SupportTicket.ticket_id == appeal_id).first()
        response.status = 'in processing'
        response.assigned_technician_id = operator_id
        db.commit()

    return JSONResponse(status_code=200, content={"status": "success", "message": "Message sent"})


# Добавление промокода по обращению
@app.post("/add_promocode/{appeal_id}")
async def add_promocode(appeal_id: int, db: Session = Depends(get_db),
                        user: Employee = Depends(check_access_level(1, 2))):
    promo_code = str(uuid.uuid4())
    send_promocode(appeal_id, promo_code)

    response = SupportResponse(
        ticket_id=appeal_id,
        operator_id=user.employee_id,
        message=f'Извините за неудобства, ваш промокод на бесплатную поездку: **********',
        created_at=datetime.utcnow()
    )
    db.add(response)

    db.commit()
    db.refresh(response)

    if response:
        response.promo_code = promo_code
        db.commit()
        return JSONResponse(status_code=200, content={"status": "success", "promo_code": promo_code})
    raise HTTPException(status_code=404, detail="Response not found")


# Создание нового предмета
@app.post("/items/", response_model=ItemCreate)
async def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = Item(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


# Создание нового сотрудника
@app.post("/employees/", response_model=EmployeeCreate)
async def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
    db_employee = Employee(
        first_name=employee.first_name,
        last_name=employee.last_name,
        email=employee.email,
        username=employee.username,
        employee_type=employee.employee_type,
        access_level=employee.access_level,
        department=employee.department,
        position=employee.position,
        hire_date=employee.hire_date,
        phone_number=employee.phone_number,
        address=employee.address,
        status=employee.status,
        last_login_date=employee.last_login_date
    )
    db_employee.set_password(employee.password)
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee


# Создание нового клиента
@app.post("/clients/", response_model=ClientCreate)
async def create_client(client: ClientCreate, db: Session = Depends(get_db),
                        user: Employee = Depends(check_access_level(0, 0))):
    db_client = Client(**client.dict())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client


# Создание нового тикета поддержки
@app.post("/support_tickets/", response_model=SupportTicketCreate)
async def create_support_ticket(ticket: SupportTicketCreate, db: Session = Depends(get_db)):
    db_ticket = SupportTicket(**ticket.dict())
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket


# Создание новой парковки
@app.post("/parkings/", response_model=ParkingCreate)
async def create_parking(parking: ParkingCreate, db: Session = Depends(get_db),
                         user: Employee = Depends(check_access_level(0, 0))):
    db_parking = Parking(**parking.dict())
    db.add(db_parking)
    db.commit()
    db.refresh(db_parking)
    return db_parking


# Создание новой поломки
@app.post("/breakdowns/", response_model=BreakdownCreate)
async def create_breakdown(breakdown: BreakdownCreate, db: Session = Depends(get_db)):
    db_breakdown = Breakdown(**breakdown.dict())
    db.add(db_breakdown)
    db.commit()
    db.refresh(db_breakdown)
    return db_breakdown


# Получение списка поломок
@app.get("/breakdowns")
def read_breakdowns(query: str = None, db: Session = Depends(get_db),
                    user: Employee = Depends(check_access_level(3, 3))):
    if query:
        breakdowns = db.query(Breakdown).filter(Breakdown.status != 'resolved').filter(
            Breakdown.item_id == int(query)).all()
    else:
        breakdowns = db.query(Breakdown).filter(Breakdown.status != 'resolved').all()
    return breakdowns


# Обновление поломки
@app.put("/update_breakdown/{breakdown_id}", response_model=BreakdownResponse)
def update_breakdown(breakdown_id: int, breakdown: BreakdownUpdate, db: Session = Depends(get_db),
                     user: Employee = Depends(check_access_level(3, 3))):
    db_breakdown = db.query(Breakdown).filter(Breakdown.breakdown_id == breakdown_id).first()
    if db_breakdown is None:
        raise HTTPException(status_code=404, detail="Breakdown not found")
    for key, value in breakdown.dict().items():
        setattr(db_breakdown, key, value)
    db.commit()
    db.refresh(db_breakdown)
    return db_breakdown


# Получение списка курьеров
@app.get("/couriers", response_model=List[CourierStatusResponse])
def get_couriers(db: Session = Depends(get_db)):
    couriers = db.query(Employee).filter(Employee.position == 'courier').all()
    today = date.today()
    courier_statuses = []

    for courier in couriers:
        schedule = db.query(CourierSchedule).filter(
            CourierSchedule.courier_id == courier.employee_id,
            CourierSchedule.date == today
        ).first()

        if schedule:
            if schedule.start_time and not schedule.end_time:
                status = 'Начал объезд'
            elif schedule.start_time and schedule.end_time:
                status = 'Объезд окончен'
            else:
                status = 'Рабочий день не начат'
        else:
            status = 'Рабочий день не начат'

        courier_statuses.append({
            "courier_id": courier.employee_id,
            "name": f"{courier.first_name} {courier.last_name}",
            "status": status
        })

    return courier_statuses


# Создание расписания для курьеров
@app.post("/courier_schedules/", response_model=CourierScheduleResponse)
def create_courier_schedule(data: CourierScheduleCreate, db: Session = Depends(get_db)):
    start_date = datetime.strptime(data.start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(data.end_date, '%Y-%m-%d').date()

    if end_date < start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date")

    couriers = db.query(Employee).filter(Employee.position == 'courier').all()
    parkings = db.query(Parking).filter(Parking.status == 'Active').all()

    if not couriers or not parkings:
        raise HTTPException(status_code=400, detail="No couriers or parkings available")

    days = (end_date - start_date).days + 1
    num_couriers = len(couriers)
    num_parkings = len(parkings)
    parkings_per_courier = num_parkings // num_couriers

    for i in range(days):
        current_date = start_date + timedelta(days=i)
        for j, courier in enumerate(couriers):
            start_index = j * parkings_per_courier
            end_index = (j + 1) * parkings_per_courier if j != num_couriers - 1 else num_parkings
            courier_parkings = parkings[start_index:end_index]

            parking_ids = ",".join([str(parking.parking_id) for parking in courier_parkings])

            existing_schedule = db.query(CourierSchedule).filter(
                CourierSchedule.courier_id == courier.employee_id,
                CourierSchedule.date == current_date
            ).first()

            if existing_schedule:
                existing_schedule.parking_ids = parking_ids
            else:
                schedule = CourierSchedule(
                    courier_id=courier.employee_id,
                    date=current_date,
                    parking_ids=parking_ids
                )
                db.add(schedule)

    db.commit()

    return {
        "status": "success",
        "message": "Courier schedule created successfully",
        "start_date": data.start_date,
        "end_date": data.end_date
    }


# Получение списка сотрудников
@app.get("/employees/", response_model=List[EmployeeManage])
async def read_employees(skip: int = 0, limit: int = 10, db: Session = Depends(get_db),
                         user: Employee = Depends(check_access_level(0, 0))):
    employees = db.query(Employee).offset(skip).limit(limit).all()
    return employees


# Получение информации о конкретном сотруднике
@app.get("/employees/{employee_id}", response_model=EmployeeCreate)
async def read_employee(employee_id: int, db: Session = Depends(get_db),
                        user: Employee = Depends(check_access_level(0, 0))):
    employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


# Обновление информации о сотруднике
@app.put("/employees/{employee_id}", response_model=EmployeeCreate)
async def update_employee(employee_id: int, employee: EmployeeCreate, db: Session = Depends(get_db),
                          user: Employee = Depends(check_access_level(0, 0))):
    db_employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if db_employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    for key, value in employee.dict(exclude_unset=True).items():
        if key == "password" and value is None:
            continue
        setattr(db_employee, key, value)

    db.commit()
    db.refresh(db_employee)
    return db_employee


# Удаление сотрудника
@app.delete("/employees/{employee_id}")
async def delete_employee(employee_id: int, db: Session = Depends(get_db),
                          user: Employee = Depends(check_access_level(0, 0))):
    db_employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if db_employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    db.delete(db_employee)
    db.commit()
    return JSONResponse(status_code=200, content={"message": "Employee deleted"})


# Получение статистики
@app.get("/statistics", response_model=Dict[str, Any])
async def get_statistics(db: Session = Depends(get_db), user: Employee = Depends(check_access_level(2, 2))):
    def generate_date_list(start_date, days):
        return [(start_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]

    start_date = datetime.now() - timedelta(days=100)
    date_labels = generate_date_list(start_date, 100)

    def generate_random_values(size, min_val, max_val):
        return [round(random.uniform(min_val, max_val), 2) for _ in range(size)]

    today = datetime.now().strftime('%Y-%m-%d')
    today_open_appeals = random.randint(5, 15)
    today_waiting_appeals = random.randint(1, 10)
    today_closed_appeals = random.randint(5, 25)

    stats = {
        "total_employees": 100,
        "total_clients": 200,
        "total_support_tickets": 150,
        "appeals_waiting": 10,
        "appeals_processing": 5,
        "operators_online": 8,
        "avg_time_to_close": {
            "labels": date_labels,
            "values": generate_random_values(100, 1, 5)
        },
        "avg_time_to_first_response": {
            "labels": date_labels,
            "values": generate_random_values(100, 0.5, 2)
        },
        "appeal_types_by_day": {
            "labels": date_labels,
            "values_recommendation": generate_random_values(100, 10, 50),
            "values_notice": generate_random_values(100, 10, 50)
        },
        "promo_codes_by_day": {
            "labels": date_labels,
            "values": generate_random_values(100, 5, 20)
        },
        "open_appeals": {
            "labels": date_labels + [today],
            "values": generate_random_values(100, 5, 15) + [today_open_appeals]
        },
        "waiting_appeals": {
            "labels": date_labels + [today],
            "values": generate_random_values(100, 1, 10) + [today_waiting_appeals]
        },
        "closed_appeals_today": {
            "labels": date_labels + [today],
            "values": generate_random_values(100, 5, 25) + [today_closed_appeals]
        }
    }

    return stats


# Базовый маршрут
@app.get("/")
def read_root():
    return {"Hello": "World"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
