from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db.database import engine, Base
from app.models import models
from app.api import auth, warden, student
from app.services.scheduler import start_scheduler

# Create tables if they don't exist
models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the scheduler when the app starts
    scheduler = start_scheduler()
    yield
    # Shutdown the scheduler when the app stops
    scheduler.shutdown()

app = FastAPI(title="Hostel Mess Attendance Management System", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(warden.router, prefix="/api/warden", tags=["warden"])
app.include_router(student.router, prefix="/api/student", tags=["student"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Hostel Mess Attendance System API"}
