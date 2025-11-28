from blinker import signal
from sqlalchemy.orm import Session
from config.database import get_db

from api.user.user_model import User
from api.litter_reports.litter_reports_model import LitterReport
from api.cleanup_events.cleanup_events_model import CleanupEvent
from api.roles.roles_model import Role
from api.notifications.notifications_model import Notification

from helpers.mail_helper import (
    send_cleanup_registration_email,
    send_report_approved_email,
    send_report_rejected_email,
    send_cleanup_completed_email,
    send_event_reminder_email
)
from utils.geoutils import get_nearby_users

# ------------------------------------------
# Define signals
# ------------------------------------------
report_submitted        = signal("report_submitted")
report_approved         = signal("report_approved")
report_rejected         = signal("report_rejected")
cleanup_event_created   = signal("cleanup_event_created")
cleanup_event_joined    = signal("cleanup_event_joined")
cleanup_event_completed = signal("cleanup_event_completed")
points_awarded          = signal("points_awarded")
alert_event_starting  = signal("alert_event_starting")

print("[listener] notification_service imported - wiring up listeners")

# ------------------------------------------
# Listener: Report Submitted
# ------------------------------------------
# @report_submitted.connect
# def on_report_submitted(sender, **kwargs):
#     report_id = kwargs.get("report_id")
#     print(f"[listener] report_submitted received for {report_id!r}")

#     db: Session = next(get_db())
#     try:
#         report = db.get(LitterReport, report_id)
#         if not report:
#             print(f"[listener] no report found for {report_id!r}")
#             return

#         user = db.get(User, report.user_id)
#         name = user.username if user else "User"
#         msg = f"Litter report #{report.id} submitted successfully."

#         db.add(Notification(
#             user_id=report.user_id,
#             message=msg,
#             type="info",
#             read_status=False,
#             link=f"/litter_reports/{report.id}"
#         ))
#         db.commit()
#         if user and user.email:
#             send_report_submitted_email(user.email, name, str(report.id))
#         print(f"[listener] notification created for {report_id!r}")
#     finally:
#         db.close()

# ------------------------------------------
# Listener: Report Verified
# ------------------------------------------
@report_approved.connect
def on_report_approved(sender, **kwargs):
    report_id = kwargs.get("report_id")
    print(f"[listener] report_approved received for {report_id!r}")

    db: Session = next(get_db())
    try:
        report = db.get(LitterReport, report_id)
        if not report:
            return

        user = db.get(User, report.user_id)
        name = user.username if user else "User"
        db.add(Notification(
            user_id=report.user_id,
            message=f"Report #{report.id} has been approved. Thank you!",
            type="info",
            read_status=False,
            link=f"/reports/{report.id}"
        ))
        db.commit()

        if user and user.email:
            send_report_approved_email(user.email, name, str(report.id))
    finally:
        db.close()



@report_rejected.connect
def on_report_rejected(sender, **kwargs):
    report_id = kwargs.get("report_id")
    print(f"[listener] report_rejected received for {report_id!r}")

    db: Session = next(get_db())
    try:
        report = db.get(LitterReport, report_id)
        if not report:
            return

        user = db.get(User, report.user_id)
        name = user.username if user else "User"
        db.add(Notification(
            user_id=report.user_id,
            message=f"Report #{report.id} has been rejected. Please check the details.",
            type="info",
            read_status=False,
            link=f"/reports/{report.id}"
        ))
        db.commit()

        if user and user.email:
            send_report_rejected_email(user.email, name, str(report.id))
    finally:
        db.close()
# ------------------------------------------
# Listener: Cleanup Event Created
# ------------------------------------------
@cleanup_event_created.connect
def on_cleanup_event_created(sender, **kwargs):
    event: CleanupEvent = kwargs.get("created_event")
    event_id: str = kwargs.get("event_id")
    print(f"[listener] cleanup_event_created for {event_id!r}")

    db: Session = next(get_db())
    try:
        users = get_nearby_users(event.centroid_lat, event.centroid_lng, db)
        for u in users:
            msg = (
                f"New cleanup event '{event.name}' is scheduled on "
                f"{event.scheduled_date}. Join now!"
            )
            db.add(Notification(
                user_id=u.id,
                message=msg,
                type="info",
                read_status=False,
                link=f"/events/{event_id}"
            ))
        db.commit()
    finally:
        db.close()

