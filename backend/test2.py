import traceback
from app.db.database import SessionLocal
from app.schemas.schemas import WhitelistCreate
from app.api.warden import add_to_whitelist

db = SessionLocal()
w = WhitelistCreate(email='test56@gmail.com', name='Test', room_number='101')
try:
    add_to_whitelist(w, db=db, current_user=None)
except Exception as e:
    traceback.print_exc()
