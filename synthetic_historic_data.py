import pandas as pd
import numpy as np

# Load CSV
df = pd.read_csv("metrics_data_2.csv")

df["timestamp"] = pd.to_datetime(df["timestamp"])

# Find timestamps where requests metric is missing
all_timestamps = df["timestamp"].unique()

request_rows = df[
    df["metric"] == "rate(http_server_requests_seconds_count[1m])"
]["timestamp"].unique()

missing_timestamps = [
    ts for ts in all_timestamps
    if ts not in request_rows
]

print("Missing timestamps:", len(missing_timestamps))

# Generate synthetic request-rate values
synthetic_rows = []

for ts in missing_timestamps:
    synthetic_value = np.random.uniform(
        0.01,   # lower bound
        0.05    # upper bound
    )

    synthetic_rows.append({
        "timestamp": ts,
        "metric": "rate(http_server_requests_seconds_count[1m])",
        "value": round(synthetic_value, 5)
    })

df_synthetic = pd.DataFrame(synthetic_rows)

# Append to original CSV
df_final = pd.concat(
    [df, df_synthetic],
    ignore_index=True
)

# Save updated file
df_final.to_csv("metrics_data_2.csv", index=False)

print("Synthetic historical request-rate data added successfully.")