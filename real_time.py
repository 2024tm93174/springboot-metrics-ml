import requests
import joblib
import pandas as pd
import time
from datetime import datetime

# Load the model
model = joblib.load("model.pkl")
PROM_URL = "http://localhost:30090/api/v1/query"
feature_order = ["requests", "memory", "threads", "cpu"]

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

while True:
    # 1. Get current snapshot
    data_dict = get_prometheus_data()
    df = pd.DataFrame([data_dict])[feature_order]
    
    """ baseline = df.mean().to_dict()
    std_dev = df.std().to_dict()
    print(baseline)
    print(std_dev) """

    # 2. Predict
    pred = model.predict(df)[0]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      
    if pred == -1:
        # 3. Identify the Reason
        # We calculate "Decision Function" - lower scores = more anomalous
        score = model.decision_function(df)[0]
        
        # Simple heuristic: which metric is furthest from 0 (if you scaled) 
        # or simply list all current values during the anomaly
        reason = ", ".join([f"{k}: {v:.2f}" for k, v in data_dict.items()])
        
        print(f" ALERT at {timestamp}")
        print(f" Reason: System state is outside normal bounds (Score: {score:.4f})")
        print(f" Current Metrics: {reason}")
        print("-" * 40) 
    else:
        print(f"[{timestamp}] System Healthy")

    # 4. Wait for the next interval (match your Prometheus resolution)
    time.sleep(10)