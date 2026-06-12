from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import date, datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    name = Column(String)
    room_number = Column(String)
    role = Column(String, default="STUDENT") # WARDEN or STUDENT
    is_active = Column(Boolean, default=False)
    
    attendances = relationship("Attendance", back_populates="student")
    fines = relationship("Ledger", back_populates="student")
    notifications = relationship("Notification", back_populates="student")

class Whitelist(Base):
    __tablename__ = "whitelist"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    room_number = Column(String)

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    target_date = Column(Date, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    breakfast = Column(Boolean, default=False)
    lunch = Column(Boolean, default=False)
    dinner = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)

    student = relationship("User", back_populates="attendances")



class Ledger(Base):
    __tablename__ = "ledger"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, index=True)
    amount = Column(Float)
    description = Column(String)

    student = relationship("User", back_populates="fines")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    message = Column(String)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", back_populates="notifications")

class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, unique=True, index=True)
    description = Column(String, nullable=True)
