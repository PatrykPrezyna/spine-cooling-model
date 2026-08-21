"""
Compare the dual-lumen catheter model to submerged-catheter sensor logs.

Put additional logs in this folder as *_sensors.csv. Each new file can have
a different flow-rate schedule, inlet temperature, and tank temperature.

CSV columns used:
  catheter_in_c                     catheter inlet water temperature
  catheter_out_c                    catheter outlet water temperature
  probe_1_c, probe_2_c              tank water (average of the two probes)
  peristaltic_pump_set_speed_rpm    commanded pump speed
  pump_flow_ml_per_s                logged flow (converted to mL/min)
"""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dual_lumen_catheter import (
    WATER_DENSITY_KG_M3,
    WATER_SPECIFIC_HEAT_J_KG_K,
    simulate,
)

HERE = Path(__file__).resolve().parent

# All sensor logs in this folder are used. Add more files later; do not
# hard-code one date in the comparison logic.
SENSOR_CSV_FILES = sorted(HERE.glob("*_sensors.csv"))

CATHETER_IN_COL = "catheter_in_c"
CATHETER_OUT_COL = "catheter_out_c"
TANK_PROBE_COLS = ("probe_1_c", "probe_2_c")
PUMP_SPEED_COL = "peristaltic_pump_set_speed_rpm"
FLOW_ML_S_COL = "pump_flow_ml_per_s"

# Ignore very short speed changes. Average the last STEADY_TAIL_S of each hold.
MIN_HOLD_DURATION_S = 40.0
STEADY_TAIL_S = 20.0
MIN_PUMP_RPM = 1.0

# Gravimetric calibration fallback if logged flow is missing or zero.
ML_PER_MIN_PER_RPM = 0.5862


def load_sensor_log(path):
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    required = [
        "timestamp",
        CATHETER_IN_COL,
        CATHETER_OUT_COL,
        TANK_PROBE_COLS[0],
        TANK_PROBE_COLS[1],
        PUMP_SPEED_COL,
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"{path.name} is missing columns: {missing}")

    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["time_s"] = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds()
    df["tank_c"] = 0.5 * (df[TANK_PROBE_COLS[0]] + df[TANK_PROBE_COLS[1]])
    df["pump_rpm"] = df[PUMP_SPEED_COL].astype(float)

    if FLOW_ML_S_COL in df.columns:
        df["flow_ml_min"] = df[FLOW_ML_S_COL].astype(float) * 60.0
    else:
        df["flow_ml_min"] = df["pump_rpm"] * ML_PER_MIN_PER_RPM

    return df


def pump_holds(df):
    """Split a log into constant pump-speed plateaus."""
    rpm_step = df["pump_rpm"].round(0)
    hold_id = rpm_step.ne(rpm_step.shift()).cumsum()
    holds = []
    for _, block in df.groupby(hold_id, sort=False):
        rpm = float(block["pump_rpm"].mean())
        duration_s = float(block["time_s"].iloc[-1] - block["time_s"].iloc[0])
        if rpm < MIN_PUMP_RPM or duration_s < MIN_HOLD_DURATION_S:
            continue
        t_end = float(block["time_s"].iloc[-1])
        steady = block[block["time_s"] >= t_end - STEADY_TAIL_S]
        if len(steady) < 5:
            continue
        flow_ml_min = float(steady["flow_ml_min"].mean())
        if flow_ml_min <= 0.0:
            flow_ml_min = rpm * ML_PER_MIN_PER_RPM
        holds.append(
            {
                "pump_rpm": rpm,
                "flow_ml_min": flow_ml_min,
                "inlet_C": float(steady[CATHETER_IN_COL].mean()),
                "outlet_C": float(steady[CATHETER_OUT_COL].mean()),
                "tank_C": float(steady["tank_c"].mean()),
                "t_start_s": float(block["time_s"].iloc[0]),
                "t_end_s": t_end,
                "duration_s": duration_s,
            }
        )
    return holds


def water_heat_and_g_eff(inlet_C, outlet_C, tank_C, flow_ml_min):
    mass_flow_kg_s = WATER_DENSITY_KG_M3 * (flow_ml_min * 1.0e-6 / 60.0)
    heat_W = mass_flow_kg_s * WATER_SPECIFIC_HEAT_J_KG_K * (outlet_C - inlet_C)
    dT = tank_C - inlet_C
    g_eff = float("nan") if abs(dT) < 1.0e-12 else heat_W / dT
    return heat_W, g_eff


def compare_hold(hold, source_name):
    measured_Q, measured_g = water_heat_and_g_eff(
        hold["inlet_C"], hold["outlet_C"], hold["tank_C"], hold["flow_ml_min"]
    )
    model = simulate(
        inlet_water_temperature_C=hold["inlet_C"],
        tank_water_temperature_C=hold["tank_C"],
        volumetric_flow_rate_ml_min=hold["flow_ml_min"],
        initial_internal_water_temperature_C=hold["tank_C"],
        initial_catheter_temperature_C=hold["tank_C"],
    )
    return {
        "file": source_name,
        "pump_rpm": hold["pump_rpm"],
        "flow_ml_min": hold["flow_ml_min"],
        "inlet_C": hold["inlet_C"],
        "tank_C": hold["tank_C"],
        "measured_outlet_C": hold["outlet_C"],
        "model_outlet_C": model["final_outlet_temperature_C"],
        "measured_Q_W": measured_Q,
        "model_Q_W": model["heat_to_water_final_W"],
        "measured_g_eff_W_K": measured_g,
        "model_g_eff_W_K": model["effective_thermal_conductance_W_K"],
        "t_start_s": hold["t_start_s"],
        "t_end_s": hold["t_end_s"],
    }


