from flask import Flask, render_template, request, jsonify, session, send_file
import pandas as pd
import csv
import requests
from io import StringIO
import os
from flask_cors import CORS
from flask_session import Session  # Import Flask-Session

app = Flask(__name__)
CORS(app)

# Configure session to use filesystem (instead of global variables)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)  # Initialize session

QUESTIONS_CSV = "https://docs.google.com/spreadsheets/d/1JOenZYvLKJcuwa7UJOle2BOkxaNT4gmnaGUeul-EiXA/export?format=csv"
PATIENT_STATEMENTS_CSV = "https://docs.google.com/spreadsheets/d/1JQxfhJR_OcHvaSeYJw0CZLwJF5skOBvTstIhlsFufhk/export?format=csv"
RESPONSES_CSV = "responses.csv"
name = ""
def ensure_csv_exists():
    if not os.path.isfile(RESPONSES_CSV):
        with open(RESPONSES_CSV, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Patient Statement", "Category", "Selected Question"])

ensure_csv_exists()

def load_data():
    questions_response = requests.get(QUESTIONS_CSV)
    patient_response = requests.get(PATIENT_STATEMENTS_CSV)

    if questions_response.status_code == 200 and patient_response.status_code == 200:
        try:
            questions_df = pd.read_csv(StringIO(questions_response.text))
            patient_df = pd.read_csv(StringIO(patient_response.text))
            print("CSV files loaded successfully.")
            return questions_df, patient_df
        except Exception as e:
            print(f"Error loading CSV files: {e}")
            return pd.DataFrame(), pd.DataFrame()
    else:
        print("Error: Unable to fetch CSV files from Google Sheets.")
        return pd.DataFrame(), pd.DataFrame()

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/get_patient_statements', methods=['GET'])
def get_patient_statements():
    _, patient_df = load_data()
    patient_statements = patient_df["questionText"].dropna().unique().tolist()
    return jsonify(patient_statements=patient_statements)

@app.route('/set_user', methods=['POST'])
def set_user():
    data = request.json
    session["current_user"] = data.get("name")  # Store in session
    return jsonify(success=True, message=f"User {session['current_user']} set successfully")

@app.route('/get_categories', methods=['POST'])
def get_categories():
    questions_df, _ = load_data()
    categories = questions_df["Category"].dropna().unique().tolist()
    return jsonify(categories=categories)

@app.route('/get_questions', methods=['POST'])
def get_questions():
    selected_category = request.json.get("category")
    questions_df, _ = load_data()
    category_questions = questions_df[questions_df["Category"] == selected_category]["Question"].dropna().tolist()
    return jsonify(questions=category_questions)

@app.route('/submit_response', methods=['POST'])
def submit_response():
    data = request.json
    name = data["name"]
    patient_statement = data["patient_statement"]
    category = data["category"]
    selected_question = data["selected_question"]

    with open(RESPONSES_CSV, "a", newline='') as f:
        writer = csv.writer(f)
        writer.writerow([name, patient_statement, category, selected_question])

    return jsonify(success=True, message="Thanks for supporting! Your response has been recorded.")

@app.route('/get_responses', methods=['GET'])
def get_responses():
    if not os.path.exists(RESPONSES_CSV):
        return jsonify({"error": "No responses recorded yet!"}), 404

    with open(RESPONSES_CSV, "r") as f:
        lines = f.readlines()

    return jsonify({"responses": lines})

@app.route('/download_responses', methods=['GET'])
def download_responses():
    if not os.path.exists(RESPONSES_CSV):
        return "No responses recorded yet!", 404
    return send_file(RESPONSES_CSV, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
