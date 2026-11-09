import json
import math
from datetime import datetime, timezone
from pathlib import Path

# ============================================================
# SCRIPT / EXPERIMENT METADATA
# ============================================================

SCRIPT_VERSION = "1.1.0"
EXPERIMENT_NUMBER = 2

# ============================================================
# VALIDATION INPUTS
# ============================================================

INPUT_TEMP_C = 17.7          # Fluid inlet temperature [°C]
ACTUAL_OUTPUT_TEMP_C = 15.5   # Measured outlet temperature [°C]
PLATE_TEMP_C = 0.0          # Cooling plate temperature [°C]

FLOWRATE_ML_MIN = 93.9         # Flow rate [mL/min]

# Known cartridge heat-transfer surface (both faces)
SURFACE_AREA_M2 = 0.006724       # m² 82mmx82mm=0.006724m²

CHANNEL_GAP_MM = 10.0        # Internal fluid gap [mm]
WALL_THICKNESS_MM = 1.0      # Wall thickness [mm]

# Geometric constraint:
# Length = ASPECT_RATIO × Height
ASPECT_RATIO = 2.0

# ============================================================
# FLUID PROPERTIES (Water-like)
# ============================================================

FLUID_DENSITY = 1000.0       # kg/m³
FLUID_CP = 4180.0            # J/(kg·K)
FLUID_VISCOSITY = 0.001      # Pa·s
FLUID_THERMAL_CONDUCTIVITY = 0.60  # W/(m·K)

# ============================================================
# WALL MATERIAL PROPERTIES
# ============================================================

WALL_MATERIAL_NAME = "Clear Resin V5"            # Label only (e.g. PP, Al, stainless)
WALL_THERMAL_CONDUCTIVITY = 0.54     # W/(m·K)

# ============================================================
# HEAT TRANSFER ASSUMPTIONS
# ============================================================

# Plate side convection coefficient
H_PLATE = 5000.0             # W/(m²·K)

# ============================================================
# CONVERSIONS
# ============================================================

gap = CHANNEL_GAP_MM / 1000.0
wall = WALL_THICKNESS_MM / 1000.0

# Total cartridge thickness
thickness_m = gap + 2.0 * wall

# Flow conversion
flow_m3_s = FLOWRATE_ML_MIN * 1e-6 / 60.0
m_dot = FLUID_DENSITY * flow_m3_s

# ============================================================
# GEOMETRY FROM SURFACE AREA
# ============================================================
#
# Area = 2 * Length * Height
# Length = ASPECT_RATIO * Height
#

height_m = math.sqrt(SURFACE_AREA_M2 / (2.0 * ASPECT_RATIO))
length_m = ASPECT_RATIO * height_m

# Flow calculations
flow_area = height_m * gap

velocity = flow_m3_s / flow_area

hydraulic_diameter = (
    2.0 * height_m * gap /
    (height_m + gap)
)

Re = (
    FLUID_DENSITY
    * velocity
    * hydraulic_diameter
    / FLUID_VISCOSITY
)

# Water Prandtl number (approx.)
Pr = (
    FLUID_CP *
    FLUID_VISCOSITY /
    FLUID_THERMAL_CONDUCTIVITY
)

# Nusselt number
if Re < 2300:
    flow_regime = "Laminar"

    # Fully developed laminar approximation
    Nu = 7.54

elif Re < 4000:
    flow_regime = "Transitional"

    Nu = 15.0

else:
    flow_regime = "Turbulent"

    Nu = (
        0.023 *
        Re**0.8 *
        Pr**0.4
    )

# Fluid-side heat transfer coefficient
h_fluid = (
    Nu *
    FLUID_THERMAL_CONDUCTIVITY /
    hydraulic_diameter
)

# Overall heat transfer coefficient
U = 1.0 / (
    (1.0 / h_fluid) +
    (wall / WALL_THERMAL_CONDUCTIVITY) +
    (1.0 / H_PLATE)
)

# ============================================================
# PREDICTED OUTLET TEMPERATURE
# ============================================================
#
# Exponential cooling (constant plate temperature):
# Tout = Tplate + (Tin - Tplate) * exp(-U A / (m Cp))
#

NTU = U * SURFACE_AREA_M2 / (m_dot * FLUID_CP)

PREDICTED_OUTPUT_TEMP_C = (
    PLATE_TEMP_C
    + (INPUT_TEMP_C - PLATE_TEMP_C) * math.exp(-NTU)
)

# ============================================================
# MEASURED vs PREDICTED DUTY
# ============================================================

Q_actual = (
    m_dot *
    FLUID_CP *
    (INPUT_TEMP_C - ACTUAL_OUTPUT_TEMP_C)
)

Q_predicted = (
    m_dot *
    FLUID_CP *
    (INPUT_TEMP_C - PREDICTED_OUTPUT_TEMP_C)
)

outlet_error_C = PREDICTED_OUTPUT_TEMP_C - ACTUAL_OUTPUT_TEMP_C
outlet_error_pct = (
    100.0 * outlet_error_C / (INPUT_TEMP_C - ACTUAL_OUTPUT_TEMP_C)
    if INPUT_TEMP_C != ACTUAL_OUTPUT_TEMP_C
    else float("nan")
)

# ============================================================
# FINAL CALCULATIONS
# ============================================================

volume_m3 = length_m * height_m * gap
volume_ml = volume_m3 * 1e6

residence_time_s = volume_m3 / flow_m3_s

# ============================================================
# RESULTS
# ============================================================

print("\n")
print("=" * 60)
print("CARTRIDGE COOLING MODEL - VALIDATION")
print(f"Script version           : {SCRIPT_VERSION}")
print(f"Experiment number        : {EXPERIMENT_NUMBER}")
print("=" * 60)

