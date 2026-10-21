import csv
from pathlib import Path
import statistics
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

base = Path("/home/karnika/westwood-plus-experiment")
csv_path = base / "results/westwood_vs_reno_validated_v2.csv"
graph_dir = base / "graphs"
graph_dir.mkdir(parents=True, exist_ok=True)

with csv_path.open(newline="") as f:
    rows = list(csv.DictReader(f))

results = {}
for algorithm in ("westwood", "reno"):
    selected = [
        float(row["receiver_mbps"])
        for row in rows
        if row["algorithm"] == algorithm and row["receiver_mbps"]
    ]
    if not selected:
        raise SystemExit(f"No receiver throughput data for {algorithm}")
    results[algorithm] = selected

# Graph 1: throughput for each trial
plt.figure(figsize=(8, 5))
for algorithm, values in results.items():
    plt.plot(
        range(1, len(values) + 1),
        values,
        marker="o",
        label=algorithm.capitalize(),
    )
plt.xlabel("Trial")
plt.ylabel("Receiver throughput (Mbps)")
plt.title("TCP Westwood vs Reno: Receiver Throughput")
plt.xticks(range(1, max(map(len, results.values())) + 1))
plt.grid(True, alpha=0.3)
plt.legend()
plt.tight_layout()
plt.savefig(graph_dir / "throughput_trials.png", dpi=200)
plt.close()

# Graph 2: mean throughput and standard deviation
algorithms = list(results)
means = [statistics.mean(results[a]) for a in algorithms]
errors = [
    statistics.stdev(results[a]) if len(results[a]) > 1 else 0
    for a in algorithms
]

plt.figure(figsize=(7, 5))
plt.bar(algorithms, means, yerr=errors, capsize=6)
plt.ylabel("Mean receiver throughput (Mbps)")
plt.title("Mean Throughput: Westwood vs Reno")
plt.grid(axis="y", alpha=0.3)
plt.tight_layout()
plt.savefig(graph_dir / "mean_throughput.png", dpi=200)
plt.close()

print("Graphs created:")
print(graph_dir / "throughput_trials.png")
print(graph_dir / "mean_throughput.png")

for algorithm in algorithms:
    print(
        f"{algorithm.capitalize()}: "
        f"trial values = {[round(v, 3) for v in results[algorithm]]}; "
        f"mean = {statistics.mean(results[algorithm]):.3f} Mbps"
    )

print("NOTE: Preliminary results; validate before final reporting.")
