import ssl
import smtplib
from email.message import EmailMessage

import requests
from jinja2 import Environment, FileSystemLoader
from robocorp.tasks import task
from robocorp import vault


SECRET_NAME = "funky_friday_newsletter"


@task
def test_configuration():
    secrets = vault.get_secret(SECRET_NAME)

    required_keys = [
        "API_BASE_URL",
        "AUTOMATION_API_KEY",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "EMAIL_FROM",
    ]

    missing_keys = [key for key in required_keys if key not in secrets]

    if missing_keys:
        raise RuntimeError(f"Missing Vault keys: {missing_keys}")

    print("Vault secret loaded successfully.")
    print("Available keys:", list(secrets.keys()))


@task
def send_weekly_newsletter():
    secrets = vault.get_secret(SECRET_NAME)

    api_base_url = secrets["API_BASE_URL"].strip().rstrip("/")
    automation_api_key = secrets["AUTOMATION_API_KEY"].strip()

    headers = {
        "Authorization": f"Bearer {automation_api_key}",
        "x-automation-key": automation_api_key,
    }

    magazine_response = requests.post(
        f"{api_base_url}/admin/magazine/generate",
        headers=headers,
        timeout=30,
    )

    if not magazine_response.ok:
        print("Magazine generate request failed")
        print("Status:", magazine_response.status_code)
        print("Response body:", magazine_response.text)

    magazine_response.raise_for_status()
    data = magazine_response.json()

    test_recipient_email = secrets.get("TEST_RECIPIENT_EMAIL")

    if test_recipient_email:
        test_recipient_email = test_recipient_email.strip().lower()

        data["recipients"] = [
            recipient
            for recipient in data["recipients"]
            if recipient["email"].strip().lower() == test_recipient_email
        ]

        if not data["recipients"]:
            raise RuntimeError(
                f"No matching test recipient found for {test_recipient_email}"
            )

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("newsletter.html")
    html = template.render(album=data["album"])

    results = []

    for recipient in data["recipients"]:
        try:
            send_email(
                smtp_host=secrets["SMTP_HOST"].strip(),
                smtp_port=int(secrets["SMTP_PORT"]),
                smtp_user=secrets["SMTP_USER"].strip(),
                smtp_password=secrets["SMTP_PASSWORD"],
                sender=secrets["EMAIL_FROM"].strip(),
                recipient=recipient["email"].strip(),
                subject=data["issue"]["subject"],
                html=html,
            )

            results.append(
                {
                    "userId": recipient["userId"],
                    "email": recipient["email"],
                    "status": "sent",
                }
            )

        except Exception as error:
            results.append(
                {
                    "userId": recipient.get("userId"),
                    "email": recipient["email"],
                    "status": "failed",
                    "error": str(error),
                }
            )

    log_response = requests.post(
        f"{api_base_url}/admin/magazine/{data['issue']['id']}/sent-log",
        headers=headers,
        json={"results": results},
        timeout=30,
    )

    if not log_response.ok:
        print("Magazine sent-log request failed")
        print("Status:", log_response.status_code)
        print("Response body:", log_response.text)

    log_response.raise_for_status()

    print("Newsletter task completed.")
    print(f"Recipients processed: {len(results)}")
    print(f"Sent: {len([r for r in results if r['status'] == 'sent'])}")
    print(f"Failed: {len([r for r in results if r['status'] == 'failed'])}")


def send_email(
    smtp_host,
    smtp_port,
    smtp_user,
    smtp_password,
    sender,
    recipient,
    subject,
    html,
):
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = recipient

    message.set_content("Your new Funky Friday Album of the Week is ready.")
    message.add_alternative(html, subtype="html")

    context = ssl.create_default_context()

    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
        server.starttls(context=context)
        server.login(smtp_user, smtp_password)
        server.send_message(message)