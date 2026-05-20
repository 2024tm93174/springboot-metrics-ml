import smtplib
from email.mime.text import MIMEText
from turtle import setx
import requests
import joblib
import pandas as pd
import time
from datetime import datetime
import requests
import time
import os
import shap
import numpy as np
from prometheus_client import Gauge, start_http_server


ALERT_COOLDOWN = 30  # seconds
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
model = joblib.load("models/model_latest.pkl")
PROM_URL = "http://localhost:30090/api/v1/query"
feature_order = ["requests", "memory", "threads", "cpu"]
APP_PASSWORD = os.getenv("EMAIL_PASS")
explainer = shap.Explainer(model)
last_alert_time = 0
confidence_level = True
CONFIDENCE_THRESHOLD = 0.95

def get_prometheus_data():
    queries = {
        "requests": "rate(http_server_requests_seconds_count[1m])",
        "memory": "jvm_memory_used_bytes",
        "threads": "jvm_threads_live_threads",
        "cpu": "system_cpu_usage"
    }
    
    current_data = {}
    for feature, query in queries.items():
        try: 
            res = requests.get(PROM_URL, params={"query": query}, timeout=5)
            result = res.json()
            values = [float(r["value"][1]) for r in result["data"]["result"]]
            current_data[feature] = sum(values) if values else 0.0
        except Exception as e:
            print(f"Error fetching {feature}: {e}")
            current_data[feature] = 0.0
    return current_data
    
print("Starting Real-Time Monitoring... (Ctrl+C to stop)")

def detect_anomaly_with_shap(df):
         # Explain WHY
        shap_values = explainer(df)

        # Get top contributing features
        feature_importance = np.abs(shap_values.values[0])
        top_features = df.columns[np.argsort(-feature_importance)]

        print(" Top contributing features:")
        for f in top_features[:3]:
            print(f, df[f].values[0])   


BASELINES = {
    'requests':0.02938,
    'memory':67554665.59236,
    'threads':23.54618,
    'cpu':0.00737
}

STD_DEVS = {
    'requests':0.01162*2,
    'memory':102235336.47906,
    'threads':6.39453,
    'cpu':0.02122
}

def identify_root_cause(data):
    z_scores = {}
    for key in BASELINES:
        z_scores[key] = abs(
            (data[key] - BASELINES[key]) / STD_DEVS[key]
        )
    print("Z-Scores:", z_scores)

    main_issue = max(z_scores, key=z_scores.get)
    print("Main Issue:", main_issue)

    reason = "General System Anomaly"
    if main_issue == "cpu":
        reason = "High CPU Usage"

    elif main_issue == "memory":
        reason = "Memory Leak"

    elif main_issue == "threads":
        reason = "High Thread Count"

    elif main_issue == "requests":
        reason = "Traffic Spike"

    return reason, z_scores, main_issue

def choose_remediation(reason):
    if "High CPU Usage" in reason:
        return "Scale deployment"

    elif "Memory Leak" in reason:
        return "Restart pod"

    elif "High Thread Count" in reason:
        return "Restart application"

    elif "Traffic Spike" in reason:
        return "Horizontal scaling"

    return "General restart"

def trigger_github_action(reason, action):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {GITHUB_TOKEN}"
    }
    payload = {
        "event_type": "smart-remediation",
        "client_payload": {
            "reason": reason,
            "action": action
        }
    }
    response = requests.post(
        "https://api.github.com/repos/2024tm93174/springboot-app/dispatches",
        json=payload,
        headers=headers
    )
    print("GitHub Action Triggered:", response.status_code)

