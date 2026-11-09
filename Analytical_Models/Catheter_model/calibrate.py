"""
Calibrate the dual-lumen catheter model against a measured stepped-flow run.

Usage:
    python calibrate.py                     # newest *_sensors.csv next to it
    python calibrate.py 20260821            # date prefix
    python calibrate.py path\\to\\file.csv  # explicit file

For each pump-speed step in the CSV, the settled tail is averaged to one
steady-state point (flow, tank temperature = mean of probes 1 and 2,
catheter inlet, catheter outlet).  Bisection then finds the exact
conductance-scaling factor K each point needs, and a power law
    K(Q) = k_ref * (Q / Q_ref) ** n
is fitted through them and written to calibration.json, which the model
(dual_lumen_catheter.py) reads.

The script also plots the measured points against the ORIGINAL model
(uncalibrated, K = 1) and the calibrated model.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import dual_lumen_catheter as model

HERE = Path(__file__).resolve().parent
CALIBRATION_JSON = HERE / "calibration.json"
REFERENCE_FLOW_ML_MIN = 60.0
TAIL_FRACTION = 0.4          # settled part of each pump-speed step to average
MIN_STEP_DURATION_S = 30.0   # ignore pump-speed blocks shorter than this


def find_csv(argument):
    """Resolve the measurement CSV from a path, a date prefix, or newest."""
    if argument:
        as_path = Path(argument)
        if as_path.exists():
            return as_path
        matches = sorted(HERE.glob(f"{argument}*_calibration.csv"))
        if matches:
            return matches[-1]
        sys.exit(f"No CSV found for '{argument}' in {HERE}")
    matches = sorted(HERE.glob("*_calibration.csv"))
    if not matches:
        sys.exit(f"No *_calibration.csv files found in {HERE}")
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


def k_needed_for_step(step):
    """Bisection: the K that makes the modelled steady outlet match this
    measured step exactly.  Outlet temperature rises monotonically with K."""
    k_low, k_high = 0.2, 8.0
    for _ in range(30):
        k_mid = 0.5 * (k_low + k_high)
        outlet = model.steady_outlet_C(step["inlet_C"], step["tank_C"],
                                       step["flow_m3_s"], calibration_k=k_mid)
        if outlet < step["outlet_C"]:
            k_low = k_mid
        else:
            k_high = k_mid
    return 0.5 * (k_low + k_high)


csv_path = find_csv(sys.argv[1] if len(sys.argv) > 1 else None)
print(f"Calibrating against: {csv_path.name}")
steps = load_measured_steps(csv_path)
if len(steps) < 2:
    sys.exit("Need at least two pump-speed steps to fit the flow exponent.")

# --- fit K(Q) = k_ref * (Q/Q_ref)^n through the exact per-step K values ----
reference_flow_m3_s = REFERENCE_FLOW_ML_MIN * 1.0e-6 / 60.0
k_needed = np.array([k_needed_for_step(s) for s in steps])
log_flow_ratio = np.log([s["flow_m3_s"] / reference_flow_m3_s for s in steps])
n_exponent, log_k_ref = np.polyfit(log_flow_ratio, np.log(k_needed), 1)
k_ref = float(np.exp(log_k_ref))

print(f"Exact K per step : " + ", ".join(f"{k:.2f}" for k in k_needed))
print(f"Fitted           : K(Q) = {k_ref:.3f} * "
      f"(Q / {REFERENCE_FLOW_ML_MIN:.0f} mL/min) ** {n_exponent:.3f}")

# --- write the coefficients for the model to read ---------------------------
calibration = {
    "k_ref": round(k_ref, 4),
    "n_exponent": round(float(n_exponent), 4),
    "reference_flow_ml_min": REFERENCE_FLOW_ML_MIN,
    "fitted_from": csv_path.name,
    "fitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
}
with open(CALIBRATION_JSON, "w") as f:
    json.dump(calibration, f, indent=2)
print(f"Written          : {CALIBRATION_JSON}")


def k_calibrated(flow_m3_s):
    return k_ref * (flow_m3_s / reference_flow_m3_s) ** n_exponent


# --- plot: measured vs original (K = 1) vs calibrated model -----------------
# Steady outlet temperature over the measured flow range; the model curves
# use each step's measured inlet/tank temperature interpolated over flow,
# so the comparison isolates the heat-transfer calibration.
measured_flows = np.array([s["flow_m3_s"] for s in steps])
measured_outlets = np.array([s["outlet_C"] for s in steps])

curve_flows = np.linspace(measured_flows.min(), measured_flows.max(), 25)
inlet_interp = np.interp(curve_flows, measured_flows,
                         [s["inlet_C"] for s in steps])
tank_interp = np.interp(curve_flows, measured_flows,
                        [s["tank_C"] for s in steps])

original_curve = [model.steady_outlet_C(ti, tk, q, calibration_k=1.0)
                  for ti, tk, q in zip(inlet_interp, tank_interp, curve_flows)]
calibrated_curve = [model.steady_outlet_C(ti, tk, q,
                                          calibration_k=k_calibrated(q))
                    for ti, tk, q in zip(inlet_interp, tank_interp,
                                         curve_flows)]

flows_ml_min = curve_flows * 6.0e7
fig, ax = plt.subplots(figsize=(8.0, 5.0))
ax.plot(measured_flows * 6.0e7, measured_outlets, "ko", markersize=7,
        label=f"Measured ({csv_path.name})")
ax.plot(flows_ml_min, original_curve, "--", color="tab:blue", linewidth=2.0,
        label="Original model (K = 1)")
ax.plot(flows_ml_min, calibrated_curve, "-", color="tab:red", linewidth=2.0,
        label=f"Calibrated model (K = {k_ref:.2f}·(Q/Q$_{{ref}}$)$^{{{n_exponent:.2f}}}$)")
ax.set_title("Catheter outlet temperature: model calibration")
ax.set_xlabel("Flow rate (mL/min)")
ax.set_ylabel("Steady outlet temperature (°C)")
ax.legend()
ax.grid(True, alpha=0.3)
fig.tight_layout()
plot_path = HERE / "calibration_fit.png"
fig.savefig(plot_path, dpi=150)
print(f"Plot saved       : {plot_path}")
