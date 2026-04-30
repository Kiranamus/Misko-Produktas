import os
import requests
from dotenv import load_dotenv

load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY")
MAIL_FROM = os.getenv("MAIL_FROM", "no-reply@forestforyou.eu")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "ForestForYou")


def send_email(to_email: str, subject: str, html_content: str) -> None:
    if not BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY is missing")

    response = requests.post(
        "https://api.brevo.com/v3/smtp/email",
        headers={
            "accept": "application/json",
            "api-key": BREVO_API_KEY,
            "content-type": "application/json",
        },
        json={
            "sender": {
                "name": MAIL_FROM_NAME,
                "email": MAIL_FROM,
            },
            "to": [
                {"email": to_email}
            ],
            "subject": subject,
            "htmlContent": html_content,
        },
        timeout=15,
    )

    if response.status_code >= 400:
        raise RuntimeError(f"Brevo email failed: {response.status_code} {response.text}")