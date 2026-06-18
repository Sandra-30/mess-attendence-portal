from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime

class UserBase(BaseModel):
    email: EmailStr
    name: str
    room_number: Optional[str] = None
    admission_year: Optional[str] = None
    year_of_study: Optional[int] = None

class UserCreate(UserBase):
    password: str
    role: str = "STUDENT"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    role: str
    is_active: bool

    class Config:
        from_attributes = True

class WhitelistBase(BaseModel):
    email: EmailStr
    name: str
    room_number: str
    admission_year: Optional[str] = None
    year_of_study: Optional[int] = None

class WhitelistCreate(WhitelistBase):
    admission_year: str
    year_of_study: int

class WhitelistResponse(WhitelistBase):
    id: int

    class Config:
        from_attributes = True

class AttendanceUpdate(BaseModel):
    breakfast: bool
    lunch: bool
    dinner: bool

class AttendanceResponse(BaseModel):
    id: int
    target_date: date
    breakfast: bool
    lunch: bool
    dinner: bool
    is_locked: bool

    class Config:
        from_attributes = True

class LedgerResponse(BaseModel):
    id: int
    date: date
    amount: float
    description: str

    class Config:
        from_attributes = True

class DailyAttendanceResponse(BaseModel):
    student_id: int
    name: Optional[str] = None
    room_number: Optional[str] = None
    breakfast: bool
    lunch: bool
    dinner: bool

class ChangePassword(BaseModel):
    old_password: str
    new_password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class NotificationResponse(BaseModel):
    id: int
    student_id: int
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

class AnnouncementCreate(BaseModel):
    message: str

class HolidayCreate(BaseModel):
    date: date
    description: Optional[str] = None

class HolidayBulkCreate(BaseModel):
    start_date: date
    end_date: date

class HolidayResponse(BaseModel):
    id: int
    date: date
    description: Optional[str] = None

    class Config:
        from_attributes = True
