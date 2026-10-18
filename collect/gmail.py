"""Read LinkedIn job-alert emails from Gmail (read-only)."""
import base64
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

ROOT = Path(__file__).resolve().parent.parent
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
QUERY = "from:linkedin.com (jobalerts OR \"job alert\" OR \"new jobs\") newer_than:{days}d"


class GmailLoginNeeded(RuntimeError):
    """The saved Gmail login is missing or expired. Run login_gmail.bat once to sign in again."""


def get_service(interactive=False):
    """Background runs (interactive=False) never open a browser; they raise GmailLoginNeeded instead."""
    token_path = ROOT / "token.json"
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if not creds or not creds.valid:
        try:
            if not (creds and creds.expired and creds.refresh_token):
                raise RefreshError("no usable saved login")
            creds.refresh(Request())
        except RefreshError as exc:
            if not interactive:
                raise GmailLoginNeeded("Gmail login expired. Run login_gmail.bat") from exc
            flow = InstalledAppFlow.from_client_secrets_file(str(ROOT / "credentials.json"), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def _html_body(payload):
    """Walk the MIME tree and return the first text/html part, decoded."""
    if payload.get("mimeType") == "text/html" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", "replace")
    for part in payload.get("parts", []):
        html = _html_body(part)
        if html:
            return html
    return None


def fetch_alert_emails(days=2, max_results=100, interactive=False):
    """Return a list of {id, subject, date, html} for recent LinkedIn alert emails."""
    service = get_service(interactive)
    resp = service.users().messages().list(
        userId="me", q=QUERY.format(days=days), maxResults=max_results
    ).execute()
    emails = []
    for ref in resp.get("messages", []):
        msg = service.users().messages().get(userId="me", id=ref["id"], format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in msg["payload"]["headers"]}
        html = _html_body(msg["payload"])
        if html:
            emails.append({
                "id": ref["id"],
                "subject": headers.get("subject", ""),
                "date": headers.get("date", ""),
                "html": html,
            })
    return emails
