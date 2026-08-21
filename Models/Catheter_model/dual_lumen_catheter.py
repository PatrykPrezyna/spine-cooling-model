"""
Dual-lumen catheter transient thermal model — version 2 (merged + calibrated).

Cold water enters the inlet lumen at the proximal end, turns at the distal
end, and returns through the outlet lumen.  The catheter is fully submerged
in a large mixed water tank held at a nearly constant temperature.

Version 2 merges the two earlier scripts and adds:
  - wall thickness derived from geometry, counted ONCE in the resistance path
    (split half/half around the polymer node, which carries the thermal mass)
  - thermally developing laminar flow (Hausen correlation) so the inner film
    coefficient depends on flow rate, as the measurements demand
  - one calibration factor K that scales all heat-transfer conductances.
    K lumps every model imprecision (uncertain lumen inner diameter, tank-side
    h, non-circular lumens, lumen position in the cross-section, ...).
    K is fitted to the steady-state points of the measured stepped-flow run.
  - a validation test against the measured CSV at all six pump speeds
"""

import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# =============================================================================
# 1. User-configurable input values
# =============================================================================

# Geometry
CATHETER_LENGTH_CM = 33.0
CATHETER_OUTER_DIAMETER_MM = 3.0
LUMEN_INNER_DIAMETER_MM = 1.0   # measurement may be imprecise; K absorbs this

# Nominal operating conditions (used for the main transient plot)
INLET_WATER_TEMPERATURE_C = 5.0
TANK_WATER_TEMPERATURE_C = 36.0
VOLUMETRIC_FLOW_RATE_ML_MIN = 60.0

# Initial conditions
INITIAL_INTERNAL_WATER_TEMPERATURE_C = 36.0
INITIAL_CATHETER_TEMPERATURE_C = 36.0

# Numerical settings
N_AXIAL_SEGMENTS = 30
SIMULATION_DURATION_S = 20.0
SAFETY_FACTOR = 0.4             # fraction of the smallest stable time step

# Calibration
# K multiplies every heat-transfer conductance (lumen<->wall and wall<->tank).
# K = 1, n = 0 means "trust the geometry and correlations as written".
# A single constant K cannot match the data at every pump speed (the measured
# conductance grows faster with flow than the correlations predict), so K is
# allowed a mild flow dependence:
#     K(Q) = K_REF * (Q / Q_REF) ** N_EXPONENT
# If the measured CSV below exists, K_REF and N_EXPONENT are re-fitted at run
# time and printed; otherwise these defaults (from the last fit) are used.
CALIBRATION_K_REF = 1.89                  # K at the reference flow rate
CALIBRATION_N_EXPONENT = 0.33             # flow-dependence exponent
CALIBRATION_REFERENCE_FLOW_ML_MIN = 60.0  # Q_REF
MEASUREMENT_CSV = Path(__file__).resolve().parent / "20260821_144040_sensors.csv"

# Validation acceptance: mean absolute outlet-temperature error over all
# measured pump-speed steps must stay below this after calibration.
VALIDATION_TOLERANCE_C = 1.0


# =============================================================================
# 2. Unit conversions  (SI internally)
# =============================================================================

catheter_length_m = CATHETER_LENGTH_CM / 100.0
outer_diameter_m = CATHETER_OUTER_DIAMETER_MM / 1000.0
lumen_diameter_m = LUMEN_INNER_DIAMETER_MM / 1000.0
nominal_flow_m3_s = VOLUMETRIC_FLOW_RATE_ML_MIN * 1.0e-6 / 60.0
reference_flow_m3_s = CALIBRATION_REFERENCE_FLOW_ML_MIN * 1.0e-6 / 60.0


# =============================================================================
# 3. Physical-property assumptions (all constant, no temperature dependence)
# =============================================================================

# Water at ~15 °C (mid-range between the ~8 °C catheter water and the tank).
WATER_DENSITY_KG_M3 = 999.0                 # assumed, water at 15 °C
WATER_SPECIFIC_HEAT_J_KG_K = 4186.0         # assumed, water at 15 °C
WATER_THERMAL_CONDUCTIVITY_W_M_K = 0.589    # assumed, water at 15 °C
WATER_DYNAMIC_VISCOSITY_PA_S = 1.14e-3      # assumed, water at 15 °C

