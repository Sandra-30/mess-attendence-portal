from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import get_db
from app.schemas import schemas
from app.crud import crud
from app.api import deps
from app.models import models
from app.core.supabase_client import get_supabase
import uuid
import datetime

router = APIRouter()

@router.post("/whitelist", response_model=schemas.WhitelistCreate)
def add_to_whitelist(
    whitelist_entry: schemas.WhitelistCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_warden)
):
    # Check email domain
    if not (whitelist_entry.email.endswith('@gmail.com') or whitelist_entry.email.endswith('@gecskp.ac.in')):
        raise HTTPException(status_code=400, detail="Email must end with @gmail.com or @gecskp.ac.in")

    # In a real app we might upload a CSV and parse it. Here we accept individual entries.
    existing = crud.get_whitelist_by_email(db, whitelist_entry.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already in whitelist")

    existing_user = crud.get_user_by_email(db, whitelist_entry.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already registered")

    # Generate default password
    first_name = whitelist_entry.name.strip().split()[0].upper()
    room = whitelist_entry.room_number.strip().upper()
    default_password = f"{first_name}{room}"

    user_create = schemas.UserCreate(
        email=whitelist_entry.email,
        name=whitelist_entry.name,
        room_number=whitelist_entry.room_number,
        password=default_password,
        role="STUDENT"
    )
    crud.create_user(db, user_create, is_active=True)
    
    return crud.add_whitelist(db, whitelist_entry)

@router.get("/whitelist", response_model=list[schemas.WhitelistResponse])
def get_whitelist(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_warden)
):
    return db.query(models.Whitelist).order_by(models.Whitelist.id.desc()).all()

@router.post("/menu/upload")
async def upload_menu(
    file: UploadFile = File(...),
    month: int = None,
    year: int = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_warden)
):
    if not month or not year:
        today = datetime.date.today()
        month = today.month
        year = today.year

    # Upload to Supabase Storage
    try:
        supabase = get_supabase()
        
        try:
            supabase.storage.get_bucket('menus')
        except Exception:
            try:
                supabase.storage.create_bucket('menus', options={'public': True})
            except Exception:
                pass
                
        file_ext = file.filename.split('.')[-1]
        file_name = f"menus/{year}_{month}_{uuid.uuid4().hex}.{file_ext}"
        file_content = await file.read()
        
        res = supabase.storage.from_("menus").upload(file_name, file_content, {"content-type": file.content_type})
        public_url = supabase.storage.from_("menus").get_public_url(file_name)
        
        existing_menu = db.query(models.Menu).filter(
            models.Menu.year == year,
            models.Menu.month == month
        ).first()
        if existing_menu:
            existing_menu.image_url = public_url
        else:
            new_menu = models.Menu(year=year, month=month, image_url=public_url)
            db.add(new_menu)
        db.commit()
        return {"message": "Menu uploaded successfully", "image_url": public_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload to Supabase: {str(e)}")

@router.get("/headcounts")
def get_daily_headcounts(
    target_date: datetime.date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_warden)
):
    attendances = db.query(models.Attendance).filter(models.Attendance.target_date == target_date).all()
    
    total_breakfast = sum(1 for a in attendances if a.breakfast)
    total_lunch = sum(1 for a in attendances if a.lunch)
    total_dinner = sum(1 for a in attendances if a.dinner)
    
    return {
        "date": target_date,
        "breakfast": total_breakfast,
        "lunch": total_lunch,
        "dinner": total_dinner,
        "total_responses": len(attendances)
    }

