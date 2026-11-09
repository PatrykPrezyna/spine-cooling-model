import math

# ============================================================
# DESIGN INPUTS
# ============================================================

FLOWRATE_ML_MIN = 80

CHANNEL_GAP_MM = 10.0
WALL_THICKNESS_MM = 0.05

# Geometry from thermal model
LENGTH_MM = 200.0
HEIGHT_MM = 100.0

# ============================================================
# FLUID PROPERTIES
# ============================================================

FLUID_DENSITY = 1000.0       # kg/m³
FLUID_VISCOSITY = 0.001      # Pa.s

# ============================================================
# UNIT CONVERSIONS
# ============================================================

flow_m3_s = FLOWRATE_ML_MIN * 1e-6 / 60.0

gap = CHANNEL_GAP_MM / 1000.0
height = HEIGHT_MM / 1000.0
length = LENGTH_MM / 1000.0

# ============================================================
# FLOW AREA
# ============================================================

flow_area = height * gap

velocity = flow_m3_s / flow_area

# ============================================================
# HYDRAULIC DIAMETER
# ============================================================

hydraulic_diameter = (
    2.0 * height * gap /
    (height + gap)
)

# ============================================================
# REYNOLDS NUMBER
# ============================================================

Re = (
    FLUID_DENSITY *
    velocity *
    hydraulic_diameter /
    FLUID_VISCOSITY
)

# ============================================================
# FRICTION FACTOR
# ============================================================

if Re < 2300:
    flow_regime = "Laminar"
    friction_factor = 64.0 / Re

elif Re < 4000:
    flow_regime = "Transitional"
    friction_factor = 0.3164 / (2300 ** 0.25)

else:
    flow_regime = "Turbulent"
    friction_factor = 0.3164 / (Re ** 0.25)

# ============================================================
# DARCY-WEISBACH PRESSURE DROP
# ============================================================

pressure_drop_pa = (
    friction_factor *
    (length / hydraulic_diameter) *
    (FLUID_DENSITY * velocity**2 / 2.0)
)

pressure_drop_kpa = pressure_drop_pa / 1000.0
pressure_drop_bar = pressure_drop_pa / 100000.0
pressure_drop_psi = pressure_drop_pa / 6894.76

# ============================================================
# RESIDENCE TIME
# ============================================================

volume_m3 = length * height * gap
residence_time_s = volume_m3 / flow_m3_s

# ============================================================
# RESULTS
# ============================================================

print("\n")
print("=" * 60)
print("CARTRIDGE PRESSURE DROP MODEL")
print("=" * 60)

print("\nGEOMETRY")
print("-" * 60)
print(f"Length               : {LENGTH_MM:.1f} mm")
print(f"Height               : {HEIGHT_MM:.1f} mm")
print(f"Gap                  : {CHANNEL_GAP_MM:.1f} mm")

print("\nFLOW")
print("-" * 60)
print(f"Flow rate            : {FLOWRATE_ML_MIN:.2f} mL/min")
print(f"Velocity             : {velocity:.6f} m/s")

print("\nHYDRAULICS")
print("-" * 60)
print(f"Hydraulic diameter   : {hydraulic_diameter*1000:.2f} mm")
print(f"Reynolds number      : {Re:.1f}")
print(f"Flow regime          : {flow_regime}")
print(f"Friction factor      : {friction_factor:.4f}")

print("\nPRESSURE DROP")
print("-" * 60)
print(f"Pressure drop        : {pressure_drop_pa:.2f} Pa")
print(f"Pressure drop        : {pressure_drop_kpa:.5f} kPa")
print(f"Pressure drop        : {pressure_drop_bar:.6f} bar")
print(f"Pressure drop        : {pressure_drop_psi:.6f} psi")

print("\nOTHER")
print("-" * 60)
print(f"Residence time       : {residence_time_s:.1f} s")

print("\n" + "=" * 60)