"""Cartridge inlet, outlet, flow, and cooling power.

P = m_dot * c_p * (T_in - T_out)

c_p = 4186 J/(kg·K). One millilitre of water is 0.001 kg.
Positive power is heat removed from the water (outlet colder than inlet).
Measured flow is used when the Keyence reads above 5 ml/min; otherwise power
is 0 W. The logged plate channels are open-circuit in this run and are not plotted.

Plate set temperature is the operator schedule in the experiment README.
It is not in the sensor log (set_temperature_c stays at 32 °C). The initial
set temperature, before 60 min, was not recorded.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import (  # noqa: E402
    elapsed_time,
    flow_power,
    load_sensor_csv,
)

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"

INLET_COLUMNS = ("cartrige_in_c", "cart_in_c", "cartridge_in_c")
OUTLET_COLUMNS = ("cartrige_out_c", "cart_out_c", "cartridge_out_c")
KEYENCE_MIN_ML_MIN = 5.0
# Elapsed minutes from the start of 20261103_141619, both plates.
PLATE_SETPOINTS_C = (
    (60.0, -10.0),
    (70.0, -5.0),
    (85.0, -1.0),
)
# Median cooling power over this many minutes at the end of each setpoint step.
STABLE_POWER_MIN = 2.0


def sensor_logs() -> list[Path]:
    found = {
        *RAW_DATA.glob("*sensors*.csv"),
        *RAW_DATA.glob("sensor_log_*.csv"),
    }
    return sorted(found)


def first_column(df: pd.DataFrame, names: tuple[str, ...]) -> str:
    for name in names:
        if name in df.columns:
            return name
    raise KeyError(f"None of {names} are in the log")


def load_run(csv_path: Path) -> pd.DataFrame:
    # Keep the logged pump flow. load_sensor_csv would replace it with an rpm fit.
    df = load_sensor_csv(csv_path, recalibrate_pump_flow=False).copy()
    inlet = first_column(df, INLET_COLUMNS)
    outlet = first_column(df, OUTLET_COLUMNS)
    df["t_min"] = elapsed_time(df["timestamp"], unit="min")
    df["inlet_c"] = df[inlet]
    df["outlet_c"] = df[outlet]
    if "pump_flow_ml_per_s" not in df.columns:
        raise KeyError(f"{csv_path.name} has no pump_flow_ml_per_s")
    df["set_ml_min"] = df["pump_flow_ml_per_s"] * 60.0
    if "flow_sensor_ml_per_min" in df.columns:
        df["sensor_ml_min"] = df["flow_sensor_ml_per_min"]
    else:
        df["sensor_ml_min"] = pd.Series(float("nan"), index=df.index)
    flowing = df["sensor_ml_min"] > KEYENCE_MIN_ML_MIN
    power_ml_min = df["sensor_ml_min"].where(flowing, 0.0)
    df["power_w"] = flow_power(power_ml_min / 60.0, df["inlet_c"], df["outlet_c"])
    df["flowing"] = flowing
    return df


def plate_set_c(t_min: pd.Series) -> pd.Series:
    """Step schedule from the README. Unknown before the first recorded change."""
    set_c = pd.Series(float("nan"), index=t_min.index, dtype=float)
    for minute, temp_c in PLATE_SETPOINTS_C:
        set_c = set_c.mask(t_min >= minute, temp_c)
    return set_c


def step_end_power(df: pd.DataFrame) -> list[tuple[float, float, float]]:
    """Median power over the last minutes of each plate-setpoint step.

    Returns (window_start_min, step_end_min, power_w).
    """
    t_end = float(df["t_min"].iloc[-1])
    edges = [minute for minute, _ in PLATE_SETPOINTS_C] + [t_end]
    found: list[tuple[float, float, float]] = []
    for start, end in zip(edges, edges[1:]):
        if end <= start:
            continue
        window_start = max(start, end - STABLE_POWER_MIN)
        part = df.loc[df["flowing"] & df["t_min"].between(window_start, end, inclusive="left")]
        if part.empty:
            continue
        found.append((window_start, end, float(part["power_w"].median())))
    return found


def plot_run(df: pd.DataFrame, stem: str) -> Path:
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    df = df.copy()
    df["plate_set_c"] = plate_set_c(df["t_min"])

    axes[0].plot(df["t_min"], df["inlet_c"], label="Cartridge input", color="#006d2c", linewidth=1.2)
    axes[0].plot(df["t_min"], df["outlet_c"], label="Cartridge output", color="#74c476", linewidth=1.2)
    axes[0].plot(
        df["t_min"],
        df["plate_set_c"],
        label="Plate set temperature",
        color="#6a3d9a",
        linewidth=1.6,
        linestyle="--",
    )
    axes[0].set_ylabel("Temperature (°C)")
    axes[0].set_title(stem)
    axes[0].grid(True, alpha=0.3)
    axes[0].legend(loc="best", framealpha=0.9)

    axes[1].plot(
        df["t_min"],
        df["set_ml_min"],
        label="Set flow",
        color="0.35",
        linewidth=1.2,
        linestyle="--",
    )
    if df["sensor_ml_min"].notna().any():
        axes[1].plot(
            df["t_min"],
            df["sensor_ml_min"].clip(lower=0),
            label="Flow sensor",
            color="tab:green",
            linewidth=1.2,
        )
    axes[1].set_ylabel("Flow (ml/min)")
    axes[1].set_ylim(bottom=0)
    axes[1].grid(True, alpha=0.3)
    axes[1].legend(loc="best", framealpha=0.9)

    axes[2].plot(df["t_min"], df["power_w"], color="#d94801", linewidth=1.2, label="Cooling power")
    axes[2].set_ylabel("Cooling power (W)")
    axes[2].set_xlabel("Elapsed time (min)")
    axes[2].grid(True, alpha=0.3)
    axes[2].legend(loc="best", framealpha=0.9)

    t_end = float(df["t_min"].max())
    for minute, temp_c in PLATE_SETPOINTS_C:
        if t_end < minute:
            continue
        for ax in axes:
            ax.axvline(minute, color="#6a3d9a", linewidth=0.8, linestyle=":", alpha=0.8)
        axes[0].annotate(
            f"{temp_c:.0f} °C",
            xy=(minute, temp_c),
            xytext=(4, 5),
            textcoords="offset points",
            ha="left",
            va="bottom",
            fontsize=8,
            color="#6a3d9a",
        )

    for window_start, end, power_w in step_end_power(df):
        axes[2].hlines(power_w, window_start, end, colors="#7f2704", linewidths=2.2, zorder=3)
        axes[2].annotate(
            f"{power_w:.0f} W",
            xy=((window_start + end) / 2.0, power_w),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#7f2704",
        )

    fig.tight_layout()
    out = OUTPUT_DATA / f"cooling_power_{stem}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def main() -> None:
    logs = sensor_logs()
    if not logs:
        print("No input files yet. Drop sensor logs in raw_data/.")
        return

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    for csv_path in logs:
        df = load_run(csv_path)
        out = plot_run(df, csv_path.stem)
        flowing = df["flowing"]
        window = df.loc[flowing & (df["power_w"] > 0)]
        print(
            f"{csv_path.name}: {df['t_min'].iloc[-1]:.1f} min, "
            f"while cooling inlet {window['inlet_c'].median():.1f} °C, "
            f"outlet {window['outlet_c'].median():.1f} °C, "
            f"median power {float(window['power_w'].median()):.1f} W "
            f"-> {out.name}"
        )
        edges = [minute for minute, _ in PLATE_SETPOINTS_C] + [float(df["t_min"].iloc[-1])]
        for start, end in zip(edges, edges[1:]):
            part = df.loc[flowing & df["t_min"].between(start, end, inclusive="left")]
            if part.empty:
                continue
            tail = part.loc[part["t_min"] >= end - STABLE_POWER_MIN]
            print(
                f"  {start:.0f}–{end:.0f} min: "
                f"inlet {part['inlet_c'].median():.1f} °C, "
                f"outlet {part['outlet_c'].median():.1f} °C, "
                f"flow {part['sensor_ml_min'].median():.1f} ml/min, "
                f"power {part['power_w'].median():.1f} W; "
                f"last {STABLE_POWER_MIN:.0f} min "
                f"inlet {tail['inlet_c'].median():.1f} °C, "
                f"outlet {tail['outlet_c'].median():.1f} °C, "
                f"power {tail['power_w'].median():.1f} W"
            )


if __name__ == "__main__":
    main()
