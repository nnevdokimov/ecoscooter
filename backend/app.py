import uuid
from datetime import datetime
from typing import List, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, Form
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from backend.send_response import send_response_to_user
from backend.models import (
    Base, engine, SessionLocal, Item, Employee, Client, SupportTicket, Parking, Breakdown, CourierSchedule,
    SupportResponse
)
from backend.schemas import (
    ItemCreate, EmployeeCreate, EmployeeManage, ClientCreate, SupportTicketCreate, ParkingCreate, BreakdownCreate,
    CourierScheduleCreate,
    AppealResponse, AppealsResponse, SupportResponseCreate, SupportResponseResponse, BreakdownResponse, BreakdownUpdate
)

# Create the database tables
Base.metadata.create_all(bind=engine)

# Initialize password context for hashing passwords
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Create FastAPI app
app = FastAPI()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_access_level(lower: int, higher:int):
    def access_level_dependency(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
        user_id = int(token)
        user = db.query(Employee).filter(Employee.employee_id == user_id).first()
        if user is None or (user.access_level != 0 and (user.access_level < lower or user.access_level > higher)):
            raise HTTPException(status_code=403, detail="Insufficient access level")
        return user

    return access_level_dependency


# Endpoints
@app.post("/token")
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(Employee).filter(Employee.username == username).first()
    if user is None or not user.check_password(password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {"user_id": user.employee_id, "access_token": str(user.employee_id), "token_type": "bearer"}


@app.get("/user")
async def get_user_data(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user_id = int(token)
    user = db.query(Employee).filter(Employee.employee_id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user.employee_id, "username": user.username, "access_level": user.access_level}


@app.get("/appeals", response_model=AppealsResponse)
async def read_appeals(skip: int = 0, limit: int = 10, db: Session = Depends(get_db),
                       user: Employee = Depends(check_access_level(1,2))):
    appeals_waiting = db.query(SupportTicket).filter(SupportTicket.status == 'waiting').offset(skip).limit(limit).all()
    appeals_processing = db.query(SupportTicket).filter(SupportTicket.status == 'in processing').offset(skip).limit(
        limit).all()

    appeals_waiting_response = [AppealResponse.from_orm(appeal) for appeal in appeals_waiting]
    appeals_processing_response = [AppealResponse.from_orm(appeal) for appeal in appeals_processing]

    return AppealsResponse(appeals_waiting=appeals_waiting_response, appeals_processing=appeals_processing_response)


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


@app.get("/appeals/{appeal_id}", response_model=AppealResponse)
async def read_appeal(appeal_id: int, db: Session = Depends(get_db), user: Employee = Depends(check_access_level(1,2))):
    appeal = db.query(SupportTicket).filter(SupportTicket.ticket_id == appeal_id).first()
    if appeal is None:
        raise HTTPException(status_code=404, detail="Appeal not found")
    return AppealResponse.from_orm(appeal)


@app.post("/appeals/{appeal_id}/update_type")
async def update_appeal_type(appeal_id: int, category: str = Form(...), db: Session = Depends(get_db),
                             user: Employee = Depends(check_access_level(1,2))):
    appeal = db.query(SupportTicket).filter(SupportTicket.ticket_id == appeal_id).first()
    if appeal:
        appeal.category = category
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Appeal type updated"})
    raise HTTPException(status_code=404, detail="Appeal not found")


@app.post("/send_message/{appeal_id}")
async def send_message(appeal_id: int, operator_id: int = Form(...), message: str = Form(...),
                       db: Session = Depends(get_db), user: Employee = Depends(check_access_level(1,2))):
    # Try to find an existing response
    response = db.query(SupportResponse).filter(SupportResponse.ticket_id == appeal_id).first()

    if response:
        # If a response exists, update it
        response.message = message
        response.created_at = datetime.utcnow()
    else:
        # Otherwise, create a new response
        response = SupportResponse(
            ticket_id=appeal_id,
            operator_id=operator_id,
            message=message,
            created_at=datetime.utcnow()
        )
        db.add(response)

    db.commit()
    db.refresh(response)  # Refresh the response to get updated data

    # Send the response to the user (assuming send_response_to_user is defined elsewhere)
    send_response_to_user(text=message, appeal_id=appeal_id, promocode=response.promo_code)

    return JSONResponse(status_code=200, content={"status": "success", "message": "Message sent"})


@app.post("/add_promocode/{appeal_id}")
async def add_promocode(appeal_id: int, db: Session = Depends(get_db), user: Employee = Depends(check_access_level(1, 2))):
    promo_code = str(uuid.uuid4())
    response = db.query(SupportResponse).filter(SupportResponse.ticket_id == appeal_id).first()
    if response:
        response.promo_code = promo_code
        db.commit()
        return JSONResponse(status_code=200, content={"status": "success", "promo_code": promo_code})
    raise HTTPException(status_code=404, detail="Response not found")


@app.post("/items/", response_model=ItemCreate)
async def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = Item(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@app.post("/employees/", response_model=EmployeeCreate)
async def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db),
                          user: Employee = Depends(check_access_level(0,0))):
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


@app.post("/clients/", response_model=ClientCreate)
async def create_client(client: ClientCreate, db: Session = Depends(get_db),
                        user: Employee = Depends(check_access_level(0,0))):
    db_client = Client(**client.dict())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client


@app.post("/support_tickets/", response_model=SupportTicketCreate)
async def create_support_ticket(ticket: SupportTicketCreate, db: Session = Depends(get_db)):
    db_ticket = SupportTicket(**ticket.dict())
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket


@app.post("/parkings/", response_model=ParkingCreate)
async def create_parking(parking: ParkingCreate, db: Session = Depends(get_db),
                         user: Employee = Depends(check_access_level(0,0))):
    db_parking = Parking(**parking.dict())
    db.add(db_parking)
    db.commit()
    db.refresh(db_parking)
    return db_parking


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
                        user: Employee = Depends(check_access_level(3,3))):
    if query:
        breakdowns = db.query(Breakdown).filter(Breakdown.status != 'resolved').filter(Breakdown.item_id == int(query)).all()
    else:
        breakdowns = db.query(Breakdown).filter(Breakdown.status != 'resolved').all()
    return breakdowns


# Обновление поломки
@app.put("/update_breakdown/{breakdown_id}", response_model=BreakdownResponse)
def update_breakdown(breakdown_id: int, breakdown: BreakdownUpdate, db: Session = Depends(get_db),
                        user: Employee = Depends(check_access_level(3,3))):
    db_breakdown = db.query(Breakdown).filter(Breakdown.breakdown_id == breakdown_id).first()
    if db_breakdown is None:
        raise HTTPException(status_code=404, detail="Breakdown not found")
    for key, value in breakdown.dict().items():
        setattr(db_breakdown, key, value)
    db.commit()
    db.refresh(db_breakdown)
    return db_breakdown


@app.post("/courier_schedules/", response_model=CourierScheduleCreate)
async def create_courier_schedule(schedule: CourierScheduleCreate, db: Session = Depends(get_db)):
    db_schedule = CourierSchedule(**schedule.dict())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule


@app.get("/employees/", response_model=List[EmployeeManage])
async def read_employees(skip: int = 0, limit: int = 10, db: Session = Depends(get_db),
                         user: Employee = Depends(check_access_level(0,0))):
    employees = db.query(Employee).offset(skip).limit(limit).all()

    return employees


@app.get("/employees/{employee_id}", response_model=EmployeeCreate)
async def read_employee(employee_id: int, db: Session = Depends(get_db),
                        user: Employee = Depends(check_access_level(0,0))):
    employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@app.put("/employees/{employee_id}", response_model=EmployeeCreate)
async def update_employee(employee_id: int, employee: EmployeeCreate, db: Session = Depends(get_db),
                          user: Employee = Depends(check_access_level(0,0))):
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


@app.delete("/employees/{employee_id}")
async def delete_employee(employee_id: int, db: Session = Depends(get_db),
                          user: Employee = Depends(check_access_level(0,0))):
    db_employee = db.query(Employee).filter(Employee.employee_id == employee_id).first()
    if db_employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    db.delete(db_employee)
    db.commit()
    return JSONResponse(status_code=200, content={"message": "Employee deleted"})


@app.get("/statistics", response_model=Dict[str, Any])
async def get_statistics(db: Session = Depends(get_db), user: Employee = Depends(check_access_level(2,2))):
    # Пример сбора статистики, этот код нужно адаптировать под ваши нужды
    total_employees = db.query(Employee).count()
    total_clients = db.query(Client).count()
    total_support_tickets = db.query(SupportTicket).count()
    appeals_waiting = db.query(SupportTicket).filter(SupportTicket.status == 'waiting').count()
    appeals_processing = db.query(SupportTicket).filter(SupportTicket.status == 'in processing').count()

    statistics = {
        "total_employees": total_employees,
        "total_clients": total_clients,
        "total_support_tickets": total_support_tickets,
        "appeals_waiting": appeals_waiting,
        "appeals_processing": appeals_processing,
        # Добавьте другие необходимые метрики
    }

    return statistics


@app.get("/")
def read_root():
    return {"Hello": "World"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
