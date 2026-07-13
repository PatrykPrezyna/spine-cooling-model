import math

# ============================================================
# DESIGN INPUTS
# ============================================================

INPUT_TEMP_C = 37.0          # Fluid inlet temperature [°C]
OUTPUT_TEMP_C = 0.0          # Target outlet temperature [°C]
PLATE_TEMP_C = -1.0          # Cooling plate temperature [°C]

FLOWRATE_ML_MIN = 80      # Flow rate [mL/min]

CHANNEL_GAP_MM = 10.0        # Internal fluid gap [mm]
WALL_THICKNESS_MM = 0.5      # Polypropylene wall thickness [mm]

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
# POLYPROPYLENE PROPERTIES
# ============================================================

PP_THERMAL_CONDUCTIVITY = 0.22     # W/(m·K)

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
# HEAT DUTY
# ============================================================

Q_required = (
    m_dot *
    FLUID_CP *
    (INPUT_TEMP_C - OUTPUT_TEMP_C)
)

# ============================================================
# ITERATIVE SOLUTION
# ============================================================
#
# Since geometry affects flow regime,
# and flow regime affects h_fluid and U,
# solve iteratively.
#
# Start with a guessed area.
#

A_required = 0.02

for _ in range(20):

    # Geometry from:
    # Area = 2 * Length * Height
    # Length = 2 * Height

    height_m = math.sqrt(A_required / 4.0)
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
        (wall / PP_THERMAL_CONDUCTIVITY) +
        (1.0 / H_PLATE)
    )

    # Update required heat-transfer area
    A_required = (
        m_dot *
        FLUID_CP /
        U
    ) * math.log(
        (INPUT_TEMP_C - PLATE_TEMP_C) /
        (OUTPUT_TEMP_C - PLATE_TEMP_C)
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
print("CARTRIDGE COOLING MODEL")
print("=" * 60)

print("\nTEMPERATURES")
print("-" * 60)
print(f"Inlet temperature        : {INPUT_TEMP_C:.1f} °C")
print(f"Outlet temperature       : {OUTPUT_TEMP_C:.1f} °C")
print(f"Plate temperature        : {PLATE_TEMP_C:.1f} °C")

print("\nFLOW")
print("-" * 60)
print(f"Flow rate                : {FLOWRATE_ML_MIN:.2f} mL/min")
print(f"Mass flow rate           : {m_dot:.6f} kg/s")
print(f"Velocity                 : {velocity:.6f} m/s")

print("\nTHERMAL")
print("-" * 60)
print(f"Cooling duty             : {Q_required:.2f} W")
print(f"Fluid h                 : {h_fluid:.1f} W/m²K")
print(f"Overall U               : {U:.1f} W/m²K")
print(f"Required heat area      : {A_required:.4f} m²")

print("\nFLOW REGIME")
print("-" * 60)
print(f"Hydraulic diameter       : {hydraulic_diameter*1000:.2f} mm")
print(f"Reynolds number          : {Re:.1f}")
print(f"Prandtl number           : {Pr:.2f}")
print(f"Nusselt number           : {Nu:.2f}")
print(f"Flow regime              : {flow_regime}")

print("\nGEOMETRY")
print("-" * 60)
print(f"Length                  : {length_m*1000:.1f} mm")
print(f"Height                  : {height_m*1000:.1f} mm")
print(f"Thickness               : {thickness_m*1000:.1f} mm")
print(f"Aspect ratio (L/H)      : {length_m/height_m:.2f}")

print("\nINTERNALS")
print("-" * 60)
print(f"Internal volume         : {volume_ml:.1f} mL")
print(f"Residence time          : {residence_time_s:.1f} s")

print("\n" + "=" * 60)