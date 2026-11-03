"""Split the wear log into three runs and plot the flow drop in each.

The original CSVs stay in ``raw_data/``. This writes three period files beside
them (sensor log and the matching 100 Hz pressure log):

1. Start through the long pump-off.
2. Switch-on of the same tubing after that pump-off.
3. ``20261006_153226_tube2_first_on``, recorded after the exchange.

On each plot the flow drop is the change from the flow just after the
50 ml/min run is established to the flow at the end of that continuous run.
The 95% time is when a 5-minute median first stays at or below 95% of the
way from the starting flow to the ending flow.
"""

from __future__ import annotations

from datetime import datetime
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

SOURCE_STEM = "20261005_090840"
SETPOINT_ML_MIN = 50.0
# A drop smaller than this is within the minute-to-minute scatter.
MIN_DROP_ML_MIN = 0.5

PERIODS = (
    {
        "key": "tube1_first_on",
        "title": "Start until pump off",
        "file_stamp": "20261005_090841",
    },
    {
        "key": "tube1_second_on",
        "title": "Old tubing, switched on after pump-off",
        "file_stamp": "20261005_213631",
    },
)

# Continuation recorded after the tubing exchange. Not a slice of the first log.
NEW_TUBING_STEM = "20261006_153226_tube2_first_on"
NEW_TUBING_TITLE = "New tubing, switched on after the exchange"


def _source(kind: str) -> Path:
    return RAW_DATA / f"{SOURCE_STEM}_{kind}.csv"


def _period_path(stamp: str, key: str, kind: str) -> Path:
    return RAW_DATA / f"{stamp}_{key}_{kind}.csv"


def _parse_timestamp(text: str) -> datetime:
    return datetime.fromisoformat(text.strip())


