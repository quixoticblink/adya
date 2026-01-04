import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import datetime

# Constants
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

@st.cache_resource
def get_client():
    """Authenticates with Google Sheets using Streamlit secrets."""
    if "service_account" not in st.secrets:
        raise RuntimeError("Missing [service_account] in secrets.toml")
    
    # Create a dict from the secrets (handles both toml dict and direct dict)
    creds_dict = dict(st.secrets["service_account"])
    
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def get_sheet():
    """Opens the Google Sheet defined in secrets."""
    if "sheet_url" not in st.secrets["service_account"]:
         raise RuntimeError("Missing 'sheet_url' in [service_account] secrets.")
         
    client = get_client()
    return client.open_by_url(st.secrets["service_account"]["sheet_url"])

# ---------------------------------------------------------
# Questions CRUD
# ---------------------------------------------------------

@st.cache_data(ttl=600)
def get_questions(subject="Chemistry"):
    """Reads questions from the subject-specific worksheet."""
    sh = get_sheet()
    sheet_name = f"Questions_{subject}"
    try:
        ws = sh.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        # Create it if missing
        ws = sh.add_worksheet(title=sheet_name, rows=100, cols=10)
        ws.append_row(["id", "topic", "marks", "prompt", "answer_type"])
        return []

    records = ws.get_all_records()
    if not records:
        return []
        
    return records

def save_questions(subject, questions_list):
    """Overwrites the subject-specific worksheet."""
    sh = get_sheet()
    sheet_name = f"Questions_{subject}"
    try:
        ws = sh.worksheet(sheet_name)
        ws.clear()
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows=100, cols=10)
        
    # Header
    headers = ["id", "topic", "marks", "prompt", "answer_type"]
    ws.append_row(headers)
    
    # Rows
    rows = []
    for q in questions_list:
        rows.append([
            q.get("id"),
            q.get("topic"),
            q.get("marks"),
            q.get("prompt"),
            q.get("answer_type", "text")
        ])
        
    if rows:
        ws.append_rows(rows)
        
    get_questions.clear() # Invalidate cache

# ---------------------------------------------------------
# History CRUD
# ---------------------------------------------------------

@st.cache_data(ttl=60)
def get_history():
    """Reads history from the 'History' worksheet."""
    sh = get_sheet()
    try:
        ws = sh.worksheet("History")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="History", rows=100, cols=5)
        ws.append_row(["timestamp", "email", "type", "content"])
        return []
        
    raw_records = ws.get_all_records()
    
    # Process records back into the format app expects
    processed = []
    for r in raw_records:
        try:
            content = json.loads(r.get("content", "{}"))
            # Merge the top-level fields back into a single dict for the app
            item = {
                "timestamp": r.get("timestamp"),
                "type": r.get("type"),
                # everything else is in content
            }
            item.update(content)
            processed.append(item)
        except:
            continue
            
    return processed

def append_history(record_type, content_dict):
    """Appends a new history record."""
    sh = get_sheet()
    try:
        ws = sh.worksheet("History")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="History", rows=100, cols=5)
        ws.append_row(["timestamp", "email", "type", "content"])
        
    ts = datetime.datetime.now().isoformat()
    email = st.session_state.get("user_email", "unknown")
    
    # Embed timestamp in content as well just in case
    content_dict["timestamp"] = ts
    
    row = [
        ts,
        email,
        record_type,
        json.dumps(content_dict, ensure_ascii=False)
    ]
    
    ws.append_row(row)
    get_history.clear() # Invalidate cache

def delete_history_entry(target_ts):
    """Deletes an entry by timestamp."""
    sh = get_sheet()
    try:
        ws = sh.worksheet("History")
    except:
        return

    # Find cell with timestamp
    # We iterate manually or use find. `find` is safer.
    try:
        cell = ws.find(target_ts)
        if cell:
            ws.delete_rows(cell.row)
            get_history.clear() # Invalidate cache
    except gspread.CellNotFound:
        pass
