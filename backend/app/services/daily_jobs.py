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
                # Create in-app notification
                notif = models.Notification(
                    student_id=student.id, 
                    message=f"Reminder: You have not marked your attendance for {t_minus_3_date}. You will be billed by default."
                )
                db.add(notif)
                
                # Send email reminder
                try:
                    from app.core.email import send_email_background
                    send_email_background(
                        to_email=student.email,
                        subject=f"Action Required: Mess Attendance for {t_minus_3_date}",
                        body_text=f"Reminder: You have not marked your mess attendance for {t_minus_3_date}.\n\nPlease log in to the portal to mark your attendance, otherwise you will be billed by default.\n\nPortal Link: {settings.FRONTEND_URL}"
                    )
                except Exception as e:
                    logger.error(f"Failed to send T-3 reminder email to {student.email}: {e}")
            
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

def generate_monthly_summary():
    logger.info("Starting monthly summary notification generation...")
    db: Session = SessionLocal()
    try:
        from sqlalchemy import func
        # Run on the 1st of the month, so get previous month
        today = datetime.date.today()
        first = today.replace(day=1)
        last_month = first - datetime.timedelta(days=1)
        target_month = last_month.month
        target_year = last_month.year
        import calendar
        days_in_month = calendar.monthrange(target_year, target_month)[1]
        
        students = db.query(models.User).filter(models.User.role == "STUDENT", models.User.is_active == True).all()
        for student in students:
            attendances = db.query(models.Attendance).filter(
                models.Attendance.student_id == student.id,
                func.extract('month', models.Attendance.target_date) == target_month,
                func.extract('year', models.Attendance.target_date) == target_year
            ).all()
            
            cuts = sum(1 for a in attendances if not a.breakfast and not a.lunch and not a.dinner)
            days_present = days_in_month - cuts
            
            notif = models.Notification(
                student_id=student.id,
                message=f"Monthly Summary for {calendar.month_name[target_month]} {target_year}: {days_present} Mess Days, {cuts} Mess Cuts."
            )
            db.add(notif)
            
        db.commit()
        logger.info("Monthly summary generated successfully.")
    except Exception as e:
        logger.error(f"Error generating monthly summary: {e}")
        db.rollback()
    finally:
        db.close()

def ping_database():
    """
    A simple ping function to keep the database alive if it's running on a free tier 
    like Supabase that snoozes after 7 days of inactivity.
    """
    logger.info("Pinging database to keep it awake...")
    db: Session = SessionLocal()
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        logger.info("Database ping successful.")
    except Exception as e:
        logger.error(f"Error pinging database: {e}")
    finally:
        db.close()
