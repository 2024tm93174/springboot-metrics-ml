from datetime import datetime
import time
import joblib
from prometheus_client import Gauge, start_http_server
import requests
import pandas as pd

model = joblib.load("models/model_latest.pkl")
PROM_URL = "http://localhost:30090/api/v1/query"
feature_order = ["requests", "memory", "threads", "cpu"]

def get_prometheus_data():
    queries = {
        "requests": "rate(http_server_requests_seconds_count[1m])",
        "memory":   "jvm_memory_used_bytes",
        "threads":  "jvm_threads_live_threads",
        "cpu":      "system_cpu_usage"
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


BASELINES = {
    "requests": 0.02938,
    "memory":   67554665.59236,
    "threads":  23.54618,
    "cpu":      0.00737,
}

STD_DEVS = {
    "requests": 0.01162 * 2,
    "memory":   102235336.47906,
    "threads":  6.39453,
    "cpu":      0.02122,
}

def identify_root_cause(data):
    z_scores = {
        key: abs((data[key] - BASELINES[key]) / STD_DEVS[key])
        for key in BASELINES
    }
    main_issue = max(z_scores, key=z_scores.get)
    return main_issue, z_scores


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

# ── Main loop ──────────────────────────────────────────────────────────────────

start_http_server(30008)
print("Prometheus exporter started on :30008")

while True:
    data_dict = get_prometheus_data()
    df = pd.DataFrame([data_dict])[feature_order]

    pred  = model.predict(df)[0]
    score = model.decision_function(df)[0]   # always capture the score
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Push raw values and decision score regardless of anomaly state
    for metric, value in data_dict.items():
        metric_gauge.labels(metric=metric).set(value)
    anomaly_score_gauge.set(score)

    if pred == -1:
        reason, z_scores = identify_root_cause(data_dict)
        print(f"[{timestamp}] ANOMALY | root cause: {reason} | z-scores: {z_scores}")

        anomaly_gauge.labels(service="api").set(1)
        top_zscore_gauge.set(z_scores[reason])
        for metric, z in z_scores.items():
            zscore_gauge.labels(metric=metric).set(z)

    else:
        print(f"[{timestamp}] Healthy | score: {score:.4f}")

        anomaly_gauge.labels(service="api").set(0)
        top_zscore_gauge.set(0)
        for metric in BASELINES:
            zscore_gauge.labels(metric=metric).set(0)

    time.sleep(10)


