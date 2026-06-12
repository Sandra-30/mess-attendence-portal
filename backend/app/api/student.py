from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas import schemas
from app.api import deps
from app.models import models
import datetime

router = APIRouter()



@router.get("/attendance/month/{year}/{month}", response_model=list[schemas.AttendanceResponse])
def get_monthly_attendance(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    import calendar
    _, num_days = calendar.monthrange(year, month)
    start_date = datetime.date(year, month, 1)
    end_date = datetime.date(year, month, num_days)
    
    attendances = db.query(models.Attendance).filter(
        models.Attendance.student_id == current_user.id,
        models.Attendance.target_date >= start_date,
        models.Attendance.target_date <= end_date
    ).all()
    
    return attendances

@router.get("/holidays")
def get_holidays(
    month: int,
    year: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    from sqlalchemy import func
    holidays = db.query(models.Holiday).filter(
        func.extract('month', models.Holiday.date) == month,
        func.extract('year', models.Holiday.date) == year
    ).all()
    return [h.date.isoformat() for h in holidays]

@router.get("/attendance/{target_date}", response_model=schemas.AttendanceResponse)
def get_attendance(
    target_date: datetime.date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    attendance = db.query(models.Attendance).filter(
        models.Attendance.student_id == current_user.id,
        models.Attendance.target_date == target_date
    ).first()
    
    if not attendance:
        # Return a default unlocked empty state so UI can render checkboxes
        return schemas.AttendanceResponse(
            id=0, target_date=target_date, 
            breakfast=False, lunch=False, dinner=False, is_locked=False
        )
    return attendance

@router.post("/attendance/{target_date}", response_model=schemas.AttendanceResponse)
def update_attendance(
    target_date: datetime.date,
    attendance_update: schemas.AttendanceUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    attendance = db.query(models.Attendance).filter(
        models.Attendance.student_id == current_user.id,
        models.Attendance.target_date == target_date
    ).first()
    
    if attendance and attendance.is_locked:
        raise HTTPException(status_code=403, detail="Attendance for this date is permanently locked.")
        
    # Check if T-2 or T-3 rules would naturally block it (in case job hasn't run yet)
    today = datetime.date.today()
    delta = (target_date - today).days
    
    if delta <= 2:
        raise HTTPException(status_code=403, detail="Too late to update attendance for this date (T-2 rule).")
        
    if not attendance:
        attendance = models.Attendance(
            target_date=target_date,
            student_id=current_user.id,
            breakfast=attendance_update.breakfast,
            lunch=attendance_update.lunch,
            dinner=attendance_update.dinner,
            is_locked=False
        )
        db.add(attendance)
    else:
        attendance.breakfast = attendance_update.breakfast
        attendance.lunch = attendance_update.lunch
        attendance.dinner = attendance_update.dinner
        
    db.commit()
    db.refresh(attendance)
    return attendance

@router.get("/fines", response_model=list[schemas.LedgerResponse])
def get_fines(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    fines = db.query(models.Ledger).filter(models.Ledger.student_id == current_user.id).order_by(models.Ledger.date.desc()).all()
    return fines

@router.post("/change-password")
def change_password(
    password_data: schemas.ChangePassword,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    from app.core.security import get_password_hash, verify_password
    
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")
        
    current_user.hashed_password = get_password_hash(password_data.new_password)
    db.commit()
    return {"message": "Password updated successfully"}

@router.get("/notifications", response_model=list[schemas.NotificationResponse])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    from app.crud import crud
    return crud.get_student_notifications(db, current_user.id)

@router.post("/notifications/{notification_id}/read", response_model=schemas.NotificationResponse)
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    from app.crud import crud
    notif = crud.mark_notification_read(db, notification_id, current_user.id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif
