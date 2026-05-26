from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.db.database import Base
from datetime import date

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

class Menu(Base):
    __tablename__ = "menus"

    id = Column(Integer, primary_key=True, index=True)
    month = Column(Integer, index=True)
    year = Column(Integer, index=True)
    image_url = Column(String)

class Ledger(Base):
    __tablename__ = "ledger"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date, index=True)
    amount = Column(Float)
    description = Column(String)

    student = relationship("User", back_populates="fines")
