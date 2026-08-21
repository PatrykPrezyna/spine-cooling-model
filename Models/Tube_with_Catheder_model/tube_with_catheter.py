"""
Transient 2-D axisymmetric heat-transfer model
==============================================

Water fills a cylindrical polymer tube.  A cooling catheter sits on the
tube axis.  The tube is submerged in a large water bath held at 36 °C.

This file is a standalone first version.  It does not import or reuse any
other thermal or catheter model in the repository.

Axisymmetric approximation
--------------------------
The catheter is treated as a centrally located cylindrical heat exchanger.
This does NOT resolve the non-axisymmetric geometry of the two internal
lumens.  Those internal details are represented by the measured (or
assumed) effective catheter thermal conductance G_catheter.

A conduction-only model of the tube water may underestimate heat transport
if natural convection develops inside the tube.  Raise
WATER_EFFECTIVE_CONDUCTIVITY_W_M_K above the molecular value to approximate
mixing; that is an engineering closure, not a resolved flow field.

Coordinate system
-----------------
  z  : axial position, 0 at the tube/catheter start, to tube length
  r  : radial position, 0 (tube centreline, only past the catheter tip)
       to the tube outer surface.  Alongside the catheter body the water
       domain starts at the catheter outer surface.
  t  : time

Governing equation in each material (axisymmetric conduction):

  rho * cp * dT/dt
      = (1/r) * d/dr (k * r * dT/dr)
      + d/dz (k * dT/dz)
"""

import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# =============================================================================
# 2. User input parameters  (change these)
# =============================================================================
#
# SI units are used after the conversion section below.
# Temperatures are in °C.  Because only temperature *differences* enter the
# heat-flux laws, °C and K increments are interchangeable here.

# --- Geometry ---
# Tube starts where the catheter starts.  Active cooling covers the first
# 30 cm.  The catheter body continues 2 cm past the active section, then
# the tube is open water (centreline included) for ~20 cm to the insulated
# distal end.
TUBE_INNER_DIAMETER_CM = 3.0
TUBE_WALL_THICKNESS_MM = 2.0

CATHETER_OUTER_DIAMETER_MM = 3.0          # typical Cool Spine catheter OD
CATHETER_AXIAL_START_CM = 0.0             # tube and catheter start together
CATHETER_ACTIVE_LENGTH_CM = 30.0
CATHETER_BODY_AFTER_ACTIVE_CM = 2.0       # inactive body past the cooling zone
TUBE_OVERHANG_AFTER_BODY_CM = 20.0        # open water past the catheter tip

TUBE_LENGTH_CM = (
    CATHETER_AXIAL_START_CM
    + CATHETER_ACTIVE_LENGTH_CM
    + CATHETER_BODY_AFTER_ACTIVE_CM
    + TUBE_OVERHANG_AFTER_BODY_CM
)

# --- Measuring points (water) ---
# P1: end of the catheter body, at the outer surface (tip rim).
# P2: end of the active cooling zone, 3 mm radially out from the catheter OD.
SENSOR_OFFSET_FROM_CATHETER_MM = 3.0

# --- Internal water ---
# Assumed: liquid water at 20 °C, 1 atm, engineering tables.
WATER_DENSITY_KG_M3 = 998.0
WATER_SPECIFIC_HEAT_J_KG_K = 4182.0
WATER_MOLECULAR_CONDUCTIVITY_W_M_K = 0.598
# Effective conductivity used in the water region.  Set equal to the
# molecular value for pure conduction.  Increase to approximate mixing /
# natural convection inside the tube.
WATER_EFFECTIVE_CONDUCTIVITY_W_M_K = WATER_MOLECULAR_CONDUCTIVITY_W_M_K
WATER_INITIAL_TEMPERATURE_C = 36.0

# --- Polymer wall ---
# ASSUMED material: clear cast acrylic (PMMA), typical handbook values.
# Replace with manufacturer or measured properties for the actual tube.
POLYMER_MATERIAL_NAME = "clear cast acrylic (PMMA) — ASSUMED, not measured"
POLYMER_THERMAL_CONDUCTIVITY_W_M_K = 0.19
POLYMER_DENSITY_KG_M3 = 1180.0
POLYMER_SPECIFIC_HEAT_J_KG_K = 1470.0
POLYMER_INITIAL_TEMPERATURE_C = 36.0

# --- External water bath (thermal reservoir, not modelled as a body) ---
EXTERNAL_WATER_TEMPERATURE_C = 36.0
# Assumed: well-mixed bath on a ~3 cm cylinder.  Order-of-magnitude only.
EXTERNAL_CONVECTION_COEFFICIENT_W_M2_K = 1000.0
# If True, the outer polymer FACE is held at EXTERNAL_WATER_TEMPERATURE_C
# (negligible external convection resistance).
OUTER_WALL_FIXED_TO_EXTERNAL_TEMPERATURE = False

# Tube-end boundary condition.
#   "insulated"  : dT/dz = 0 at z = 0 and z = L   (default for this first model)
#   "convection" : ends exposed to the 36 °C bath, same h as the outer wall
END_BOUNDARY_CONDITION = "insulated"

# --- Catheter (preferred: effective-conductance representation) ---
# "effective_conductance" uses G_CATHETER_W_PER_K directly (default).
# "detailed" builds G from the film coefficient and outer surface area.
CATHETER_REPRESENTATION = "effective_conductance"

# ASSUMED conductance.  Benchtop calorimetry of a similar immersed catheter
# at ~47–60 mL/min gave UA of order 0.8–1.3 W/K.  Replace with the value
# characterised for this catheter in this geometry.
G_CATHETER_W_PER_K = 1.0

CATHETER_COOLANT_INLET_TEMPERATURE_C = 5.0
CATHETER_COOLANT_FLOW_ML_MIN = 60.0
CATHETER_COOLANT_DENSITY_KG_M3 = 998.0          # assumed, water at 20 °C
CATHETER_COOLANT_SPECIFIC_HEAT_J_KG_K = 4182.0  # assumed, water at 20 °C

