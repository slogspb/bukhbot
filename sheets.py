from dotenv import load_dotenv
load_dotenv()

import os
import glob
import logging

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "")
SHEET_NAME = os.getenv("SHEET_NAME", "Лист1")

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

shared = glob.glob("/app/shared/*.json")
SERVICE_ACCOUNT_FILE = shared[0] if shared else os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")

_service = None


def _get_service():
    global _service

    if _service is None:
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )

        _service = build(
            "sheets",
            "v4",
            credentials=creds
        )

    return _service


def _get_sheet_id(service):
    meta = service.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID
    ).execute()

    for sheet in meta["sheets"]:
        if sheet["properties"]["title"] == SHEET_NAME:
            return sheet["properties"]["sheetId"]

    raise ValueError(f"Лист '{SHEET_NAME}' не найден")


def append_invoice_row(data: dict):
    service = _get_service()
    sheets = service.spreadsheets()

    # Ищем следующую строку по столбцу D, где хранится контрагент
    result = sheets.values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!D:D"
    ).execute()

    values = result.get("values", [])
    next_row = len(values) + 1

    # Записываем данные
    updates = [
        # A — дата сообщения по Москве
        (f"{SHEET_NAME}!A{next_row}", [[data["date"]]]),

        # D — контрагент
        (f"{SHEET_NAME}!D{next_row}", [[data["contractor"]]]),

        # E — сумма с НДС
        (f"{SHEET_NAME}!E{next_row}", [[data["s_nds"]]]),

        # H — значение чекбокса
        (f"{SHEET_NAME}!H{next_row}", [[False]]),

        # I — период
        (f"{SHEET_NAME}!I{next_row}", [[data["period"]]]),
    ]

    body = {
        "valueInputOption": "USER_ENTERED",
        "data": [
            {
                "range": rng,
                "values": vals
            }
            for rng, vals in updates
        ]
    }

    sheets.values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body=body
    ).execute()

    # Добавляем чекбокс в столбец H
    sheet_id = _get_sheet_id(service)

    checkbox_request = {
        "requests": [
            {
                "setDataValidation": {
                    "range": {
                        "sheetId": sheet_id,

                        # строка в API считается с нуля
                        "startRowIndex": next_row - 1,
                        "endRowIndex": next_row,

                        # H = 7, потому что A = 0
                        "startColumnIndex": 7,
                        "endColumnIndex": 8
                    },
                    "rule": {
                        "condition": {
                            "type": "BOOLEAN"
                        },
                        "strict": True,
                        "showCustomUi": True
                    }
                }
            }
        ]
    }

    sheets.batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body=checkbox_request
    ).execute()

    logger.info(f"Строка {next_row} записана")