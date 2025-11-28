from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Event  # your SQLAlchemy Event model

def update_upcoming_to_ongoing():
    db: Session = SessionLocal()
    try:
        now = datetime.now()
        db.query(Event).filter(
            Event.start_time <= now,
            Event.event_status == "upcoming"
        ).update({"event_status": "ongoing"}, synchronize_session=False)
        db.commit()
    finally:
        db.close()

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(update_upcoming_to_ongoing, 'interval', minutes=1)
    scheduler.start()