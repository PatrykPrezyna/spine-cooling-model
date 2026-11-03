"""Plot Keyence flow against the protocol steps for the 2026-11-02 wear run.

The sensor log is one session. Step 4 is the long stretch at 57 rpm with no
stop. Each later protocol action is the next pump stop, in the order written
in the README. Step 11 is the stop at about 1011 min. Steps 12 and 13 fall in
that same stop; step 14 is the run that follows. Raw logs are not modified.
"""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import load_sensor_csv

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"

SOURCE = RAW_DATA / "20261102_164405_sensors.csv"
PRESSURE_SOURCE = RAW_DATA / "20261102_164405_pressure_100Hz.csv"
SETPOINT_ML_MIN = 50.0
# column, legend, color, draw the 10 s min–max band
PRESSURE_SERIES = (
    ("pump_in_bar", "Before pump", "tab:green", True),
    ("pump_out_bar", "After pump", "tab:red", True),
    ("catheter_in_bar", "Catheter in", "tab:purple", False),
    ("catheter_out_bar", "Catheter out", "tab:orange", False),
)
# Steps 5–10, then the shared stop for steps 11–13. Step 14 is the last run.
LATE_STEP_LABELS = (
    "5  +1 cm",
    "6  +1 cm",
    "7  To the end",
    "8  Bleed fitting",
    "9  New tube",
    "10  Catheter outlet",
    "11–13  Original tube",
)
LATE_STEP_COLORS = (
    "#9ecae1",
    "#6baed6",
    "#fdae6b",
    "#fd8d3c",
    "#e6550d",
    "#74c476",
    "#238b45",
)
STEP_14_COLOR = "#00441b"
SETUP_COLOR = "#d9d9d9"
STEP_4_COLOR = "#c6dbef"


def _blocks(rpm: pd.Series, minutes: pd.Series) -> list[dict]:
    """Contiguous pump on/off stretches. Boundaries meet, so spans tile the log."""

    changed = rpm.ne(rpm.shift(fill_value=rpm.iloc[0]))
    starts = [float(value) for value in minutes[changed]]
    on_flags = [bool(value) for value in rpm[changed].gt(1.0)]
    ends = starts[1:] + [float(minutes.iloc[-1])]
    return [
        {"on": on, "start": start, "end": end}
        for on, start, end in zip(on_flags, starts, ends, strict=True)
    ]


def _median_on(sensors: pd.DataFrame, start: float, end: float) -> float:
    window = sensors[
        (sensors["min"] >= start)
        & (sensors["min"] < end)
        & (sensors["peristaltic_pump_set_speed_rpm"] > 1.0)
        & (sensors["flow_sensor_ml_per_min"] > 5.0)
    ]
    if window.empty:
        return float("nan")
    return float(window["flow_sensor_ml_per_min"].median())


def protocol_steps(sensors: pd.DataFrame) -> list[dict]:
    """Assign README steps from the pump on/off sequence."""

    blocks = _blocks(
        sensors["peristaltic_pump_set_speed_rpm"], sensors["min"]
    )
    step4 = max(
        (block for block in blocks if block["on"]),
        key=lambda block: block["end"] - block["start"],
    )
    if (step4["end"] - step4["start"]) < 10 * 60:
        raise RuntimeError("No multi-hour pump-on stretch for step 4")

    after = [block for block in blocks if block["start"] >= step4["end"] - 1e-6]
    if not after or after[0]["on"]:
        raise RuntimeError("Step 4 does not end in a pump stop")
    if len(after) != 2 * len(LATE_STEP_LABELS):
        raise RuntimeError(
            f"Expected {len(LATE_STEP_LABELS)} stops after step 4, "
            f"found {sum(not block['on'] for block in after)}"
        )

    steps = [
        {
            "label": "1–3  Setup",
            "start": 0.0,
            "end": step4["start"],
            "color": SETUP_COLOR,
        },
        {
            "label": "4  Starting position",
            "start": step4["start"],
            "end": step4["end"],
            "color": STEP_4_COLOR,
        },
    ]
    for label, color, index in zip(
        LATE_STEP_LABELS, LATE_STEP_COLORS, range(len(LATE_STEP_LABELS)), strict=True
    ):
        stop = after[2 * index]
        run = after[2 * index + 1]
        if stop["on"] or not run["on"]:
            raise RuntimeError(f"Expected stop then run for {label}")
        # Steps 11–13 are the stop at ~1011 min. The run after them is step 14.
        if index == len(LATE_STEP_LABELS) - 1:
            steps.append(
                {
                    "label": label,
                    "start": stop["start"],
                    "end": stop["end"],
                    "color": color,
                }
            )
            steps.append(
                {
                    "label": "14  Run again",
                    "start": run["start"],
                    "end": sensors["min"].iloc[-1],
                    "color": STEP_14_COLOR,
                }
            )
            continue
        steps.append(
            {
                "label": label,
                "start": stop["start"],
                "end": run["end"],
                "color": color,
            }
        )
    return steps


