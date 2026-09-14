"""
Dual-lumen catheter transient thermal model.

Cold water enters the inlet lumen at the proximal end, turns at the distal
end, and returns through the outlet lumen.  The catheter is fully submerged
in a large mixed water tank held at a constant temperature.

Calibration coefficients are read from calibration.json (written by
calibrate.py).  Without that file the model runs uncalibrated (K = 1),
i.e. pure geometry + correlations.

Run this file directly for the nominal transient case and its plot;
import it (simulate, calibration_k_for_flow) from the calibration and
validation scripts.
"""

import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

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

# Calibration file (written by calibrate.py).  The calibration factor
#     K(Q) = k_ref * (Q / reference flow) ** n_exponent
# multiplies every heat-transfer conductance and lumps all model imprecision
# (uncertain lumen diameter, tank-side h, real lumen geometry, ...).
CALIBRATION_JSON = Path(__file__).resolve().parent / "calibration.json"


# =============================================================================
# 2. Unit conversions  (SI internally)
# =============================================================================

catheter_length_m = CATHETER_LENGTH_CM / 100.0
outer_diameter_m = CATHETER_OUTER_DIAMETER_MM / 1000.0
lumen_diameter_m = LUMEN_INNER_DIAMETER_MM / 1000.0
nominal_flow_m3_s = VOLUMETRIC_FLOW_RATE_ML_MIN * 1.0e-6 / 60.0


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
# 5. Calibration coefficients (from calibration.json, else uncalibrated)
# =============================================================================

if CALIBRATION_JSON.exists():
    with open(CALIBRATION_JSON) as f:
        _cal = json.load(f)
    CALIBRATION_K_REF = _cal["k_ref"]
    CALIBRATION_N_EXPONENT = _cal["n_exponent"]
    CALIBRATION_REFERENCE_FLOW_ML_MIN = _cal["reference_flow_ml_min"]
    CALIBRATION_SOURCE = _cal.get("fitted_from", str(CALIBRATION_JSON.name))
else:
    CALIBRATION_K_REF = 1.0          # uncalibrated: trust geometry as written
    CALIBRATION_N_EXPONENT = 0.0
    CALIBRATION_REFERENCE_FLOW_ML_MIN = 60.0
    CALIBRATION_SOURCE = "none (uncalibrated, K = 1)"

reference_flow_m3_s = CALIBRATION_REFERENCE_FLOW_ML_MIN * 1.0e-6 / 60.0


def calibration_k_for_flow(flow_m3_s):
    """Flow-dependent calibration factor K(Q) = k_ref * (Q / Q_ref) ** n."""
    return (CALIBRATION_K_REF
            * (flow_m3_s / reference_flow_m3_s) ** CALIBRATION_N_EXPONENT)


# =============================================================================
# 6. Transient simulation
# =============================================================================
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
#
# Numerics: first-order upwind advection, explicit Euler.  Index 0 is the
# UPSTREAM end of each lumen (inlet lumen: proximal; outlet lumen: distal),
# so the distal turn is simply "last inlet segment feeds first outlet segment"
# and mass flow is conserved by construction.

def simulate(inlet_C, tank_C, flow_m3_s, duration_s, calibration_k=None):
    """Return (time array, proximal-outlet-temperature array).

    calibration_k defaults to the flow-dependent K from calibration.json;
    pass an explicit value (e.g. 1.0) to override it."""
    if calibration_k is None:
        calibration_k = calibration_k_for_flow(flow_m3_s)

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


def steady_outlet_C(inlet_C, tank_C, flow_m3_s, calibration_k=None):
    """Steady-state proximal outlet temperature for one operating point."""
    _, outlet = simulate(inlet_C, tank_C, flow_m3_s, duration_s=60.0,
                         calibration_k=calibration_k)
    return float(outlet[-1])


# =============================================================================
# 7. Nominal transient simulation and plot (only when run directly)
# =============================================================================

if __name__ == "__main__":
    print(f"Calibration source: {CALIBRATION_SOURCE}")
    print(f"K(Q) = {CALIBRATION_K_REF:.2f} * "
          f"(Q / {CALIBRATION_REFERENCE_FLOW_ML_MIN:.0f} mL/min) "
          f"** {CALIBRATION_N_EXPONENT:.2f}")

    time_s, outlet_history_C = simulate(
        INLET_WATER_TEMPERATURE_C, TANK_WATER_TEMPERATURE_C,
        nominal_flow_m3_s, SIMULATION_DURATION_S)

    velocity_m_s = nominal_flow_m3_s / lumen_cross_section_m2
    residence_time_one_lumen_s = catheter_length_m / velocity_m_s
    final_outlet_temperature_C = outlet_history_C[-1]

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    ax.plot(time_s, np.full_like(time_s, INLET_WATER_TEMPERATURE_C),
            color="tab:blue", linewidth=2.0, label="Inlet-water temperature")
    ax.plot(time_s, outlet_history_C,
            color="tab:red", linewidth=2.0,
            label="Proximal outlet-water temperature")
    ax.set_title("Dual-lumen catheter: inlet and proximal outlet temperature")
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Temperature (°C)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0.0, SIMULATION_DURATION_S)
    fig.tight_layout()
    plot_path = Path(__file__).resolve().parent / "dual_lumen_catheter_outlet.png"
    fig.savefig(plot_path, dpi=150)

    print()
    print("Residence time, one lumen          : "
          f"{residence_time_one_lumen_s:.4f} s")
    print("Residence time, both lumens        : "
          f"{2.0 * residence_time_one_lumen_s:.4f} s")
    print("Final simulated outlet temperature : "
          f"{final_outlet_temperature_C:.2f} °C")
    print(f"Plot saved to: {plot_path}")

    # Physical checks.  The tank is a constant reservoir by construction
    # (tank_C is never updated) and mass conservation at the distal turn is
    # structural (the same mass flow advects both lumens).
    assert INLET_WATER_TEMPERATURE_C <= final_outlet_temperature_C \
        <= TANK_WATER_TEMPERATURE_C, "Outlet left the physical range."


# =============================================================================
# Main simplifications of this version
# =============================================================================
#
# - The calibration factor K(Q) scales all conductances; it lumps the
#   uncertain lumen inner diameter, tank-side h, real (non-circular, off-
#   centre) lumen geometry, and correlation error together, so it cannot
#   distinguish WHERE the model is wrong — only correct the total.
# - Constant water and polymer properties evaluated at ~15 °C.
# - One lumped polymer temperature per axial station; lumen-to-lumen
#   interaction only through that shared node (no explicit septum term).
# - Distal turn has no extra volume, transit time, or heat-transfer area.
