"""Steady hold on the 2026-10-16 cartridge log, 13–18 min, for a slide.

Temperature and cooling power only. Ice bath is probe_4_c (the cold steady
probe; the old ice_water header is now a plate backup). Hot bath is hot_bath1_c.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from plot_cooling_power import OUTPUT_DATA, RAW_DATA, load_run  # noqa: E402

CSV_PATH = RAW_DATA / "20261016_155612_sensors.csv"
START_MIN = 13.0
END_MIN = 18.0
TITLE = "Cartridge Power Test\nIce Bath (0°C), 45 ml/min"

plt.rcParams.update(
    {
        "axes.labelsize": 22,
        "xtick.labelsize": 18,
        "ytick.labelsize": 18,
        "legend.fontsize": 18,
        "figure.titlesize": 26,
        "axes.linewidth": 1.4,
    }
)


def plot() -> Path:
    df = load_run(CSV_PATH)
    part = df[(df["t_min"] >= START_MIN) & (df["t_min"] <= END_MIN)].copy()
    if part.empty:
        raise ValueError(f"No samples between {START_MIN} and {END_MIN} min")

    fig, axes = plt.subplots(4, 1, figsize=(13.5, 14), sharex=True)

    axes[0].plot(part["t_min"], part["inlet_c"], label="Input to Cartridge", color="#006d2c", linewidth=2.4)
    axes[0].plot(part["t_min"], part["outlet_c"], label="Output from Cartridge", color="#74c476", linewidth=2.4)
    axes[0].set_ylabel("Temperature (°C)")
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best", framealpha=0.95)
    axes[0].tick_params(width=1.4, length=6)

    axes[1].plot(part["t_min"], part["power_w"], color="#d94801", linewidth=2.4)
    axes[1].set_ylabel("Cooling power (W)")
    axes[1].grid(True, alpha=0.3)
    axes[1].tick_params(width=1.4, length=6)

    axes[2].plot(part["t_min"], part["probe_4_c"], color="#08519c", linewidth=2.4)
    axes[2].set_ylabel("Ice bath (°C)")
    axes[2].grid(True, alpha=0.3)
    axes[2].tick_params(width=1.4, length=6)

    axes[3].plot(part["t_min"], part["hot_bath1_c"], color="#cb181d", linewidth=2.4)
    axes[3].set_ylabel("Hot bath (°C)")
    axes[3].set_xlabel("Elapsed time (min)")
    axes[3].grid(True, alpha=0.3)
    axes[3].tick_params(width=1.4, length=6)

    fig.suptitle(TITLE, fontsize=26)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out = OUTPUT_DATA / f"cooling_power_{CSV_PATH.stem}_13_18_steady.png"
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(plot())
