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

def get_student_notifications(db: Session, student_id: int):
    return db.query(models.Notification).filter(
        models.Notification.student_id == student_id
    ).order_by(models.Notification.created_at.desc()).all()

def create_notification(db: Session, student_id: int, message: str):
    db_notif = models.Notification(student_id=student_id, message=message)
    db.add(db_notif)
    db.commit()
    db.refresh(db_notif)
    return db_notif

def mark_notification_read(db: Session, notification_id: int, student_id: int):
    notif = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.student_id == student_id
    ).first()
    if notif:
        notif.is_read = True
        db.commit()
        db.refresh(notif)
    return notif