# Coolant temperature along the active length.
#   True  : T_coolant = inlet temperature everywhere (simplest)
#   False : coolant warms as it picks up heat (energy balance along z)
USE_CONSTANT_COOLANT_TEMPERATURE = True
CATHETER_FLOW_TOWARD_POSITIVE_Z = True          # inlet at axial start

# Detailed-representation parameters (used only if CATHETER_REPRESENTATION
# is "detailed").  All are ASSUMED until measured.
CATHETER_EFFECTIVE_CONDUCTIVITY_W_M_K = 0.19    # assumed, typical PU
CATHETER_THERMAL_CAPACITANCE_J_K = 0.0          # 0 => neglected in this version
H_CATHETER_TO_WATER_W_M2_K = 500.0              # assumed film coefficient

# --- Numerical settings ---
N_RADIAL_CORE = 5                           # r = 0 to catheter OD (wake only)
N_RADIAL_WATER = 16                         # catheter OD to tube inner wall
N_RADIAL_POLYMER = 5
N_AXIAL_ACTIVE = 36                         # along the 30 cm cooling length
N_AXIAL_BODY_TIP = 4                        # along the 2 cm inactive body
N_AXIAL_WAKE = 24                           # along the 20 cm open-water overhang
TIME_STEP_S = 0.10
MAX_SIMULATION_TIME_S = 10000.0
STEADY_STATE_TOLERANCE_C_PER_S = 0.0001
STEADY_STATE_REQUIRED_STEPS = 20
SNAPSHOT_INTERVAL_S = 2.0
# Intermediate plot is taken at this fraction of the time to steady state.
INTERMEDIATE_FRACTION_OF_STEADY_STATE = 0.50
FOURIER_SAFETY_FACTOR = 0.40                    # explicit-step stability margin

# Output
SAVE_PLOTS = True
SHOW_PLOTS = True
OUTPUT_DIRECTORY = Path(__file__).resolve().parent


# =============================================================================
# 3. Unit conversions  (SI internally: m, kg, s, W, J, K)
# =============================================================================

tube_length_m = TUBE_LENGTH_CM / 100.0
tube_inner_radius_m = (TUBE_INNER_DIAMETER_CM / 100.0) / 2.0
tube_wall_thickness_m = TUBE_WALL_THICKNESS_MM / 1000.0
tube_outer_radius_m = tube_inner_radius_m + tube_wall_thickness_m

catheter_outer_radius_m = (CATHETER_OUTER_DIAMETER_MM / 1000.0) / 2.0
catheter_axial_start_m = CATHETER_AXIAL_START_CM / 100.0
catheter_active_length_m = CATHETER_ACTIVE_LENGTH_CM / 100.0
catheter_body_after_active_m = CATHETER_BODY_AFTER_ACTIVE_CM / 100.0
tube_overhang_after_body_m = TUBE_OVERHANG_AFTER_BODY_CM / 100.0

catheter_active_end_m = catheter_axial_start_m + catheter_active_length_m
catheter_body_end_m = catheter_active_end_m + catheter_body_after_active_m

sensor_offset_from_catheter_m = SENSOR_OFFSET_FROM_CATHETER_MM / 1000.0

# Requested probe coordinates (m).  The solver samples the nearest water cell.
probe_1_r_m = catheter_outer_radius_m
probe_1_z_m = catheter_body_end_m
probe_2_r_m = catheter_outer_radius_m + sensor_offset_from_catheter_m
probe_2_z_m = catheter_active_end_m

coolant_flow_m3_s = CATHETER_COOLANT_FLOW_ML_MIN * 1.0e-6 / 60.0

if catheter_outer_radius_m >= tube_inner_radius_m:
    raise ValueError("Catheter outer radius must be smaller than the tube inner radius.")
if catheter_axial_start_m < 0.0:
    raise ValueError("Catheter must start at or after z = 0.")
if catheter_body_end_m > tube_length_m + 1.0e-12:
    raise ValueError("Catheter body extends past the tube length.")


# =============================================================================
# 4. Material properties and assumptions
# =============================================================================
#
# Every value below is constant (no temperature dependence).
# Assumed quantities are named as such in the comments above.

k_water = WATER_EFFECTIVE_CONDUCTIVITY_W_M_K
k_polymer = POLYMER_THERMAL_CONDUCTIVITY_W_M_K

rho_water = WATER_DENSITY_KG_M3
rho_polymer = POLYMER_DENSITY_KG_M3

cp_water = WATER_SPECIFIC_HEAT_J_KG_K
cp_polymer = POLYMER_SPECIFIC_HEAT_J_KG_K

T_water_initial = WATER_INITIAL_TEMPERATURE_C
T_polymer_initial = POLYMER_INITIAL_TEMPERATURE_C
T_external = EXTERNAL_WATER_TEMPERATURE_C
T_coolant_inlet = CATHETER_COOLANT_INLET_TEMPERATURE_C

# Catheter conductance actually used by the solver.
catheter_surface_area_m2 = (
    2.0 * math.pi * catheter_outer_radius_m * catheter_active_length_m
)
if CATHETER_REPRESENTATION == "effective_conductance":
    G_catheter = G_CATHETER_W_PER_K
elif CATHETER_REPRESENTATION == "detailed":
    # First-version detailed option: film conductance on the outer surface.
    # Internal lumens are still not resolved.  G_CATHETER_W_PER_K is ignored.
    G_catheter = H_CATHETER_TO_WATER_W_M2_K * catheter_surface_area_m2
    print(
        "Using detailed catheter representation: "
        f"G = h * A_outer = {G_catheter:.4f} W/K "
        f"(h = {H_CATHETER_TO_WATER_W_M2_K:.1f} W/m²K)."
    )
    if CATHETER_THERMAL_CAPACITANCE_J_K > 0.0:
        print(
            "NOTE: catheter thermal capacitance is listed but not used in "
            "this first version.  The modelled domain starts at the catheter "
            "outer surface."
        )
