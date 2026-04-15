"""Google Drive API client — OAuth, folder creation, file upload."""

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Minimal scope: only access files created by this app
SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def authenticate(credentials_dir: Path):
    """Run OAuth flow if needed, cache token. Returns Drive v3 service resource."""
    credentials_dir = Path(credentials_dir)
    token_path = credentials_dir / "token.json"
    secret_path = credentials_dir / "client_secret.json"

    if not secret_path.exists():
        raise FileNotFoundError(
            f"Google OAuth credentials not found at {secret_path}\n"
            "See README.md for instructions on obtaining client_secret.json."
        )

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(secret_path), SCOPES)
            creds = flow.run_local_server(port=0)
        credentials_dir.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())

    return build("drive", "v3", credentials=creds)


def create_folder(service, name: str, parent_id: str = None) -> str:
    """Create a Drive folder (or return existing one's ID if it already exists)."""
    # Check if folder already exists under this parent
    query = (
        f"name = {_q(name)} "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = (
        service.files()
        .list(q=query, fields="files(id, name)", spaces="drive")
        .execute()
    )
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def create_folder_tree(service, path_parts: list[str], root_id: str = None) -> str:
    """Create nested folders from a list of names. Returns the leaf folder ID."""
    parent_id = root_id
    for part in path_parts:
        parent_id = create_folder(service, part, parent_id)
    return parent_id


def upload_file(service, local_path: Path, folder_id: str, filename: str = None) -> str:
    """Upload a local file to Drive, returning its file ID. Idempotent (skips if exists)."""
    filename = filename or local_path.name

    existing_id = _find_file(service, filename, folder_id)
    if existing_id:
        return existing_id

    metadata = {"name": filename, "parents": [folder_id]}
    media = MediaFileUpload(str(local_path), resumable=True)
    file = (
        service.files()
        .create(body=metadata, media_body=media, fields="id")
        .execute()
    )
    return file["id"]


def upload_html_as_doc(service, html_content: str, folder_id: str, filename: str) -> str:
    """Upload HTML content as a Google Doc. Idempotent (skips if exists)."""
    existing_id = _find_file(service, filename, folder_id)
    if existing_id:
        return existing_id

    import io
    from googleapiclient.http import MediaIoBaseUpload

    metadata = {
        "name": filename,
        "parents": [folder_id],
        "mimeType": "application/vnd.google-apps.document",
    }
    media = MediaIoBaseUpload(
        io.BytesIO(html_content.encode("utf-8")),
        mimetype="text/html",
        resumable=True,
    )
    file = (
        service.files()
        .create(body=metadata, media_body=media, fields="id")
        .execute()
    )
    return file["id"]


def _find_file(service, name: str, parent_id: str) -> str | None:
    """Return file ID if a file with this name exists in the folder, else None."""
    query = (
        f"name = {_q(name)} "
        f"and '{parent_id}' in parents "
        f"and trashed = false"
    )
    results = service.files().list(q=query, fields="files(id)", spaces="drive").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None


def _q(name: str) -> str:
    """Escape a name for use in a Drive API query string."""
    return "'" + name.replace("'", "\\'") + "'"
