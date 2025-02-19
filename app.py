from flask import Flask, render_template, request, jsonify
import pandas as pd
import csv
import requests
from io import StringIO
import os
from flask_cors import CORS
app = Flask(__name__)

CORS(app)

QUESTIONS_CSV = "https://docs.google.com/spreadsheets/d/1JOenZYvLKJcuwa7UJOle2BOkxaNT4gmnaGUeul-EiXA/export?format=csv"
PATIENT_STATEMENTS_CSV = "https://docs.google.com/spreadsheets/d/1JQxfhJR_OcHvaSeYJw0CZLwJF5skOBvTstIhlsFufhk/export?format=csv"
RESPONSES_CSV = "responses.csv"

def ensure_csv_exists():
    if not os.path.isfile(RESPONSES_CSV):
        with open(RESPONSES_CSV, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "Patient Statement", "Category", "Selected Question"])

ensure_csv_exists()
current_user = None


def load_data():
    questions_response = requests.get(QUESTIONS_CSV)
    patient_response = requests.get(PATIENT_STATEMENTS_CSV)

    if questions_response.status_code == 200 and patient_response.status_code == 200:
        try:
            questions_df = pd.read_csv(StringIO(questions_response.text))
            patient_df = pd.read_csv(StringIO(patient_response.text))
            print("CSV files loaded successfully.")
            print(f"Questions DataFrame Shape: {questions_df.shape}")
            print(f"Patient Statements DataFrame Shape: {patient_df.shape}")
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
    global current_user
    data = request.json
    current_user = data.get("name")
    return jsonify(success=True)

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
    global current_user
    data = request.json
    patient_statement = data["patient_statement"]
    category = data["category"]
    selected_question = data["selected_question"]

    with open(RESPONSES_CSV, "a", newline='') as f:
        writer = csv.writer(f)
        writer.writerow([current_user, patient_statement, category, selected_question])

    return jsonify(success=True, message="Thanks for supporting! Your response has been recorded.")

if __name__ == '__main__':
    app.run(debug=True)