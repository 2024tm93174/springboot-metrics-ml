from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
import pandas as pd
import time
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Load your historical data
df = pd.read_csv('metrics_data.csv')

df["timestamp"] = pd.to_datetime(df["timestamp"])

# convert metric rows to columns
#df_pivot = df.pivot(index="timestamp", columns="metric", values="value")

df_pivot = df.pivot_table(
    index="timestamp",
    columns="metric",
    values="value",
    aggfunc="mean"
)

# rename columns for clarity
df_pivot.columns = [
    "requests",
    "memory",   
    "threads" ,
    "cpu"
]

df_pivot = df_pivot.dropna()

# features for ML
X = df_pivot[["requests","memory","threads","cpu"]]

models = {
    "Isolation Forest": IsolationForest(n_estimators=100,contamination=0.02,random_state=42),
    "Local Outlier Factor": LocalOutlierFactor(contamination=0.02),
    "One-Class SVM": OneClassSVM(nu=0.02)
}

for name, model in models.items():
    start = time.time()
    # Note: LOF uses fit_predict, others use fit then predict
    preds = model.fit_predict(X) if name == "Local Outlier Factor" else model.fit(X).predict(X)
    end = time.time()

    anomaly_rows = df_pivot[preds == -1]   
    anomalies = (preds == -1).sum()
    print(f"{name}: Found {anomalies} anomalies in {end-start:.4f} seconds")
    df_pivot["anomaly"] = preds
    df_pivot["anomaly"] = df_pivot["anomaly"].map({1: 0, -1: 1})
 
if anomalies > 0:
    print("Anomalies detected!")
    # Write a trigger file for GitHub Actions
    os.makedirs("output", exist_ok=True)
    anomaly_rows.to_csv("output/modelanomalies.csv", index=False)
    # Set environment variable for GitHub Actions
    with open("output/modelanomaly_flag.txt", "w") as f:
        f.write("1")
else:
    with open("output/modelanomaly_flag.txt", "w") as f:
        f.write("0")
    print("No anomalies detected.")


## visualize anomalies
metrics = ["requests", "memory", "threads", "cpu"]

plt.figure(figsize=(12, 8))

for i, metric in enumerate(metrics, 1):
    plt.subplot(2, 2, i)
    # plt.scatter(
    #     range(len(df_pivot)),
    #     df_pivot[metric],
    #     c=df_pivot["anomaly"],  # color anomalies
    #     cmap="coolwarm",
    #     label=metric
    # )

    plt.scatter(
        df_pivot.index,      # real timestamps
        df_pivot["cpu"],
        c=df_pivot["anomaly"],
        cmap="coolwarm"
    )

    plt.title(f"{metric.capitalize()} Anomalies")
    plt.xlabel("Time")
    
    plt.ylabel(metric.capitalize())

    ax = plt.gca()

    # Show fewer time labels
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    # Format time
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
  
