from robocorp.tasks import task
from robocorp import vault


@task
def test_configuration():
    secret = vault.get_secret("funky-friday-newsletter")

    required_keys = [
        "API_BASE_URL",
        "AUTOMATION_API_KEY",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "EMAIL_FROM",
    ]

    missing_keys = [key for key in required_keys if key not in secret]

    if missing_keys:
        raise RuntimeError(f"Missing Vault keys: {missing_keys}")

    print("Vault secret loaded successfully.")
    print("Available keys:", list(secret.keys()))