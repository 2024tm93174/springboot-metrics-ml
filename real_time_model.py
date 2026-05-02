import requests
import joblib
import pandas as pd
import time

model = joblib.load("model.pkl")

PROM_URL = "http://localhost:30090/api/v1/query"

query = "rate(http_server_requests_seconds_count[1m])"

while True:
    res = requests.get(PROM_URL, params={"query": query})
    data = res.json()

    values = []

    for r in data["data"]["result"]:
        timestamp, value = r["value"]
        values.append(float(value))

    if values:
        df = pd.DataFrame(values, columns=["request_rate"])

        preds = model.predict(df)

        if -1 in preds:
            print(" Anomaly detected!")
	# send alert

    time.sleep(60)

