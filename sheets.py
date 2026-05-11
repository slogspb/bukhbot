from dotenv import load_dotenv
load_dotenv()
import os
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
SHEET_NAME = os.getenv("SHEET_NAME", "Лист1")
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_service = None

def _get_service():
    global _service
    if _service is None:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        _service = build("sheets", "v4", credentials=creds)
    return _service

def append_invoice_row(data: dict):
    service = _get_service()
    sheets = service.spreadsheets()
    result = sheets.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!D:D"
    ).execute()
    values = result.get("values", [])
    next_row = len(values) + 1
    updates = [
        (f"{SHEET_NAME}!D{next_row}", [[data["contractor"]]]),
        (f"{SHEET_NAME}!E{next_row}", [[data["s_nds"]]]),
        (f"{SHEET_NAME}!I{next_row}", [[data["period"]]]),
    ]
    body = {
        "valueInputOption": "USER_ENTERED",
        "data": [{"range": rng, "values": vals} for rng, vals in updates]
    }
    sheets.values().batchUpdate(spreadsheetId=SPREADSHEET_ID, body=body).execute()
    logger.info(f"Строка {next_row} записана")
