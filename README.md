# Funky Friday Newsletter Worker

Robocorp worker for sending the Funky Friday weekly album newsletter.

The worker asks the Funky Friday app to generate the current magazine issue, renders the album details into an HTML email, sends the email to each recipient over SMTP, then reports the delivery results back to the app.

## What It Does

- Validates required Robocorp Vault configuration.
- Calls the Funky Friday admin API to generate a newsletter issue.
- Optionally limits delivery to one test recipient.
- Renders `templates/newsletter.html` with the generated album data.
- Sends HTML email through an SMTP server using STARTTLS.
- Posts sent/failed delivery results back to the Funky Friday API.

## Project Structure

```text
.
+-- tasks.py                    # Robocorp task definitions and email sender
+-- robot.yaml                  # Robocorp task configuration
+-- conda.yaml                  # Robocorp runtime environment
+-- requirements.txt            # Python dependencies for local installs
+-- templates/
|   +-- newsletter.html         # Jinja2 HTML email template
+-- output/                     # Robocorp artifacts directory
```

## Tasks

The worker exposes two Robocorp tasks:

| Task | Purpose |
| --- | --- |
| `test_configuration` | Loads the Vault secret and checks all required keys exist. |
| `send_weekly_newsletter` | Generates the issue, sends the emails, and logs delivery results. |

The friendly task names in `robot.yaml` are:

- `Test configuration`
- `Send weekly newsletter`

## Configuration

Secrets are loaded from the Robocorp Vault secret named:

```text
funky_friday_newsletter
```

Required keys:

| Key | Description |
| --- | --- |
| `API_BASE_URL` | Base URL for the Funky Friday app API. The code removes trailing slashes automatically. |
| `AUTOMATION_API_KEY` | API key sent as both `Authorization: Bearer ...` and `x-automation-key`. |
| `SMTP_HOST` | SMTP server hostname. |
| `SMTP_PORT` | SMTP server port. |
| `SMTP_USER` | SMTP username. |
| `SMTP_PASSWORD` | SMTP password. |
| `EMAIL_FROM` | Sender email address. |

Optional key:

| Key | Description |
| --- | --- |
| `TEST_RECIPIENT_EMAIL` | When set, the worker filters the generated recipient list to this single email address. Useful for test sends. |

Example secret shape:

```json
{
  "API_BASE_URL": "http://localhost:3001",
  "AUTOMATION_API_KEY": "replace-me",
  "SMTP_HOST": "smtp.example.com",
  "SMTP_PORT": "587",
  "SMTP_USER": "funkyfriday@saiofam.com",
  "SMTP_PASSWORD": "replace-me",
  "EMAIL_FROM": "Funky Friday <funkyfriday@saiofam.com>",
  "TEST_RECIPIENT_EMAIL": "test@example.com"
}
```


## API Contract

`send_weekly_newsletter` expects the app to support these endpoints:

```text
POST {API_BASE_URL}/admin/magazine/generate
POST {API_BASE_URL}/admin/magazine/{issue.id}/sent-log
```

The generate endpoint should return JSON containing:

- `album`: used by the Jinja template. Expected fields include `image`, `title`, `artist`, `description`, and `appUrl`.
- `issue`: expected fields include `id` and `subject`.
- `recipients`: a list of recipients with `email` and `userId`.

The sent-log endpoint receives:

```json
{
  "results": [
    {
      "userId": "user-id",
      "email": "listener@example.com",
      "status": "sent"
    }
  ]
}
```

Failed sends are reported with `status: "failed"` and an `error` message.

## Local Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

For Robocorp/Control Room runs, `robot.yaml` uses `conda.yaml`, which pins Python 3.11 and installs the runtime dependencies.

## Running Tasks

Validate configuration first:

```powershell
python -m robocorp.tasks run tasks.py -t test_configuration
```

Send the newsletter:

```powershell
python -m robocorp.tasks run tasks.py -t send_weekly_newsletter
```

During testing, set `TEST_RECIPIENT_EMAIL` in the Vault secret so the task only sends to one address.

## Email Template

The HTML email lives at:

```text
templates/newsletter.html
```

It is rendered with:

```python
template.render(album=data["album"])
```

If you add template fields, make sure the `/admin/magazine/generate` response includes matching properties on `album`.

## Notes

- SMTP is sent with `starttls`, so use a port and provider that support STARTTLS, usually port `587`.
- The worker continues processing recipients if one email fails.
- After all recipients are processed, the worker posts a delivery log back to the API.
- If the delivery log request fails, the task raises an error after printing the status and response body.
- Currently the worker only generates a simple email with variables depending on data. In the future, it is ready to have AI generated magazine issues implemented.
