import pandas as pd
import numpy as np
from datetime import timedelta

# -----------------------------------------
# LOAD ORIGINAL DATA
# -----------------------------------------

# Load CSV
df = pd.read_csv("dataset/metrics_data_latest.csv")
# Parse timestamp
df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    format="%Y-%m-%d %H:%M:%S.%f"
)

print(df.head())

# -----------------------------------------
# PIVOT TO WIDE FORMAT
# -----------------------------------------

df_pivot = df.pivot_table(
    index="timestamp",
    columns="metric",
    values="value",
    aggfunc="mean"
).reset_index()

# Rename columns for simplicity
df_pivot.columns.name = None

df_pivot = df_pivot.rename(columns={
    "system_cpu_usage": "cpu",
    "jvm_memory_used_bytes": "memory",
    "jvm_threads_live_threads": "threads",
    "rate(http_server_requests_seconds_count[1m])": "requests"
})

# -----------------------------------------
# HANDLE MISSING VALUES
# -----------------------------------------

# Sort by timestamp
df_pivot = df_pivot.sort_values("timestamp")

# Forward fill missing values
df_pivot = df_pivot.ffill()

# -----------------------------------------
# CALCULATE REAL BASELINES
# -----------------------------------------

BASELINES = {
    col: df_pivot[col].mean()
    for col in ["cpu", "memory", "threads", "requests"]
}

STD_DEVS = {
    col: df_pivot[col].std()
    for col in ["cpu", "memory", "threads", "requests"]
}

print("\nBASELINES")
print(BASELINES)

print("\nSTD DEVS")
print(STD_DEVS)

# -----------------------------------------
# GENERATE SYNTHETIC DATA
# -----------------------------------------

NUM_SYNTHETIC = 10000

""" timestamps = [
    df_pivot["timestamp"].max() + timedelta(seconds=15*i)
    for i in range(NUM_SYNTHETIC)
]

synthetic = pd.DataFrame({
    "timestamp": timestamps
})

for metric in ["cpu", "memory", "threads", "requests"]:

    synthetic[metric] = np.random.normal(
        BASELINES[metric],
        STD_DEVS[metric],
        NUM_SYNTHETIC
    )
 """

full_range = pd.date_range(
    start=df_pivot["timestamp"].min(),
    end=df_pivot["timestamp"].max(),
    freq="15s"
)
existing = set(df_pivot["timestamp"])
missing = full_range.difference(existing)

synthetic = pd.DataFrame({
    "timestamp": missing
})

for metric in ["cpu", "memory", "threads", "requests"]:
    synthetic[metric] = np.random.normal(
        BASELINES[metric],
        STD_DEVS[metric],
        len(synthetic)
    )

# -----------------------------------------
# INSERT REALISTIC ANOMALIES
# -----------------------------------------

#    synthetic["anomaly"] = 0

anomaly_indices = np.random.choice(
    NUM_SYNTHETIC,
    int(NUM_SYNTHETIC * 0.05),
    replace=False
)

for idx in anomaly_indices:

    metric = np.random.choice(
        ["cpu", "memory", "threads", "requests"]
    )

    synthetic.loc[idx, metric] += (
        np.random.uniform(4, 8)
        * STD_DEVS[metric]
    )

    # synthetic.loc[idx, "anomaly"] = 1

# -----------------------------------------
# CLEAN NEGATIVES
# -----------------------------------------

synthetic["cpu"] = synthetic["cpu"].clip(lower=0)
synthetic["memory"] = synthetic["memory"].clip(lower=0)
synthetic["threads"] = synthetic["threads"].clip(lower=1)
synthetic["requests"] = synthetic["requests"].clip(lower=0)

# -----------------------------------------
# COMBINE REAL + SYNTHETIC
# -----------------------------------------

final_df = pd.concat([
    df_pivot.assign(anomaly=0),
    synthetic
])

final_df = final_df.sort_values("timestamp")

# -----------------------------------------
# SAVE
# -----------------------------------------

final_df.to_csv(
    "dataset/synthetic_dataset.csv",
    index=False
)

print("\nDataset generated successfully.")
print(final_df.head())

# -----------------------------------------
# CONVERT BACK TO LONG FORMAT
# -----------------------------------------

long_df = final_df.melt(
    #  id_vars=["timestamp", "anomaly"],
    id_vars=["timestamp"],
    value_vars=["cpu", "memory", "threads", "requests"],
    var_name="metric",
    value_name="value"
)

# Rename metrics back to original Prometheus names
metric_mapping = {
    "cpu": "system_cpu_usage",
    "memory": "jvm_memory_used_bytes",
    "threads": "jvm_threads_live_threads",
    "requests": "rate(http_server_requests_seconds_count[1m])"
}

long_df["metric"] = long_df["metric"].map(metric_mapping)

# -----------------------------------------
# SORT
# -----------------------------------------

long_df = long_df.sort_values("timestamp")

# -----------------------------------------
# SAVE
# -----------------------------------------

long_df.to_csv(
    "dataset/synthetic_prom_dataset.csv",
    index=False,
    header=False
)

print("\nPrometheus-style dataset generated.")
print(long_df.head())

# -----------------------------------------
# APPEND TO EXISTING CSV
# -----------------------------------------

existing_file = "dataset/metrics_data_latest.csv"

# Append synthetic rows
long_df.to_csv(
    existing_file,
    mode='a',          # append mode
    header=False,      # don't write header again
    index=False
)

print("\nSynthetic data appended successfully.")