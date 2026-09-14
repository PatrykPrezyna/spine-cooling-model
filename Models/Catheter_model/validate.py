"""
Validate the calibrated dual-lumen catheter model against a measured run.

Usage:
    python validate.py                     # newest *_sensors.csv next to it
    python validate.py 20260821            # date prefix
    python validate.py path\\to\\file.csv  # explicit file

Loads the calibration coefficients via the model (calibration.json), runs the
model to steady state at every measured pump-speed step using the MEASURED
boundary conditions (catheter inlet, tank = mean of probes 1 and 2, flow),
prints a comparison table, plots measured vs modelled outlet temperature,
and passes/fails on the mean absolute outlet error.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import dual_lumen_catheter as model

HERE = Path(__file__).resolve().parent
TAIL_FRACTION = 0.4          # settled part of each pump-speed step to average
MIN_STEP_DURATION_S = 30.0   # ignore pump-speed blocks shorter than this
TOLERANCE_C = 1.0            # acceptance: mean absolute outlet error


def find_csv(argument):
    """Resolve the measurement CSV from a path, a date prefix, or newest."""
    if argument:
        as_path = Path(argument)
        if as_path.exists():
            return as_path
        matches = sorted(HERE.glob(f"{argument}*_validation.csv"))
        if matches:
            return matches[-1]
        sys.exit(f"No CSV found for '{argument}' in {HERE}")
    matches = sorted(HERE.glob("*_validation.csv"))
    if not matches:
        sys.exit(f"No *_validation.csv files found in {HERE}")
    return matches[-1]


def load_measured_steps(csv_path):
    """One steady-state point per pump-speed step (settled tail averaged)."""
    data = pd.read_csv(csv_path, parse_dates=["timestamp"])
    data["t"] = (data.timestamp - data.timestamp.iloc[0]).dt.total_seconds()
    data["tank"] = (data.probe_1_c + data.probe_2_c) / 2.0

    # Group CONTIGUOUS blocks of constant pump speed (a speed may repeat
    # later in a long run) and keep blocks long enough to settle.
    data["block"] = (data.peristaltic_pump_set_speed_rpm
                     .ne(data.peristaltic_pump_set_speed_rpm.shift())
                     .cumsum())
    steps = []
    running = data[data.peristaltic_pump_set_speed_rpm > 0]
    for _, group in running.groupby("block"):
        rpm = group.peristaltic_pump_set_speed_rpm.iloc[0]
        t0, t1 = group.t.iloc[0], group.t.iloc[-1]
        if t1 - t0 < MIN_STEP_DURATION_S:
            continue
        tail = group[group.t > t0 + (1.0 - TAIL_FRACTION) * (t1 - t0)]
        steps.append({
            "rpm": float(rpm),
            "flow_m3_s": tail.pump_flow_ml_per_s.mean() * 1.0e-6,
            "tank_C": tail.tank.mean(),
            "inlet_C": tail.catheter_in_c.mean(),
            "outlet_C": tail.catheter_out_c.mean(),
        })
    return steps


csv_path = find_csv(sys.argv[1] if len(sys.argv) > 1 else None)
print(f"Validating against : {csv_path.name}")
print(f"Calibration source : {model.CALIBRATION_SOURCE}")
print(f"K(Q) = {model.CALIBRATION_K_REF:.2f} * "
      f"(Q / {model.CALIBRATION_REFERENCE_FLOW_ML_MIN:.0f} mL/min) "
      f"** {model.CALIBRATION_N_EXPONENT:.2f}")
print()

steps = load_measured_steps(csv_path)
if not steps:
    sys.exit("No pump-running data found in the CSV.")

print(f"{'rpm':>5} {'flow mL/min':>12} {'tank °C':>8} {'in °C':>7} "
      f"{'out meas °C':>12} {'out model °C':>13} {'error K':>8}")
model_outlets, errors = [], []
for step in steps:
    model_out = model.steady_outlet_C(step["inlet_C"], step["tank_C"],
                                      step["flow_m3_s"])
    model_outlets.append(model_out)
    errors.append(model_out - step["outlet_C"])
    print(f"{step['rpm']:>5.0f} {step['flow_m3_s']*6.0e7:>12.1f} "
          f"{step['tank_C']:>8.2f} {step['inlet_C']:>7.2f} "
          f"{step['outlet_C']:>12.2f} {model_out:>13.2f} {errors[-1]:>+8.2f}")

mean_abs_error = float(np.mean(np.abs(errors)))
max_abs_error = float(np.max(np.abs(errors)))
print()
print(f"Mean absolute outlet error : {mean_abs_error:.2f} °C "
      f"(tolerance {TOLERANCE_C:.1f} °C)")
print(f"Max absolute outlet error  : {max_abs_error:.2f} °C")

# --- plot: measured vs modelled outlet, step by step (chronological) -------
# The run may vary both flow AND tank temperature, so the x axis is the
# step sequence; each tick is labelled with that step's flow.
step_index = np.arange(len(steps))
flows_ml_min = np.array([s["flow_m3_s"] for s in steps]) * 6.0e7
measured = np.array([s["outlet_C"] for s in steps])
modelled = np.array(model_outlets)
tanks = np.array([s["tank_C"] for s in steps])

fig, (ax, ax_err) = plt.subplots(
    2, 1, figsize=(9.0, 6.5), sharex=True,
    gridspec_kw={"height_ratios": [3, 1]})
ax.plot(step_index, measured, "ko-", markersize=7,
        label=f"Measured ({csv_path.name})")
ax.plot(step_index, modelled, "s--", color="tab:red", markersize=6,
        label="Calibrated model")
ax.plot(step_index, tanks, ":", color="tab:gray", linewidth=1.5,
        label="Tank temperature")
ax.set_title("Model validation: steady outlet temperature per pump-speed step")
ax.set_ylabel("Temperature (°C)")
ax.legend()
ax.grid(True, alpha=0.3)

ax_err.axhline(0.0, color="gray", linewidth=1.0)
ax_err.bar(step_index, np.array(errors), width=0.6, color="tab:red",
           alpha=0.7)
ax_err.set_xticks(step_index)
ax_err.set_xticklabels([f"{q:.0f}" for q in flows_ml_min])
ax_err.set_xlabel("Flow rate of each step (mL/min)")
ax_err.set_ylabel("Model − measured (K)")
ax_err.grid(True, alpha=0.3)
fig.tight_layout()
plot_path = HERE / f"validation_{csv_path.stem}.png"
fig.savefig(plot_path, dpi=150)
print(f"Plot saved                 : {plot_path}")

if mean_abs_error < TOLERANCE_C:
    print("Validation PASSED.")
else:
    sys.exit(f"Validation FAILED: mean absolute error {mean_abs_error:.2f} °C "
             f"exceeds {TOLERANCE_C:.1f} °C.")
