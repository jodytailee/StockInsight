import requests

from app.config import settings

RESEND_API_URL = "https://api.resend.com/emails"


def send_email(subject: str, html_body: str) -> None:
    if not settings.resend_api_key or not settings.notification_email_to:
        print("[email] RESEND_API_KEY o NOTIFICATION_EMAIL_TO no configurados, se omite el envío")
        return

    response = requests.post(
        RESEND_API_URL,
        headers={"Authorization": f"Bearer {settings.resend_api_key}"},
        json={
            "from": settings.resend_from_email,
            "to": [settings.notification_email_to],
            "subject": subject,
            "html": html_body,
        },
        timeout=15,
    )
    response.raise_for_status()