else:
    raise ValueError("CATHETER_REPRESENTATION must be 'effective_conductance' or 'detailed'.")

coolant_heat_capacity_rate_W_PER_K = (
    CATHETER_COOLANT_DENSITY_KG_M3
    * coolant_flow_m3_s
    * CATHETER_COOLANT_SPECIFIC_HEAT_J_KG_K
)

if END_BOUNDARY_CONDITION not in ("insulated", "convection"):
    raise ValueError("END_BOUNDARY_CONDITION must be 'insulated' or 'convection'.")


# =============================================================================
# 5. Computational grid
# =============================================================================
#
# Finite-volume mesh in (r, z).  Faces are placed exactly on:
#   - the axis r = 0
#   - the catheter outer surface
#   - the water–polymer interface
#   - the end of the active cooling length
#   - the catheter-body tip
#
# Cells with r < r_catheter and z < z_body are inside the catheter.  They
# are blocked: not part of the water/wall domain.  Past the tip, those
# same radial cells are open water, so heat can conduct around the tip
# the same way it conducts radially at the sides.

n_r_core = N_RADIAL_CORE
n_r_water = N_RADIAL_WATER
n_r_polymer = N_RADIAL_POLYMER
n_r = n_r_core + n_r_water + n_r_polymer

r_face_core = np.linspace(0.0, catheter_outer_radius_m, n_r_core + 1)
r_face_water = np.linspace(
    catheter_outer_radius_m, tube_inner_radius_m, n_r_water + 1
)
r_face_polymer = np.linspace(
    tube_inner_radius_m, tube_outer_radius_m, n_r_polymer + 1
)
r_face = np.concatenate(
    [r_face_core[:-1], r_face_water[:-1], r_face_polymer]
)

z_face_active = np.linspace(
    0.0, catheter_active_end_m, N_AXIAL_ACTIVE + 1
)
z_face_body = np.linspace(
    catheter_active_end_m, catheter_body_end_m, N_AXIAL_BODY_TIP + 1
)
z_face_wake = np.linspace(
    catheter_body_end_m, tube_length_m, N_AXIAL_WAKE + 1
)
z_face = np.concatenate(
    [z_face_active[:-1], z_face_body[:-1], z_face_wake]
)
n_z = len(z_face) - 1

r_center = 0.5 * (r_face[:-1] + r_face[1:])
z_center = 0.5 * (z_face[:-1] + z_face[1:])
dz = np.diff(z_face)

i_catheter_face = n_r_core                       # r_face index at catheter OD
i_annulus_water = n_r_core                       # first water cell outside catheter

is_core_cell = np.arange(n_r) < n_r_core
is_annulus_water_cell = (np.arange(n_r) >= n_r_core) & (
    np.arange(n_r) < n_r_core + n_r_water
)
is_polymer_cell = np.arange(n_r) >= n_r_core + n_r_water
is_radial_water_cell = is_core_cell | is_annulus_water_cell

# Blocked = inside the solid catheter body (not modelled).
is_blocked = (
    (r_center[:, np.newaxis] < catheter_outer_radius_m)
    & (z_center[np.newaxis, :] < catheter_body_end_m)
)
is_active = np.logical_not(is_blocked)
is_water_2d = is_radial_water_cell[:, np.newaxis] & is_active
is_polymer_2d = is_polymer_cell[:, np.newaxis] * np.ones((1, n_z), dtype=bool)


def nearest_water_cell(r_target_m, z_target_m):
    """Index of the nearest active water cell to (r, z)."""
    distance_sq = (
        (r_center[:, np.newaxis] - r_target_m) ** 2
        + (z_center[np.newaxis, :] - z_target_m) ** 2
    )
    distance_sq[np.logical_not(is_water_2d)] = np.inf
    i_found, j_found = np.unravel_index(np.argmin(distance_sq), distance_sq.shape)
    return int(i_found), int(j_found)


i_probe_1, j_probe_1 = nearest_water_cell(probe_1_r_m, probe_1_z_m)
i_probe_2, j_probe_2 = nearest_water_cell(probe_2_r_m, probe_2_z_m)
probe_1_r_used_m = r_center[i_probe_1]
probe_1_z_used_m = z_center[j_probe_1]
probe_2_r_used_m = r_center[i_probe_2]
probe_2_z_used_m = z_center[j_probe_2]

k_cell = np.where(is_radial_water_cell, k_water, k_polymer)
rho_cell = np.where(is_radial_water_cell, rho_water, rho_polymer)
cp_cell = np.where(is_radial_water_cell, cp_water, cp_polymer)

ring_area_m2 = math.pi * (r_face[1:] ** 2 - r_face[:-1] ** 2)
cell_volume_m3 = ring_area_m2[:, np.newaxis] * dz[np.newaxis, :]
heat_capacity_J_PER_K = (
    rho_cell[:, np.newaxis] * cp_cell[:, np.newaxis] * cell_volume_m3
)
heat_capacity_J_PER_K[is_blocked] = np.inf

# --- Radial conduction between neighbouring cell centres (cylindrical) ---
G_radial_interior = np.zeros((n_r - 1, n_z))
for i in range(n_r - 1):
    r_left = r_center[i]
    r_at_face = r_face[i + 1]
    r_right = r_center[i + 1]
    two_pi_dz = 2.0 * math.pi * dz
    resistance = (
        np.log(r_at_face / r_left) / (k_cell[i] * two_pi_dz)
        + np.log(r_right / r_at_face) / (k_cell[i + 1] * two_pi_dz)
    )
    G_radial_interior[i, :] = 1.0 / resistance
    face_touches_blocked = is_blocked[i, :] | is_blocked[i + 1, :]
    G_radial_interior[i, face_touches_blocked] = 0.0

