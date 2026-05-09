import os
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
ASSETS_DIR = os.path.join(BASE_DIR, 'Assets')

GMAIL_ADDRESS = os.getenv('GMAIL_ADDRESS')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD')
SHEET_ID = os.getenv('GOOGLE_SHEET_ID')
CREDENTIALS_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)


def get_sheet():
    creds_dict = json.loads(CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    return sheet


def ensure_sheet_headers(sheet):
    headers = ['Timestamp', 'Type', 'Name', 'Email', 'Roll/Company ID', 'Branch/Industry', 'Area of Interest', 'Message']
    if sheet.row_values(1) != headers:
        sheet.insert_row(headers, 1)


def send_email(name, email, app_type, field, dept, reason):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"[TRR Website] New {app_type} Contact: {name}"
    msg['From'] = GMAIL_ADDRESS
    msg['To'] = GMAIL_ADDRESS

    body = f"""
New contact form submission on the TRR Electric website.

Type      : {app_type}
Name      : {name}
Email     : {email}
Branch    : {field}
Interest  : {dept}

Message:
{reason}

---
Reply directly to: {email}
"""
    msg.attach(MIMEText(body, 'plain'))
    msg['Reply-To'] = email

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.ehlo()
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, GMAIL_ADDRESS, msg.as_string())


@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory(ASSETS_DIR, filename)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/team')
def team_page():
    return render_template('team.html')


@app.route('/gallery')
def gallery_page():
    return render_template('gallery.html')


@app.route('/brochure')
def brochure_page():
    return render_template('brochure.html')


@app.route('/research')
def research_page():
    return render_template('research.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact_page():
    if request.method == 'POST':
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        app_type = request.form.get('applicant_type')
        name = request.form.get('name')
        email = request.form.get('email')
        user_id = request.form.get('user_id', '')
        field = request.form.get('field')
        dept = request.form.get('department')
        reason = request.form.get('reason')

        email_ok = False
        sheet_ok = False
        sheet_error = None
        email_error = None

        # Google Sheets
        try:
            sheet = get_sheet()
            ensure_sheet_headers(sheet)
            sheet.append_row([timestamp, app_type, name, email, user_id, field, dept, reason])
            sheet_ok = True
            print(f"Sheet OK: {name}")
        except Exception as e:
            sheet_error = str(e)
            print(f"Sheet error: {e}")

        # Email
        try:
            send_email(name, email, app_type, field, dept, reason)
            email_ok = True
            print(f"Email OK: {name}")
        except Exception as e:
            email_error = str(e)
            print(f"Email error: {e}")

        # Success only if at least email went through
        if email_ok:
            return render_template('join.html', success=True, sheet_warning=not sheet_ok)

        # Total failure
        return render_template('join.html', failed=True, email_error=email_error, sheet_error=sheet_error)

    return render_template('join.html')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
