"""
Transient thermal model of a dual-lumen cooling catheter (version 1).

Physical picture
----------------
A 30 cm catheter with two parallel 1 mm lumens is fully submerged in a large,
stirred water tank held at a constant 36 degC.  Cold water (5 degC) enters the
inlet lumen at the proximal end, flows 30 cm to the distal tip, turns around,
flows 30 cm back through the outlet lumen, and exits at the proximal end.
The model computes the proximal outlet temperature as a function of time.

Numerical approach
------------------
1-D axial discretization.  Each lumen is split into N segments.  Every axial
position also has one catheter-wall temperature node with thermal mass.
Heat path:  tank (constant 36 degC)  ->  catheter wall  ->  lumen water.
Because both lumens exchange heat with the *same* wall node at each axial
position, the wall also provides the thermal interaction between the two
neighbouring lumens.  Water transport uses first-order upwind advection with
explicit Euler time stepping.
"""

# ---------------------------------------------------------------------------
# 1. Imports
# ---------------------------------------------------------------------------
import numpy as np
import matplotlib
matplotlib.use("Agg")          # save the plot to a file (no display needed)
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# 2. User-configurable input values
# ---------------------------------------------------------------------------
catheter_length_cm     = 30.0   # length of the catheter (each lumen), cm
catheter_outer_diam_mm = 3.0    # outer diameter of the catheter, mm
lumen_inner_diam_mm    = 1.0    # inner diameter of EACH lumen, mm

inlet_temperature_C    = 5.0    # cold water entering the inlet lumen, degC
tank_temperature_C     = 36.0   # surrounding tank water (constant), degC
flow_rate_ml_per_min   = 60.0   # volumetric flow rate, mL/min

initial_water_temp_C   = 36.0   # water inside the catheter at t = 0, degC
initial_wall_temp_C    = 36.0   # catheter material at t = 0, degC

segments_per_lumen     = 30     # axial segments in each lumen
simulation_time_s      = 20.0   # total simulated time, s

# ---------------------------------------------------------------------------
# 3. Unit conversions (everything below is SI: m, kg, s, W, K)
# ---------------------------------------------------------------------------
L        = catheter_length_cm / 100.0            # catheter length, m
d_outer  = catheter_outer_diam_mm / 1000.0       # catheter outer diameter, m
d_lumen  = lumen_inner_diam_mm / 1000.0          # lumen inner diameter, m
Q_flow   = flow_rate_ml_per_min * 1e-6 / 60.0    # flow rate, m^3/s

T_inlet  = inlet_temperature_C                   # temperatures stay in degC;
T_tank   = tank_temperature_C                    # only DIFFERENCES enter the
T_water0 = initial_water_temp_C                  # equations, so degC == K here
T_wall0  = initial_wall_temp_C

# ---------------------------------------------------------------------------
# 4. Physical-property assumptions (all values are assumptions of this model)
# ---------------------------------------------------------------------------
rho_water = 1000.0    # water density, kg/m^3                       (assumed)
cp_water  = 4180.0    # water specific heat, J/(kg K)               (assumed)
k_water   = 0.60      # water thermal conductivity, W/(m K)         (assumed)
mu_water  = 1.0e-3    # water dynamic viscosity, Pa s               (assumed)

rho_wall  = 1100.0    # catheter material (polyurethane), kg/m^3    (assumed)
cp_wall   = 1800.0    # catheter material specific heat, J/(kg K)   (assumed)
k_wall    = 0.20      # catheter material conductivity, W/(m K)     (assumed)

# Convection on the OUTSIDE of the catheter: the tank is well mixed, so we
# assume mild forced/natural convection over a thin cylinder.
h_outside = 500.0     # external heat-transfer coefficient, W/(m^2 K) (assumed)

# Effective conduction path length through the catheter material between a
# lumen surface and the outer surface (half of ~1 mm of plastic).
wall_conduction_thickness = 0.5e-3   # m                            (assumed)