def _shade(axis, steps: list[dict], minutes_per_unit: float) -> None:
    for step in steps:
        axis.axvspan(
            step["start"] / minutes_per_unit,
            step["end"] / minutes_per_unit,
            color=step["color"],
            alpha=0.45,
            linewidth=0,
            zorder=0,
        )


def _step_number(label: str) -> str:
    return label.split()[0]


def binned_pressure(t0: pd.Timestamp) -> tuple[pd.DataFrame, pd.Series]:
    """10 s mean and min–max from the 100 Hz pressure log."""

    pressure = load_sensor_csv(PRESSURE_SOURCE, recalibrate_pump_flow=False)
    columns = [item[0] for item in PRESSURE_SERIES]
    indexed = pressure.set_index("timestamp")[columns]
    binned = indexed.resample("10s").agg(["mean", "min", "max"]).dropna(how="all")
    elapsed_min = pd.Series(
        (binned.index - t0).total_seconds() / 60.0,
        index=binned.index,
    )
    return binned, elapsed_min


def _draw_pressure(axis, binned: pd.DataFrame, elapsed_min: pd.Series, per_unit: float) -> None:
    x_values = elapsed_min.to_numpy() / per_unit
    for column, label, color, band in PRESSURE_SERIES:
        if band:
            axis.fill_between(
                x_values,
                binned[(column, "min")],
                binned[(column, "max")],
                color=color,
                alpha=0.16,
                linewidth=0,
                zorder=1,
            )
        axis.plot(
            x_values,
            binned[(column, "mean")],
            color=color,
            linewidth=1.4,
            label=label,
            zorder=2,
        )
    axis.axhline(0.0, color="0.45", linewidth=0.8, alpha=0.7, zorder=1)
    axis.set_ylabel("Pressure (bar)")
    axis.grid(True, alpha=0.3)


def _pressure_limits(binned: pd.DataFrame) -> tuple[float, float]:
    means = pd.concat([binned[(column, "mean")] for column, *_ in PRESSURE_SERIES])
    low = float(means.quantile(0.001))
    high = float(means.quantile(0.999))
    pad = 0.08 * (high - low)
    return low - pad, high + pad


