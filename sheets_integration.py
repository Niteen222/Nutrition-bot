import os
import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

import json

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv("GOOGLE_SHEET_ID")
CREDENTIALS_FILE = 'credentials.json'

def get_sheets_service():
    """Builds and returns the Google Sheets service."""
    creds = None
    # 1. Check if full JSON is passed via environment variable (ideal for 24/7 cloud hosts like Render/Railway)
    raw_creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if raw_creds_json:
        try:
            info = json.loads(raw_creds_json)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as e:
            print(f"Error loading credentials from GOOGLE_CREDENTIALS_JSON: {e}")

    # 2. Fallback to local credentials.json file
    if not creds:
        if os.path.exists(CREDENTIALS_FILE):
            creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPES)
        else:
            print(f"Warning: Neither GOOGLE_CREDENTIALS_JSON env var nor {CREDENTIALS_FILE} found.")
            return None

    service = build('sheets', 'v4', credentials=creds)
    return service


def get_candidates():
    """
    Fetches the candidate list from the 'Candidates' sheet.
    Assumes columns: A (Name), B (Discord ID)
    Returns a list of dicts: [{'name': '...', 'discord_id': '...'}]
    """
    service = get_sheets_service()
    if not service or not SPREADSHEET_ID:
        return []

    try:
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='Candidates!A2:B').execute()
        values = result.get('values', [])
        
        candidates = []
        for row in values:
            if len(row) >= 2:
                candidates.append({
                    'name': row[0],
                    'discord_id': row[1]
                })
        return candidates
    except Exception as e:
        print(f"Error fetching candidates: {e}")
        return []

def mark_attendance(discord_id, name, status, notes=""):
    """
    Appends a new row to the 'Attendance' sheet.
    Assumes columns: A (Date), B (Name), C (Discord ID), D (Status), E (Notes)
    """
    service = get_sheets_service()
    if not service or not SPREADSHEET_ID:
        return False

    today_str = datetime.date.today().isoformat()
    values = [[today_str, name, str(discord_id), status, notes]]
    body = {'values': values}

    try:
        sheet = service.spreadsheets()
        sheet.values().append(
            spreadsheetId=SPREADSHEET_ID,
            range='Attendance!A:E',
            valueInputOption='USER_ENTERED',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        return True
    except Exception as e:
        print(f"Error marking attendance: {e}")
        return False
