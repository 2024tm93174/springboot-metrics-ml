import pandas as pd

# Load old CSV
df = pd.read_csv("metrics_data.csv")

# Remove old request counter rows
df = df[
    df["metric"] != "http_server_requests_seconds_count"
]

# Save updated CSV
df.to_csv("metrics_data_2.csv", index=False)
print("Updated CSV saved successfully.")
print(df["metric"].unique())