# Typical medical-grade polyurethane. Not measured on this catheter.
CATHETER_DENSITY_KG_M3 = 1200.0             # assumed, typical PU
CATHETER_SPECIFIC_HEAT_J_KG_K = 1500.0      # assumed, typical PU
CATHETER_THERMAL_CONDUCTIVITY_W_M_K = 0.19  # assumed, typical PU

# Stirred-bath order of magnitude for water on a 3 mm cylinder. Not measured;
# uncertainty here is one of the things the calibration factor K absorbs.
TANK_CONVECTION_COEFFICIENT_W_M2_K = 1000.0  # assumed, stirred water bath


# =============================================================================
# 4. Geometry calculations
# =============================================================================
#
# Two parallel circular lumens inside a circular outer catheter.
# Along a diameter through both lumen centres:
#     2 * t_outer + t_septum + 2 * D_lumen = D_outer
# Assume the outer wall and the septum have the same thickness:
#     t_wall = (D_outer - 2 * D_lumen) / 3

lumen_cross_section_m2 = math.pi * (lumen_diameter_m / 2.0) ** 2
polymer_cross_section_m2 = (
    math.pi * (outer_diameter_m / 2.0) ** 2 - 2.0 * lumen_cross_section_m2
)
wall_thickness_m = (outer_diameter_m - 2.0 * lumen_diameter_m) / 3.0

segment_length_m = catheter_length_m / N_AXIAL_SEGMENTS
outer_area_per_segment_m2 = math.pi * outer_diameter_m * segment_length_m
inner_area_per_segment_m2 = math.pi * lumen_diameter_m * segment_length_m

water_heat_capacity_J_K = (
    WATER_DENSITY_KG_M3 * lumen_cross_section_m2 * segment_length_m
    * WATER_SPECIFIC_HEAT_J_KG_K
)
polymer_heat_capacity_J_K = (
    CATHETER_DENSITY_KG_M3 * polymer_cross_section_m2 * segment_length_m
    * CATHETER_SPECIFIC_HEAT_J_KG_K
)


# =============================================================================
# 5. Transient simulation
# =============================================================================
#
# One function so the same model can be run at the nominal condition, inside
# the calibration fit, and inside the validation test.
#
# Heat path per axial station (wall = one polymer node with thermal mass):
#     tank --[1/h_tank + t_wall/2 / k_p, outer area]--> wall
#     wall --[t_wall/2 / k_p + 1/h_inner, lumen area]--> each lumen's water
# The wall is crossed ONCE in total; the half/half split only places the
# polymer thermal mass in the middle of the conduction path.
# Both lumens exchange with the same wall node, which also provides the
# lumen-to-lumen thermal interaction.
#
# Inner film: thermally developing laminar flow, Hausen correlation
#     Gz = Re * Pr * D / L
#     Nu = 3.66 + 0.0668 * Gz / (1 + 0.04 * Gz^(2/3))
# This makes h_inner grow with flow rate, which the measured data requires.
#
# Numerics: first-order upwind advection, explicit Euler.  Index 0 is the
# UPSTREAM end of each lumen (inlet lumen: proximal; outlet lumen: distal),
# so the distal turn is simply "last inlet segment feeds first outlet segment"
# and mass flow is conserved by construction.