# --- Axial conduction between neighbouring cell centres ---
dz_between_centres = z_center[1:] - z_center[:-1]
G_axial_interior = (
    (k_cell[:, np.newaxis] * ring_area_m2[:, np.newaxis])
    / dz_between_centres[np.newaxis, :]
)
for j in range(n_z - 1):
    face_touches_blocked = is_blocked[:, j] | is_blocked[:, j + 1]
    G_axial_interior[face_touches_blocked, j] = 0.0

# --- Outer polymer-wall boundary (external 36 °C reservoir) ---
R_half_outer = np.log(tube_outer_radius_m / r_center[-1]) / (
    2.0 * math.pi * k_cell[-1] * dz
)
A_outer_m2 = 2.0 * math.pi * tube_outer_radius_m * dz
if OUTER_WALL_FIXED_TO_EXTERNAL_TEMPERATURE:
    R_outer = R_half_outer
else:
    R_outer = R_half_outer + 1.0 / (
        EXTERNAL_CONVECTION_COEFFICIENT_W_M2_K * A_outer_m2
    )
G_outer = 1.0 / R_outer

# --- Catheter cooling on the cylindrical surface, active length only ---
# The 2 cm body past the active section has no cooling (adiabatic wall).
# The tip face is also adiabatic.  Heat still reaches the wake by conduction
# through the water around the tip.
overlap_m = np.maximum(
    0.0,
    np.minimum(z_face[1:], catheter_active_end_m)
    - np.maximum(z_face[:-1], catheter_axial_start_m),
)
G_catheter_j = G_catheter * overlap_m / catheter_active_length_m
G_catheter_integrated = float(G_catheter_j.sum())

# --- Tube-end boundary ---
A_end_m2 = ring_area_m2.copy()
R_half_end_left = (z_center[0] - z_face[0]) / (k_cell * A_end_m2)
R_half_end_right = (z_face[-1] - z_center[-1]) / (k_cell * A_end_m2)
if END_BOUNDARY_CONDITION == "insulated":
    G_end_left = np.zeros(n_r)
    G_end_right = np.zeros(n_r)
else:
    R_conv_end = 1.0 / (EXTERNAL_CONVECTION_COEFFICIENT_W_M2_K * A_end_m2)
    G_end_left = 1.0 / (R_half_end_left + R_conv_end)
    G_end_right = 1.0 / (R_half_end_right + R_conv_end)
G_end_left[is_blocked[:, 0]] = 0.0

# --- Explicit time-step stability (active cells only) ---
sum_G = np.zeros((n_r, n_z))
sum_G[i_annulus_water, :] += G_catheter_j
sum_G[-1, :] += G_outer
sum_G[:-1, :] += G_radial_interior
sum_G[1:, :] += G_radial_interior
sum_G[:, :-1] += G_axial_interior
sum_G[:, 1:] += G_axial_interior
sum_G[:, 0] += G_end_left
sum_G[:, -1] += G_end_right
sum_G[is_blocked] = 0.0

stable_dt_s = FOURIER_SAFETY_FACTOR * np.min(
    heat_capacity_J_PER_K[is_active] / np.maximum(sum_G[is_active], 1.0e-30)
)
dt = min(TIME_STEP_S, float(stable_dt_s))
if dt < TIME_STEP_S:
    print(
        f"Time step reduced from {TIME_STEP_S:.4f} s to {dt:.4f} s "
        "for explicit-scheme stability."
    )


# =============================================================================
# 6. Initial temperature fields
# =============================================================================

T = np.zeros((n_r, n_z))
T[is_water_2d] = T_water_initial
T[is_polymer_2d] = T_polymer_initial
T[is_blocked] = T_water_initial
T_initial = T.copy()

T_coolant_axial = np.full(n_z, T_coolant_inlet)


def coolant_temperature_along_catheter(T_wall_water):
    """Local coolant temperature in each axial cell, °C."""
    if USE_CONSTANT_COOLANT_TEMPERATURE:
        return np.full(n_z, T_coolant_inlet)

    T_c_line = np.full(n_z, T_coolant_inlet)
    axial_order = range(n_z) if CATHETER_FLOW_TOWARD_POSITIVE_Z else range(n_z - 1, -1, -1)
    T_c = T_coolant_inlet
    for j in axial_order:
        T_c_line[j] = T_c
        heat_into_coolant_W = G_catheter_j[j] * (T_wall_water[j] - T_c)
        if coolant_heat_capacity_rate_W_PER_K > 0.0:
            T_c = T_c + heat_into_coolant_W / coolant_heat_capacity_rate_W_PER_K
    return T_c_line


# =============================================================================
# 7. Boundary conditions  (encoded as face conductances above)
# =============================================================================
#
# Inner radial face along the active catheter length:
#     Q_removed = G_j * (T_water_at_surface − T_coolant)
#     The 2 cm inactive body and the tip face have G = 0 (adiabatic).
#     Past the tip, r = 0 is a symmetry axis (dT/dr = 0) and the core
#     is ordinary water, so cooling wraps around the end.
#
# Outer polymer face:
#     Q_into_wall = G_outer * (T_external − T_outer_cell)
#
# Water–polymer interface:
#     one shared temperature field; split cylindrical resistance
#     gives equal temperature and equal heat flux at the interface face.
#
# Tube ends:
#     insulated (dT/dz = 0) or convection to the 36 °C bath.
#     The proximal end is the tube/catheter start.  The distal end is
#     ~20 cm past the catheter body.


# =============================================================================
# 8. Time-stepping loop
# =============================================================================

snapshot_times_s = [0.0]
snapshot_fields = [T_initial.copy()]
next_snapshot_s = SNAPSHOT_INTERVAL_S

heat_from_external_J = 0.0
heat_to_catheter_J = 0.0
heat_from_ends_J = 0.0

consecutive_steady_steps = 0
steady_state_reached = False
time_to_steady_state_s = None
Q_catheter_first_step_W = None

max_steps = int(math.ceil(MAX_SIMULATION_TIME_S / dt))
time_s = 0.0
progress_marker = 0.10