def print_table(rows):
    print()
    print(
        f"{'file':<24} {'RPM':>6} {'mL/min':>8} {'Tin C':>7} {'Tank C':>7} "
        f"{'Tout meas':>10} {'Tout model':>11} {'G meas':>8} {'G model':>8}"
    )
    print("-" * 108)
    for row in rows:
        print(
            f"{row['file']:<24} "
            f"{row['pump_rpm']:6.0f} "
            f"{row['flow_ml_min']:8.1f} "
            f"{row['inlet_C']:7.2f} "
            f"{row['tank_C']:7.2f} "
            f"{row['measured_outlet_C']:10.2f} "
            f"{row['model_outlet_C']:11.2f} "
            f"{row['measured_g_eff_W_K']:8.3f} "
            f"{row['model_g_eff_W_K']:8.3f}"
        )


if not SENSOR_CSV_FILES:
    raise FileNotFoundError(
        f"No *_sensors.csv files found in {HERE}. "
        "Copy a sensor log into this folder and run again."
    )

all_rows = []
loaded_logs = []
for csv_path in SENSOR_CSV_FILES:
    df = load_sensor_log(csv_path)
    holds = pump_holds(df)
    print()
    print(f"{csv_path.name}: {len(df)} samples, {df['time_s'].iloc[-1]:.0f} s, "
          f"{len(holds)} pump-speed holds")
    loaded_logs.append((csv_path.name, df, holds))
    for hold in holds:
        all_rows.append(compare_hold(hold, csv_path.name))

print_table(all_rows)

print()
print("Checks")
print("-" * 108)
if all_rows:
    outlet_errors = np.array(
        [row["model_outlet_C"] - row["measured_outlet_C"] for row in all_rows]
    )
    print(
        f"  Outlet error (model - measured): "
        f"mean {outlet_errors.mean():+.2f} C, "
        f"max |error| {np.abs(outlet_errors).max():.2f} C"
    )
    between = []
    for row in all_rows:
        low = min(row["inlet_C"], row["tank_C"])
        high = max(row["inlet_C"], row["tank_C"])
        between.append(low - 0.5 <= row["measured_outlet_C"] <= high + 0.5)
    if all(between):
        print("  Measured outlet stayed between inlet and tank on every hold.")
    else:
        print("  Note: a measured outlet left the inlet-tank band.")


# Time series of each log, plus model vs measured summary.
n_logs = len(loaded_logs)
fig = plt.figure(figsize=(11.0, 3.6 * (n_logs + 1)))

for i, (name, df, holds) in enumerate(loaded_logs):
    ax = fig.add_subplot(n_logs + 1, 1, i + 1)
    ax.plot(df["time_s"], df[CATHETER_IN_COL], color="tab:blue", label="Catheter inlet")
    ax.plot(df["time_s"], df[CATHETER_OUT_COL], color="tab:red", label="Catheter outlet")
    ax.plot(df["time_s"], df["tank_c"], color="tab:orange", label="Tank (probe 1+2 avg)")
    model_outlet_labeled = False
    for row in all_rows:
        if row["file"] != name:
            continue
        ax.hlines(
            row["model_outlet_C"],
            row["t_start_s"],
            row["t_end_s"],
            colors="0.25",
            linestyles="--",
            linewidth=1.5,
            label="Model outlet" if not model_outlet_labeled else None,
        )
        model_outlet_labeled = True
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Temperature (C)")
    ax.set_title(name)
    ax.grid(True, alpha=0.3)
    ax2 = ax.twinx()
    ax2.step(df["time_s"], df["pump_rpm"], where="post", color="0.6", alpha=0.8)
    ax2.set_ylabel("Pump speed (rpm)")
    ax.legend(loc="best")

ax_sum = fig.add_subplot(n_logs + 1, 1, n_logs + 1)
flows = [row["flow_ml_min"] for row in all_rows]
ax_sum.plot(
    flows,
    [row["measured_outlet_C"] for row in all_rows],
    "o",
    color="tab:red",
    label="Measured outlet",
)
ax_sum.plot(
    flows,
    [row["model_outlet_C"] for row in all_rows],
    "s--",
    color="0.25",
    label="Model outlet",
)
ax_sum.set_xlabel("Flow rate (mL/min)")
ax_sum.set_ylabel("Outlet temperature (C)")
ax_sum.set_title("Steady holds: measured vs model")
ax_sum.grid(True, alpha=0.3)
ax_sum.legend()

fig.tight_layout()
plot_path = HERE / "dual_lumen_catheter_validation.png"
fig.savefig(plot_path, dpi=150)
print()
print(f"Plot saved to: {plot_path}")
print()

plt.show()
