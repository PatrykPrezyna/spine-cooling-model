"""Zoomed cooling-power plots for two windows of the 2026-10-15 cartridge log.

Same panels as plot_cooling_power.py: cartridge inlet and outlet, plate 1,
set flow versus the flow sensor, and water-side cooling power.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from plot_cooling_power import OUTPUT_DATA, RAW_DATA, load_run  # noqa: E402

CSV_PATH = RAW_DATA / "20261015_082137_sensors.csv"
WINDOWS_MIN = ((250.0, 320.0), (1000.0, 1060.0))


def window(df: pd.DataFrame, start_min: float, end_min: float) -> pd.DataFrame:
    selected = df[(df["t_min"] >= start_min) & (df["t_min"] <= end_min)]
    if selected.empty:
        raise ValueError(f"No samples between {start_min} and {end_min} min")
    return selected


def draw(axes: list, df: pd.DataFrame, title: str) -> None:
    axes[0].plot(df["t_min"], df["inlet_c"], label="Cartridge input", color="#006d2c", linewidth=1.2)
    axes[0].plot(df["t_min"], df["outlet_c"], label="Cartridge output", color="#74c476", linewidth=1.2)
    if "plate_1_c" in df.columns:
        axes[0].plot(df["t_min"], df["plate_1_c"], label="Plate 1", color="#08519c", linewidth=1.2)
    axes[0].set_ylabel("Temperature (°C)")
    axes[0].set_title(title)
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best", framealpha=0.9)

    axes[1].plot(df["t_min"], df["set_ml_min"], label="Set flow", color="0.35", linewidth=1.2, linestyle="--")
    if df["sensor_ml_min"].notna().any():
        axes[1].plot(df["t_min"], df["sensor_ml_min"], label="Flow sensor", color="tab:green", linewidth=1.2)
    axes[1].set_ylabel("Flow (ml/min)")
    axes[1].set_ylim(bottom=0)
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best", framealpha=0.9)

    axes[2].plot(df["t_min"], df["power_w"], color="#d94801", linewidth=1.2, label="From measured flow")
    axes[2].set_ylabel("Cooling power (W)")
    axes[2].set_xlabel("Elapsed time (min)")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(loc="best", framealpha=0.9)


def plot(df: pd.DataFrame) -> Path:
    fig, axes = plt.subplots(3, 2, figsize=(14, 9), sharex="col")
    for column, (start_min, end_min) in enumerate(WINDOWS_MIN):
        part = window(df, start_min, end_min)
        mean_w = float(part["power_w"].mean())
        title = f"{start_min:.0f}–{end_min:.0f} min  (mean {mean_w:.1f} W)"
        draw([axes[row, column] for row in range(3)], part, title)
    fig.suptitle(CSV_PATH.stem, fontsize=12)
    fig.tight_layout()
    out = OUTPUT_DATA / f"cooling_power_{CSV_PATH.stem}_250_320_and_1000_1060.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    df = load_run(CSV_PATH)
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = plot(df)
    print(out)


if __name__ == "__main__":
    main()
