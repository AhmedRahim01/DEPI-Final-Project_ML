import matplotlib.pyplot as plt

metrics = ["Top-1 Accuracy", "Top-3 Accuracy"]
before = [26.32, 47.37]
after = [48.28, 65.52]

x = range(len(metrics))
width = 0.35

plt.figure(figsize=(8, 5))

plt.bar([i - width/2 for i in x], before, width, label="1 Image per Identity")
plt.bar([i + width/2 for i in x], after, width, label="5 Images per Identity")

plt.xticks(x, metrics)
plt.ylabel("Accuracy (%)")
plt.title("RMFRD/AFDB Evaluation Results")
plt.ylim(0, 100)

for i, value in enumerate(before):
    plt.text(i - width/2, value + 1, f"{value}%", ha="center")

for i, value in enumerate(after):
    plt.text(i + width/2, value + 1, f"{value}%", ha="center")

plt.legend()
plt.tight_layout()
plt.savefig("evaluation_accuracy_chart.png", dpi=300)

print("Saved chart as evaluation_accuracy_chart.png")