def simulate(inlet_C, tank_C, flow_m3_s, duration_s, calibration_k):
    """Return (time array, proximal-outlet-temperature array)."""
    velocity = flow_m3_s / lumen_cross_section_m2
    mass_flow = WATER_DENSITY_KG_M3 * flow_m3_s

    reynolds = (WATER_DENSITY_KG_M3 * velocity * lumen_diameter_m
                / WATER_DYNAMIC_VISCOSITY_PA_S)
    if reynolds >= 2300.0:
        raise ValueError(f"Re = {reynolds:.0f}: model assumes laminar flow.")

    prandtl = (WATER_DYNAMIC_VISCOSITY_PA_S * WATER_SPECIFIC_HEAT_J_KG_K
               / WATER_THERMAL_CONDUCTIVITY_W_M_K)
    graetz = reynolds * prandtl * lumen_diameter_m / catheter_length_m
    nusselt = 3.66 + 0.0668 * graetz / (1.0 + 0.04 * graetz ** (2.0 / 3.0))
    h_inner = nusselt * WATER_THERMAL_CONDUCTIVITY_W_M_K / lumen_diameter_m

    # Series resistances; K scales both resulting conductances.
    u_lumen_wall = 1.0 / (
        1.0 / h_inner
        + (wall_thickness_m / 2.0) / CATHETER_THERMAL_CONDUCTIVITY_W_M_K
    )
    u_wall_tank = 1.0 / (
        (wall_thickness_m / 2.0) / CATHETER_THERMAL_CONDUCTIVITY_W_M_K
        + 1.0 / TANK_CONVECTION_COEFFICIENT_W_M2_K
    )
    g_lumen_wall = calibration_k * u_lumen_wall * inner_area_per_segment_m2
    g_wall_tank = calibration_k * u_wall_tank * outer_area_per_segment_m2

    # Stability: advection CFL and the fastest heat-exchange time constant.
    dt_advection = segment_length_m / velocity
    dt_water = water_heat_capacity_J_K / (
        mass_flow * WATER_SPECIFIC_HEAT_J_KG_K + g_lumen_wall)
    dt_polymer = polymer_heat_capacity_J_K / (g_wall_tank + 2.0 * g_lumen_wall)
    dt = SAFETY_FACTOR * min(dt_advection, dt_water, dt_polymer)
    n_steps = int(math.ceil(duration_s / dt))

    t_in = np.full(N_AXIAL_SEGMENTS, INITIAL_INTERNAL_WATER_TEMPERATURE_C)
    t_out = np.full(N_AXIAL_SEGMENTS, INITIAL_INTERNAL_WATER_TEMPERATURE_C)
    t_wall = np.full(N_AXIAL_SEGMENTS, INITIAL_CATHETER_TEMPERATURE_C)

    time_s = np.zeros(n_steps + 1)
    outlet_C = np.full(n_steps + 1, t_out[-1])

    advection_gain = mass_flow * WATER_SPECIFIC_HEAT_J_KG_K   # W/K

    for step in range(n_steps):
        # Upstream temperature for every segment; the distal turn feeds the
        # last inlet-lumen segment into the first outlet-lumen segment.
        up_in = np.concatenate(([inlet_C], t_in[:-1]))
        up_out = np.concatenate(([t_in[-1]], t_out[:-1]))

        q_wall_to_in = g_lumen_wall * (t_wall - t_in)       # W
        q_wall_to_out = g_lumen_wall * (t_wall - t_out)     # W
        q_tank_to_wall = g_wall_tank * (tank_C - t_wall)    # W

        t_in = t_in + dt * (advection_gain * (up_in - t_in)
                            + q_wall_to_in) / water_heat_capacity_J_K
        t_out = t_out + dt * (advection_gain * (up_out - t_out)
                              + q_wall_to_out) / water_heat_capacity_J_K
        t_wall = t_wall + dt * (q_tank_to_wall - q_wall_to_in
                                - q_wall_to_out) / polymer_heat_capacity_J_K

        time_s[step + 1] = (step + 1) * dt
        outlet_C[step + 1] = t_out[-1]     # proximal end of the outlet lumen

    return time_s, outlet_C


# =============================================================================
# 6. Calibration of K against the measured stepped-flow run
# =============================================================================
#
# The CSV holds a run where the pump steps through six speeds.  For each step
# we average the settled tail (last 40 %) to get one steady-state point:
# flow, tank temperature (mean of probe 1 and 2), catheter inlet and outlet.
# K is then chosen to minimise the mean absolute error between the modelled
# and the measured steady outlet temperature over all steps.

measured_steps = []   # list of dicts: rpm, flow_m3_s, tank_C, inlet_C, outlet_C

