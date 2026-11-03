"""Plot measured flow and pump inlet/outlet pressure over a wear run.

Reads ``*_sensors.csv`` for ``flow_sensor_ml_per_min`` and the matching
``*_pressure_100Hz.csv`` for ``pump_in_bar`` and ``pump_out_bar``. Writes one
PNG per pair to ``output_data/``.

The 100 Hz pressure log is drawn as a 10 s min–max band plus the 10 s mean so
the peristaltic pulsation and the slow trend are both visible. A short pump
stop near the end, after which measured flow steps up and stays up, is marked
as the tubing exchange. Raw logs are not modified.
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
# A tubing change is a short stop, not the multi-hour pump-off in the middle.
TUBING_STOP_MIN_S = 20.0
TUBING_STOP_MAX_S = 15 * 60.0
TUBING_FLOW_STEP_ML_MIN = 1.5
COMPARE_WINDOW_H = 10.0 / 60.0


def sensor_logs() -> list[Path]:
    """Full-run logs only. Period slices are written beside them and plotted separately."""

    # 20261006 is the archived tube-2 run and is not part of this analysis.
    skip = ("tube1_", "tube2_", "20261006")
    return sorted(
        p
        for p in RAW_DATA.glob("*_sensors.csv")
        if p.is_file() and not any(token in p.name for token in skip)
    )


def pressure_log_for(sensor_path: Path) -> Path:
    stem = sensor_path.name.removesuffix("_sensors.csv")
    return sensor_path.with_name(f"{stem}_pressure_100Hz.csv")


def _output_path(sensor_path: Path) -> Path:
    stem = sensor_path.name.removesuffix("_sensors.csv")
    return OUTPUT_DATA / f"flow_and_pump_pressure_{stem}.png"


def _elapsed_hours(timestamps: pd.Series, t0: pd.Timestamp) -> pd.Series:
    return (timestamps - t0).dt.total_seconds() / 3600.0


def pump_off_intervals(rpm: pd.Series, hours: pd.Series) -> list[tuple[float, float]]:
    """Return (start_h, end_h) for each stretch with the pump commanded off."""

    off = (rpm.to_numpy() <= 1.0)
    elapsed = hours.to_numpy()
    intervals: list[tuple[float, float]] = []
    start: int | None = None
    for i, is_off in enumerate(off):
        if is_off and start is None:
            start = i
        elif not is_off and start is not None:
            if (elapsed[i - 1] - elapsed[start]) * 3600.0 >= TUBING_STOP_MIN_S:
                intervals.append((float(elapsed[start]), float(elapsed[i - 1])))
            start = None
    if start is not None and (elapsed[-1] - elapsed[start]) * 3600.0 >= TUBING_STOP_MIN_S:
        intervals.append((float(elapsed[start]), float(elapsed[-1])))
    return intervals


def _median_flow(
    measured: pd.Series, hours: pd.Series, start_h: float, end_h: float
) -> float | None:
    window = measured[(hours >= start_h) & (hours < end_h) & (measured > 5.0)]
    if len(window) < 10:
        return None
    return float(window.median())


def tubing_exchange(
    measured: pd.Series, hours: pd.Series, intervals: list[tuple[float, float]]
) -> tuple[float, float, float] | None:
    """Last short stop after which measured flow stays higher.

    Returns (mark_h, flow_before, flow_after). The mark is the restart, when
    the new tube is in the circuit.
    """

    found: tuple[float, float, float] | None = None
    for start_h, end_h in intervals:
        duration_s = (end_h - start_h) * 3600.0
        if duration_s > TUBING_STOP_MAX_S or start_h < 1.0:
            continue
        before = _median_flow(measured, hours, start_h - COMPARE_WINDOW_H, start_h)
        after = _median_flow(measured, hours, end_h, end_h + COMPARE_WINDOW_H)
        if before is None or after is None:
            continue
        if after - before >= TUBING_FLOW_STEP_ML_MIN:
            found = (end_h, before, after)
    return found


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

    # Scale to the main setpoint. A few-second ramp to a higher set flow
    # (100 ml/min at the restart) would otherwise hide the wear trend.
    set_on = set_ml_min[flow["peristaltic_pump_set_speed_rpm"] > 1.0]
    if len(set_on):
        setpoint = float(set_on.round().mode().iloc[0])
        at_setpoint = measured[(set_ml_min - setpoint).abs() < 2.0]
        low = float(at_setpoint.quantile(0.01)) if len(at_setpoint) else setpoint - 8.0
        ax_f.set_ylim(low - 2.0, setpoint + 5.0)

    off_intervals = pump_off_intervals(
        flow["peristaltic_pump_set_speed_rpm"], flow_h
    )
    exchange = tubing_exchange(measured, flow_h, off_intervals)
    for start_h, end_h in off_intervals:
        if (end_h - start_h) * 60.0 < 30.0:
            continue
        for axis in (ax_f, ax_p):
            axis.axvspan(start_h, end_h, color="0.75", alpha=0.35, linewidth=0, zorder=0)
    long_offs = [
        (start_h, end_h)
        for start_h, end_h in off_intervals
        if (end_h - start_h) >= 0.5
    ]
    if long_offs:
        start_h, end_h = max(long_offs, key=lambda span: span[1] - span[0])
        ax_f.text(
            (start_h + end_h) / 2.0,
            0.08,
            "Pump off",
            transform=ax_f.get_xaxis_transform(),
            ha="center",
            va="bottom",
            fontsize=8,
            color="0.25",
        )

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

    if exchange is not None:
        mark_h, flow_before, flow_after = exchange
        for axis in (ax_f, ax_p):
            axis.axvline(mark_h, color="0.15", linewidth=1.0, linestyle=":")
        ax_f.annotate(
            f"Tubing exchanged\n{flow_before:.1f} → {flow_after:.1f} ml/min",
            xy=(mark_h, flow_after),
            xytext=(-8, 14),
            textcoords="offset points",
            ha="right",
            va="bottom",
            fontsize=8,
            color="0.15",
            arrowprops={"arrowstyle": "-", "color": "0.15"},
        )
        print(
            f"  tubing exchanged at {mark_h:.2f} h: "
            f"{flow_before:.2f} -> {flow_after:.2f} ml/min"
        )

    ax_f.legend(loc="lower left", framealpha=0.9)

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
