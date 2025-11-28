# api/otp/otp_service.py
import random, string, datetime
from sqlalchemy.orm import Session
from api.otp.otp_model import OTP
from helpers.mail_helper import send_email, send_otp_email
from config.settings import settings

def send_otp_to_email(db: Session, email: str, username: str, purpose: str) -> None:
    # 1) Generate code
    code = "".join(random.choices(string.digits, k=6))

    # 2) Compute expiration
    expires_at = datetime.datetime.now() + datetime.timedelta(
        minutes=settings.OTP_EXPIRE_MINUTES
    )

    # 3) Persist
    otp = OTP(email=email, code=code, purpose=purpose, expires_at=expires_at)
    db.add(otp)
    db.commit()

    # 4) Send mail (now uses HTML template function)
    send_otp_email(email, username, code, purpose)


def verify_otp_for_email(db: Session, email: str, otp_code: str, purpose: str) -> bool:
    now = datetime.datetime.now()
    print(f"[DEBUG] Verifying OTP: email={email}, code={otp_code}, purpose={purpose}, now={now}")
    record = (
        db.query(OTP)
          .filter_by(email=email, code=otp_code, purpose=purpose, used=False)
          .filter(OTP.expires_at > now)
          .order_by(OTP.created_at.desc())
          .first()
    )
    print(f"[DEBUG] OTP record found: {record}")
    if not record:
        print("[DEBUG] No valid OTP found.")
        return False
    record.used = True
    db.commit()
    print("[DEBUG] OTP marked as used and committed.")
    return True
