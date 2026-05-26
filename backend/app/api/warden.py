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
        file_ext = file.filename.split('.')[-1]
        file_name = f"menus/{year}_{month}_{uuid.uuid4().hex}.{file_ext}"
        file_content = await file.read()
        
        # We assume the bucket 'menus' exists and is public in Supabase Storage
        res = supabase.storage.from_("menus").upload(file_name, file_content, {"content-type": file.content_type})
        
        # Get public URL
        public_url = supabase.storage.from_("menus").get_public_url(file_name)
        
        # Save to DB
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
        
        days_present = 0
        for a in student_attendances:
            if a.breakfast or a.lunch or a.dinner:
                days_present += 1
                
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