@router.get("/billing-matrix")
def get_billing_matrix(
    month: int,
    year: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_warden)
):
    import calendar
    days_in_month = calendar.monthrange(year, month)[1]
    
    # Get holidays for this month
    holidays = db.query(models.Holiday).filter(
        func.extract('month', models.Holiday.date) == month,
        func.extract('year', models.Holiday.date) == year
    ).all()
    holiday_dates = {h.date for h in holidays}
    
    # Get config
    config = db.query(models.MonthlyConfig).filter(
        models.MonthlyConfig.month == month,
        models.MonthlyConfig.year == year
    ).first()
    per_day_amount = config.per_day_amount if config else 0.0

    # Get overrides
    overrides = db.query(models.MonthlyBill).filter(
        models.MonthlyBill.month == month,
        models.MonthlyBill.year == year
    ).all()
    override_dict = {o.student_id: o.amount for o in overrides}

    # Get all students
    students = db.query(models.User).filter(models.User.role == "STUDENT").all()
    
    matrix = []
    total_hostel_days = 0
    working_days = days_in_month - len(holiday_dates)
    
    for student in students:
        student_attendances = db.query(models.Attendance).filter(
            models.Attendance.student_id == student.id,
            func.extract('month', models.Attendance.target_date) == month,
            func.extract('year', models.Attendance.target_date) == year
        ).all()
        
        # Calculate explicit cuts (excluding holidays)
        cuts = 0
        for a in student_attendances:
            if not a.breakfast and not a.lunch and not a.dinner and a.target_date not in holiday_dates:
                cuts += 1
                
        days_present = max(0, working_days - cuts)
        total_hostel_days += days_present
        
        # Get fines
        fines = db.query(models.Ledger).filter(
            models.Ledger.student_id == student.id,
            func.extract('month', models.Ledger.date) == month,
            func.extract('year', models.Ledger.date) == year
        ).all()
        total_fines = sum(f.amount for f in fines)
        
        is_manual_override = student.id in override_dict
        if is_manual_override:
            mess_bill = override_dict[student.id]
        else:
            mess_bill = (days_present * per_day_amount) + total_fines + 310
        
        matrix.append({
            "student_id": student.id,
            "name": student.name,
            "email": student.email,
            "room_number": student.room_number,
            "days_present": days_present,
            "total_fines": total_fines,
            "mess_bill": mess_bill,
            "is_manual_override": is_manual_override
        })
        
    return {
        "month": month,
        "year": year,
        "total_hostel_days": total_hostel_days,
        "per_day_amount": per_day_amount,
        "student_matrix": matrix
    }

@router.post("/billing/config")
def update_billing_config(
    payload: schemas.MonthlyConfigCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_warden)
):
    config = db.query(models.MonthlyConfig).filter(
        models.MonthlyConfig.month == payload.month,
        models.MonthlyConfig.year == payload.year
    ).first()
    if config:
        config.per_day_amount = payload.per_day_amount
    else:
        config = models.MonthlyConfig(
            month=payload.month,
            year=payload.year,
            per_day_amount=payload.per_day_amount
        )
        db.add(config)
    db.commit()
    return {"message": "Configuration updated successfully"}

@router.post("/billing/override")
def update_billing_override(
    payload: schemas.MonthlyBillOverride,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_warden)
):
    override = db.query(models.MonthlyBill).filter(
        models.MonthlyBill.student_id == payload.student_id,
        models.MonthlyBill.month == payload.month,
        models.MonthlyBill.year == payload.year
    ).first()
    if override:
        override.amount = payload.amount
    else:
        override = models.MonthlyBill(
            student_id=payload.student_id,
            month=payload.month,
            year=payload.year,
            amount=payload.amount
        )
        db.add(override)
    db.commit()
    return {"message": "Bill override updated successfully"}