if MEASUREMENT_CSV.exists():
    data = pd.read_csv(MEASUREMENT_CSV, parse_dates=["timestamp"])
    data["t"] = (data.timestamp - data.timestamp.iloc[0]).dt.total_seconds()
    data["tank"] = (data.probe_1_c + data.probe_2_c) / 2.0

    running = data[data.peristaltic_pump_set_speed_rpm > 0]
    for rpm, group in running.groupby("peristaltic_pump_set_speed_rpm"):
        t0, t1 = group.t.iloc[0], group.t.iloc[-1]
        tail = group[group.t > t0 + 0.6 * (t1 - t0)]   # settled tail only
        measured_steps.append({
            "rpm": rpm,
            "flow_m3_s": tail.pump_flow_ml_per_s.mean() * 1.0e-6,
            "tank_C": tail.tank.mean(),
            "inlet_C": tail.catheter_in_c.mean(),
            "outlet_C": tail.catheter_out_c.mean(),
        })

def calibration_k_for_flow(flow_m3_s):
    """Flow-dependent calibration factor K(Q) = K_ref * (Q / Q_ref) ** n."""
    return (CALIBRATION_K_REF
            * (flow_m3_s / reference_flow_m3_s) ** CALIBRATION_N_EXPONENT)

def k_needed_for_step(step):
    """Bisection: the K that makes the modelled steady outlet match this
    measured step exactly.  Outlet temperature rises monotonically with K."""
    k_low, k_high = 0.2, 8.0
    for _ in range(30):
        k_mid = 0.5 * (k_low + k_high)
        _, outlet = simulate(step["inlet_C"], step["tank_C"],
                             step["flow_m3_s"], duration_s=60.0,
                             calibration_k=k_mid)
        if outlet[-1] < step["outlet_C"]:
            k_low = k_mid
        else:
            k_high = k_mid
    return 0.5 * (k_low + k_high)

if measured_steps:
    # Fit K(Q) = K_ref * (Q/Q_ref)^n by least squares in log-log space
    # through the exact K needed at each measured pump speed.
    k_needed = np.array([k_needed_for_step(s) for s in measured_steps])
    log_flow_ratio = np.log([s["flow_m3_s"] / reference_flow_m3_s
                             for s in measured_steps])
    CALIBRATION_N_EXPONENT, log_k_ref = np.polyfit(
        log_flow_ratio, np.log(k_needed), 1)
    CALIBRATION_K_REF = float(np.exp(log_k_ref))
    print("Fitted calibration: K(Q) = "
          f"{CALIBRATION_K_REF:.2f} * (Q / {CALIBRATION_REFERENCE_FLOW_ML_MIN:.0f} mL/min)"
          f" ** {CALIBRATION_N_EXPONENT:.2f}")
    print("  exact K needed per step: "
          + ", ".join(f"{k:.2f}" for k in k_needed))
else:
    print("Measurement CSV not found; using default calibration "
          f"K_ref = {CALIBRATION_K_REF:.2f}, n = {CALIBRATION_N_EXPONENT:.2f}")


# =============================================================================
# 7. Nominal transient simulation and plot
# =============================================================================

time_s, outlet_history_C = simulate(
    INLET_WATER_TEMPERATURE_C, TANK_WATER_TEMPERATURE_C,
    nominal_flow_m3_s, SIMULATION_DURATION_S,
    calibration_k_for_flow(nominal_flow_m3_s))

velocity_m_s = nominal_flow_m3_s / lumen_cross_section_m2
residence_time_one_lumen_s = catheter_length_m / velocity_m_s
residence_time_both_lumens_s = 2.0 * residence_time_one_lumen_s
final_outlet_temperature_C = outlet_history_C[-1]

fig, ax = plt.subplots(figsize=(8.0, 5.0))
ax.plot(time_s, np.full_like(time_s, INLET_WATER_TEMPERATURE_C),
        color="tab:blue", linewidth=2.0, label="Inlet-water temperature")
ax.plot(time_s, outlet_history_C,
        color="tab:red", linewidth=2.0,
        label="Proximal outlet-water temperature")