def plot(sensors: pd.DataFrame, steps: list[dict]) -> Path:
    flow = sensors.set_index("timestamp")
    on = flow["peristaltic_pump_set_speed_rpm"] > 1.0
    measured = flow["flow_sensor_ml_per_min"].where(on)
    smooth = measured.rolling("30s", center=True, min_periods=5).median()
    hours = sensors["min"] / 60.0

    fig, (ax_full, ax_zoom) = plt.subplots(
        2,
        1,
        figsize=(12, 8.2),
        height_ratios=[1.15, 1.05],
        gridspec_kw={"hspace": 0.55},
    )
    fig.suptitle(
        "Keyence flow at a set 50 ml/min\n"
        "20261102_164405  ·  bands are protocol steps",
        fontsize=13,
    )

    for axis, x_values, per_unit in (
        (ax_full, hours, 60.0),
        (ax_zoom, sensors["min"], 1.0),
    ):
        _shade(axis, steps, per_unit)
        axis.plot(
            x_values,
            measured.to_numpy(),
            color="tab:blue",
            linewidth=0.4,
            alpha=0.25,
            label="Measured",
        )
        axis.plot(
            x_values,
            smooth.to_numpy(),
            color="tab:blue",
            linewidth=1.5,
            label="Measured (30 s median)",
        )
        axis.axhline(
            SETPOINT_ML_MIN,
            color="0.25",
            linewidth=1.0,
            linestyle="--",
            label="Set 50 ml/min",
        )
        axis.set_ylabel("Flow (ml/min)")
        axis.set_ylim(30.0, 54.0)
        axis.grid(True, alpha=0.3)

    ax_full.set_xlim(0.0, float(hours.iloc[-1]))
    ax_full.set_xlabel("Elapsed time (h)")
    zoom_start = steps[1]["end"] - 15.0
    ax_zoom.set_xlim(zoom_start, float(sensors["min"].iloc[-1]) + 0.5)
    ax_zoom.set_xlabel("Elapsed time (min)")

    step4 = steps[1]
    settled = _median_on(sensors, 28.0, 38.0)
    ending = _median_on(sensors, step4["end"] - 10.0, step4["end"])
    ax_full.text(
        4.6,
        51.2,
        f"Step 4   {settled:.1f} to {ending:.1f} ml/min",
        ha="center",
        va="bottom",
        fontsize=9,
        color="0.15",
    )
    ax_full.text(0.35, 51.2, "Steps 1-3", ha="left", va="bottom", fontsize=8, color="0.25")
    ax_full.text(16.55, 51.2, "Steps 5-14", ha="right", va="bottom", fontsize=8, color="0.25")

    for step in steps:
        visible_start = max(step["start"], zoom_start)
        if step["end"] - visible_start < 3.0:
            continue
        ax_zoom.text(
            (visible_start + step["end"]) / 2.0,
            52.6,
            _step_number(step["label"]),
            ha="center",
            va="top",
            fontsize=8,
            color="0.1",
            clip_on=True,
        )

    ax_full.legend(loc="upper right", bbox_to_anchor=(0.80, 0.98), framealpha=0.92, fontsize=8)
    zoom_steps = [step for step in steps if step["end"] > zoom_start]
    ax_zoom.legend(
        handles=[
            Patch(facecolor=step["color"], edgecolor="none", alpha=0.7, label=step["label"])
            for step in zoom_steps
        ],
        loc="center left",
        bbox_to_anchor=(1.01, 0.5),
        frameon=False,
        fontsize=8,
    )

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DATA / "flow_by_protocol_step_20261102_164405.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_with_pressure(
    sensors: pd.DataFrame,
    steps: list[dict],
    binned: pd.DataFrame,
    elapsed_min: pd.Series,
) -> Path:
    flow = sensors.set_index("timestamp")
    on = flow["peristaltic_pump_set_speed_rpm"] > 1.0
    measured = flow["flow_sensor_ml_per_min"].where(on)
    smooth = measured.rolling("30s", center=True, min_periods=5).median()
    hours = sensors["min"] / 60.0
    low, high = _pressure_limits(binned)

    fig, axes = plt.subplots(
        4,
        1,
        figsize=(12, 12.4),
        height_ratios=[1.05, 0.95, 1.0, 0.95],
        gridspec_kw={"hspace": 0.38},
    )
    ax_flow, ax_press, ax_zflow, ax_zpress = axes
    fig.suptitle(
        "Flow and pressure at a set 50 ml/min\n"
        "20261102_164405  ·  bands are protocol steps",
        fontsize=13,
    )

    panels = (
        (ax_flow, ax_press, hours, 60.0),
        (ax_zflow, ax_zpress, sensors["min"], 1.0),
    )
    for flow_axis, press_axis, x_values, per_unit in panels:
        _shade(flow_axis, steps, per_unit)
        _shade(press_axis, steps, per_unit)
        flow_axis.plot(x_values, measured.to_numpy(), color="tab:blue", linewidth=0.4, alpha=0.25)
        flow_axis.plot(
            x_values,
            smooth.to_numpy(),
            color="tab:blue",
            linewidth=1.4,
            label="Measured (30 s median)",
        )
        flow_axis.axhline(SETPOINT_ML_MIN, color="0.25", linewidth=1.0, linestyle="--", label="Set 50 ml/min")
        flow_axis.set_ylabel("Flow (ml/min)")
        flow_axis.set_ylim(30.0, 54.0)
        flow_axis.grid(True, alpha=0.3)
        flow_axis.tick_params(labelbottom=False)
        _draw_pressure(press_axis, binned, elapsed_min, per_unit)
        press_axis.set_ylim(low, high)

    ax_press.sharex(ax_flow)
    ax_zpress.sharex(ax_zflow)
    ax_flow.set_xlim(0.0, float(hours.iloc[-1]))
    ax_press.set_xlabel("Elapsed time (h)")
    zoom_start = steps[1]["end"] - 15.0
    ax_zflow.set_xlim(zoom_start, float(sensors["min"].iloc[-1]) + 0.5)
    ax_zpress.set_xlabel("Elapsed time (min)")

    step4 = steps[1]
    settled = _median_on(sensors, 28.0, 38.0)
    ending = _median_on(sensors, step4["end"] - 10.0, step4["end"])
    ax_flow.text(
        4.6,
        51.2,
        f"Step 4   {settled:.1f} to {ending:.1f} ml/min",
        ha="center",
        va="bottom",
        fontsize=9,
        color="0.15",
    )
    ax_flow.text(0.35, 51.2, "Steps 1-3", ha="left", va="bottom", fontsize=8, color="0.25")
    ax_flow.text(16.55, 51.2, "Steps 5-14", ha="right", va="bottom", fontsize=8, color="0.25")

    for step in steps:
        visible_start = max(step["start"], zoom_start)
        if step["end"] - visible_start < 3.0:
            continue
        ax_zflow.text(
            (visible_start + step["end"]) / 2.0,
            52.6,
            _step_number(step["label"]),
            ha="center",
            va="top",
            fontsize=8,
            color="0.1",
            clip_on=True,
        )

    ax_flow.legend(loc="upper right", bbox_to_anchor=(0.80, 0.98), framealpha=0.92, fontsize=8)
    ax_press.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, 1.02),
        ncol=4,
        frameon=False,
        fontsize=8,
    )
    zoom_steps = [step for step in steps if step["end"] > zoom_start]
    ax_zflow.legend(
        handles=[
            Patch(facecolor=step["color"], edgecolor="none", alpha=0.7, label=step["label"])
            for step in zoom_steps
        ],
        loc="center left",
        bbox_to_anchor=(1.01, 0.5),
        frameon=False,
        fontsize=8,
    )

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DATA / "flow_pressure_by_protocol_step_20261102_164405.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def _median_pressure(sensors: pd.DataFrame, column: str, start: float, end: float) -> float:
    window = sensors[
        (sensors["min"] >= start)
        & (sensors["min"] < end)
        & (sensors["peristaltic_pump_set_speed_rpm"] > 1.0)
    ]
    if window.empty:
        return float("nan")
    return float(window[column].median())