print()
print("Running axisymmetric tube-with-catheter transient model...")
print(
    f"  Grid: {n_r_core} core + {n_r_water} annulus water + {n_r_polymer} polymer "
    f"radial cells, {n_z} axial cells"
)
print(f"  Time step: {dt:.4f} s   max time: {MAX_SIMULATION_TIME_S:.1f} s")
print(
    f"  Active cooling 0–{catheter_active_end_m*100:.1f} cm; "
    f"catheter body ends at {catheter_body_end_m*100:.1f} cm; "
    f"tube length {tube_length_m*100:.1f} cm"
)
print(
    f"  P1 body tip: requested "
    f"z = {probe_1_z_m*100:.2f} cm, r = {probe_1_r_m*1000:.2f} mm "
    f"→ cell z = {probe_1_z_used_m*100:.2f} cm, r = {probe_1_r_used_m*1000:.2f} mm"
)
print(
    f"  P2 cooling zone +{SENSOR_OFFSET_FROM_CATHETER_MM:.1f} mm: requested "
    f"z = {probe_2_z_m*100:.2f} cm, r = {probe_2_r_m*1000:.2f} mm "
    f"→ cell z = {probe_2_z_used_m*100:.2f} cm, r = {probe_2_r_used_m*1000:.2f} mm"
)
print()

for step in range(1, max_steps + 1):
    T_coolant_axial = coolant_temperature_along_catheter(T[i_annulus_water, :])

    # Face heat rates, positive in the +r or +z direction, watts.
    Q_r_face = np.zeros((n_r + 1, n_z))
    Q_z_face = np.zeros((n_r, n_z + 1))

    # Axis r = 0: no radial heat flux.
    Q_r_face[0, :] = 0.0

    # Interior radial conduction (already zero on catheter-blocked faces).
    Q_r_face[1:-1, :] = G_radial_interior * (T[:-1, :] - T[1:, :])

    # Active-length cooling at the catheter outer surface.
    Q_r_face[i_catheter_face, :] += -G_catheter_j * (
        T[i_annulus_water, :] - T_coolant_axial
    )

    # Outer wall: heat flowing +r (out of the domain).
    Q_r_face[-1, :] = G_outer * (T[-1, :] - T_external)

    # Left end: heat flowing +z into the first axial cells.
    Q_z_face[:, 0] = G_end_left * (T_external - T[:, 0])

    # Interior axial conduction (zero across the adiabatic catheter tip).
    Q_z_face[:, 1:-1] = G_axial_interior * (T[:, :-1] - T[:, 1:])

    # Right end: heat flowing +z out of the domain.
    Q_z_face[:, -1] = G_end_right * (T[:, -1] - T_external)

    Q_net_W = (
        Q_r_face[:-1, :] - Q_r_face[1:, :]
        + Q_z_face[:, :-1] - Q_z_face[:, 1:]
    )
    Q_net_W[is_blocked] = 0.0

    Q_catheter_W = float(
        np.sum(G_catheter_j * (T[i_annulus_water, :] - T_coolant_axial))
    )
    Q_external_W = float(-Q_r_face[-1, :].sum())
    Q_ends_W = float(Q_z_face[:, 0].sum() - Q_z_face[:, -1].sum())

    dT = dt * Q_net_W / heat_capacity_J_PER_K
    dT[is_blocked] = 0.0
    max_abs_dT = float(np.max(np.abs(dT[is_active])))

    T = T + dT
    time_s = step * dt

    if Q_catheter_first_step_W is None:
        Q_catheter_first_step_W = Q_catheter_W

    heat_to_catheter_J += Q_catheter_W * dt
    heat_from_external_J += Q_external_W * dt
    heat_from_ends_J += Q_ends_W * dt

    # Snapshot storage for later plot-time selection.
    if time_s + 0.5 * dt >= next_snapshot_s:
        snapshot_times_s.append(time_s)
        snapshot_fields.append(T.copy())
        next_snapshot_s += SNAPSHOT_INTERVAL_S

    # 9. Steady-state detection
    # max|T_new − T_old| < (tolerance in °C/s) * dt, for several steps.
    if max_abs_dT < STEADY_STATE_TOLERANCE_C_PER_S * dt:
        consecutive_steady_steps += 1
        if consecutive_steady_steps >= STEADY_STATE_REQUIRED_STEPS and not steady_state_reached:
            steady_state_reached = True
            time_to_steady_state_s = time_s
            break
    else:
        consecutive_steady_steps = 0

    if time_s >= progress_marker * MAX_SIMULATION_TIME_S:
        T_water_mean = float(
            np.sum(T[is_water_2d] * cell_volume_m3[is_water_2d])
            / np.sum(cell_volume_m3[is_water_2d])
        )
        print(
            f"  t = {time_s:8.1f} s  |  "
            f"mean water T = {T_water_mean:6.3f} °C  |  "
            f"max |dT| = {max_abs_dT / dt:.4e} °C/s"
        )
        progress_marker += 0.10

T_final = T.copy()
if time_s not in snapshot_times_s:
    snapshot_times_s.append(time_s)
    snapshot_fields.append(T_final.copy())

probe_1_history_C = np.array(
    [field[i_probe_1, j_probe_1] for field in snapshot_fields]
)
probe_2_history_C = np.array(
    [field[i_probe_2, j_probe_2] for field in snapshot_fields]
)
probe_times_s = np.array(snapshot_times_s)

if not steady_state_reached:
    time_to_steady_state_s = time_s
    print()
    print(
        f"Steady state NOT reached by t = {time_s:.1f} s "
        f"(max |dT/dt| still above {STEADY_STATE_TOLERANCE_C_PER_S} °C/s)."
    )
else:
    print()
    print(f"Steady state reached at t = {time_to_steady_state_s:.1f} s.")


# =============================================================================
# 10. Selection of the three plotting times
# =============================================================================

snapshot_times = np.array(snapshot_times_s)
t_plot_initial_s = 0.0
t_plot_steady_s = time_to_steady_state_s
t_plot_intermediate_s = INTERMEDIATE_FRACTION_OF_STEADY_STATE * t_plot_steady_s


