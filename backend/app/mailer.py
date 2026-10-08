import smtplib
from email.message import EmailMessage

from app.config import get_settings


def send_reset_email(email: str, token: str) -> None:
    settings = get_settings()
    if not all((settings.smtp_host, settings.smtp_from, settings.smtp_username,
                settings.smtp_password.get_secret_value())):
        if settings.app_env == "development":
            # No token or credentials are logged; configure SMTP to enable delivery.
            return
        raise RuntimeError("SMTP is not configured")
    message = EmailMessage()
    message["Subject"] = "Reset your Gnk Algo password"
    message["From"] = settings.smtp_from
    message["To"] = email
    message.set_content(f"Use this link within {settings.reset_token_minutes} minutes to reset your password:\n\n{settings.frontend_url}/reset-password#token={token}\n")
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        server.send_message(message)
