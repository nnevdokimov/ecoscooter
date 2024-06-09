from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class ItemCreate(BaseModel):
    item_type: str
    model: str
    status: str
    location: str
    deployment_date: datetime
    last_service_date: Optional[datetime] = None
    last_location_update: Optional[str] = None
    movement_history: Optional[str] = None
    working_hours: Optional[int] = None

    class Config:
        from_attributes = True


class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    username: str
    password: Optional[str] = None
    employee_type: str
    access_level: int
    department: str
    position: str
    hire_date: datetime
    phone_number: Optional[str] = None
    address: Optional[str] = None
    status: str
    last_login_date: Optional[datetime] = datetime.utcnow()

    class Config:
        from_attributes = True


class EmployeeManage(BaseModel):
    employee_id: int
    first_name: str
    last_name: str
    email: str
    username: str
    password: str
    employee_type: str
    access_level: int
    department: str
    position: str
    hire_date: datetime
    phone_number: Optional[str] = None
    address: Optional[str] = None
    status: str
    last_login_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class ClientCreate(BaseModel):
    full_name: str
    email: str
    dob: datetime
    phone_number: str
    registration_date: datetime
    membership_type: str
    payment_details: Optional[str] = None
    ride_history: Optional[str] = None
    active_bookings: Optional[str] = None

    class Config:
        from_attributes = True


class SupportTicketCreate(BaseModel):
    user_id: int
    category: str
    description: str
    status: str
    creation_date: datetime
    last_update_date: datetime
    assigned_technician_id: Optional[int] = None
    resolution_details: Optional[str] = None
    closure_date: Optional[datetime] = None
    promocode: Optional[str] = None

    class Config:
        from_attributes = True


class SupportResponseCreate(BaseModel):
    ticket_id: int
    operator_id: int
    message: Optional[str] = None
    promo_code: Optional[str] = None

    class Config:
        from_attributes = True


class SupportResponseResponse(BaseModel):
    id: int
    ticket_id: int
    operator_id: int
    message: Optional[str] = None
    created_at: datetime
    promo_code: Optional[str] = None

    class Config:
        from_attributes = True


class AppealResponse(BaseModel):
    ticket_id: int
    user_id: int
    category: str
    description: str
    status: str
    creation_date: datetime
    last_update_date: datetime
    assigned_technician_id: Optional[int] = None
    resolution_details: Optional[str] = None
    closure_date: Optional[datetime] = None
    promocode: Optional[str] = None

    class Config:
        from_attributes = True


class AppealsResponse(BaseModel):
    appeals_waiting: List[AppealResponse]
    appeals_processing: List[AppealResponse]

    class Config:
        from_attributes = True


class ParkingCreate(BaseModel):
    location: str
    desired_scooter_quantity: int
    current_scooter_quantity: int
    last_updated: datetime
    area_size: Optional[int] = None
    parking_type: str
    status: str

    class Config:
        from_attributes = True


class BreakdownCreate(BaseModel):
    item_id: int
    reported_date: datetime
    breakdown_type: str
    description: str
    status: str
    reported_by: str
    assigned_to: Optional[str] = None
    priority_level: str
    resolution_date: Optional[datetime] = None
    resolution_details: Optional[str] = None
    downtime_duration: Optional[int] = None
    parts_replaced: Optional[str] = None
    maintenance_notes: Optional[str] = None
    follow_up_actions: Optional[str] = None

    class Config:
        orm_mode = True

class BreakdownUpdate(BaseModel):
    breakdown_type: str
    description: str
    priority_level: str
    status: str
    maintenance_notes: Optional[str] = None

    class Config:
        orm_mode = True

class BreakdownResponse(BaseModel):
    breakdown_id: int
    item_id: int
    breakdown_type: str
    description: str
    priority_level: str
    status: str
    maintenance_notes: Optional[str]

    class Config:
        orm_mode = True


class CourierScheduleCreate(BaseModel):
    courier_id: int
    date: datetime
    start_time: datetime
    end_time: datetime
    parking_ids: Optional[str] = None
    total_distance: Optional[int] = None
    route_details: Optional[str] = None
    special_instructions: Optional[str] = None

    class Config:
        from_attributes = True
