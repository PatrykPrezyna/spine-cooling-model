"""Cooling power versus bath temperature for the 2026-10-20 cartridge log.

P = m_dot * c_p * (T_in - T_out), using the flow sensor.
Each point is the last 45 s of a stable hot-bath hold while the pump is on.
The panel underneath is cartridge inlet and outlet at those same holds.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from plot_cooling_power import (  # noqa: E402
    KEYENCE_MIN_ML_MIN,
    OUTPUT_DATA,
    RAW_DATA,
    load_run,
)

CSV_PATH = RAW_DATA / "20261020_094133_sensors.csv"
BATH_STD_MAX_C = 0.08
BATH_SMOOTH_S = 40.0
MIN_HOLD_S = 120.0
STEADY_TAIL_S = 45.0
TAIL_POWER_STD_MAX_W = 1.5
RPM_ON = 1.0


def bath_holds(df: pd.DataFrame) -> pd.DataFrame:
    """Last 45 s of each flat bath interval with steady cooling power."""

    flowing = (df["peristaltic_pump_set_speed_rpm"] > RPM_ON) & (
        df["sensor_ml_min"] > KEYENCE_MIN_ML_MIN
    )
    sub = df.loc[flowing].copy()
    if len(sub) < 8:
        return pd.DataFrame()

    t0 = df["timestamp"].iloc[0]
    sub["t_s"] = (sub["timestamp"] - t0).dt.total_seconds()
    sub["bath_c"] = sub["hot_bath1_c"]
    dt = float(np.median(np.diff(sub["t_s"].to_numpy())))
    win = max(5, int(round(BATH_SMOOTH_S / max(dt, 1e-3))))
    smooth = sub["bath_c"].rolling(win, center=True, min_periods=5).mean()
    roll_std = smooth.rolling(win, center=True, min_periods=5).std()
    flat = (roll_std <= BATH_STD_MAX_C).fillna(False)
    block = flat.ne(flat.shift()).cumsum()

    rows = []
    for _, group in sub.loc[flat].groupby(block.loc[flat]):
        start_s = float(group["t_s"].iloc[0])
        end_s = float(group["t_s"].iloc[-1])
        if end_s - start_s < MIN_HOLD_S:
            continue
        tail = group[group["t_s"] >= end_s - STEADY_TAIL_S]
        if len(tail) < 8 or float(tail["power_w"].std()) > TAIL_POWER_STD_MAX_W:
            continue
        rows.append(
            {
                "t_start_s": start_s,
                "t_end_s": end_s,
                "bath_c": float(tail["bath_c"].mean()),
                "inlet_c": float(tail["inlet_c"].mean()),
                "outlet_c": float(tail["outlet_c"].mean()),
                "sensor_ml_min": float(tail["sensor_ml_min"].mean()),
                "power_w": float(tail["power_w"].mean()),
                "rpm": float(tail["peristaltic_pump_set_speed_rpm"].mean()),
            }
        )
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("t_start_s").reset_index(drop=True)


def later_bath_steps(holds: pd.DataFrame) -> pd.Series:
    """True for the final run of holds whose bath temperature does not fall."""

    later = pd.Series(False, index=holds.index)
    if holds.empty:
        return later
    start = len(holds) - 1
    baths = holds["bath_c"].to_numpy()
    while start > 0 and baths[start] >= baths[start - 1] - 0.05:
        start -= 1
    later.iloc[start:] = True
    return later


def _label(ax, x: float, y: float, text: str, color: str, dx: float, dy: float) -> None:
    if dy == 0.0 and dx != 0.0:
        ha = "left" if dx > 0 else "right"
        va = "center"
    else:
        ha = "center"
        va = "bottom" if dy >= 0 else "top"
    ax.annotate(
        text,
        (x, y),
        textcoords="offset points",
        xytext=(dx, dy),
        ha=ha,
        va=va,
        fontsize=8,
        color=color,
        annotation_clip=False,
    )


def _power_offsets(holds: pd.DataFrame) -> list[tuple[float, float]]:
    xs = holds["bath_c"].to_numpy()
    ys = holds["power_w"].to_numpy()
    offsets = [(0.0, 8.0) for _ in ys]
    for i, (x, y) in enumerate(zip(xs, ys)):
        dx, dy = 0.0, 8.0
        for j in range(i):
            same_bath = abs(x - xs[j]) < 0.4 and abs(y - ys[j]) >= 1.2
            if same_bath and y >= ys[j]:
                dx, dy = 0.0, 10.0
                offsets[j] = (-14.0, 0.0)
            elif same_bath:
                dx, dy = -14.0, 0.0
                offsets[j] = (0.0, 10.0)
            elif abs(y - ys[j]) < 1.0 and abs(x - xs[j]) < 1.6 and dy > 0:
                dy = -11.0
        offsets[i] = (dx, dy)
    return offsets


def plot(holds: pd.DataFrame, stem: str) -> Path:
    later = later_bath_steps(holds)
    steps = holds.loc[later]
    earlier = holds.loc[~later]
    fig, (ax_p, ax_t) = plt.subplots(2, 1, figsize=(8.2, 7.6), sharex=True)

    ax_p.plot(
        steps["bath_c"],
        steps["power_w"],
        "-o",
        color="#d94801",
        linewidth=1.6,
        markersize=7,
        label="Bath steps",
        zorder=3,
    )
    if not earlier.empty:
        ax_p.scatter(
            earlier["bath_c"],
            earlier["power_w"],
            marker="s",
            s=46,
            color="#d94801",
            label="Initial hold",
            zorder=4,
        )
    for (_, row), (dx, dy) in zip(holds.iterrows(), _power_offsets(holds)):
        _label(ax_p, row["bath_c"], row["power_w"], f"{row['power_w']:.1f}", "#d94801", dx, dy)
    ax_p.set_ylabel("Cooling power (W)")
    ax_p.set_title("Power vs bath temperature\n57 rpm, last 45 s of each hold")
    ax_p.grid(True, alpha=0.3)
    ax_p.legend(loc="upper left", framealpha=0.9)
    power_pad = max(1.6, (holds["power_w"].max() - holds["power_w"].min()) * 0.45)
    ax_p.set_ylim(holds["power_w"].min() - power_pad, holds["power_w"].max() + power_pad)

    ax_t.plot(
        steps["bath_c"],
        steps["inlet_c"],
        "-o",
        color="#006d2c",
        linewidth=1.6,
        markersize=7,
        label="Cartridge input",
        zorder=3,
    )
    ax_t.plot(
        steps["bath_c"],
        steps["outlet_c"],
        "-o",
        color="#74c476",
        linewidth=1.6,
        markersize=7,
        label="Cartridge output",
        zorder=3,
    )
    if not earlier.empty:
        ax_t.scatter(
            earlier["bath_c"],
            earlier["inlet_c"],
            marker="s",
            s=46,
            color="#006d2c",
            label="Initial hold",
            zorder=4,
        )
        ax_t.scatter(
            earlier["bath_c"],
            earlier["outlet_c"],
            marker="s",
            s=46,
            color="#74c476",
            zorder=4,
        )

    placed: list[tuple[float, float]] = []
    for _, row in holds.iterrows():
        for column, color, dy in (
            ("inlet_c", "#006d2c", 8.0),
            ("outlet_c", "#74c476", -11.0),
        ):
            x = float(row["bath_c"])
            y = float(row[column])
            if any(abs(x - px) < 0.4 and abs(y - py) < 0.25 for px, py in placed):
                continue
            dx = -16.0 if (not bool(later.loc[row.name]) and column == "outlet_c") else 0.0
            _label(ax_t, x, y, f"{y:.1f}", color, dx, dy)
            placed.append((x, y))

    ax_t.set_xlabel("Bath temperature (°C)")
    ax_t.set_ylabel("Temperature (°C)")
    ax_t.grid(True, alpha=0.3)
    ax_t.legend(loc="center left", framealpha=0.9)
    temp_top = float(holds["inlet_c"].max())
    temp_bottom = float(holds["outlet_c"].min())
    ax_t.set_ylim(temp_bottom - 1.8, temp_top + 1.6)
    span = float(holds["bath_c"].max() - holds["bath_c"].min())
    pad_x = max(0.35, span * 0.08)
    ax_t.set_xlim(float(holds["bath_c"].min()) - pad_x, float(holds["bath_c"].max()) + pad_x)

    fig.tight_layout()
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DATA / f"power_vs_bath_temperature_{stem}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    if not CSV_PATH.exists():
        print(f"Missing {CSV_PATH}")
        return
    holds = bath_holds(load_run(CSV_PATH))
    # The final 17 °C step was still colder at the outlet than the long hold.
    holds = holds.iloc[:-1].reset_index(drop=True)
    if holds.empty:
        print(f"No stable bath holds in {CSV_PATH.name}")
        return
    out = plot(holds, CSV_PATH.stem)
    print(f"{CSV_PATH.name} -> {out.name}")
    print(
        holds[
            ["bath_c", "inlet_c", "outlet_c", "sensor_ml_min", "power_w", "t_start_s", "t_end_s"]
        ].to_string(index=False, float_format=lambda value: f"{value:.2f}")
    )


if __name__ == "__main__":
    main()
