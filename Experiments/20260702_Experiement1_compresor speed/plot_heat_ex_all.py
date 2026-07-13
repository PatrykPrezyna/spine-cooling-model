import glob
import pandas as pd
import matplotlib.pyplot as plt

fig, ax = plt.subplots()   # heat_ex_c curves

for f in glob.glob("*.csv"):
    if f.startswith("_"):
        continue
    df = pd.read_csv(f)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Cooling starts at the beginning of the longest continuous compressor-on
    # block; t=0 is that moment. Using the longest run (rather than the first
    # "1") ignores brief start-up blips that would otherwise misalign the curve.
    cooling = df["compressor_cooling"] == 1
    if not cooling.any():
        continue
    block = (cooling != cooling.shift()).cumsum()
    on_blocks = block[cooling]
    longest = on_blocks.value_counts().idxmax()
    start = on_blocks.index[on_blocks == longest][0]

    minutes = (df["timestamp"] - df["timestamp"].loc[start]).dt.total_seconds() / 60.0
    heat_ex = df["heat_ex_c"]

    label = "_".join(f.replace(".csv", "").split("_")[4:]) or f.replace(".csv", "")
    print(f"{label:<24} heat_ex_c min {heat_ex.min():.2f}  max {heat_ex.max():.2f}  mean {heat_ex.mean():.2f}")
    ax.plot(minutes, heat_ex, label=label)

ax.axvline(0, color="gray", linestyle="--", alpha=0.6)
ax.set_xlabel("Time from cooling start (min)")
ax.set_ylabel("heat_ex_c (°C)")
ax.set_title("Heat exchanger temperature")
ax.grid(True, alpha=0.3)
ax.legend()

plt.show()
