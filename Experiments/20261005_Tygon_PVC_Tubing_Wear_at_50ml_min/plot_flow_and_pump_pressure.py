"""Plot measured flow and pump inlet/outlet pressure over a wear run.

Reads ``*_sensors.csv`` for ``flow_sensor_ml_per_min`` and the matching
``*_pressure_100Hz.csv`` for ``pump_in_bar`` and ``pump_out_bar``. Writes one
PNG per pair to ``output_data/``.

The 100 Hz pressure log is drawn as a 10 s min–max band plus the 10 s mean so
the peristaltic pulsation and the slow trend are both visible. Raw logs are
not modified.
"""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import load_sensor_csv

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"

FLOW_SMOOTH = "30s"
PRESSURE_BIN = "10s"


def sensor_logs() -> list[Path]:
    return sorted(p for p in RAW_DATA.glob("*_sensors.csv") if p.is_file())


def pressure_log_for(sensor_path: Path) -> Path:
    stem = sensor_path.name.removesuffix("_sensors.csv")
    return sensor_path.with_name(f"{stem}_pressure_100Hz.csv")


def _output_path(sensor_path: Path) -> Path:
    stem = sensor_path.name.removesuffix("_sensors.csv")
    return OUTPUT_DATA / f"flow_and_pump_pressure_{stem}.png"


def _elapsed_hours(timestamps: pd.Series, t0: pd.Timestamp) -> pd.Series:
    return (timestamps - t0).dt.total_seconds() / 3600.0


def plot_pair(sensor_path: Path, pressure_path: Path) -> Path:
    sensors = load_sensor_csv(sensor_path, recalibrate_pump_flow=False)
    pressure = load_sensor_csv(pressure_path, recalibrate_pump_flow=False)
    t0 = min(sensors["timestamp"].iloc[0], pressure["timestamp"].iloc[0])

    flow = sensors.set_index("timestamp")
    flow_h = _elapsed_hours(flow.index.to_series(), t0)
    measured = flow["flow_sensor_ml_per_min"]
    measured_mean = measured.rolling(FLOW_SMOOTH, center=True, min_periods=1).mean()
    set_ml_min = flow["pump_flow_ml_per_s"] * 60.0

    pump = pressure.set_index("timestamp")[["pump_in_bar", "pump_out_bar"]]
    binned = pump.resample(PRESSURE_BIN).agg(["mean", "min", "max"]).dropna(how="all")
    bin_h = _elapsed_hours(binned.index.to_series(), t0)

    fig, (ax_f, ax_p) = plt.subplots(
        2, 1, figsize=(11, 7), sharex=True, height_ratios=[1, 1.15]
    )
    fig.suptitle(f"Measured flow and pump pressure\n{sensor_path.stem}")

    ax_f.plot(
        flow_h,
        measured,
        color="tab:blue",
        linewidth=0.4,
        alpha=0.25,
        label="Measured",
    )
    ax_f.plot(
        flow_h,
        measured_mean,
        color="tab:blue",
        linewidth=1.4,
        label=f"Measured ({FLOW_SMOOTH} mean)",
    )
    ax_f.plot(
        flow_h,
        set_ml_min,
        color="0.35",
        linewidth=1.0,
        linestyle="--",
        label="Set",
    )
    ax_f.set_ylabel("Flow (ml/min)")
    ax_f.grid(True, alpha=0.3)
    ax_f.legend(loc="lower right", framealpha=0.9)

    series = (
        ("pump_in_bar", "Before pump", "tab:green"),
        ("pump_out_bar", "After pump", "tab:red"),
    )
    for column, label, color in series:
        ax_p.fill_between(
            bin_h,
            binned[(column, "min")],
            binned[(column, "max")],
            color=color,
            alpha=0.18,
            linewidth=0,
        )
        ax_p.plot(
            bin_h,
            binned[(column, "mean")],
            color=color,
            linewidth=1.2,
            label=f"{label} ({PRESSURE_BIN} mean)",
        )
    ax_p.axhline(0.0, color="0.5", linewidth=0.8, alpha=0.6)
    ax_p.set_ylabel("Pressure (bar)")
    ax_p.set_xlabel("Elapsed time (h)")
    ax_p.grid(True, alpha=0.3)
    ax_p.legend(loc="upper right", framealpha=0.9)

    duration_h = max(float(flow_h.iloc[-1]), float(bin_h.iloc[-1]))
    ax_p.set_xlim(0.0, duration_h)

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = _output_path(sensor_path)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)

    on = flow["peristaltic_pump_set_speed_rpm"] > 1.0
    on_flow = measured.loc[on]
    print(f"\n{sensor_path.name}  ({duration_h:.2f} h, {len(sensors)} sensor samples)")
    print(f"  pressure: {pressure_path.name}  ({len(pressure)} samples)")
    if len(on_flow):
        print(
            f"  measured flow while pump on: "
            f"mean {on_flow.mean():.2f} ml/min, "
            f"set {set_ml_min.loc[on].mean():.2f} ml/min"
        )
    return out


def main() -> None:
    logs = sensor_logs()
    if not logs:
        print(f"No *_sensors.csv in {RAW_DATA}")
        return
    for sensor_path in logs:
        pressure_path = pressure_log_for(sensor_path)
        if not pressure_path.is_file():
            raise FileNotFoundError(
                f"No matching pressure log for {sensor_path.name}: {pressure_path.name}"
            )
        out = plot_pair(sensor_path, pressure_path)
        print(f"{sensor_path.name} -> {out}")


if __name__ == "__main__":
    main()
