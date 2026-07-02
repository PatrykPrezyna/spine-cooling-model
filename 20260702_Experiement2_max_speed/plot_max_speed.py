import glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Manual compressor speed changes made with the external potentiometer.
# Times are minutes from cooling start (see speed_change.txt).
# (minute, label)
SPEED_EVENTS = [
    (0, "-17 (pump off)"),
    (11, "-10"),
    (28, "0"),
    (40, "+20"),
    (58, "+40"),
    (69, "+80"),
    (76, "compressor off/on 10s"),
]

fig, ax = plt.subplots(figsize=(12, 6))

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

    ax.plot(minutes, heat_ex, "-", color="tab:blue", label="heat_ex_c")

    # Per-segment analysis: for each interval between consecutive speed changes,
    # report how heat_ex_c behaves (level + drift) so we can see the response
    # to each potentiometer step.
    print(f"\n=== {f} : heat_ex_c response per speed segment ===")
    print(f"{'segment':<22}{'span(min)':>10}{'start':>8}{'end':>8}{'delta':>8}{'mean':>8}{'slope/min':>11}")
    bounds = [m for m, _ in SPEED_EVENTS] + [float(minutes.max())]
    for i, (m0, label) in enumerate(SPEED_EVENTS):
        m1 = bounds[i + 1]
        seg = (minutes >= m0) & (minutes < m1)
        if seg.sum() < 2:
            continue
        t = minutes[seg].to_numpy()
        y = heat_ex[seg].to_numpy()
        slope = np.polyfit(t, y, 1)[0]  # °C per minute
        print(
            f"{label:<22}{m1 - m0:>10.1f}{y[0]:>8.2f}{y[-1]:>8.2f}"
            f"{y[-1] - y[0]:>8.2f}{y.mean():>8.2f}{slope:>11.3f}"
        )

# Overlay the manual potentiometer speed changes.
for minute, label in SPEED_EVENTS:
    ax.axvline(minute, color="red", linestyle="--", alpha=0.5)
    ax.annotate(
        label,
        xy=(minute, 1.0),
        xycoords=("data", "axes fraction"),
        xytext=(2, -4),
        textcoords="offset points",
        rotation=90,
        va="top",
        ha="left",
        fontsize=8,
        color="red",
    )

ax.set_xlabel("Time from cooling start (min)")
ax.set_ylabel("heat_ex_c (°C)")
ax.set_title("Experiment 2 — heat exchanger temp vs. manual speed changes")
ax.grid(True, alpha=0.3)
ax.legend(loc="best")

plt.tight_layout()
plt.show()
