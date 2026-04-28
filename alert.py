import requests
import json
from datetime import datetime

# 🔹 Example: Webhook URL (use Slack / custom API)
WEBHOOK_URL = "http://your-webhook-url"   # replace later


def send_alert(message, severity="critical"):
    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "severity": severity,
        "message": message
    }

    try:
        response = requests.post(WEBHOOK_URL, json=payload)

        if response.status_code == 200:
            print("✅ Alert sent successfully")
        else:
            print(f"⚠️ Alert failed: {response.status_code}, {response.text}")

    except Exception as e:
        print(f"❌ Error sending alert: {e}")