import os
import requests
import joblib
import pandas as pd
import time
from datetime import datetime
from alert import send_alert
import requests
import time

# Load the model
model = joblib.load("model_latest.pkl")
PROM_URL = "http://localhost:30090/api/v1/query"
feature_order = ["requests", "memory", "threads", "cpu"]
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GRAFANA_WEBHOOK = "http://localhost:30300/api/v1/alerts"
last_alert_time = 0
ALERT_COOLDOWN = 120  # seconds

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
            # Prometheus might return multiple results (one for each pod/replica).current script sums them up
            values = [float(r["value"][1]) for r in result["data"]["result"]]
            current_data[feature] = sum(values) if values else 0.0

            # 3 replicas of your Spring Boot app, an anomaly might be hidden because you are averaging them.
            # prometheus query to a specific pod:
            # jvm_memory_used_bytes{kubernetes_pod_name="myapp-xyz"}.
        except Exception as e:
            print(f"Error fetching {feature}: {e}")
            current_data[feature] = 0.0
    return current_data
    
print("Starting Real-Time Monitoring... (Ctrl+C to stop)")

def send_alert(reason):
    print("ALERT: Anomaly Detected!")
    print("Reason:", reason)
    payload = {
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "ML_Anomaly",
                    "severity": "critical"
                },
                "annotations": {
                    "description": reason
                }
            }
        ]
    }

    try:
        r = requests.post(GRAFANA_WEBHOOK, json=payload)
        print("Grafana alert sent:", r.status_code)
    except Exception as e:
        print("Grafana alert failed:", e)

def trigger_github_action(reason, action):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {GITHUB_TOKEN}"
    }
    # payload = {
    #     "event_type": "remediate_cpu_spike",
    #     "client_payload": {
    #         "reason": reason
    #     }
    # }
    payload = {
        "event_type": "smart-remediation",
        "client_payload": {
            "reason": ", ".join(reason),
            "action": action
        }
    }
    response = requests.post(
        # GITHUB_DISPATCH_URL,
        "https://api.github.com/repos/2024tm93174/springboot-app/dispatches",
        json=payload,
        headers=headers
    )
    print("GitHub Action Triggered:", response.status_code)

def identify_root_cause(data):
    BASELINES = {
        'requests': 0.02159,
        'memory': 20902611.0, 
        'threads': 23.0,
        'cpu': 0.002529
    }
    deviations = {}

    for key in data:
        deviations[key] = data[key] / BASELINES[key]
    # Find highest deviation   
    reasonDeviation = max(deviations, key=deviations.get)
    print(f" reasonDeviation: {reasonDeviation}")    
   
    # CPU Spike check FIRST
    if data["cpu"] > BASELINES["cpu"] * 3:
        return "High CPU Usage"

    # Request Flood + Memory Pressure
    if (
        # data["memory"] > BASELINES["memory"] * 2 and
        data["requests"] > BASELINES["requests"]
    ):
        return "Traffic Spike"

    # Thread Leak
    if data["threads"] > BASELINES["threads"] * 2:
        return "Thread Leak / High Thread Count"

    # Memory Leak
    if data["memory"] > BASELINES["memory"] * 2:
        return "High Memory Usage"

    return "General System Anomaly"


def choose_remediation(reason):
    if "High CPU Usage" in reason:
        return "Scale deployment / restart pod"

    elif "High Memory Usage" in reason:
        return "Restart pod / memory cleanup"

    elif "Thread Leak / High Thread Count" in reason:
        return "Restart application"

    elif "Traffic Spike" in reason:
        return "Horizontal scaling"

    return "General restart"

while True:
    # 1. Get current snapshot
    data_dict = get_prometheus_data()
    df = pd.DataFrame([data_dict])[feature_order]   

    # 2. Predict
    pred = model.predict(df)[0]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      
    if pred == -1:
        # 3. Identify the Reason
        # We calculate "Decision Function" - lower scores = more anomalous
        score = model.decision_function(df)[0]
        
        # Simple heuristic: which metric is furthest from 0 (if you scaled) 
        # or simply list all current values during the anomaly
        # reasonCurrentMetrics = ", ".join([f"{k}: {v:.2f}" for k, v in data_dict.items()])
        
        print(f" ALERT at {timestamp}")
        #print(f" Reason: System state is outside normal bounds (Score: {score:.4f})")
        #print(f" Current Metrics: {reasonCurrentMetrics}")
        #print("-" * 40) 

        print(f" data: {data_dict}")
        #reason = identify_root_cause(data_dict)
        #print(reason)
        #action = choose_remediation(reason)
     
        current_time = time.time()
        if current_time - last_alert_time > ALERT_COOLDOWN:
            # 5. Alert
            #send_alert(reason)

            # 6. Trigger GitHub webhook for remediation
            # trigger_github_action(reason, action)
            last_alert_time = current_time
        else:
             print("Anomaly detected, but cooldown active")

    else:
        print(f"[{timestamp}] System Healthy")

    # 4. Wait for the next interval (match your Prometheus resolution)
    time.sleep(30)