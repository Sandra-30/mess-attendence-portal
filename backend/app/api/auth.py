from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.db.database import get_db
from app.schemas import schemas
from app.crud import crud
from app.core import security
from app.models import models

router = APIRouter()

@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # Check email domain
    if not (user.email.endswith('@gmail.com') or user.email.endswith('@gecskp.ac.in')):
        raise HTTPException(status_code=400, detail="Email must end with @gmail.com or @gecskp.ac.in")

    # Check if user already exists
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Check against whitelist only for students
    if user.role == "STUDENT":
        whitelist_entry = crud.get_whitelist_by_email(db, email=user.email)
        if not whitelist_entry:
            raise HTTPException(
                status_code=403, 
                detail="Security Warning: Email not in Warden's approved whitelist. Access denied."
            )

    # Email matches whitelist, create and activate student
    # Note: In a real system, you might want to verify name and room match as well, or just rely on email
    new_user = crud.create_user(db=db, user=user, is_active=True)
    return new_user

@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    if form_data.username.strip().upper() == "WARDEN" and form_data.password.strip() == "warden@lh":
        access_token = security.create_access_token(data={"sub": "WARDEN", "role": "WARDEN"})
        return {"access_token": access_token, "token_type": "bearer"}

    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
         raise HTTPException(status_code=400, detail="Inactive user")
         
    access_token = security.create_access_token(data={"sub": user.email, "role": user.role, "name": user.name})
    return {"access_token": access_token, "token_type": "bearer"}