# ---------------------------------------------------------------------------
# 5. Geometry calculations
# ---------------------------------------------------------------------------
N  = segments_per_lumen
dx = L / N                                     # axial segment length, m

area_lumen      = np.pi / 4.0 * d_lumen**2     # flow area of one lumen, m^2
perim_lumen     = np.pi * d_lumen              # inner perimeter of one lumen, m
perim_outer     = np.pi * d_outer              # outer perimeter of catheter, m

# Catheter-material cross-section = full circle minus the two lumen bores.
area_wall = np.pi / 4.0 * d_outer**2 - 2.0 * area_lumen   # m^2

# ---------------------------------------------------------------------------
# 6. Flow velocity and residence-time calculations
# ---------------------------------------------------------------------------
velocity = Q_flow / area_lumen                 # mean water velocity, m/s
mass_flow = rho_water * Q_flow                 # mass flow rate, kg/s

residence_one_lumen = L / velocity             # time to pass one lumen, s
residence_total     = 2.0 * residence_one_lumen

# ---------------------------------------------------------------------------
# 7. Heat-transfer calculations
# ---------------------------------------------------------------------------
# Internal convection: check the flow regime, then use a laminar or a simple
# turbulent correlation for the Nusselt number.
reynolds = rho_water * velocity * d_lumen / mu_water
prandtl  = mu_water * cp_water / k_water
if reynolds < 2300.0:
    nusselt = 3.66                                  # laminar, constant wall T
else:
    nusselt = 0.023 * reynolds**0.8 * prandtl**0.4  # Dittus-Boelter
h_inside = nusselt * k_water / d_lumen              # W/(m^2 K)

# Series resistances give one overall coefficient per surface:
#   lumen water <-> wall node:  internal convection + half the plastic wall
U_lumen_wall = 1.0 / (1.0 / h_inside
                      + wall_conduction_thickness / k_wall)   # W/(m^2 K)
#   wall node <-> tank:  half the plastic wall + external convection
U_wall_tank  = 1.0 / (wall_conduction_thickness / k_wall
                      + 1.0 / h_outside)                      # W/(m^2 K)

# Conductances per segment (W/K)
G_lumen_wall = U_lumen_wall * perim_lumen * dx     # each lumen <-> wall
G_wall_tank  = U_wall_tank  * perim_outer * dx     # wall <-> tank

# Heat capacities per segment (J/K)
C_water_seg = rho_water * cp_water * area_lumen * dx   # water in one lumen seg
C_wall_seg  = rho_wall  * cp_wall  * area_wall  * dx   # catheter material seg

# ---------------------------------------------------------------------------
# 8. Initial conditions
# ---------------------------------------------------------------------------
# Index 0 is always the UPSTREAM end of each lumen:
#   inlet lumen:  0 = proximal (where cold water enters), N-1 = distal tip
#   outlet lumen: 0 = distal tip (fed by the turn),       N-1 = proximal exit
T_in   = np.full(N, T_water0)   # water temperature in inlet lumen, degC
T_out  = np.full(N, T_water0)   # water temperature in outlet lumen, degC
T_wall = np.full(N, T_wall0)    # catheter wall temperature, degC

# ---------------------------------------------------------------------------
# 9. Time-stepping simulation (explicit Euler, upwind advection)
# ---------------------------------------------------------------------------
# Stability: advection needs dt < dx / velocity (CFL condition); the water
# heat exchange needs dt < C_water_seg / (2 * G_lumen_wall).  Use the smaller
# with a safety factor.
dt_advection = dx / velocity
dt_exchange  = C_water_seg / (2.0 * G_lumen_wall)
dt = 0.4 * min(dt_advection, dt_exchange)
n_steps = int(simulation_time_s / dt)

time_history   = np.zeros(n_steps)
outlet_history = np.zeros(n_steps)   # proximal outlet temperature vs time