# ------------------------------------------
# Listener: Cleanup Event Joined
# ------------------------------------------
@cleanup_event_joined.connect
def on_cleanup_event_joined(sender, **kwargs):
    user_id: int = kwargs.get("user_id")
    event: CleanupEvent = kwargs.get("event")
    print(f"[listener] cleanup_event_joined by user {user_id!r}")

    db: Session = next(get_db())
    try:
        user = db.get(User, user_id)
        name = user.username if user else "User"
        db.add(Notification(
            user_id=user_id,
            message=f"Joined the cleanup event '{event.event_name}'.",
            type="info",
            read_status=False,
            link=f"/events/{event.id}"
        ))
        db.commit()

        if user and user.email:
            send_cleanup_registration_email(user.email, name, event.event_name)
    finally:
        db.close()

# ------------------------------------------
# Listener: Cleanup Event Completed
# ------------------------------------------
@cleanup_event_completed.connect
def on_cleanup_event_completed(sender, **kwargs):
    event: CleanupEvent = kwargs.get("event")
    print(f"[listener] cleanup_event_completed for event {event.id!r}")

    db: Session = next(get_db())
    try:
        participants = (
            db.query(Role.user_id)
              .filter(Role.cleanup_event_id == event.id)
              .distinct()
              .all()
        )
        for (uid,) in participants:
            user = db.get(User, uid)
            name = user.username if user else "User"
            db.add(Notification(
                user_id=uid,
                message=f"Thank you {name}! The cleanup event '{event.event_name}' is complete.",
                type="info",
                read_status=False,
                link=f"/events/{event.id}/results"
            ))
        db.commit()
        if user and user.email:
            send_cleanup_completed_email(user.email, name, event.event_name)
    finally:
        db.close()

# ------------------------------------------
# Listener: Points Awarded
# ------------------------------------------
@points_awarded.connect
def on_points_awarded(sender, **kwargs):
    user_id: int = kwargs.get("user_id")
    points: int = kwargs.get("points")
    reason: str = kwargs.get("reason")
    print(f"[listener] points_awarded for user {user_id!r}")

    db: Session = next(get_db())
    try:
        user = db.get(User, user_id)
        name = user.username if user else "User"
        db.add(Notification(
            user_id=user_id,
            message=f"Congrats {name}! You earned {points} points for {reason}.",
            type="info",
            read_status=False,
            link="/user/points"
        ))
        db.commit()
    finally:
        db.close()

@alert_event_starting.connect
def on_alert_event_starting(sender, **kwargs):
    event: CleanupEvent = kwargs.get("event")
    print(f"[listener] alert_event_starting for event {event.id!r}")

    db: Session = next(get_db())
    try:
        # find all users who have joined this event
        participants = (
            db.query(Role.user_id)
              .filter(Role.cleanup_event_id == event.id)
              .distinct()
              .all()
        )

        for (uid,) in participants:
            user = db.get(User, uid)
            name = user.username if user else "User"
            # create an in-app alert notification
            db.add(Notification(
                user_id=uid,
                message=(
                    f"Reminder, {name}! "
                    f"The cleanup event '{event.name}' starts tomorrow at "
                    f"{event.start_time.strftime('%I:%M %p')}."
                ),
                type="alert",
                read_status=False,
                link=f"/events/{event.id}"
            ))
        db.commit()

        # send reminder emails
        for (uid,) in participants:
            user = db.get(User, uid)
            if user and user.email:
                send_event_reminder_email(
                    to_email=user.email,
                    first_name=user.username or "User",
                    event_name=event.name,
                    start_time=event.start_time
                )

    finally:
        db.close()
