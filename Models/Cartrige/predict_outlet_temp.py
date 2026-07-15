import math

# ============================================================
# DESIGN INPUTS
# -------------
# Model cartridge v0 as a long straight tube in a fixed temp
# bath. Tube adjacency due to torturous-path geometry is
# is handled by an 'effective area' generated from the model
# in Fusion360. (0.01632 m^2, ~88% of bare, straight cylinder)
# ============================================================

INPUT_TEMP_C = 17.7          # Fluid inlet temperature [°C]
BATH_TEMP_C = 0.0            # Cold-water bath temperature [°C]
FLOWRATE_ML_MIN = 46.9       # Flow rate [mL/min]

# Tube geometry
INNER_DIAMETER_MM = 9.0   # mm
OUTER_DIAMETER_MM = 11.0  # mm
LENGTH_M = 0.590  # m   (total path length)

A_CYLINDER = math.pi * (OUTER_DIAMETER_MM / 1000) * LENGTH_M
A_FUSION = 0.01632 # m^2

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

WALL_THERMAL_CONDUCTIVITY = 0.54  # W/(m·K)  Clear Resin V5 (https://formlabs.com/support/Thermal-properties-of-selected-Formlabs-SLA-resins/?language=en_US)
H_BATH = 500.0                    # W/(m²·K) bath-side convection
# ~200–1000 typical for immersion; use higher if bath is stirred

# ============================================================
# UNIT CONVERSIONS
# ============================================================

D_i = INNER_DIAMETER_MM / 1000   # m
D_o = OUTER_DIAMETER_MM / 1000   # m
t_w = (D_o - D_i) / 2  # wall thickness per side, m

flow_m3_s = FLOWRATE_ML_MIN * 1e-6 / 60.0
m_dot = FLUID_DENSITY * flow_m3_s

# ============================================================
# FLOW / HEAT TRANSFER (channel side)
# ============================================================

flow_area = math.pi / 4 * D_i**2
velocity  = flow_m3_s / flow_area
 
Re = FLUID_DENSITY * velocity * D_i / FLUID_VISCOSITY
Pr = FLUID_CP * FLUID_VISCOSITY / FLUID_THERMAL_CONDUCTIVITY

# Graetz number on entry-length
Gz = (D_i / LENGTH_M) * Re * Pr

if Re < 2300:
    flow_regime = "Laminar"
    Nu_fd = 3.66  # fully-developed, constant wall temperature
    #
    # Gnielinski / Shah-London entry-length correction:
    #   Nu = 3.66 + [0.0668 * Gz] / [1 + 0.04 * Gz^(2/3)]
    #
    # when Gz is non-negligible (here Gz ~ 12 -> Nu ~ 4.3).
    # NOTE: laminar regime means that heat transfer in 
    # the cartridge is almost entirely conductive (not assuming
    # radial mixing, convection)
    #
    # same form as 2.75 paper eqn 4 where (D/L)*Re*Pr == Gz
    Nu = Nu_fd + (0.0668 * Gz) / (1 + 0.04 * Gz**(2/3))
elif Re < 4000:
    flow_regime = "Transitional"
    Nu = 15.0
else:
    flow_regime = "Turbulent"
    Nu = 0.023 * Re**0.8 * Pr**0.4

h_fluid = Nu * FLUID_THERMAL_CONDUCTIVITY / D_i

# 1/U = 1/h_fluid + wall/k_wall + 1/h_bath
U = 1.0 / (
    (1.0 / h_fluid)
    + (t_w / WALL_THERMAL_CONDUCTIVITY)
    + (1.0 / H_BATH)
)

# ============================================================
# OUTLET TEMPERATURE
# ============================================================
#
# Constant bath temperature (effectiveness-NTU):
#   Tout = Tbath + (Tin - Tbath) * exp(-UA / (m Cp))
#

results = {}
for label, A in [("Cylinder (bare, upper bound)", A_CYLINDER),
                 ("Fusion360 (primary)",           A_FUSION)]:
    NTU    = U * A / (m_dot * FLUID_CP)
    T_out  = BATH_TEMP_C + (INPUT_TEMP_C - BATH_TEMP_C) * math.exp(-NTU)
    Q_cool = m_dot * FLUID_CP * (INPUT_TEMP_C - T_out)
    results[label] = dict(A=A, NTU=NTU, T_out=T_out, Q_cool=Q_cool)

#TODO: wall thermal mass if lag in calorimetric data

# ============================================================
# RESULTS
# ============================================================
print("\n" + "=" * 60)
print("CARTRIDGE OUTLET TEMPERATURE PREDICTION")
print("=" * 60)
 
print("\nINPUTS")
print("-" * 60)
print(f"  Inlet temperature          : {INPUT_TEMP_C:.1f} degC")
print(f"  Bath temperature           : {BATH_TEMP_C:.1f} degC")
print(f"  Flow rate                  : {FLOWRATE_ML_MIN:.2f} mL/min")
print(f"  Tube inner diameter        : {INNER_DIAMETER_MM:.1f} mm")
print(f"  Tube outer diameter        : {OUTER_DIAMETER_MM:.1f} mm")
print(f"  Path length                : {LENGTH_M*1000:.0f} mm")
 
print("\nFLOW")
print("-" * 60)
print(f"  Velocity                   : {velocity*1000:.3f} mm/s")
print(f"  Reynolds number            : {Re:.1f}  ({flow_regime})")
print(f"  Prandtl number             : {Pr:.2f}")
print(f"  Graetz number (D/L*Re*Pr)  : {Gz:.3f}")
print(f"  Nu (entry-length corrected): {Nu:.3f}  [fd = {Nu_fd}]")
 
print("\nTHERMAL RESISTANCE  [m^2 K/W]")
print("-" * 60)
R_f = 1.0 / h_fluid
R_w = t_w / WALL_THERMAL_CONDUCTIVITY
R_b = 1.0 / H_BATH
R_tot = R_f + R_w + R_b
print(f"  R_fluid  (1/h_fluid)       : {R_f:.5f}   ({100*R_f/R_tot:.1f}%)")
print(f"  R_wall   (t_w / k_wall)    : {R_w:.5f}   ({100*R_w/R_tot:.1f}%)")
print(f"  R_bath   (1/h_bath)        : {R_b:.5f}   ({100*R_b/R_tot:.1f}%)")
print(f"  Overall U                  : {U:.2f} W/m^2K")
 
print("\nPREDICTED OUTLET")
print("-" * 60)
for label, r in results.items():
    print(f"\n  [{label}]")
    print(f"    A                        : {r['A']:.5f} m^2")
    print(f"    NTU                      : {r['NTU']:.4f}")
    print(f"    Predicted outlet         : {r['T_out']:.3f} degC")
    print(f"    DeltaT (in - out)        : {INPUT_TEMP_C - r['T_out']:.3f} K")
    print(f"    Cooling duty             : {r['Q_cool']:.3f} W")
    
print("\n" + "=" * 60)