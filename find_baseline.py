import pandas as pd

# Metric mapping
metric_map = {
    "http_server_requests_seconds_count": "requests",
    "jvm_memory_used_bytes": "memory",
    "jvm_threads_live_threads": "threads",
    "system_cpu_usage": "cpu"
}

feature_order = ["requests", "memory", "threads", "cpu"]

# Load CSV
df = pd.read_csv("dataset/metrics_data.csv")
#print(df.columns)
#print(df.head())

# Rename metric names
df["metric"] = df["metric"].map(metric_map)

# Remove unknown metrics if any
df = df.dropna(subset=["metric"])

# Pivot long → wide
df_pivot = df.pivot_table(
    index="timestamp",
    columns="metric",
    values="value",
    aggfunc="mean"
)

# Reset index (optional)
df_pivot = df_pivot.reset_index()

# Keep required columns only
df_pivot = df_pivot[["timestamp"] + feature_order]

# Remove rows with missing values
df_pivot = df_pivot.dropna()


BASELINES = {
"cpu": df_pivot["cpu"].mean(),
"memory": df_pivot["memory"].mean(),
"threads": df_pivot["threads"].mean(),
"requests": df_pivot["requests"].mean()
} 


print("BASELINES:")
print(BASELINES) 


  
   