import requests
import pandas as pd
from datetime import datetime

PROM_URL = "http://localhost:30090/api/v1/query_range"

query = "rate(http_server_requests_seconds_count[1m])"

params = {
    "query": query,

    # OLD historical date range
    "start": "2026-03-22T00:00:00Z",
    "end": "2026-05-01T23:59:59Z",

    # every 5 minutes
    "step": "5m"
}

response = requests.get(PROM_URL, params=params)
result = response.json()

rows = []

if result["status"] == "success":
    for series in result["data"]["result"]:
        for value in series["values"]:
            timestamp = datetime.fromtimestamp(float(value[0]))
            metric_value = float(value[1])

            rows.append({
                "timestamp": timestamp,
                "metric": "rate(http_server_requests_seconds_count[1m])",
                "value": metric_value
            })

df_new = pd.DataFrame(rows)

print(df_new.head())

# Append to existing CSV
df_old = pd.read_csv("metrics_data_2.csv")
print(df_old.head())

#df_final = pd.concat([df_old, df_new], ignore_index=True)

#df_final.to_csv("metrics_data_2.csv", index=False)

print("Historical request-rate data appended successfully.")