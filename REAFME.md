
# Data Redundancy Removal System

## About the Project
A Python-based student record management application
that prevents duplicate records using SQLite.

## Features
- Add student records
- Detect duplicate email addresses
- Case-insensitive email duplicate detection
- Store records persistently in SQLite
- Display records in a table
- Validate basic input

## Technologies Used
- Python
- Streamlit
- SQLite

## Installation and Setup

1. Install Python 3.13 or a compatible Python version.
2. Open the project folder in VS Code.
3. Create a virtual environment:

   python -m venv .venv

4. Install Streamlit:

   python -m pip install streamlit

5. Run the application:

   python -m streamlit run app.py

## How It Works
The application checks whether an email already exists
before accepting a student record. SQLite also enforces
a unique, case-insensitive email constraint.

## Testing
- New records save successfully.
- Duplicate emails are rejected.
- Uppercase duplicates are rejected.
- Records remain available after restarting the app.

## Future Improvements
- Cloud database integration
- Export records to CSV
- Improved input validation
- User authentication
