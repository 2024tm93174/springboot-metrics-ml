import shap
import joblib
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime
from sklearn.model_selection import train_test_split

# Load model
model = joblib.load("models/model_latest.pkl")
PROM_URL = "http://localhost:30090/api/v1/query"
feature_order = ["requests", "memory", "threads", "cpu"]
# Create SHAP explainer (do this ONCE, not inside loop)
explainer = shap.Explainer(model)


def detect_anomaly_with_shap(df):
         # Explain WHY
        shap_values = explainer(df)

        # Get top contributing features
        feature_importance = np.abs(shap_values.values[0])
        top_features = df.columns[np.argsort(-feature_importance)]

        print(" Top contributing features:")
        for f in top_features[:3]:
            print(f, df[f].values[0])   


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

while True:
    # 1. Get current snapshot
    data_dict = get_prometheus_data()
    df = pd.DataFrame([data_dict])[feature_order]   

    # 2. Predict
    pred = model.predict(df)[0]
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      
    if pred == -1:
        print(f" ALERT at {timestamp}")
        score = model.decision_function(df)[0]      
        detect_anomaly_with_shap(df)
            
    else:
        print(f"[{timestamp}] System Healthy")
        
    time.sleep(10)






