import math

# ============================================================
# DESIGN INPUTS
# ============================================================

INPUT_TEMP_C = 17.7          # Fluid inlet temperature [°C]
BATH_TEMP_C = 0.0            # Cold-water bath temperature [°C]
FLOWRATE_ML_MIN = 46.9       # Flow rate [mL/min]

LENGTH_MM = 82.0             # Flow-direction length [mm]
HEIGHT_MM = 82.0             # Cross-flow height [mm]
CHANNEL_GAP_MM = 10.0        # Internal fluid gap [mm]
WALL_THICKNESS_MM = 1.0      # Wall thickness (one side) [mm]

# ============================================================
# FLUID PROPERTIES (Water-like, channel fluid)
# ============================================================

FLUID_DENSITY = 1000.0       # kg/m³
FLUID_CP = 4180.0            # J/(kg·K)
FLUID_VISCOSITY = 0.001      # Pa·s
FLUID_THERMAL_CONDUCTIVITY = 0.60  # W/(m·K)

# ============================================================
# WALL / BATH
# ============================================================
# Cartridge immersed in cold water (no metal cooling plate).
# Outer resistance is water-side convection, not plate contact.

WALL_THERMAL_CONDUCTIVITY = 0.54  # W/(m·K)  Clear Resin V5
H_BATH = 500.0                    # W/(m²·K) bath-side convection
# ~200–1000 typical for immersion; use higher if bath is stirred

# ============================================================
# UNIT CONVERSIONS
# ============================================================

length = LENGTH_MM / 1000.0
height = HEIGHT_MM / 1000.0
gap = CHANNEL_GAP_MM / 1000.0
wall = WALL_THICKNESS_MM / 1000.0

flow_m3_s = FLOWRATE_ML_MIN * 1e-6 / 60.0
m_dot = FLUID_DENSITY * flow_m3_s

# Both faces exposed to bath
surface_area = 2.0 * length * height

# ============================================================
# FLOW / HEAT TRANSFER (channel side)
# ============================================================

flow_area = height * gap
velocity = flow_m3_s / flow_area

hydraulic_diameter = 2.0 * height * gap / (height + gap)

Re = FLUID_DENSITY * velocity * hydraulic_diameter / FLUID_VISCOSITY
Pr = FLUID_CP * FLUID_VISCOSITY / FLUID_THERMAL_CONDUCTIVITY

if Re < 2300:
    flow_regime = "Laminar"
    Nu = 7.54
elif Re < 4000:
    flow_regime = "Transitional"
    Nu = 15.0
else:
    flow_regime = "Turbulent"
    Nu = 0.023 * Re**0.8 * Pr**0.4

h_fluid = Nu * FLUID_THERMAL_CONDUCTIVITY / hydraulic_diameter

# 1/U = 1/h_fluid + wall/k_wall + 1/h_bath
U = 1.0 / (
    (1.0 / h_fluid)
    + (wall / WALL_THERMAL_CONDUCTIVITY)
    + (1.0 / H_BATH)
)

# ============================================================
# OUTLET TEMPERATURE
# ============================================================
#
# Constant bath temperature (effectiveness-NTU):
#   Tout = Tbath + (Tin - Tbath) * exp(-UA / (m Cp))
#

NTU = U * surface_area / (m_dot * FLUID_CP)

PREDICTED_OUTPUT_TEMP_C = (
    BATH_TEMP_C
    + (INPUT_TEMP_C - BATH_TEMP_C) * math.exp(-NTU)
)

cooling_duty_W = m_dot * FLUID_CP * (INPUT_TEMP_C - PREDICTED_OUTPUT_TEMP_C)

# ============================================================
# RESULTS
# ============================================================

print("\n")
print("=" * 60)
print("CARTRIDGE OUTLET TEMPERATURE PREDICTION (BATH)")
print("=" * 60)

print("\nINPUTS")
print("-" * 60)
print(f"Inlet temperature    : {INPUT_TEMP_C:.1f} °C")
print(f"Bath temperature     : {BATH_TEMP_C:.1f} °C")
print(f"Flow rate            : {FLOWRATE_ML_MIN:.2f} mL/min")

print("\nPREDICTION")
print("-" * 60)
print(f"Predicted outlet     : {PREDICTED_OUTPUT_TEMP_C:.2f} °C")
print(f"Delta T (in - out)   : {INPUT_TEMP_C - PREDICTED_OUTPUT_TEMP_C:.2f} °C")
print(f"Cooling duty         : {cooling_duty_W:.2f} W")

print("\nTHERMAL")
print("-" * 60)
print(f"Surface area         : {surface_area:.4f} m²")
print(f"Fluid h (channel)    : {h_fluid:.1f} W/m²K")
print(f"Bath h               : {H_BATH:.1f} W/m²K")
print(f"Overall U            : {U:.1f} W/m²K")
print(f"NTU                  : {NTU:.3f}")

print("\nFLOW")
print("-" * 60)
print(f"Velocity             : {velocity:.6f} m/s")
print(f"Hydraulic diameter   : {hydraulic_diameter * 1000:.2f} mm")
print(f"Reynolds number      : {Re:.1f}")
print(f"Nusselt number       : {Nu:.2f}")
print(f"Flow regime          : {flow_regime}")

print("\n" + "=" * 60)
