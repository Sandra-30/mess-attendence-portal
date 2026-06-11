import logging
import datetime
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models import models
from app.core.config import settings
from app.services.email_service import send_email

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
                # Still blank, trigger automated reminder email
                logger.info(f"Dispatching REMINDER EMAIL to Student {student.name} ({student.email}) for {t_minus_3_date}")
                
                subject = f"Action Required: Mess Attendance for {t_minus_3_date.strftime('%d %b %Y')}"
                html_body = f"""
                <html>
                <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                        <h2 style="color: #2563eb;">Mess Attendance Reminder</h2>
                        <p>Hi <strong>{student.name}</strong>,</p>
                        <p>You have not marked your attendance for <strong>{t_minus_3_date.strftime('%A, %d %B %Y')}</strong>.</p>
                        <p style="background-color: #fef2f2; border-left: 4px solid #ef4444; padding: 10px; color: #b91c1c;">
                            <strong>Warning:</strong> If you do not mark your attendance, the system will automatically assume you are <strong>Present</strong> and you will be billed for all meals. Furthermore, you may incur a late fine.
                        </p>
                        <p>Please log in to the portal immediately to update your status.</p>
                        <a href="https://mess-attendence-portal.vercel.app" style="display: inline-block; background-color: #2563eb; color: #fff; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">Log In to Portal</a>
                        <p style="margin-top: 20px; font-size: 0.9em; color: #666;">Thank you,<br/>Warden Administration</p>
                    </div>
                </body>
                </html>
                """
                send_email(to_email=student.email, subject=subject, html_content=html_body)
            
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
