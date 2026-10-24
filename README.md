# Data Redundancy Removal System

A Streamlit student-record management app using SQLite, with case-insensitive duplicate-email prevention.

## Features
- Add student records with basic validation
- Prevent duplicate email addresses, including uppercase/lowercase variants
- Search records by name or email
- View and delete records
- Show total students and duplicate attempts blocked
- Store records locally in SQLite
- Custom sage green, walnut brown, cream and amber theme

## Run locally
1. Install Python 3.10 or newer.
2. Open this folder in VS Code.
3. Create and activate a virtual environment if desired:
   - Windows: `python -m venv .venv`
   - Windows PowerShell: `.venv\Scripts\Activate.ps1`
4. Install dependencies: `python -m pip install -r requirements.txt`
5. Run: `python -m streamlit run app.py`

The `students.db` file is created automatically when the app runs. It is intentionally excluded from Git so personal/test records are not uploaded.
