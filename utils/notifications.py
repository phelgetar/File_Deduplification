import os
import json
import requests
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECIPIENT = os.getenv("EMAIL_RECIPIENT")

def send_slack_notification(message: str, rich_format: bool = True):
    if not SLACK_WEBHOOK_URL:
        print("⚠️ SLACK_WEBHOOK_URL not set in .env. Skipping Slack notification.")
        return
    payload = {
        "text": message
    }
    if rich_format:
        payload = {
            "attachments": [
                {
                    "fallback": "File Deduplication Notification",
                    "color": "#36a64f",
                    "pretext": "*📁 File Deduplication Notification*",
                    "text": message,
                    "footer": "File_Deduplification Bot"
                }
            ]
        }
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print("✅ Slack notification sent.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Slack notification failed: {e}")

def send_email_notification(subject: str, body: str):
    if not all([EMAIL_HOST, EMAIL_USERNAME, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
        print("⚠️ Email credentials incomplete in .env. Skipping email notification.")
        return
    msg = EmailMessage()
    msg["From"] = EMAIL_USERNAME
    msg["To"] = EMAIL_RECIPIENT
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
            server.send_message(msg)
            print("✅ Email notification sent.")
    except Exception as e:
        print(f"❌ Email notification failed: {e}")

def notify(method: str, message: str, test: bool = False):
    if method == "slack":
        send_slack_notification(message)
    elif method == "email":
        send_email_notification("📂 File Deduplication Complete", message)
    elif method == "test":
        print("🔧 Testing Slack and Email notification setup...")
        send_slack_notification("🔧 *Slack test successful!*", rich_format=True)
        send_email_notification("📬 Email Test", "This is a test email from File_Deduplification.")
    else:
        print(f"⚠️ Unknown notification method: {method}")