for step in range(n_steps):
    # --- advection: shift water downstream (first-order upwind) ------------
    # upstream temperature for each segment (segment 0 gets the boundary value)
    T_in_upstream  = np.concatenate(([T_inlet],   T_in[:-1]))
    T_out_upstream = np.concatenate(([T_in[-1]],  T_out[:-1]))  # distal turn:
    # the last inlet-lumen segment feeds the first outlet-lumen segment, so
    # mass flow is conserved and both lumens carry the same flow rate.

    dT_in_adv  = velocity / dx * (T_in_upstream  - T_in)
    dT_out_adv = velocity / dx * (T_out_upstream - T_out)

    # --- heat exchange with the wall node ----------------------------------
    q_wall_to_in  = G_lumen_wall * (T_wall - T_in)    # W, wall -> inlet water
    q_wall_to_out = G_lumen_wall * (T_wall - T_out)   # W, wall -> outlet water
    q_tank_to_wall = G_wall_tank * (T_tank - T_wall)  # W, tank -> wall

    # --- explicit Euler update ---------------------------------------------
    T_in   = T_in   + dt * (dT_in_adv  + q_wall_to_in  / C_water_seg)
    T_out  = T_out  + dt * (dT_out_adv + q_wall_to_out / C_water_seg)
    T_wall = T_wall + dt * (q_tank_to_wall
                            - q_wall_to_in - q_wall_to_out) / C_wall_seg

    time_history[step]   = (step + 1) * dt
    outlet_history[step] = T_out[-1]   # proximal end of the outlet lumen

# ---------------------------------------------------------------------------
# Physical checks
# ---------------------------------------------------------------------------
final_outlet_temp = outlet_history[-1]
assert T_inlet <= final_outlet_temp <= T_tank, \
    "Outlet temperature left the physical range 5..36 degC"
# The tank is a constant reservoir by construction: T_tank is never updated.

# ---------------------------------------------------------------------------
# Summary printout
# ---------------------------------------------------------------------------
print(f"Flow velocity in each lumen : {velocity:.3f} m/s")
print(f"Reynolds number             : {reynolds:.0f} "
      f"({'laminar' if reynolds < 2300 else 'turbulent'})")
print(f"Internal h                  : {h_inside:.0f} W/(m^2 K)")
print(f"Residence time, one lumen   : {residence_one_lumen:.3f} s")
print(f"Residence time, total path  : {residence_total:.3f} s")
print(f"Time step                   : {dt*1000:.2f} ms  ({n_steps} steps)")
print(f"Final outlet temperature    : {final_outlet_temp:.2f} degC")

# ---------------------------------------------------------------------------
# 10. Plot creation
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(8, 5))
ax.plot(time_history, np.full(n_steps, T_inlet),
        label="Inlet water (proximal)", color="tab:blue")
ax.plot(time_history, outlet_history,
        label="Outlet water (proximal)", color="tab:red")
ax.set_title("Dual-lumen catheter in a 36 °C tank – transient response")
ax.set_xlabel("Time [s]")
ax.set_ylabel("Temperature [°C]")
ax.legend()
ax.grid(True, alpha=0.3)
fig.tight_layout()
fig.savefig("catheter_v1_outlet_temperature.png", dpi=150)
print("Plot saved to catheter_v1_outlet_temperature.png")

# ---------------------------------------------------------------------------
# Main simplifications of this first version / possible improvements
# ---------------------------------------------------------------------------
# - One shared wall node per axial position: the wall is not resolved
#   radially or circumferentially, and lumen-to-lumen interaction happens
#   only through this shared node.  A finer model could give each lumen its
#   own wall segment plus an explicit septum conductance.
# - Constant water properties (no temperature dependence, 5..36 degC span).
# - Fixed Nu = 3.66 for laminar flow (thermally developed); entrance effects
#   near the proximal end are ignored.
# - External h is a single assumed constant; a better model would use a
#   natural/forced-convection correlation for the actual tank stirring.
# - The distal turn is treated as instantaneous with no extra volume or
#   heat-transfer area at the tip.
# - First-order upwind advection smears sharp temperature fronts
#   (numerical diffusion); higher-order schemes or more segments would
#   sharpen the transient.
