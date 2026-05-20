import pandas as pd

# Load old CSV
df = pd.read_csv("dataset/metrics_data.csv")

# Remove old request counter rows
df = df[
    df["metric"] != "http_server_requests_seconds_count"
]

# Save updated CSV
df.to_csv("dataset/metrics_data_latest.csv", index=False)
print("Updated CSV saved successfully.")
print(df["metric"].unique())