def nearest_snapshot(target_s):
    index = int(np.argmin(np.abs(snapshot_times - target_s)))
    return snapshot_times[index], snapshot_fields[index]


t_initial_used_s, T_plot_initial = nearest_snapshot(t_plot_initial_s)
t_intermediate_used_s, T_plot_intermediate = nearest_snapshot(t_plot_intermediate_s)
t_steady_used_s, T_plot_steady = nearest_snapshot(t_plot_steady_s)

# Shared colour scale from the three selected fields.
T_color_min = min(
    float(np.nanmin(T_plot_initial[is_active])),
    float(np.nanmin(T_plot_intermediate[is_active])),
    float(np.nanmin(T_plot_steady[is_active])),
)
T_color_max = max(
    float(np.nanmax(T_plot_initial[is_active])),
    float(np.nanmax(T_plot_intermediate[is_active])),
    float(np.nanmax(T_plot_steady[is_active])),
)
if abs(T_color_max - T_color_min) < 1.0e-6:
    T_color_min -= 0.5
    T_color_max += 0.5


# =============================================================================
# 11. Plot creation
# =============================================================================
#
# Each figure shows a full-diameter cut: the negative-radius half is a
# visual mirror of the axisymmetric solution, not an independently computed
# field.

z_cm_faces = z_face * 100.0
r_mm_faces = r_face * 1000.0
Z_cm, R_pos_mm = np.meshgrid(z_cm_faces, r_mm_faces)
R_neg_mm = -R_pos_mm[::-1, :]

catheter_r_mm = catheter_outer_radius_m * 1000.0
interface_r_mm = tube_inner_radius_m * 1000.0
outer_r_mm = tube_outer_radius_m * 1000.0
z_active_start_cm = catheter_axial_start_m * 100.0
z_active_end_cm = catheter_active_end_m * 100.0
z_body_end_cm = catheter_body_end_m * 100.0
z_left_cm = 0.0
z_right_cm = tube_length_m * 100.0

colormap = "RdYlBu_r"

plot_jobs = [
    (
        T_plot_initial,
        t_initial_used_s,
        "Initial temperature distribution",
        "tube_with_catheter_initial.png",
    ),
    (
        T_plot_intermediate,
        t_intermediate_used_s,
        "Intermediate temperature distribution",
        "tube_with_catheter_intermediate.png",
    ),
    (
        T_plot_steady,
        t_steady_used_s,
        "Steady-state temperature distribution",
        "tube_with_catheter_steady.png",
    ),
]


def draw_geometry_overlays(ax):
    """Catheter body, active length, interfaces, outer wall."""
    ax.fill_between(
        [z_active_start_cm, z_body_end_cm],
        -catheter_r_mm,
        catheter_r_mm,
        color="0.82",
        zorder=4,
        label="Catheter body (not resolved)",
    )
    ax.fill_between(
        [z_active_start_cm, z_active_end_cm],
        -catheter_r_mm,
        catheter_r_mm,
        color="0.45",
        zorder=5,
        label="Active cooling length",
    )
    ax.plot(
        [z_active_start_cm, z_body_end_cm],
        [catheter_r_mm, catheter_r_mm],
        color="k",
        linewidth=1.2,
        zorder=6,
    )
    ax.plot(
        [z_active_start_cm, z_body_end_cm],
        [-catheter_r_mm, -catheter_r_mm],
        color="k",
        linewidth=1.2,
        zorder=6,
    )
    ax.plot(
        [z_body_end_cm, z_body_end_cm],
        [-catheter_r_mm, catheter_r_mm],
        color="k",
        linewidth=1.2,
        zorder=6,
    )
    ax.plot(
        [z_left_cm, z_right_cm],
        [interface_r_mm, interface_r_mm],
        color="k",
        linewidth=1.4,
        linestyle="--",
        zorder=6,
        label="Water–polymer interface",
    )
    ax.plot(
        [z_left_cm, z_right_cm],
        [-interface_r_mm, -interface_r_mm],
        color="k",
        linewidth=1.4,
        linestyle="--",
        zorder=6,
    )
    ax.plot(
        [z_left_cm, z_right_cm],
        [outer_r_mm, outer_r_mm],
        color="k",
        linewidth=1.6,
        zorder=6,
        label="Outer tube wall",
    )
    ax.plot(
        [z_left_cm, z_right_cm],
        [-outer_r_mm, -outer_r_mm],
        color="k",
        linewidth=1.6,
        zorder=6,
    )
    ax.axvline(z_active_end_cm, color="k", linewidth=1.0, linestyle=":", zorder=6)
    ax.axvline(z_body_end_cm, color="k", linewidth=1.0, linestyle=":", zorder=6)

    # Measuring points (shown on both sides of the mirrored cut).
    # Measuring points, shown once on the +r side of each time snapshot.
    ax.plot(
        probe_1_z_used_m * 100.0,
        probe_1_r_used_m * 1000.0,
        marker="o",
        markersize=8,
        markerfacecolor="white",
        markeredgecolor="black",
        markeredgewidth=1.2,
        linestyle="None",
        zorder=8,
        label="P1 body tip",
    )
    ax.plot(
        probe_2_z_used_m * 100.0,
        probe_2_r_used_m * 1000.0,
        marker="s",
        markersize=8,
        markerfacecolor="yellow",
        markeredgecolor="black",
        markeredgewidth=1.2,
        linestyle="None",
        zorder=8,
        label="P2 cooling zone, +3 mm",
    )


