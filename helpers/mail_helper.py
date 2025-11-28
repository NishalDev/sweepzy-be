# helpers/mail_helper.py

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config.settings import settings
from datetime import datetime

from pathlib import Path

def render_template(template_name: str, **kwargs) -> str:
    template_path = Path("templates") / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    html = template_path.read_text(encoding="utf-8")

    for key, value in kwargs.items():
        html = html.replace(f"{{{{ {key} }}}}", str(value))

    return html

def send_email(to_email: str, subject: str, body: str, html: bool = False):
    msg = MIMEMultipart()
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to_email
    msg["Subject"] = subject

    if html:
        msg.attach(MIMEText(body, "html"))   # send as HTML
    else:
        msg.attach(MIMEText(body, "plain"))  # fallback to plain text

    with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
        server.starttls()
        server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
        server.send_message(msg)


# def send_report_submitted_email(to_email: str, user_name: str, report_id: str):
#     subject = f"Your Litter Report #{report_id} Has Been Submitted"
#     body = (
#         f"Hi {user_name},\n\n"
#         f"Thank you for submitting your litter report (ID: {report_id}).\n"
#         f"Our team will review it shortly.\n\n"
#         f"Keep up the great work!\n\n"
#         f"— Sweepzy Team"
#     )
#     send_email(to_email, subject, body)

def send_otp_email(to_email: str, username: str, otp: str, purpose: str):
    subject = f"[Sweepzy] OTP for {purpose.replace('_',' ').title()}"

    # Select template based on purpose
    if purpose == "user_registration":
        template = "emails/otp_registration.html"
    elif purpose == "password_reset":
        template = "emails/otp_reset.html"
    else:
        template = "emails/otp_generic.html"  # fallback template

    html_body = render_template(
        template,
        name=username,
        otp=otp
    )

    send_email(to_email, subject, html_body, html=True)

def send_cleanup_completed_email(to_email: str, user_name: str, event_name: str):
    subject = f"Cleanup event {event_name} completed"
    body = (
        f"Hi {user_name},\n\n"
        f"Thank you for your participation in the cleanup event: {event_name}.\n"
        f"We appreciate your efforts in helping the environment!\n\n"
        f"— Sweezpy Team"
    )
    send_email(to_email, subject, body)
    
def send_cleanup_registration_email(to_email: str, user_name: str, event_name: str):
    subject = f"Registered for Cleanup Event: {event_name}"
    body = (
        f"Hi {user_name},\n\n"
        f"You have successfully registered for the cleanup event: {event_name}.\n"
        f"Please be ready and await further instructions.\n\n"
        f"Thanks for your contribution to a cleaner environment!\n\n"
        f"— Sweezpy Team"
    )
    send_email(to_email, subject, body)

def send_report_approved_email(to_email: str, user_name: str, report_id: str):
    subject = f"Your Litter Report #{report_id} Has Been Approved"
    html_body = render_template(
        "emails/report_approved.html",
        name=user_name,
        report_id=report_id
    )
    send_email(to_email, subject, html_body, html=True)

def send_report_rejected_email(to_email: str, user_name: str, report_id: str):
    subject = f"Your Litter Report #{report_id} Has Been Rejected"
    body = (
        f"Hi {user_name},\n\n"
        f"Unfortunately, your litter report (ID: {report_id}) has been rejected.\n"
        f"Please check the details and consider resubmitting.\n\n"
        f"Thank you for your efforts!\n\n"
        f"— Sweepzy Team"
    )
    send_email(to_email, subject, body)
    
def send_event_reminder_email(
    to_email: str,
    first_name: str,
    event_name: str,
    start_time: datetime
):
    """
    Sends a reminder email to a user about their upcoming cleanup event,
    scheduled to start tomorrow.
    """
    # Format the event start time as, e.g., "August 06, 2025 at 03:00 PM"
    formatted_time = start_time.strftime("%B %d, %Y at %I:%M %p")

    subject = f"Reminder: '{event_name}' Starts Tomorrow"
    body = (
        f"Hi {first_name},\n\n"
        f"This is a friendly reminder that the cleanup event '{event_name}' "
        f"starts tomorrow at {formatted_time}.\n\n"
        f"We look forward to seeing you there!\n\n"
        f"— Sweepzy Team"
    )

    send_email(to_email, subject, body)

