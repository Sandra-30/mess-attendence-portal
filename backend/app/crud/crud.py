from sqlalchemy.orm import Session
from app.models import models
from app.schemas import schemas
from app.core.security import get_password_hash

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def get_whitelist_by_email(db: Session, email: str):
    return db.query(models.Whitelist).filter(models.Whitelist.email == email).first()

def create_user(db: Session, user: schemas.UserCreate, is_active: bool = False):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        name=user.name,
        room_number=user.room_number,
        hashed_password=hashed_password,
        role=user.role,
        is_active=is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def add_whitelist(db: Session, whitelist: schemas.WhitelistCreate):
    db_whitelist = models.Whitelist(
        email=whitelist.email,
        name=whitelist.name,
        room_number=whitelist.room_number
    )
    db.add(db_whitelist)
    db.commit()
    db.refresh(db_whitelist)
    return db_whitelist