saved_plot_paths = []
for T_plot, t_plot, title_prefix, filename in plot_jobs:
    fig, ax = plt.subplots(figsize=(14.0, 5.8))

    T_pos = T_plot.copy()
    T_pos[is_blocked] = np.nan
    T_neg = T_pos[::-1, :]

    mesh_pos = ax.pcolormesh(
        Z_cm,
        R_pos_mm,
        T_pos,
        cmap=colormap,
        vmin=T_color_min,
        vmax=T_color_max,
        shading="flat",
        zorder=1,
    )
    ax.pcolormesh(
        Z_cm,
        R_neg_mm,
        T_neg,
        cmap=colormap,
        vmin=T_color_min,
        vmax=T_color_max,
        shading="flat",
        zorder=1,
    )

    draw_geometry_overlays(ax)

    colorbar = fig.colorbar(mesh_pos, ax=ax, pad=0.02)
    colorbar.set_label("Temperature (°C)")
    colorbar.set_ticks(np.linspace(T_color_min, T_color_max, 6))

    ax.set_xlabel("Axial position (cm)")
    ax.set_ylabel("Radial position (mm)")
    ax.set_title(f"{title_prefix}  —  t = {t_plot:.1f} s")
    ax.set_xlim(z_left_cm, z_right_cm)
    ax.set_ylim(-outer_r_mm * 1.08, outer_r_mm * 1.08)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.92)
    ax.text(
        0.01,
        0.02,
        "Negative radius is a visual mirror of the axisymmetric solution.",
        transform=ax.transAxes,
        fontsize=8,
        va="bottom",
    )
    fig.tight_layout()

    plot_path = OUTPUT_DIRECTORY / filename
    if SAVE_PLOTS:
        fig.savefig(plot_path, dpi=160)
        saved_plot_paths.append(plot_path)
        print(f"Saved plot: {plot_path}")
    if not SHOW_PLOTS:
        plt.close(fig)