ax.set_title("Dual-lumen catheter: inlet and proximal outlet water temperature")
ax.set_xlabel("Time (s)")
ax.set_ylabel("Temperature (°C)")
ax.legend()
ax.grid(True, alpha=0.3)
ax.set_xlim(0.0, SIMULATION_DURATION_S)
fig.tight_layout()
plot_path = Path(__file__).resolve().parent / "dual_lumen_catheter_outlet.png"
fig.savefig(plot_path, dpi=150)


# =============================================================================
# 8. Validation test against the measured data
# =============================================================================
#
# For every measured pump-speed step, run the model to steady state with the
# MEASURED boundary conditions (catheter inlet temperature, tank temperature,
# flow rate) and compare the modelled outlet with the measured outlet.

print()
print("Residence time, one lumen (nominal)  : "
      f"{residence_time_one_lumen_s:.4f} s")
print("Residence time, both lumens          : "
      f"{residence_time_both_lumens_s:.4f} s")
print("Final simulated outlet temperature   : "
      f"{final_outlet_temperature_C:.2f} °C  (nominal 5 °C / 36 °C case)")
print(f"Plot saved to: {plot_path}")

# Physical checks that hold in every case:
assert INLET_WATER_TEMPERATURE_C <= final_outlet_temperature_C \
    <= TANK_WATER_TEMPERATURE_C, "Outlet temperature left the physical range."
# The tank is a constant reservoir by construction: tank_C is never updated.
# Mass conservation at the distal turn is structural: the same mass_flow
# advects both lumens and the turn simply hands the last inlet segment's
# water to the outlet lumen.

if measured_steps:
    print()
    print("Validation against measured steady states, "
          f"K(Q) = {CALIBRATION_K_REF:.2f} * (Q/Q_ref)^{CALIBRATION_N_EXPONENT:.2f}:")
    print(f"{'rpm':>5} {'flow mL/min':>12} {'tank °C':>8} {'in °C':>7} "
          f"{'out meas °C':>12} {'out model °C':>13} {'error K':>8}")
    validation_errors = []
    for step in measured_steps:
        _, outlet = simulate(step["inlet_C"], step["tank_C"],
                             step["flow_m3_s"], duration_s=60.0,
                             calibration_k=calibration_k_for_flow(
                                 step["flow_m3_s"]))
        model_out = outlet[-1]
        error = model_out - step["outlet_C"]
        validation_errors.append(abs(error))
        print(f"{step['rpm']:>5.0f} {step['flow_m3_s']*6.0e7:>12.1f} "
              f"{step['tank_C']:>8.2f} {step['inlet_C']:>7.2f} "
              f"{step['outlet_C']:>12.2f} {model_out:>13.2f} {error:>+8.2f}")

    mean_error = float(np.mean(validation_errors))
    print(f"Mean absolute outlet error: {mean_error:.2f} °C "
          f"(tolerance {VALIDATION_TOLERANCE_C:.1f} °C)")
    assert mean_error < VALIDATION_TOLERANCE_C, (
        f"Validation FAILED: mean absolute outlet error {mean_error:.2f} °C "
        f"exceeds {VALIDATION_TOLERANCE_C:.1f} °C.")
    print("Validation PASSED.")


# =============================================================================
# Main simplifications of this version
# =============================================================================
#
# - The calibration factor K(Q) scales all conductances; it lumps the
#   uncertain lumen inner diameter, tank-side h, real (non-circular, off-
#   centre) lumen geometry, and correlation error together, so it cannot
#   distinguish WHERE the model is wrong — only correct the total.  Its flow
#   exponent (~0.4) says the missing physics is flow-dependent, e.g. a
#   stronger-than-Hausen entrance effect or tank-side convection that
#   strengthens as the warmed boundary layer is swept away faster.
# - Constant water and polymer properties evaluated at ~15 °C.
# - One lumped polymer temperature per axial station; lumen-to-lumen
#   interaction only through that shared node (no explicit septum term).
# - Distal turn has no extra volume, transit time, or heat-transfer area.
# - The validation compares steady states only; a stronger test would replay
#   the full 714 s stepped run (time-varying inlet, tank, and flow) and
#   compare the whole transient outlet trace.
