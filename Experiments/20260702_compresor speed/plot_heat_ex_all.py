"""Compare heat-exchanger cooldown curves and plot the load / equilibrium run."""

from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import load_sensor_csv, longest_true_block_start

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "output_data"
OUT_DIR.mkdir(exist_ok=True)

# Overlay: room-temp cooldowns (skip leading "_" = already-cold / load runs)
cooldown_files = sorted(
    f for f in HERE.glob("sensor_log_*.csv") if not f.name.startswith("_")
)
# Prefixed "_" logs are separate load / equilibrium tests
load_files = sorted(HERE.glob("_sensor_log_*.csv"))


def align_on_cooling_start(df: pd.DataFrame):
    cooling = df["compressor_cooling"] == 1
    if not cooling.any():
        return None
    start = longest_true_block_start(cooling)
    t0 = df["timestamp"].loc[start]
    minutes = (df["timestamp"] - t0).dt.total_seconds() / 60.0
    return minutes, t0


# --- Figure 1: heat_ex cooldown overlay ---
fig, ax = plt.subplots(figsize=(9, 5))
for f in cooldown_files:
    df = load_sensor_csv(f)
    aligned = align_on_cooling_start(df)
    if aligned is None:
        continue
    minutes, t0 = aligned
    heat_ex = df["heat_ex_c"]
    label = "_".join(f.stem.split("_")[4:]) or f.stem
    print(
        f"{label:<24} heat_ex min {heat_ex.min():.2f}  max {heat_ex.max():.2f}  "
        f"mean {heat_ex.mean():.2f}  cool_start {t0.strftime('%H:%M:%S')}"
    )
    ax.plot(minutes, heat_ex, label=label)

ax.axvline(0, color="gray", linestyle="--", alpha=0.6)
ax.axhline(-1.0, color="black", linestyle=":", alpha=0.5, label="setpoint ~-1 C")
ax.set_xlabel("Time from cooling start (min)")
ax.set_ylabel("heat_ex_c (C)")
ax.set_title("Heat exchanger cooldown vs compressor dial setting")
ax.grid(True, alpha=0.3)
ax.legend()
fig.tight_layout()
out1 = OUT_DIR / "heat_ex_cooldown_overlay.png"
fig.savefig(out1, dpi=150)
plt.close(fig)
print(f"Saved {out1}")

# --- Figure 2: load / equilibrium run (pump heat to force continuous cooling) ---
for f in load_files:
    df = load_sensor_csv(f)
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(9, 6))
    t = df["timestamp"]

    ax1.plot(t, df["heat_ex_c"], color="tab:blue", label="heat_ex")
    ax1.plot(t, df["heat_ex_2_c"], color="tab:cyan", alpha=0.7, label="heat_ex_2")
    ax1.axhline(-1.0, color="black", linestyle=":", alpha=0.5)
    on = df["compressor_cooling"] == 1
    if on.any():
        ax1.fill_between(
            t, -5, 25, where=on, color="tab:gray", alpha=0.12, label="compressor on"
        )
    ax1.set_ylabel("Temperature (C)")
    ax1.set_ylim(-3, 8)
    ax1.set_title(f"Load / equilibrium run — {f.name}")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="upper right")

    ax2.plot(t, df["peristaltic_pump_set_speed_rpm"], color="tab:purple", label="pump rpm")
    ax2b = ax2.twinx()
    # cart sensors were swapped; show both for context
    ax2b.plot(t, df["cart_out_c"], color="tab:red", alpha=0.6, label="cart_out (hot side?)")
    ax2b.plot(t, df["cart_in_c"], color="tab:orange", alpha=0.6, label="cart_in")
    ax2.set_ylabel("Pump (rpm)", color="tab:purple")
    ax2b.set_ylabel("Cart temp (C)")
    ax2.set_xlabel("Time")
    ax2.grid(True, alpha=0.3)
    lines, labels = ax2.get_legend_handles_labels()
    lines2, labels2 = ax2b.get_legend_handles_labels()
    ax2.legend(lines + lines2, labels + labels2, loc="upper left")

    fig.tight_layout()
    out2 = OUT_DIR / (f.stem.lstrip("_") + "_load.png")
    fig.savefig(out2, dpi=150)
    plt.close(fig)
    print(f"Saved {out2}")
