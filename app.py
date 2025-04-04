from flask import Flask, render_template, request, jsonify, session
import pandas as pd
import requests
from io import StringIO
import os

from flask_cors import CORS
from flask_session import Session

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import json

app = Flask(__name__)
CORS(app)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

QUESTIONS_CSV = "https://docs.google.com/spreadsheets/d/1JOenZYvLKJcuwa7UJOle2BOkxaNT4gmnaGUeul-EiXA/export?format=csv"
PATIENT_STATEMENTS_CSV = "https://docs.google.com/spreadsheets/d/1JQxfhJR_OcHvaSeYJw0CZLwJF5skOBvTstIhlsFufhk/export?format=csv"

SHEET_ID = "1HlcfTjowsy_z7C8sFJOHSpIBybhwllPVnM1Yjkfi_kE"


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
json_str = os.environ["GCP_SERVICE_ACCOUNT_JSON"]
creds_dict = json.loads(json_str)
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
service = build("sheets", "v4", credentials=creds)
sheet = service.spreadsheets()

def load_data():
    """Fetch questions and patient statements from your existing Google Sheets CSVs."""
    questions_response = requests.get(QUESTIONS_CSV)
    patient_response = requests.get(PATIENT_STATEMENTS_CSV)

    if questions_response.status_code == 200 and patient_response.status_code == 200:
        try:
            questions_df = pd.read_csv(StringIO(questions_response.text))
            patient_df = pd.read_csv(StringIO(patient_response.text))
            print("CSV files loaded successfully from Google Sheets.")
            return questions_df, patient_df
        except Exception as e:
            print(f"Error loading CSV files: {e}")
            return pd.DataFrame(), pd.DataFrame()
    else:
        print("Error: Unable to fetch CSV files from Google Sheets.")
        return pd.DataFrame(), pd.DataFrame()

def append_to_google_sheet(name, patient_statement, category, selected_question, dropdown_time, response_time, feedback):
    """Append a single response row to the Google Sheet."""
    row_data = [[name, patient_statement, category, selected_question, dropdown_time, response_time, feedback]]
    body = {"values": row_data}

    result = sheet.values().append(
        spreadsheetId=SHEET_ID,
        range="Sheet1!A1",            
        valueInputOption="RAW",       
        body=body
    ).execute()

    return result

@app.route('/')
def index():
    """Serve the main HTML page."""
    return render_template("index.html")

@app.route('/get_patient_statements', methods=['GET'])
def get_patient_statements():
    """Return a list of unique patient statements."""
    _, patient_df = load_data()
    patient_statements = patient_df["questionText"].dropna().unique().tolist()
    return jsonify(patient_statements=patient_statements)

@app.route('/set_user', methods=['POST'])
def set_user():
    """Store the current user's name in session."""
    data = request.json
    session["current_user"] = data.get("name", "")
    return jsonify(success=True, message=f"User {session['current_user']} set successfully")

@app.route('/get_categories', methods=['POST'])
def get_categories():
    """Return the unique categories from the questions CSV."""
    questions_df, _ = load_data()
    categories = questions_df["Category"].dropna().unique().tolist()
    return jsonify(categories=categories)

@app.route('/get_questions', methods=['POST'])
def get_questions():
    """Return the list of questions for a given category."""
    selected_category = request.json.get("category")
    questions_df, _ = load_data()
    category_questions = questions_df[questions_df["Category"] == selected_category]["Question"].dropna().tolist()
    return jsonify(questions=category_questions)

@app.route('/submit_response', methods=['POST'])
def submit_response():
    """
    Receive a single response from the user (name, patient_statement, category, selected_question),
    and append it to the Google Sheet.
    """
    data = request.json
    name = data["name"]
    patient_statement = data["patient_statement"]
    category = data["category"]
    selected_question = data["selected_question"]
    dropdown_time = data.get("dropdown_time", "")
    response_time = data.get("response_time", "")
    feedback = data.get("feedback", "")

    try:
        append_to_google_sheet(name, patient_statement, category, selected_question, dropdown_time, response_time, feedback)
        return jsonify(success=True, message="Response Submitted.")
    except Exception as e:
        return jsonify(success=False, message=f"Error writing to Google Sheets: {e}")

if __name__ == '__main__':
    app.run(debug=True)