@router.post("/notify-bill")
def notify_bill_ready(
    month: int,
    year: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_warden)
):
    from app.crud import crud
    from sqlalchemy import func
    import calendar
    
    month_name = calendar.month_name[month]
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

    # Set as published
    if config:
        config.is_published = True
    else:
        config = models.MonthlyConfig(
            month=month,
            year=year,
            per_day_amount=0.0,
            is_published=True
        )
        db.add(config)
    db.commit()

    # Get overrides
    overrides = db.query(models.MonthlyBill).filter(
        models.MonthlyBill.month == month,
        models.MonthlyBill.year == year
    ).all()
    override_dict = {o.student_id: o.amount for o in overrides}
    
    students = db.query(models.User).filter(models.User.role == "STUDENT", models.User.is_active == True).all()
    
    count = 0
    for student in students:
        student_attendances = db.query(models.Attendance).filter(
            models.Attendance.student_id == student.id,
            func.extract('month', models.Attendance.target_date) == month,
            func.extract('year', models.Attendance.target_date) == year
        ).all()
        
        cuts = 0
        for a in student_attendances:
            if not a.breakfast and not a.lunch and not a.dinner and a.target_date not in holiday_dates:
                cuts += 1
                
        days_present = max(0, working_days - cuts)
        
        fines = db.query(models.Ledger).filter(
            models.Ledger.student_id == student.id,
            func.extract('month', models.Ledger.date) == month,
            func.extract('year', models.Ledger.date) == year
        ).all()
        total_fines = sum(f.amount for f in fines)
        
        is_manual_override = student.id in override_dict
        if is_manual_override:
            mess_bill = override_dict[student.id]
        else:
            mess_bill = (days_present * per_day_amount) + total_fines + 310
            
        from app.core.config import settings
        
        in_app_message = f"Your mess bill for {month_name} {year} is ₹{mess_bill:.2f}. Please pay it using the online portal."
        crud.create_notification(db, student.id, in_app_message)
        
        email_message = f'Your mess bill for {month_name} {year} is ₹{mess_bill:.2f}.<br><br>To view your full bill breakdown, <a href="{settings.FRONTEND_URL}" style="color: #3498db; text-decoration: none; font-weight: bold;">Log in to your Dashboard</a>.<br><br>To make the payment directly, use the official SBI portal: <a href="https://onlinesbi.sbi.bank.in/sbicollect/icollecthome.htm?saralID=-918004880" style="color: #27ae60; text-decoration: none; font-weight: bold;">Click Here to Pay Online</a>'
        
        from app.core.email import send_email_background
        background_tasks.add_task(send_email_background, student.email, f"Mess Bill Ready - {month_name} {year}", email_message)
        
        count += 1
        
    return {"message": f"Successfully notified {count} students."}

@router.post("/announce")
def broadcast_announcement(
    payload: schemas.AnnouncementCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_warden)
):
    from app.crud import crud
    
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="Announcement message cannot be empty.")
        
    students = db.query(models.User).filter(models.User.role == "STUDENT", models.User.is_active == True).all()
    
    count = 0
    for student in students:
        # Prefix with 'Announcement:' so it stands out
        crud.create_notification(db, student.id, f"📢 Announcement: {payload.message.strip()}")
        
        from app.core.email import send_email_background
        background_tasks.add_task(send_email_background, student.email, "Warden Announcement", payload.message.strip())
        
        count += 1
        
    return {"message": f"Successfully broadcasted announcement to {count} students."}

@router.get("/holidays", response_model=list[schemas.HolidayResponse])
def get_holidays(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_warden)
):
    return db.query(models.Holiday).order_by(models.Holiday.date).all()

@router.post("/holidays", response_model=schemas.HolidayResponse)
def create_holiday(
    payload: schemas.HolidayCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_warden)
):
    existing = db.query(models.Holiday).filter(models.Holiday.date == payload.date).first()
    if existing:
        raise HTTPException(status_code=400, detail="Date is already a holiday")
        
    new_holiday = models.Holiday(date=payload.date, description=payload.description)
    db.add(new_holiday)
    db.commit()
    db.refresh(new_holiday)
    return new_holiday

@router.post("/holidays/bulk", response_model=list[schemas.HolidayResponse])
def create_bulk_holidays(
    payload: schemas.HolidayBulkCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_warden)
):
    from datetime import timedelta
    delta = payload.end_date - payload.start_date
    created_holidays = []
    
    if delta.days < 0:
        raise HTTPException(status_code=400, detail="End date must be on or after start date")
        
    for i in range(delta.days + 1):
        target_date = payload.start_date + timedelta(days=i)
        existing = db.query(models.Holiday).filter(models.Holiday.date == target_date).first()
        if not existing:
            new_holiday = models.Holiday(date=target_date)
            db.add(new_holiday)
            created_holidays.append(new_holiday)
            
    db.commit()
    for h in created_holidays:
        db.refresh(h)
    return created_holidays

@router.delete("/holidays/{holiday_id}")
def delete_holiday(
    holiday_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_warden)
):
    holiday = db.query(models.Holiday).filter(models.Holiday.id == holiday_id).first()
    if not holiday:
        raise HTTPException(status_code=404, detail="Holiday not found")
        
    db.delete(holiday)
    db.commit()
    return {"message": "Holiday deleted successfully"}
