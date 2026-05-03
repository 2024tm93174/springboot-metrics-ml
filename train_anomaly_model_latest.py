import pandas as pd
from sklearn.ensemble import IsolationForest
import matplotlib.pyplot as plt
import os
import matplotlib.dates as mdates
import joblib

# load dataset
df = pd.read_csv("dataset/metrics_data_latest.csv")
print(df.head())
df["timestamp"] = pd.to_datetime(df["timestamp"])

# convert metric rows to columns
#df_pivot = df.pivot(index="timestamp", columns="metric", values="value")

df_pivot = df.pivot_table(
    index="timestamp",
    columns="metric",
    values="value",
    aggfunc="mean"
)
print(df_pivot.head())

df_pivot = df_pivot.rename(columns={
    "rate(http_server_requests_seconds_count[1m])": "requests",
    "jvm_memory_used_bytes": "memory",
    "jvm_threads_live_threads": "threads",
    "system_cpu_usage": "cpu"
})
print(df_pivot.head())

# rename columns for clarity
""" df_pivot.columns = [
    "requests",
    "memory",
    "threads",
    "cpu"
] """
df_pivot = df_pivot[
    ["requests", "memory", "threads", "cpu"]
]
df_pivot = df_pivot.dropna()

# features for ML
X = df_pivot[["requests","memory","threads","cpu"]]

# train Isolation Forest
model = IsolationForest(
    n_estimators=100,
    contamination=0.02,
    random_state=42
)

df_pivot["anomaly"] = model.fit_predict(X)

# save model
joblib.dump(model, "models/model_latest.pkl")

# anomaly label
df_pivot["anomaly"] = df_pivot["anomaly"].map({1:0, -1:1})

print(df_pivot.head())

#  Check if any anomalies exist
anomalies = df_pivot[df_pivot["anomaly"] == 1]

if not anomalies.empty:
    print("Anomalies detected!")
    # Write a trigger file for GitHub Actions
    os.makedirs("output", exist_ok=True)
    anomalies.to_csv("output/anomalies_latest.csv", index=False)
    # Set environment variable for GitHub Actions
    with open("output/anomaly_flag_latest.txt", "w") as f:
        f.write("1")
else:
    with open("output/anomaly_flag_latest.txt", "w") as f:
        f.write("0")
    print("No anomalies detected.")


metrics = ["requests", "memory", "threads", "cpu"]

plt.figure(figsize=(12, 8))

for i, metric in enumerate(metrics, 1):
    plt.subplot(2, 2, i)
    plt.scatter(
        df_pivot.index, 
        df_pivot[metric],
        c=df_pivot["anomaly"],  # color anomalies
        cmap="coolwarm",
        label=metric,
        s=10            
    )

    plt.title(f"{metric.capitalize()} Anomalies")
    plt.xlabel("Time")
    
    plt.ylabel(metric.capitalize())

    ax = plt.gca()

    # Show fewer time labels
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    # Format time
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))

    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

    df_pivot.to_csv("output/metrics_with_anomalies_latest.csv")

