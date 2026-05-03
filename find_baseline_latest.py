import pandas as pd

# Metric mapping
metric_map = {
    "rate(http_server_requests_seconds_count[1m])": "requests",
    "jvm_memory_used_bytes": "memory",
    "jvm_threads_live_threads": "threads",
    "system_cpu_usage": "cpu"
}

feature_order = ["requests", "memory", "threads", "cpu"]

# Load CSV
df = pd.read_csv("dataset/metrics_data_latest.csv")
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

BASELINES_Mean = {
"cpu": df_pivot["cpu"].mean(),
"memory": df_pivot["memory"].mean(),
"threads": df_pivot["threads"].mean(),
"requests": df_pivot["requests"].mean()
} 

BASELINES_Median = {
    "cpu": df_pivot["cpu"].median(),
    "memory": df_pivot["memory"].median(),
    "threads": df_pivot["threads"].median(),   
    "requests": df_pivot["requests"].median()
} 

BASELINES_Std = {
    "cpu": df_pivot["cpu"].std(),
    "memory": df_pivot["memory"].std(),
    "threads": df_pivot["threads"].std(),   
    "requests": df_pivot["requests"].std()
}

cpu_mean = df_pivot["cpu"].mean()
cpu_std = df_pivot["cpu"].std()
cpu_threshold = cpu_mean + 2 * cpu_std

memory_mean = df_pivot["memory"].mean()
memory_std = df_pivot["memory"].std()
memory_threshold = memory_mean + 2 * memory_std

threads_mean = df_pivot["threads"].mean()
threads_std = df_pivot["threads"].std()
threads_threshold = threads_mean + 2 * threads_std

requests_mean = df_pivot["requests"].mean()
requests_std = df_pivot["requests"].std()
requests_threshold = requests_mean + 2 * requests_std
   
BASELINES_Thresholds = {
    "cpu": cpu_threshold,
    "memory": memory_threshold,
    "threads": threads_threshold,
    "requests": requests_threshold
}

print("BASELINES:")
print(BASELINES_Mean)
print(BASELINES_Median)  
print(BASELINES_Std) 
print(BASELINES_Thresholds) 