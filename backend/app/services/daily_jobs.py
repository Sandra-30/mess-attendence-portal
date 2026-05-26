import logging
import datetime
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models import models
from app.core.config import settings

logger = logging.getLogger(__name__)

def evaluate_dynamic_rules():
    logger.info("Starting daily dynamic rules evaluation for T-3 and T-2...")
    db: Session = SessionLocal()
    try:
        today = datetime.date.today()
        t_minus_3_date = today + datetime.timedelta(days=3)
        t_minus_2_date = today + datetime.timedelta(days=2)
        
        # All students
        students = db.query(models.User).filter(models.User.role == "STUDENT", models.User.is_active == True).all()
        
        for student in students:
            # ---------------- T-3 Logic ----------------
            # At T-3 Days:
            # - If marked -> Lock permanently
            # - If blank -> Leave unlocked, trigger Reminder Email
            t3_att = db.query(models.Attendance).filter(
                models.Attendance.student_id == student.id,
                models.Attendance.target_date == t_minus_3_date
            ).first()
            
            if t3_att and (t3_att.breakfast or t3_att.lunch or t3_att.dinner):
                t3_att.is_locked = True
            else:
                # Still blank, trigger automated reminder email (mocked as console log)
                logger.info(f"REMINDER EMAIL: Student {student.name} ({student.email}), please log in to mark attendance for {t_minus_3_date}. Link: https://production-app-url/login")
            
            # ---------------- T-2 Logic ----------------
            # At T-2 Days:
            # - If blank -> Lock permanently. IMMEDIATELY implement static fine onto ledger.
            t2_att = db.query(models.Attendance).filter(
                models.Attendance.student_id == student.id,
                models.Attendance.target_date == t_minus_2_date
            ).first()
            
            if not t2_att or not (t2_att.breakfast or t2_att.lunch or t2_att.dinner):
                # Lock permanent by creating a blank locked record if it doesn't exist
                if not t2_att:
                    t2_att = models.Attendance(
                        target_date=t_minus_2_date,
                        student_id=student.id,
                        breakfast=False,
                        lunch=False,
                        dinner=False,
                        is_locked=True
                    )
                    db.add(t2_att)
                else:
                    t2_att.is_locked = True
                
                # Apply static fine amount onto ledger
                fine = models.Ledger(
                    student_id=student.id,
                    date=today, # implemented "on this day (T-2)"
                    amount=settings.FINE_AMOUNT,
                    description=f"Late attendance penalty for {t_minus_2_date}"
                )
                db.add(fine)
            else:
                # It was marked and likely already locked from T-3, but ensure it's locked
                t2_att.is_locked = True

        db.commit()
        logger.info("Daily evaluation completed successfully.")
    except Exception as e:
        logger.error(f"Error during daily evaluation: {e}")
        db.rollback()
    finally:
        db.close()
