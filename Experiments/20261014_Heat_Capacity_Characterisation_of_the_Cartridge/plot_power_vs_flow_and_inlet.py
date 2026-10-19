"""Cooling power versus flow for the newest sensor log.

P = m_dot * c_p * (T_in - T_out), using the flow sensor.
Each point is the last 30 s of a pump-speed step while the cartridge
inlet is 19–21 °C.
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

INLET_BAND_C = (19.0, 21.0)


def newest_log() -> Path | None:
    logs = sorted(RAW_DATA.glob("*sensors*.csv"))
    return logs[-1] if logs else None


def long_hold_start(df: pd.DataFrame) -> pd.Timestamp:
    """Start of the last pump-speed hold longer than 5 minutes."""

    rpm = df["peristaltic_pump_set_speed_rpm"].round(0)
    block = rpm.ne(rpm.shift()).cumsum()
    long_starts: list[pd.Timestamp] = []
    for _, group in df.groupby(block):
        dur_s = (group["timestamp"].iloc[-1] - group["timestamp"].iloc[0]).total_seconds()
        if dur_s >= 300 and group["peristaltic_pump_set_speed_rpm"].median() > 1:
            long_starts.append(group["timestamp"].iloc[0])
    if not long_starts:
        return df["timestamp"].iloc[0]
    return long_starts[-1]


def step_tails(df: pd.DataFrame, hold_start: pd.Timestamp) -> pd.DataFrame:
    """Last 30 s of each speed step while the inlet is still 19–21 °C."""

    ladder = df[df["timestamp"] < hold_start]
    rpm = ladder["peristaltic_pump_set_speed_rpm"].round(0)
    block = rpm.ne(rpm.shift()).cumsum()
    rows = []
    low, high = INLET_BAND_C
    for _, group in ladder.groupby(block):
        dur_s = (group["timestamp"].iloc[-1] - group["timestamp"].iloc[0]).total_seconds()
        if dur_s < 45 or group["peristaltic_pump_set_speed_rpm"].median() < 1:
            continue
        tail = group[group["timestamp"] >= group["timestamp"].iloc[-1] - pd.Timedelta(seconds=30)]
        tail = tail[tail["sensor_ml_min"] > 5]
        if tail.empty or not (low <= float(tail["inlet_c"].median()) <= high):
            continue
        rows.append(
            {
                "rpm": float(group["peristaltic_pump_set_speed_rpm"].median()),
                "sensor_ml_min": float(tail["sensor_ml_min"].median()),
                "inlet_c": float(tail["inlet_c"].median()),
                "outlet_c": float(tail["outlet_c"].median()),
                "power_w": float(tail["power_w"].median()),
            }
        )
    return pd.DataFrame(rows)


def _label(ax, x: float, y: float, text: str, color: str) -> None:
    ax.annotate(
        text,
        (x, y),
        textcoords="offset points",
        xytext=(0, 8),
        ha="center",
        va="bottom",
        fontsize=8,
        color=color,
        annotation_clip=False,
    )


def plot(flow_steps: pd.DataFrame, stem: str) -> Path:
    fig, (ax_p, ax_t) = plt.subplots(2, 1, figsize=(7, 7.4), sharex=True)
    ax_p.plot(
        flow_steps["sensor_ml_min"],
        flow_steps["power_w"],
        "-o",
        color="#d94801",
        linewidth=1.6,
        markersize=7,
    )
    for _, row in flow_steps.iterrows():
        _label(ax_p, row["sensor_ml_min"], row["power_w"], f"{row['power_w']:.1f}", "#d94801")
    ax_p.set_ylabel("Cooling power (W)")
    ax_p.set_title("Power vs flow")
    ax_p.grid(True, alpha=0.3)
    power_pad = (flow_steps["power_w"].max() - flow_steps["power_w"].min()) * 0.25
    ax_p.set_ylim(flow_steps["power_w"].min() - 1, flow_steps["power_w"].max() + power_pad)

    ax_t.plot(
        flow_steps["sensor_ml_min"],
        flow_steps["inlet_c"],
        "-o",
        color="#006d2c",
        linewidth=1.6,
        markersize=7,
        label="Cartridge input",
    )
    ax_t.plot(
        flow_steps["sensor_ml_min"],
        flow_steps["outlet_c"],
        "-o",
        color="#74c476",
        linewidth=1.6,
        markersize=7,
        label="Cartridge output",
    )
    for _, row in flow_steps.iterrows():
        _label(ax_t, row["sensor_ml_min"], row["inlet_c"], f"{row['inlet_c']:.1f}", "#006d2c")
        _label(ax_t, row["sensor_ml_min"], row["outlet_c"], f"{row['outlet_c']:.1f}", "#74c476")
    ax_t.set_xlabel("Flow (ml/min)")
    ax_t.set_ylabel("Temperature (°C)")
    ax_t.grid(True, alpha=0.3)
    ax_t.legend(loc="center right", framealpha=0.9)
    temp_top = max(flow_steps["inlet_c"].max(), flow_steps["outlet_c"].max())
    temp_bottom = min(flow_steps["inlet_c"].min(), flow_steps["outlet_c"].min())
    ax_t.set_ylim(temp_bottom - 1.5, temp_top + 2.2)
    fig.tight_layout()
    out = OUTPUT_DATA / f"power_vs_flow_and_inlet_{stem}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    csv_path = newest_log()
    if csv_path is None:
        print("No input files yet. Drop sensor logs in raw_data/.")
        return

    df = load_run(csv_path)
    flow_steps = step_tails(df, long_hold_start(df))
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = plot(flow_steps, csv_path.stem)
    print(f"{csv_path.name} -> {out.name}")
    print(flow_steps.to_string(index=False, float_format=lambda value: f"{value:.1f}"))


if __name__ == "__main__":
    main()