def send_alert(reason,confidence_level,action):
    print("send_alert: Anomaly Detected!")

    sender_email = "ai.remediation.project.2026@gmail.com"
    receiver_email = "ai.remediation.project.2026@gmail.com"   
    password =APP_PASSWORD

    if confidence_level:
        subject = "AUTO-REMEDIATION TRIGGERED: Anomaly Detected in Spring Boot System"
        body = f"Anomaly detected!\n\nReason:\n{reason}\n\nAction:\n{action}"
    else:
        subject = "ALERT: Anomaly Detected in Spring Boot System - Low Confidence"
        body = f"Possible anomaly detected but confidence is below auto-remediation threshold."
    

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("Email alert sent!")
    except Exception as e:
        print("Email failed:", e)


# ── Prometheus Gauges ──────────────────────────────────────────────────────────

anomaly_gauge = Gauge(
    "anomaly_detected",
    "1 = anomaly, 0 = normal",
    ["service"],
)

# Raw metric values
metric_gauge = Gauge(
    "aiops_metric_value",
    "Current raw value for each monitored metric",
    ["metric"],
)

# Per-metric z-scores (exposed individually for threshold alerts)
zscore_gauge = Gauge(
    "aiops_metric_zscore",
    "Z-score deviation from baseline for each metric",
    ["metric"],
)

# Root-cause z-score of the worst offender (legacy / convenience)
top_zscore_gauge = Gauge(
    "aiops_top_zscore",
    "Z-score of the metric most responsible for the anomaly",
)

# Isolation Forest decision function score (lower = more anomalous)
anomaly_score_gauge = Gauge(
    "anomaly_score",
    "Isolation Forest decision score (negative = anomalous)",
)

#  Main loop ──────────────────────────────────────────────────────────────────

start_http_server(30008)
print("Prometheus exporter started on :30008")

while True:
    # 1. Get current snapshot
    data_dict = get_prometheus_data()
    df = pd.DataFrame([data_dict])[feature_order]   

    # 2. Predict
    pred = model.predict(df)[0]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      
    if pred == -1:
         print(f" ALERT at {timestamp}")
         print(f" data: {data_dict}")
         
         reason, z_scores, main_issue = identify_root_cause(data_dict)
         print(f"[{timestamp}] ANOMALY | root cause: {reason} | z-scores: {z_scores}")

         action = choose_remediation(reason)
         print("action:", action)
         score = model.decision_function(df)[0]
         print(f"Raw Anomaly Score : {score:.4f}")
         anomaly_score_gauge.set(score)

         confidence = 1 / (1 + np.exp(score * 40))  # sigmoid conversion
         print(f"Anomaly confidence: {confidence:.2f}")

         current_time = time.time()
         if current_time - last_alert_time > ALERT_COOLDOWN:
             
             if confidence >= CONFIDENCE_THRESHOLD:
                 print(f"Confidence {confidence:.2%} >= {CONFIDENCE_THRESHOLD:.2%}")
                 print("AUTO-REMEDIATION triggered")
                 confidence_level = True
                 send_alert(reason,confidence_level,action)
                 trigger_github_action(reason, action)
                 detect_anomaly_with_shap(df)

                 anomaly_gauge.labels(service="api").set(1)
                 top_zscore_gauge.set(z_scores[main_issue])
                 for metric, z in z_scores.items():
                    zscore_gauge.labels(metric=metric).set(z)

                 for metric, value in data_dict.items():
                     metric_gauge.labels(metric=metric).set(value)   

             else:
                print(f"Confidence {confidence:.2%} < {CONFIDENCE_THRESHOLD:.2%}")
                print("LOW CONFIDENCE - Human alert only, no auto-remediation") 
                confidence_level = False               
                send_alert(reason,confidence_level,confidence,)
               
             last_alert_time = current_time    

         else:
             print("Anomaly detected, but cooldown active")

    else:
        print(f"[{timestamp}] System Healthy")
        anomaly_gauge.labels(service="api").set(0)
        top_zscore_gauge.set(0)
        for metric in BASELINES:
            zscore_gauge.labels(metric=metric).set(0)
        anomaly_score_gauge.set(0)
       

    # 4. Wait for the next interval (match your Prometheus resolution)
    time.sleep(10)