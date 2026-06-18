import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.email import send_email_background

print("Sending test email...")
send_email_background("sandraaneesh30@gmail.com", "Test Subject", "Test Body")