def off_spans(sensors: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    off = sensors["peristaltic_pump_set_speed_rpm"] <= 1.0
    if not bool(off.any()):
        return []
    block = off.ne(off.shift(fill_value=False)).cumsum()
    spans: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for _, idx in sensors.loc[off].groupby(block[off]).groups.items():
        labels = list(idx)
        spans.append(
            (
                sensors.loc[labels[0], "timestamp"],
                sensors.loc[labels[-1], "timestamp"],
            )
        )
    return spans


def period_bounds(
    sensors: pd.DataFrame,
) -> list[tuple[pd.Timestamp | None, pd.Timestamp | None]]:
    """Return (start, end) pairs, end exclusive, for the three runs."""

    spans = off_spans(sensors)
    if not spans:
        raise RuntimeError("No pump-off interval in the sensor log")
    long_off = max(spans, key=lambda span: span[1] - span[0])
    if long_off[1] - long_off[0] < pd.Timedelta(minutes=30):
        raise RuntimeError("No multi-hour pump-off interval in the sensor log")
    later = [
        span
        for span in spans
        if span[0] > long_off[1]
        and pd.Timedelta(seconds=20) <= (span[1] - span[0]) <= pd.Timedelta(minutes=15)
    ]
    if len(later) != 1:
        raise RuntimeError(
            f"Expected one short stop after the pump-off for the tubing change, found {len(later)}"
        )
    tube_off = later[0]
    timestamps = sensors["timestamp"]
    on = sensors["peristaltic_pump_set_speed_rpm"] > 1.0
    on_block = on.ne(on.shift(fill_value=False)).cumsum()
    wear_end = timestamps.iloc[0]
    wear_dur = pd.Timedelta(0)
    for _, idx in sensors.loc[on & (timestamps < long_off[0])].groupby(on_block[on]).groups.items():
        labels = list(idx)
        dur = timestamps.loc[labels[-1]] - timestamps.loc[labels[0]]
        if dur > wear_dur:
            wear_dur = dur
            wear_end = timestamps.loc[labels[-1]]
    # Stop the first file when that run is switched off, not during the
    # short restarts just before the multi-hour off.
    first_end = timestamps[timestamps > wear_end].iloc[0]

    def first_after(when: pd.Timestamp) -> pd.Timestamp:
        later_than = timestamps[timestamps > when]
        if later_than.empty:
            raise RuntimeError(f"No samples after {when}")
        return later_than.iloc[0]

    # End bounds are exclusive. Runs do not include the pump-off gaps.
    # The new-tubing run is a separate log and is not sliced from this file.
    return [
        (None, first_end),
        (first_after(long_off[1]), tube_off[0]),
    ]


def split_csv(
    source: Path,
    destinations: list[tuple[Path, pd.Timestamp | None, pd.Timestamp | None]],
) -> None:
    handles: list[tuple] = []
    with source.open(newline="") as src:
        header = src.readline()
        if not header:
            raise RuntimeError(f"Empty CSV: {source}")
        for dest, start, end in destinations:
            handle = dest.open("w", newline="")
            handle.write(header)
            handles.append((handle, start, end))
        for line in src:
            if not line.strip():
                continue
            timestamp = _parse_timestamp(line.split(",", 1)[0])
            for handle, start, end in handles:
                if start is not None and timestamp < start.to_pydatetime():
                    continue
                if end is not None and timestamp >= end.to_pydatetime():
                    continue
                handle.write(line)
                break
    for handle, _, _ in handles:
        handle.close()


def write_period_files(bounds: list[tuple[pd.Timestamp | None, pd.Timestamp | None]]) -> list[Path]:
    sensor_dest = []
    pressure_dest = []
    sensor_paths = []
    for period, (start, end) in zip(PERIODS, bounds):
        sensor_path = _period_path(period["file_stamp"], period["key"], "sensors")
        pressure_path = _period_path(
            period["file_stamp"], period["key"], "pressure_100Hz"
        )
        sensor_dest.append((sensor_path, start, end))
        pressure_dest.append((pressure_path, start, end))
        sensor_paths.append(sensor_path)
    split_csv(_source("sensors"), sensor_dest)
    split_csv(_source("pressure_100Hz"), pressure_dest)
    for path, _, _ in sensor_dest + pressure_dest:
        print(f"  wrote {path.name}")
    return sensor_paths


def _longest_on_span(sensors: pd.DataFrame) -> pd.DataFrame:
    """The longest stretch with the pump commanded on, startup blips excluded."""

    on = sensors["peristaltic_pump_set_speed_rpm"] > 1.0
    if not bool(on.any()):
        return sensors.iloc[0:0]
    block = on.ne(on.shift(fill_value=False)).cumsum()
    best: list | None = None
    best_dur = pd.Timedelta(0)
    for _, idx in sensors.loc[on].groupby(block[on]).groups.items():
        labels = list(idx)
        dur = (
            sensors.loc[labels[-1], "timestamp"] - sensors.loc[labels[0], "timestamp"]
        )
        if dur > best_dur:
            best_dur = dur
            best = labels
    if best is None:
        return sensors.iloc[0:0]
    return sensors.loc[best[0] : best[-1]]


def _minute_median(sensors: pd.DataFrame) -> pd.Series:
    """1-minute median flow on the longest continuous 50 ml/min run."""

    span = _longest_on_span(sensors)
    set_ml = span["pump_flow_ml_per_s"] * 60.0
    at_setpoint = span.loc[set_ml.between(48.0, 52.0)]
    if at_setpoint.empty:
        return pd.Series(dtype=float)
    indexed = at_setpoint.set_index("timestamp").sort_index()
    med = (
        indexed["flow_sensor_ml_per_min"]
        .rolling("60s", center=True, min_periods=8)
        .median()
        .resample("1min")
        .median()
        .dropna()
    )
    # The last minutes include the pump being switched off.
    if len(med) > 6:
        med = med.iloc[:-2]
    return med


def _trim_opening_spike(med: pd.Series) -> pd.Series:
    """Drop a brief flow overshoot in the first minutes (the 100 ml/min bump)."""

    if len(med) < 20:
        return med
    later = med.iloc[8:16]
    if float(med.iloc[:15].max()) <= float(later.median()) + 1.0:
        return med
    settled = med.iloc[:15][med.iloc[:15] <= float(later.median()) + 0.5]
    if settled.empty:
        return med
    return med.loc[settled.index[-1] :]


def flow_drop(sensors: pd.DataFrame) -> dict:
    med = _trim_opening_spike(_minute_median(sensors))
    if len(med) < 6:
        return {"initial": None, "final": None, "drop": None, "t95": None, "t_initial": None}
    # Starting flow is the early peak, once the run is up, not the ramp into it.
    head = med.iloc[:20] if len(med) >= 20 else med
    peak_at = head.idxmax()
    center = int(med.index.get_loc(peak_at))
    window = med.iloc[max(0, center - 2) : center + 3]
    initial = float(window.median())
    t_initial = peak_at
    final = float(med.iloc[-10:].median()) if len(med) >= 20 else float(med.iloc[-3:].median())
    drop = initial - final
    result = {
        "initial": initial,
        "final": final,
        "drop": drop,
        "t_initial": t_initial,
        "t95": None,
    }
    if drop < MIN_DROP_ML_MIN:
        return result
    target = initial - 0.95 * drop
    hold = med.rolling(5, min_periods=3).median()
    below = (hold <= target).to_numpy()
    for i in range(len(below) - 10):
        if med.index[i] < t_initial:
            continue
        if bool(below[i : i + 10].all()):
            result["t95"] = med.index[i]
            break
    return result


def _format_span(hours: float) -> str:
    if hours < 3.0:
        return f"{hours * 60.0:.0f} min"
    return f"{hours:.1f} h"


def _elapsed_hours(timestamps: pd.Series, t0: pd.Timestamp) -> pd.Series:
    return (timestamps - t0).dt.total_seconds() / 3600.0


def plot_period(sensor_path: Path, pressure_path: Path, title: str) -> Path:
    sensors = load_sensor_csv(sensor_path, recalibrate_pump_flow=False)
    pressure = load_sensor_csv(pressure_path, recalibrate_pump_flow=False)
    t0 = sensors["timestamp"].iloc[0]
    drop = flow_drop(sensors)

    flow = sensors.set_index("timestamp")
    flow_h = _elapsed_hours(flow.index.to_series(), t0)
    measured = flow["flow_sensor_ml_per_min"]
    measured_mean = measured.rolling("30s", center=True, min_periods=1).mean()
    set_ml = flow["pump_flow_ml_per_s"] * 60.0

    pump = pressure.set_index("timestamp")[["pump_in_bar", "pump_out_bar"]]
    binned = pump.resample("10s").agg(["mean", "min", "max"]).dropna(how="all")
    bin_h = _elapsed_hours(binned.index.to_series(), t0)
    duration_h = max(float(flow_h.iloc[-1]), float(bin_h.iloc[-1]))
    use_minutes = duration_h < 1.0
    scale = 60.0 if use_minutes else 1.0
    flow_x = flow_h * scale
    bin_x = bin_h * scale

    fig, (ax_f, ax_p) = plt.subplots(
        2, 1, figsize=(11, 7), sharex=True, height_ratios=[1.15, 1]
    )
    fig.suptitle(title)

    ax_f.plot(flow_x, measured, color="tab:blue", linewidth=0.4, alpha=0.25, label="Measured")
    ax_f.plot(
        flow_x,
        measured_mean,
        color="tab:blue",
        linewidth=1.4,
        label="Measured (30 s mean)",
    )
    ax_f.plot(flow_x, set_ml, color="0.35", linewidth=1.0, linestyle="--", label="Set")
    ax_f.set_ylabel("Flow (ml/min)")
    ax_f.grid(True, alpha=0.3)

    on = flow["peristaltic_pump_set_speed_rpm"] > 1.0
    running = measured[on & set_ml.between(48.0, 52.0) & (measured > 30.0)]
    if len(running):
        ax_f.set_ylim(float(running.quantile(0.01)) - 1.0, SETPOINT_ML_MIN + 4.0)

    lines = []
    settled_drop = (
        drop["initial"] is not None
        and drop["drop"] is not None
        and drop["drop"] >= MIN_DROP_ML_MIN
    )
    if settled_drop:
        pct = 100.0 * drop["drop"] / drop["initial"]
        if drop["t95"] is not None:
            t95_x = float((drop["t95"] - t0).total_seconds() / 3600.0) * scale
            span = _format_span(
                (drop["t95"] - drop["t_initial"]).total_seconds() / 3600.0
            )
            ax_f.axvline(t95_x, color="0.15", linewidth=1.0, linestyle=":")
            ax_p.axvline(t95_x, color="0.15", linewidth=1.0, linestyle=":")
            lines.append(f"Fell {drop['drop']:.1f} ml/min ({pct:.1f}%)")
            lines.append(f"{drop['initial']:.1f} to {drop['final']:.1f} ml/min")
            lines.append(f"95% of that drop in {span}")
            print(
                f"  {drop['initial']:.2f} -> {drop['final']:.2f} ml/min"
                f"  ({drop['drop']:.2f} ml/min, {pct:.1f}%)"
                f"  95% in {span} at {drop['t95']}"
            )
        else:
            lines.append(f"Fell {drop['drop']:.1f} ml/min ({pct:.1f}%)")
            lines.append("95% of that drop was not reached")
            print(
                f"  {drop['initial']:.2f} -> {drop['final']:.2f} ml/min"
                f"  95% not reached"
            )
    elif drop["initial"] is not None:
        lines.append(f"Held near {drop['final']:.1f} ml/min")
        lines.append(f"No decrease in {_format_span(duration_h)}")
        print(
            f"  no settled decrease in {_format_span(duration_h)}"
            f"  ({drop['initial']:.2f} -> {drop['final']:.2f} ml/min)"
        )
    if lines:
        ax_f.text(
            0.98,
            0.97,
            "\n".join(lines),
            transform=ax_f.transAxes,
            ha="right",
            va="top",
            fontsize=9,
            color="0.1",
            bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.9, "edgecolor": "0.8"},
        )
    ax_f.legend(loc="upper left" if not settled_drop else "lower left", framealpha=0.9)

    for column, label, color in (
        ("pump_in_bar", "Before pump", "tab:green"),
        ("pump_out_bar", "After pump", "tab:red"),
    ):
        ax_p.fill_between(
            bin_x,
            binned[(column, "min")],
            binned[(column, "max")],
            color=color,
            alpha=0.18,
            linewidth=0,
        )
        ax_p.plot(
            bin_x,
            binned[(column, "mean")],
            color=color,
            linewidth=1.2,
            label=f"{label} (10 s mean)",
        )
    ax_p.axhline(0.0, color="0.5", linewidth=0.8, alpha=0.6)
    ax_p.set_ylabel("Pressure (bar)")
    ax_p.set_xlabel("Elapsed time (min)" if use_minutes else "Elapsed time (h)")
    ax_p.grid(True, alpha=0.3)
    ax_p.legend(loc="upper right", framealpha=0.9)
    ax_p.set_xlim(0.0, duration_h * scale)

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    stem = sensor_path.name.removesuffix("_sensors.csv")
    out = OUTPUT_DATA / f"flow_drop_{stem}.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    source = _source("sensors")
    if not source.is_file():
        print(f"No source log {source.name}")
        return
    sensors = load_sensor_csv(source, recalibrate_pump_flow=False)
    bounds = period_bounds(sensors)
    print("Splitting the sensor and pressure logs")
    sensor_paths = write_period_files(bounds)
    for period, sensor_path in zip(PERIODS, sensor_paths):
        pressure_path = _period_path(
            period["file_stamp"], period["key"], "pressure_100Hz"
        )
        print(f"\n{period['title']}")
        out = plot_period(sensor_path, pressure_path, period["title"])
        print(f"  {sensor_path.name} -> {out.name}")

    new_sensors = RAW_DATA / f"{NEW_TUBING_STEM}_sensors.csv"
    new_pressure = RAW_DATA / f"{NEW_TUBING_STEM}_pressure_100Hz.csv"
    if not new_sensors.is_file() or not new_pressure.is_file():
        raise FileNotFoundError(
            f"New-tubing log missing: {new_sensors.name} and {new_pressure.name}"
        )
    print(f"\n{NEW_TUBING_TITLE}")
    out = plot_period(new_sensors, new_pressure, NEW_TUBING_TITLE)
    print(f"  {new_sensors.name} -> {out.name}")


if __name__ == "__main__":
    main()
