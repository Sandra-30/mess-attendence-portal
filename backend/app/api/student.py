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

@router.get("/holidays", response_model=list[schemas.HolidayResponse])
def get_holidays(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    return db.query(models.Holiday).order_by(models.Holiday.date).all()

@router.get("/daily-attendance", response_model=list[schemas.DailyAttendanceResponse])
def get_daily_attendance(
    target_date: datetime.date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    students = db.query(models.User).filter(models.User.role == "STUDENT").all()
    
    # Get all attendance records for the target date
    attendances = db.query(models.Attendance).filter(models.Attendance.target_date == target_date).all()
    attendance_map = {a.student_id: a for a in attendances}
    
    roster = []
    for s in students:
        att = attendance_map.get(s.id)
        if att:
            roster.append({
                "student_id": s.id,
                "name": s.name,
                "room_number": s.room_number,
                "breakfast": att.breakfast,
                "lunch": att.lunch,
                "dinner": att.dinner
            })
        else:
            roster.append({
                "student_id": s.id,
                "name": s.name,
                "room_number": s.room_number,
                "breakfast": False,
                "lunch": False,
                "dinner": False
            })
            
    # Sort by room number
    # Room numbers might be strings like "A-101", so sort as strings
    roster.sort(key=lambda x: str(x['room_number']))
    return roster

@router.get("/bill/month/{year}/{month}")
def get_monthly_bill(
    year: int,
    month: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user)
):
    from sqlalchemy import func
    import calendar
    days_in_month = calendar.monthrange(year, month)[1]
    
    # Get holidays for this month
    holidays = db.query(models.Holiday).filter(
        func.extract('month', models.Holiday.date) == month,
        func.extract('year', models.Holiday.date) == year
    ).all()
    holiday_dates = {h.date for h in holidays}
    working_days = days_in_month - len(holiday_dates)

    # Get config
    config = db.query(models.MonthlyConfig).filter(
        models.MonthlyConfig.month == month,
        models.MonthlyConfig.year == year
    ).first()
    per_day_amount = config.per_day_amount if config else 0.0

    # Get overrides
    override = db.query(models.MonthlyBill).filter(
        models.MonthlyBill.student_id == current_user.id,
        models.MonthlyBill.month == month,
        models.MonthlyBill.year == year
    ).first()

    student_attendances = db.query(models.Attendance).filter(
        models.Attendance.student_id == current_user.id,
        func.extract('month', models.Attendance.target_date) == month,
        func.extract('year', models.Attendance.target_date) == year
    ).all()
    
    cuts = 0
    for a in student_attendances:
        if not a.breakfast and not a.lunch and not a.dinner and a.target_date not in holiday_dates:
            cuts += 1
            
    days_present = max(0, working_days - cuts)
    
    fines = db.query(models.Ledger).filter(
        models.Ledger.student_id == current_user.id,
        func.extract('month', models.Ledger.date) == month,
        func.extract('year', models.Ledger.date) == year
    ).all()
    total_fines = sum(f.amount for f in fines)
    
    is_manual_override = override is not None
    if is_manual_override:
        mess_bill = override.amount
    else:
        mess_bill = (days_present * per_day_amount) + total_fines + 310
        
    return {
        "month": month,
        "year": year,
        "per_day_amount": per_day_amount,
        "days_present": days_present,
        "penalties": total_fines,
        "total_bill": mess_bill,
        "is_manual_override": is_manual_override
    }
