"""Cartridge inlet, outlet, flow, and cooling power.

P = m_dot * c_p * (T_in - T_out)

c_p = 4186 J/(kg·K). One millilitre of water is 0.001 kg.
Positive power is heat removed from the water (outlet colder than inlet).
Measured flow is used when the Keyence reads above 5 ml/min; otherwise power
is 0 W. The logged plate channels are open-circuit in this run and are not plotted.

The 60 min line is the operator note that both solid-state plates were set to
-10 °C. That command is not in the sensor log (set_temperature_c stays at 32 °C).
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
SETPOINT_MARK_MIN = {
    "20261103_141619_sensors": 60.0,
}


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


def plot_run(df: pd.DataFrame, stem: str) -> Path:
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)

    axes[0].plot(df["t_min"], df["inlet_c"], label="Cartridge input", color="#006d2c", linewidth=1.2)
    axes[0].plot(df["t_min"], df["outlet_c"], label="Cartridge output", color="#74c476", linewidth=1.2)
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

    mark = SETPOINT_MARK_MIN.get(stem)
    if mark is not None and df["t_min"].max() >= mark:
        for ax in axes:
            ax.axvline(mark, color="0.25", linewidth=1.0, linestyle=":")
        axes[0].annotate(
            "both plates set to −10 °C",
            xy=(mark, axes[0].get_ylim()[1]),
            xytext=(4, -6),
            textcoords="offset points",
            ha="left",
            va="top",
            fontsize=8,
            color="0.2",
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


if __name__ == "__main__":
    main()