def report(sensors: pd.DataFrame, steps: list[dict]) -> None:
    print(f"log {sensors['timestamp'].iloc[0]}  to  {sensors['timestamp'].iloc[-1]}")
    print(f"duration {sensors['min'].iloc[-1] / 60.0:.2f} h")
    step4 = next(step for step in steps if step["label"].startswith("4"))
    settled = _median_on(sensors, 28.0, 38.0)
    ending = _median_on(sensors, step4["end"] - 10.0, step4["end"])
    hours = (step4["end"] - 28.0) / 60.0
    print(
        f"step 4 settled 28-38 min: {settled:.2f} ml/min; "
        f"last 10 min: {ending:.2f} ml/min; "
        f"drop {settled - ending:.2f} ml/min over {hours:.2f} h "
        f"({(settled - ending) / hours:.2f} ml/min per hour)"
    )
    print(f"{'step':<28} {'start min':>10} {'end min':>10} {'on median':>10}")
    for step in steps:
        flow = _median_on(sensors, step["start"], step["end"])
        print(
            f"{step['label']:<28} {step['start']:10.2f} {step['end']:10.2f} "
            f"{flow:10.2f}"
        )
    print("pressure medians while the pump is on (bar)")
    header = f"{'window':<28}" + "".join(f"{label:>14}" for _, label, _, _ in PRESSURE_SERIES)
    print(header)
    windows = [("28-38 min", 28.0, 38.0), ("step 4 last 10 min", step4["end"] - 10.0, step4["end"])]
    windows.extend((step["label"], step["start"], step["end"]) for step in steps)
    for label, start, end in windows:
        values = "".join(
            f"{_median_pressure(sensors, column, start, end):14.3f}"
            for column, *_ in PRESSURE_SERIES
        )
        print(f"{label:<28}{values}")


def main() -> None:
    if not SOURCE.is_file():
        print(f"No sensor log at {SOURCE}")
        return
    sensors = load_sensor_csv(SOURCE, recalibrate_pump_flow=False)
    t0 = sensors["timestamp"].iloc[0]
    sensors["min"] = (sensors["timestamp"] - t0).dt.total_seconds() / 60.0
    steps = protocol_steps(sensors)
    out = plot(sensors, steps)
    print(out)
    if not PRESSURE_SOURCE.is_file():
        print(f"No pressure log at {PRESSURE_SOURCE}")
        report(sensors, steps)
        return
    binned, elapsed_min = binned_pressure(sensors["timestamp"].iloc[0])
    pressure_out = plot_with_pressure(sensors, steps, binned, elapsed_min)
    report(sensors, steps)
    print(pressure_out)


if __name__ == "__main__":
    main()
