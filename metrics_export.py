import requests
import pandas as pd
from datetime import datetime, timedelta
import os

PROM_URL = "http://localhost:30090/api/v1/query_range"

# Metrics to collect
metrics = [
    "http_server_requests_seconds_count",
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


""" def get_filename():
    # Generates a filename like: metrics_2026-03-18.csv
    date_str = datetime.now().strftime("%Y-%m-%d")
    return f"metrics_{date_str}.csv"

while True:
 current_file = get_filename()

file_exists = os.path.isfile(current_file)
df.to_csv(current_file,mode='a',index=False,  header=not file_exists) """


file_exists = os.path.isfile("metrics_data.csv")
df.to_csv("metrics_data.csv", mode='a',index=False, header=not file_exists)
print("Metrics exported to metrics_data.csv")