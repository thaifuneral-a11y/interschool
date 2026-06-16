"""api/services/email.py — SendGrid email service"""

import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from api.core.config import settings

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail
    HAS_SENDGRID = True
except ImportError:
    HAS_SENDGRID = False

_jinja = Environment(
    loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "../templates/email")),
    autoescape=select_autoescape(["html"]),
)


def _render(template_name: str, **ctx) -> str:
    return _jinja.get_template(template_name).render(**ctx)


async def _send(to_email: str, subject: str, html: str):
    if not HAS_SENDGRID or not settings.SENDGRID_API_KEY:
        print(f"[EMAIL] To: {to_email} | Subject: {subject}")
        return
    sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
    message = Mail(
        from_email=(settings.FROM_EMAIL, settings.FROM_NAME),
        to_emails=to_email,
        subject=subject,
        html_content=html,
    )
    sg.send(message)


async def send_password_reset_email(email: str, name: str, token: str):
    reset_url = f"{settings.GOOGLE_REDIRECT_URI.rsplit('/', 2)[0]}/auth/reset-password?token={token}"
    html = _render("password_reset.html", name=name, reset_url=reset_url)
    await _send(email, "Reset your password — International Student Care OS", html)


async def send_invite_email(email: str, name: str, school_id: str, token: str):
    invite_url = f"{settings.GOOGLE_REDIRECT_URI.rsplit('/', 2)[0]}/auth/accept-invite?token={token}"
    html = _render("invite.html", name=name, invite_url=invite_url)
    await _send(email, "You've been invited — International Student Care OS", html)


async def send_absence_alert(parent_email: str, student_name: str, date_str: str):
    html = _render("absence_alert.html", student_name=student_name, date=date_str)
    await _send(parent_email, f"Attendance Alert: {student_name}", html)