# Time history at the two measuring points.
fig_probe, ax_probe = plt.subplots(figsize=(8.5, 5.0))
ax_probe.plot(
    probe_times_s,
    probe_1_history_C,
    color="0.15",
    linewidth=2.0,
    marker="o",
    markevery=max(len(probe_times_s) // 12, 1),
    markerfacecolor="white",
    markeredgecolor="black",
    label=(
        f"P1 body tip  "
        f"(z = {probe_1_z_used_m*100:.2f} cm, r = {probe_1_r_used_m*1000:.2f} mm)"
    ),
)
ax_probe.plot(
    probe_times_s,
    probe_2_history_C,
    color="darkgoldenrod",
    linewidth=2.0,
    marker="s",
    markevery=max(len(probe_times_s) // 12, 1),
    markerfacecolor="yellow",
    markeredgecolor="black",
    label=(
        f"P2 cooling zone +{SENSOR_OFFSET_FROM_CATHETER_MM:.1f} mm  "
        f"(z = {probe_2_z_used_m*100:.2f} cm, r = {probe_2_r_used_m*1000:.2f} mm)"
    ),
)
ax_probe.set_xlabel("Time (s)")
ax_probe.set_ylabel("Temperature (°C)")
ax_probe.set_title("Estimated water temperature at the measuring points")
ax_probe.set_xlim(0.0, probe_times_s[-1])
ax_probe.grid(True, alpha=0.3)
ax_probe.legend(loc="best", fontsize=8, framealpha=0.92)
fig_probe.tight_layout()
probe_plot_path = OUTPUT_DIRECTORY / "tube_with_catheter_probe_temps.png"
if SAVE_PLOTS:
    fig_probe.savefig(probe_plot_path, dpi=160)
    saved_plot_paths.append(probe_plot_path)
    print(f"Saved plot: {probe_plot_path}")
if not SHOW_PLOTS:
    plt.close(fig_probe)


# =============================================================================
# 12. Printed summary
# =============================================================================

water_volume_m3 = float(cell_volume_m3[is_water_2d].sum())
water_mass_kg = rho_water * water_volume_m3

water_volume_analytic_m3 = (
    math.pi * (tube_inner_radius_m ** 2 - catheter_outer_radius_m ** 2)
    * catheter_body_end_m
    + math.pi * tube_inner_radius_m ** 2 * (tube_length_m - catheter_body_end_m)
)


def volume_average_water_C(T_field):
    return float(
        np.sum(T_field[is_water_2d] * cell_volume_m3[is_water_2d])
        / np.sum(cell_volume_m3[is_water_2d])
    )


T_water_initial_avg = volume_average_water_C(T_initial)
T_water_final_avg = volume_average_water_C(T_final)
T_water_final_min = float(T_final[is_water_2d].min())
T_water_final_max = float(T_final[is_water_2d].max())
T_domain_min = float(T_final[is_active].min())
T_domain_max = float(T_final[is_active].max())
T_run_min = min(float(field[is_active].min()) for field in snapshot_fields)
T_run_max = max(float(field[is_active].max()) for field in snapshot_fields)

# Recompute final heat rates from T_final for the printed energy numbers.
T_coolant_final = coolant_temperature_along_catheter(T_final[i_annulus_water, :])
Q_catheter_final_W = float(
    np.sum(G_catheter_j * (T_final[i_annulus_water, :] - T_coolant_final))
)
Q_external_final_W = float(np.sum(G_outer * (T_external - T_final[-1, :])))
Q_ends_final_W = float(
    np.sum(G_end_left * (T_external - T_final[:, 0]))
    + np.sum(G_end_right * (T_external - T_final[:, -1]))
)

energy_initial_J = float(np.sum(heat_capacity_J_PER_K[is_active] * T_initial[is_active]))
energy_final_J = float(np.sum(heat_capacity_J_PER_K[is_active] * T_final[is_active]))
energy_change_J = energy_final_J - energy_initial_J
energy_from_boundaries_J = (
    heat_from_external_J + heat_from_ends_J - heat_to_catheter_J
)
energy_balance_error_J = energy_change_J - energy_from_boundaries_J
energy_scale_J = max(
    abs(heat_to_catheter_J),
    abs(heat_from_external_J),
    abs(energy_change_J),
    1.0,
)
energy_balance_relative = energy_balance_error_J / energy_scale_J

print()
print("=" * 72)
print("NUMERICAL SUMMARY")
print("=" * 72)
print(f"Internal water volume                 : {water_volume_m3 * 1.0e6:.3f} mL")
print(f"Internal water mass                   : {water_mass_kg:.4f} kg")
print(f"Effective catheter conductance        : {G_catheter:.4f} W/K")
print(f"Integrated G along active length      : {G_catheter_integrated:.4f} W/K")
print(f"Initial volume-averaged water T       : {T_water_initial_avg:.4f} °C")
print(f"Final volume-averaged water T         : {T_water_final_avg:.4f} °C")
print(f"Minimum steady-state water T          : {T_water_final_min:.4f} °C")
print(f"Maximum steady-state water T          : {T_water_final_max:.4f} °C")
print(
    f"P1 body tip                            : "
    f"z = {probe_1_z_used_m*100:.2f} cm, r = {probe_1_r_used_m*1000:.2f} mm, "
    f"T(t=0) = {probe_1_history_C[0]:.3f} °C, "
    f"T(final) = {probe_1_history_C[-1]:.3f} °C"
)
print(
    f"P2 cooling zone +{SENSOR_OFFSET_FROM_CATHETER_MM:.0f} mm             : "
    f"z = {probe_2_z_used_m*100:.2f} cm, r = {probe_2_r_used_m*1000:.2f} mm, "
    f"T(t=0) = {probe_2_history_C[0]:.3f} °C, "
    f"T(final) = {probe_2_history_C[-1]:.3f} °C"
)
if steady_state_reached:
    print(f"Steady-state time                     : {time_to_steady_state_s:.1f} s")
else:
    print(
        f"Steady-state time                     : not reached "
        f"(stopped at {time_to_steady_state_s:.1f} s)"
    )
print(f"Final catheter heat-removal rate      : {Q_catheter_final_W:.4f} W")
print(f"Final heat entering through wall      : {Q_external_final_W:.4f} W")
print(f"Final heat entering through ends      : {Q_ends_final_W:.4f} W")
print(f"Energy-balance error                  : {energy_balance_error_J:.4e} J")
print(f"Energy-balance relative error         : {energy_balance_relative:.4e}")
print()

print("-" * 72)
print("VALIDATION CHECKS (this run)")
print("-" * 72)

check_1 = (
    abs(T_water_initial_avg - WATER_INITIAL_TEMPERATURE_C) < 1.0e-9
    and abs(float(T_initial[is_polymer_2d].mean()) - POLYMER_INITIAL_TEMPERATURE_C) < 1.0e-9
)
check_2 = True   # T_external is imposed and never updated
check_3 = Q_catheter_first_step_W is not None and Q_catheter_first_step_W > 0.0
check_4 = T_run_min >= T_coolant_inlet - 0.05
check_5 = T_run_max <= T_external + 0.05
check_6 = abs(G_catheter_integrated - G_catheter) < 1.0e-9 * max(G_catheter, 1.0)
check_7 = abs(energy_balance_relative) < 1.0e-6
check_8 = steady_state_reached

print(f"  1. Initial water and polymer T are 36 °C          : {'PASS' if check_1 else 'FAIL'}")
print(f"  2. External water remains exactly 36 °C           : {'PASS' if check_2 else 'FAIL'} (imposed reservoir)")
print(f"  3. Catheter removes heat while water is warmer    : {'PASS' if check_3 else 'FAIL'} ({Q_catheter_first_step_W:.4f} W at first step)")
print(f"  4. No T below coolant inlet temperature           : {'PASS' if check_4 else 'FAIL'} (min {T_run_min:.4f} °C)")
print(f"  5. No T above 36 °C under these conditions        : {'PASS' if check_5 else 'FAIL'} (max {T_run_max:.4f} °C)")
print(f"  6. Integrated catheter conductance equals G       : {'PASS' if check_6 else 'FAIL'}")
print(f"  7. Domain energy matches wall minus catheter heat : {'PASS' if check_7 else 'FAIL'}")
print(f"  8. Final field meets the steady-state criterion   : {'PASS' if check_8 else 'FAIL'}")
print()
print("Checks that require a second run (change a parameter and re-execute):")
print("  9.  Halve the grid spacing and time step; mean water T should change little.")
print("  10. Set G_CATHETER_W_PER_K = 0; the whole domain should stay at 36 °C.")
print("  11. Set CATHETER_COOLANT_INLET_TEMPERATURE_C = 36; there should be no net cooling.")
print("  12. Increase G_CATHETER_W_PER_K; the internal-water temperature should fall.")
print("  13. Increase POLYMER_THERMAL_CONDUCTIVITY_W_M_K; wall heat gain should rise.")
print("=" * 72)
print()


# =============================================================================
# 13. Model limitations
# =============================================================================

limitations_text = """
MAIN LIMITATIONS
----------------
- The model is axisymmetric.  It does not resolve the two internal lumens
  or any other non-circular catheter cross-section.
- Those internal details are represented only by the effective catheter
  conductance G_catheter.
- Natural convection inside the tube is not resolved.  A conduction-only
  water region may underestimate radial and axial heat transport.  The
  optional effective water conductivity is only an approximate mixing model.
- Perfect mixing in the external container is represented by a constant
  36 °C boundary.  The bath, heater, and mixer are not modelled.
- Tube ends are insulated unless END_BOUNDARY_CONDITION is changed to
  "convection".
- Water and polymer properties are constant and, for the polymer, assumed
  handbook values for clear acrylic until measured data are supplied.
- Catheter thermal capacitance is neglected; the body is a blocked
  cylinder with cooling only on the active outer surface.  The 2 cm
  inactive body and the tip face are adiabatic.
- Past the catheter tip the water fills the centreline, so heat can
  wrap around the end by conduction, similar in kind to the radial
  side gradient.
- Accuracy is limited by the experimentally validated range of the
  catheter parameters, especially G_catheter, coolant flow, and inlet
  temperature.
""".strip()

print(limitations_text)
print()

if SHOW_PLOTS and "agg" not in plt.get_backend().lower():
    plt.show()
