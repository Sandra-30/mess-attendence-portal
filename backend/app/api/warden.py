from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
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

@router.get("/holidays")
def get_holidays(month: int, year: int, db: Session = Depends(get_db)):
    from sqlalchemy import func
    holidays = db.query(models.Holiday).filter(
        func.extract('month', models.Holiday.date) == month,
        func.extract('year', models.Holiday.date) == year
    ).all()
    return [h.date.isoformat() for h in holidays]

@router.post("/holidays/toggle")
def toggle_holiday(
    data: dict,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_warden)
):
    date_str = data.get("date")
    if not date_str:
        raise HTTPException(status_code=400, detail="Date is required")
        
    from datetime import datetime
    target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    holiday = db.query(models.Holiday).filter(models.Holiday.date == target_date).first()
    if holiday:
        db.delete(holiday)
        db.commit()
        return {"status": "removed", "date": date_str}
    else:
        new_holiday = models.Holiday(date=target_date)
        db.add(new_holiday)
        db.commit()
        return {"status": "added", "date": date_str}

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
    from sqlalchemy import func
    holidays = db.query(models.Holiday).filter(
        func.extract('month', models.Holiday.date) == month,
        func.extract('year', models.Holiday.date) == year
    ).all()
    holiday_dates = {h.date for h in holidays}
    working_days = days_in_month - len(holiday_dates)
    
    # Get all students
    students = db.query(models.User).filter(models.User.role == "STUDENT").all()
    
    matrix = []
    total_hostel_days = 0
    
    for student in students:
        # Find attendance for this student in the given month/year
        student_attendances = db.query(models.Attendance).filter(
            models.Attendance.student_id == student.id,
            func.extract('month', models.Attendance.target_date) == month,
            func.extract('year', models.Attendance.target_date) == year
        ).all()
        
        # We only count cuts for non-holiday days
        # A cut is an attendance record where ALL meals are false
        cuts = 0
        for a in student_attendances:
            if a.target_date not in holiday_dates:
                if not a.breakfast and not a.lunch and not a.dinner:
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
        
        matrix.append({
            "student_id": student.id,
            "name": student.name,
            "email": student.email,
            "room_number": student.room_number,
            "days_present": days_present,
            "total_fines": total_fines
        })
        
    return {
        "month": month,
        "year": year,
        "total_hostel_days": total_hostel_days,
        "student_matrix": matrix
    }

@router.post("/notify-bill")
def notify_bill_ready(
    month: int,
    year: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_warden)
):
    from app.crud import crud
    import calendar
    
    month_name = calendar.month_name[month]
    students = db.query(models.User).filter(models.User.role == "STUDENT", models.User.is_active == True).all()
    
    count = 0
    for student in students:
        crud.create_notification(db, student.id, f"The mess bill for {month_name} {year} is now ready. Please check the notice board.")
        count += 1
        
    return {"message": f"Successfully notified {count} students."}

@router.post("/announce")
def broadcast_announcement(
    payload: schemas.AnnouncementCreate,
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
        count += 1
        
    return {"message": f"Successfully broadcasted announcement to {count} students."}