print("\nTEMPERATURES")
print("-" * 60)
print(f"Inlet temperature        : {INPUT_TEMP_C:.1f} °C")
print(f"Plate temperature        : {PLATE_TEMP_C:.1f} °C")
print(f"Predicted outlet         : {PREDICTED_OUTPUT_TEMP_C:.2f} °C")
print(f"Actual outlet            : {ACTUAL_OUTPUT_TEMP_C:.2f} °C")
print(f"Outlet error (pred-act)  : {outlet_error_C:+.2f} °C")
print(f"Outlet error             : {outlet_error_pct:+.1f} % of measured dT")

print("\nFLOW")
print("-" * 60)
print(f"Flow rate                : {FLOWRATE_ML_MIN:.2f} mL/min")
print(f"Mass flow rate           : {m_dot:.6f} kg/s")
print(f"Velocity                 : {velocity:.6f} m/s")

print("\nTHERMAL")
print("-" * 60)
print(f"Wall material            : {WALL_MATERIAL_NAME}")
print(f"Wall k                   : {WALL_THERMAL_CONDUCTIVITY:.3f} W/mK")
print(f"Measured cooling duty    : {Q_actual:.2f} W")
print(f"Predicted cooling duty   : {Q_predicted:.2f} W")
print(f"Fluid h                  : {h_fluid:.1f} W/m²K")
print(f"Overall U                : {U:.1f} W/m²K")
print(f"NTU                      : {NTU:.3f}")
print(f"Surface area (input)     : {SURFACE_AREA_M2:.4f} m²")

print("\nFLOW REGIME")
print("-" * 60)
print(f"Hydraulic diameter       : {hydraulic_diameter*1000:.2f} mm")
print(f"Reynolds number          : {Re:.1f}")
print(f"Prandtl number           : {Pr:.2f}")
print(f"Nusselt number           : {Nu:.2f}")
print(f"Flow regime              : {flow_regime}")

print("\nGEOMETRY")
print("-" * 60)
print(f"Length                   : {length_m*1000:.1f} mm")
print(f"Height                   : {height_m*1000:.1f} mm")
print(f"Thickness                : {thickness_m*1000:.1f} mm")
print(f"Aspect ratio (L/H)       : {length_m/height_m:.2f}")

print("\nINTERNALS")
print("-" * 60)
print(f"Internal volume          : {volume_ml:.1f} mL")
print(f"Residence time           : {residence_time_s:.1f} s")

print("\n" + "=" * 60)

# ============================================================
# JSON OUTPUT
# ============================================================

def _json_number(value):
    """Convert floats for JSON (NaN/Inf -> None)."""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


results = {
    "script_version": SCRIPT_VERSION,
    "experiment_number": EXPERIMENT_NUMBER,
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "inputs": {
        "input_temp_C": INPUT_TEMP_C,
        "actual_output_temp_C": ACTUAL_OUTPUT_TEMP_C,
        "plate_temp_C": PLATE_TEMP_C,
        "flowrate_mL_min": FLOWRATE_ML_MIN,
        "surface_area_m2": SURFACE_AREA_M2,
        "channel_gap_mm": CHANNEL_GAP_MM,
        "wall_thickness_mm": WALL_THICKNESS_MM,
        "aspect_ratio": ASPECT_RATIO,
        "h_plate_W_m2K": H_PLATE,
        "fluid": {
            "density_kg_m3": FLUID_DENSITY,
            "cp_J_kgK": FLUID_CP,
            "viscosity_Pa_s": FLUID_VISCOSITY,
            "thermal_conductivity_W_mK": FLUID_THERMAL_CONDUCTIVITY,
        },
        "wall_material": {
            "name": WALL_MATERIAL_NAME,
            "thermal_conductivity_W_mK": WALL_THERMAL_CONDUCTIVITY,
        },
    },
    "results": {
        "temperatures": {
            "predicted_output_temp_C": PREDICTED_OUTPUT_TEMP_C,
            "actual_output_temp_C": ACTUAL_OUTPUT_TEMP_C,
            "outlet_error_C": outlet_error_C,
            "outlet_error_pct_of_measured_dT": _json_number(outlet_error_pct),
        },
        "flow": {
            "mass_flow_kg_s": m_dot,
            "velocity_m_s": velocity,
        },
        "thermal": {
            "measured_cooling_duty_W": Q_actual,
            "predicted_cooling_duty_W": Q_predicted,
            "h_fluid_W_m2K": h_fluid,
            "U_W_m2K": U,
            "NTU": NTU,
            "surface_area_m2": SURFACE_AREA_M2,
        },
        "flow_regime": {
            "hydraulic_diameter_mm": hydraulic_diameter * 1000.0,
            "Reynolds": Re,
            "Prandtl": Pr,
            "Nusselt": Nu,
            "regime": flow_regime,
        },
        "geometry": {
            "length_mm": length_m * 1000.0,
            "height_mm": height_m * 1000.0,
            "thickness_mm": thickness_m * 1000.0,
            "aspect_ratio": length_m / height_m,
        },
        "internals": {
            "volume_mL": volume_ml,
            "residence_time_s": residence_time_s,
        },
    },
}

output_dir = Path(__file__).resolve().parent / "outputs"
output_dir.mkdir(exist_ok=True)

output_path = (
    output_dir
    / f"cartrige_model_exp{EXPERIMENT_NUMBER}_v{SCRIPT_VERSION}.json"
)

with output_path.open("w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print(f"\nJSON written to: {output_path}")
print("=" * 60)
