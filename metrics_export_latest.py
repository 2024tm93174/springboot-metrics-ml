import requests
import pandas as pd
from datetime import datetime, timedelta
import os

PROM_URL = "http://localhost:30090/api/v1/query_range"

# Metrics to collect
metrics = [
    "rate(http_server_requests_seconds_count[1m])",
    "jvm_memory_used_bytes",
    "system_cpu_usage",
    "jvm_threads_live_threads"
]

end = datetime.now()
start = end - timedelta(hours=1)

rows = []

for metric in metrics:

    params = {
        "query": metric,
        "start": start.timestamp(),
        "end": end.timestamp(),
        "step": "15s"
    }

    response = requests.get(PROM_URL, params=params)
    data = response.json()

    for result in data["data"]["result"]:
        for value in result["values"]:

            timestamp = datetime.fromtimestamp(value[0])
            metric_value = float(value[1])

            rows.append({
                "timestamp": timestamp,
                "metric": metric,
                "value": metric_value
            })

df = pd.DataFrame(rows)
file_exists = os.path.isfile("dataset/metrics_data_latest.csv")
df.to_csv("dataset/metrics_data_latest.csv", mode='a',index=False, header=not file_exists)
print("Metrics exported to dataset/metrics_data_latest.csv")