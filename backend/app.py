import uuid
from datetime import datetime

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
    ItemCreate, EmployeeCreate, ClientCreate, SupportTicketCreate, ParkingCreate, BreakdownCreate,
    CourierScheduleCreate,
    AppealResponse, AppealsResponse, SupportResponseCreate, SupportResponseResponse
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


# Endpoints
@app.post("/token")
async def login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(Employee).filter(Employee.username == username).first()
    if user is None or not user.check_password(password):
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    return {"access_token": str(user.employee_id), "token_type": "bearer"}


@app.get("/appeals", response_model=AppealsResponse)
async def read_appeals(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
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
async def read_appeal(appeal_id: int, db: Session = Depends(get_db)):
    appeal = db.query(SupportTicket).filter(SupportTicket.ticket_id == appeal_id).first()
    if appeal is None:
        raise HTTPException(status_code=404, detail="Appeal not found")
    return AppealResponse.from_orm(appeal)


@app.post("/appeals/{appeal_id}/update_type")
async def update_appeal_type(appeal_id: int, category: str = Form(...), db: Session = Depends(get_db)):
    appeal = db.query(SupportTicket).filter(SupportTicket.ticket_id == appeal_id).first()
    if appeal:
        appeal.category = category
        db.commit()
        return JSONResponse(status_code=200, content={"message": "Appeal type updated"})
    raise HTTPException(status_code=404, detail="Appeal not found")


@app.post("/send_message/{appeal_id}")
async def send_message(appeal_id: int, operator_id: int = Form(...), message: str = Form(...),
                       db: Session = Depends(get_db)):
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
async def add_promocode(appeal_id: int, db: Session = Depends(get_db)):
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


@app.post("/clients/", response_model=ClientCreate)
async def create_client(client: ClientCreate, db: Session = Depends(get_db)):
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
async def create_parking(parking: ParkingCreate, db: Session = Depends(get_db)):
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


@app.post("/courier_schedules/", response_model=CourierScheduleCreate)
async def create_courier_schedule(schedule: CourierScheduleCreate, db: Session = Depends(get_db)):
    db_schedule = CourierSchedule(**schedule.dict())
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    return db_schedule


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
