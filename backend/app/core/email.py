import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

def send_email_background(to_email: str, subject: str, body_text: str):
    if not settings.SMTP_EMAIL or not settings.SMTP_PASSWORD:
        print(f"Skipping email to {to_email} (SMTP not configured)")
        return
        
    sender_email = settings.SMTP_EMAIL
    password = settings.SMTP_PASSWORD

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = to_email

    # Turn the text into HTML
    html = f"""\
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
          <h2 style="color: #2c3e50;">Mess Attendance Portal Notification</h2>
          <p style="font-size: 16px;">{body_text.replace(chr(10), '<br>')}</p>
          <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
          <p style="font-size: 12px; color: #7f8c8d;">
            This is an automated message from the Hostel Mess Attendance Portal.<br>
            Please do not reply directly to this email.
          </p>
        </div>
      </body>
    </html>
    """
    
    part = MIMEText(html, "html")
    message.attach(part)

    try:
        # Create secure connection with server and send email
        context = smtplib.SMTP("smtp.gmail.com", 587)
        context.starttls()
        context.login(sender_email, password)
        context.sendmail(sender_email, to_email, message.as_string())
        context.quit()
        print(f"Successfully sent email to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {str(e)}")
