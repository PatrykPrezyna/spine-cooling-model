"""
Plot 3 pump rotations starting at a given time: simulated shaft position + pressures.

Reads CSVs from raw_data/ (or an explicit path) and writes PNGs to output_data/.

Usage:
  python plot_three_rotations.py sensor_log_20260715_111143.csv 11:12:04
  python plot_three_rotations.py sensor_log_20260715_110327.csv "2026-07-15 11:04:30"
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import load_sensor_csv

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"
N_ROTATIONS = 3

PRESSURE_COLS = [
    ("cartridge_input_psi", "Cartridge input (psi)", "tab:blue"),
    ("cartridge_output_psi", "Cartridge output (psi)", "tab:orange"),
    ("pump_input_psi", "Pump input (psi)", "tab:green"),
    ("pump_output_psi", "Pump output (psi)", "tab:red"),
]


def parse_start_time(raw: str, timestamps: pd.Series) -> pd.Timestamp:
    """Accept full timestamp or time-of-day (HH:MM[:SS[.fff]])."""
    raw = raw.strip()
    try:
        t = pd.to_datetime(raw)
    except (ValueError, TypeError) as exc:
        raise SystemExit(f"Could not parse start time {raw!r}: {exc}") from exc

    if t.tzinfo is not None:
        t = t.tz_localize(None)
    # Time-only strings parse as today 1900 — treat as clock time on log day.
    if t.year == 1900 or (len(raw) <= 12 and " " not in raw and "T" not in raw.upper()):
        day = timestamps.iloc[0].normalize()
        t = day + (t - t.normalize())
    return pd.Timestamp(t)


def resolve_csv(raw: str) -> Path:
    csv_path = Path(raw)
    if csv_path.is_file():
        return csv_path
    for candidate in (HERE / raw, RAW_DATA / raw, RAW_DATA / Path(raw).name):
        if candidate.is_file():
            return candidate
    raise SystemExit(f"CSV not found: {raw} (looked in {HERE} and {RAW_DATA})")


def load_window(csv_path: Path, start_raw: str) -> tuple[pd.DataFrame, float, float]:
    df = load_sensor_csv(csv_path)

    start = parse_start_time(start_raw, df["timestamp"])
    if start < df["timestamp"].iloc[0] or start > df["timestamp"].iloc[-1]:
        raise SystemExit(
            f"Start {start} is outside log range "
            f"[{df['timestamp'].iloc[0]} .. {df['timestamp'].iloc[-1]}]"
        )

    # Nearest sample at/after start
    idx = int((df["timestamp"] - start).abs().idxmin())
    if df.loc[idx, "timestamp"] < start and idx + 1 < len(df):
        idx += 1

    rpm = float(df.loc[idx, "peristaltic_pump_set_speed_rpm"])
    if rpm <= 0:
        raise SystemExit(f"Pump RPM is {rpm} at start — need non-zero speed for rotations.")

    duration_s = N_ROTATIONS * 60.0 / rpm
    t0 = df.loc[idx, "timestamp"]
    t1 = t0 + pd.Timedelta(seconds=duration_s)
    window = df[(df["timestamp"] >= t0) & (df["timestamp"] <= t1)].copy()
    if len(window) < 2:
        raise SystemExit(
            f"Too few samples in {duration_s:.3f}s window (need higher RPM or denser data)."
        )

    t_rel = (window["timestamp"] - t0).dt.total_seconds().to_numpy()
    window["t_s"] = t_rel
    window["revolutions"] = rpm / 60.0 * t_rel
    # Unitless roller-phase waveform (1 cycle per shaft revolution)
    window["pump_phase"] = np.sin(2.0 * np.pi * window["revolutions"])

    return window, rpm, duration_s


def _plot_panel(ax, window: pd.DataFrame, series: list[tuple[str, str, str]], rpm: float) -> None:
    for col, label, color in series:
        ax.plot(
            window["t_s"],
            window[col],
            color=color,
            marker="o",
            markersize=3,
            linewidth=1,
            label=label,
        )

    ax2 = ax.twinx()
    ax2.plot(
        window["t_s"],
        window["pump_phase"],
        color="gray",
        linestyle="--",
        linewidth=1.5,
        alpha=0.85,
        label="sim. pump phase",
    )
    ax2.set_ylabel("Sim. pump phase", color="gray")
    ax2.set_ylim(-1.3, 1.3)
    ax2.tick_params(axis="y", labelcolor="gray")

    for k in range(1, N_ROTATIONS):
        ax.axvline(k * 60.0 / rpm, color="black", linestyle=":", alpha=0.4)

    ax.set_ylabel("Pressure (psi)")
    ax.grid(True, alpha=0.3)

    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="best", fontsize=8)


def plot_window(window: pd.DataFrame, csv_path: Path, rpm: float, duration_s: float) -> Path:
    fig, (ax_pump, ax_cart) = plt.subplots(2, 1, sharex=True, figsize=(11, 8))
    t0 = window["timestamp"].iloc[0]
    fig.suptitle(
        f"{N_ROTATIONS} pump rotations @ {rpm:.0f} RPM  "
        f"({duration_s:.2f}s, {len(window)} samples @ ~10 Hz)\n"
        f"{csv_path.name}  start {t0.strftime('%H:%M:%S.%f')[:-3]}"
    )

    pump_series = [s for s in PRESSURE_COLS if s[0].startswith("pump_")]
    cart_series = [s for s in PRESSURE_COLS if s[0].startswith("cartridge_")]

    _plot_panel(ax_pump, window, pump_series, rpm)
    ax_pump.set_title("Pump input / output")

    _plot_panel(ax_cart, window, cart_series, rpm)
    ax_cart.set_title("Cartridge input / output")
    ax_cart.set_xlabel("Time from start (s)")

    fig.tight_layout()

    stamp = t0.strftime("%H%M%S")
    stem = csv_path.stem.removeprefix("sensor_log_")
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DATA / f"three_rotations_{stem}_{stamp}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.show()
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", help="CSV file name (in raw_data/ or a path)")
    parser.add_argument("start_time", help="Start time, e.g. 11:12:04 or full timestamp")
    args = parser.parse_args()

    csv_path = resolve_csv(args.csv)
    window, rpm, duration_s = load_window(csv_path, args.start_time)
    print(f"RPM={rpm:.1f}  window={duration_s:.3f}s  samples={len(window)}")
    print(
        f"revolutions: {window['revolutions'].iloc[0]:.3f} -> "
        f"{window['revolutions'].iloc[-1]:.3f}"
    )
    out = plot_window(window, csv_path, rpm, duration_s)
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
