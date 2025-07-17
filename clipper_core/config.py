# config.py
"""
Centralized configuration and Dropbox client factory.
"""
import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# ─── Load environment variables ───────────────────────────────────────────────
dotenv_path = find_dotenv(usecwd=True)
if dotenv_path:
    load_dotenv(dotenv_path, override=True)

# ─── Base directory and paths ─────────────────────────────────────────────────
# Move BASE_DIR up one to the project root, not the scripts/ folder
BASE_DIR     = Path(__file__).parent.parent
UPLOADS_DIR  = BASE_DIR / "uploads_and_transcripts"
DROPBOX_INPUT  = os.getenv("DROPBOX_INPUT", "/AI/Clipper_input")
DROPBOX_OUTPUT = os.getenv("DROPBOX_OUTPUT", "/AI/Clipper_output")
WEBHOOK_URL    = "https://webhook.oracleboxing.com/webhook"

# ─── Dropbox credentials ─────────────────────────────────────────────────────
APP_KEY           = os.getenv("DROPBOX_APP_KEY")
APP_SECRET        = os.getenv("DROPBOX_APP_SECRET")
REFRESH_TOKEN     = os.getenv("DROPBOX_REFRESH_TOKEN")
ACCESS_TOKEN      = os.getenv("DROPBOX_ACCESS_TOKEN")
SELECT_USER       = os.getenv("SELECT_USER")
ROOT_NAMESPACE_ID = os.getenv("ROOT_NAMESPACE_ID")

required = ["APP_KEY", "APP_SECRET", "REFRESH_TOKEN", "SELECT_USER", "ROOT_NAMESPACE_ID"]
missing = [name for name in required if not globals()[name]]
if missing:
    raise RuntimeError(f"Missing required Dropbox env vars: {', '.join(missing)}")


def get_dropbox_client(use_refresh: bool = True, use_namespace: bool = True):
    """
    Returns a Dropbox client—either team-refresh-based or direct access token.
    """
    if use_refresh:
        from dropbox import DropboxTeam, common
        team = DropboxTeam(
            oauth2_refresh_token=REFRESH_TOKEN,
            app_key=APP_KEY,
            app_secret=APP_SECRET,
        )
        dbx = team.as_user(SELECT_USER)
    else:
        from dropbox import Dropbox
        if not ACCESS_TOKEN:
            raise RuntimeError("Missing DROPBOX_ACCESS_TOKEN for direct client")
        dbx = Dropbox(oauth2_access_token=ACCESS_TOKEN)

    if use_namespace:
        from dropbox import common
        dbx = dbx.with_path_root(common.PathRoot.namespace_id(ROOT_NAMESPACE_ID))

    return dbx