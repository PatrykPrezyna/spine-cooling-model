import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch


#  FLUID / CATHETER PARAMETERS  (from design table)
RHO_WATER   = 999.84        # kg/m^3   density of water @0°C
MU_WATER    = 0.001792      # Pa*s    dynamic viscosity @0°C
CP_WATER    = 4218.0        # J/(kg*K) or (W*s)/(Kg*K) specific heat of water @0°C This is very important!! It's the cargo capacity of the coolant.
K_WATER     = 0.569         # W/(m*K) thermal conductivity of water @0°C
FLOWRATE    = 50e-6 / 60    # m^3/s   50 ml/min i.e. 8.333e-7 m^3/s

# Lumen radii (from table)
R_INFLOW    = 0.0004445     # m   inflow lumen inner radius  (0.445 mm)
R_OUT_DIST  = 0.0005461     # m   outflow distal inner radius (0.546 mm)
R_OUT_PROX  = 0.0004445     # m   outflow proximal inner radius (0.445 mm)

# Lumen lengths
L_INFLOW    = 0.40          # m
L_OUT_DIST  = 0.33          # m
L_OUT_PROX  = 0.13          # m

# Wall thickness (inner lumen wall)
T_WALL      = 0.000102      # m   (0.102 mm)
K_POLYMER   = 0.25          # W/(m*K)  Plastic catheter material

#Calculus of the Nu numbers for each part
# Hydraulic diameter (circular lumens --> D_h = 2*R)
D_INFLOW    = 2 * R_INFLOW
D_OUT_DIST  = 2 * R_OUT_DIST
D_OUT_PROX  = 2 * R_OUT_PROX

A_lumen_in  = np.pi * R_INFLOW**2
A_lumen_od  = np.pi * R_OUT_DIST**2
A_lumen_op  = np.pi * R_OUT_PROX**2

# Nusselt number — Hausen correlation (one per lumen)
# Re = rho*V*D_h/mu   Pr = mu*Cp/k   Gz = (D_h/L)*Re*Pr
# Nu = 3.66 + (0.0668*Gz) / (1 + 0.04*Gz^(2/3))
PR = MU_WATER * CP_WATER / K_WATER

def calc_Nu(A_lumen, D_h, L):
    V   = FLOWRATE / A_lumen
    Re  = RHO_WATER * V * D_h / MU_WATER
    Gz  = (D_h / L) * Re * PR
    Nu  = 3.66 + (0.0668 * Gz) / (1 + 0.04 * Gz**(2/3))
    return Nu, Re, Gz

NU_INFLOW,   RE_IN, GZ_IN = calc_Nu(A_lumen_in, D_INFLOW,   L_INFLOW)
NU_OUT_DIST, RE_OD, GZ_OD = calc_Nu(A_lumen_od, D_OUT_DIST, L_OUT_DIST)
NU_OUT_PROX, RE_OP, GZ_OP = calc_Nu(A_lumen_op, D_OUT_PROX, L_OUT_PROX)

#  DERIVE h_internal from Nusselt number
#----------------------
#  DERIVE h_internal from Nusselt number
#  Laminar fully-developed flow in a tube: Nu = 3.66 (uniform wall temp)
#  h = Nu * k_fluid / D_hydraulic

D_INFLOW    = 2 * R_INFLOW
D_OUT_DIST  = 2 * R_OUT_DIST
D_OUT_PROX  = 2 * R_OUT_PROX

h_in_inflow   = NU_INFLOW * K_WATER / D_INFLOW
h_in_out_dist = NU_OUT_DIST * K_WATER / D_OUT_DIST
h_in_out_prox = NU_OUT_PROX * K_WATER / D_OUT_PROX

# Wall conduction resistance per unit area: R_wall = thickness / (coef of conductive heat transfer: k)  [m^2*K/W]
R_wall = T_WALL / K_POLYMER

# Thermal resistance are in serie: fluid convection + wall conduction
# Resistance_eff = 1/h_internal + R_wall [m^2*K/W]
# h_eff = 1 / (1/h_internal + R_wall) [W/m^2*K]
h_eff_inflow   = 1 / (1/h_in_inflow   + R_wall)
h_eff_out_dist = 1 / (1/h_in_out_dist + R_wall)
h_eff_out_prox = 1 / (1/h_in_out_prox + R_wall)

# Contact surface areas of each lumen: inner wall = pi * D * L
A_inflow   = np.pi * D_INFLOW   * L_INFLOW
A_out_dist = np.pi * D_OUT_DIST * L_OUT_DIST
A_out_prox = np.pi * D_OUT_PROX * L_OUT_PROX

# Coolant temperature
T_COOLANT   = -10.0           # °C  saline inlet temperature

# Saline heat capacity rate mdot*Cp [W/K] This is the physical limit on heat extraction!!!
MDOT        = RHO_WATER * FLOWRATE   # kg/s
MDOT_CP     = MDOT * CP_WATER        # W/K

#  TISSUE / CORD GEOMETRY
RADIUS_CYLINDER = 0.025
HEIGHT          = 0.2
SURFACE_AREA    = 2 * np.pi * RADIUS_CYLINDER * HEIGHT
MASS_KG         = np.pi * RADIUS_CYLINDER**2 * HEIGHT * 1050

CP_TISSUE   = 3500.0
EMISSIVITY  = 0.98
SIGMA       = 5.67e-8
H_CONV      = 10.0      # W/(m^2*K) outer surface (tissue surrounded by CSF)

Q_METABOLIC = MASS_KG * 1.0    # W  (1 W/kg)

#  SIMULATION
T_INITIAL   = 37.0
T_ENV       = 20.0
T_TARGET    = 30.0
T_TOTAL_S   = 1 * 3600 #Total simulation duration in s
DT_S        = 1.0 # time step

N          = int(T_TOTAL_S / DT_S) + 1
t_arr      = np.zeros(N)
T_arr      = np.zeros(N)
Qrad_arr   = np.zeros(N)
Qconv_arr  = np.zeros(N)
Qcool_arr  = np.zeros(N)
Qnet_arr   = np.zeros(N)

T = T_INITIAL
C = MASS_KG * CP_TISSUE

for i in range(N):
    t_arr[i] = i * DT_S
    T_arr[i] = T

    Q_rad  = EMISSIVITY * SIGMA * SURFACE_AREA * ((T + 273.15)**4 - (T_ENV + 273.15)**4)
    Q_surf = H_CONV * SURFACE_AREA * (T - T_ENV)

    dT = T - T_COOLANT
    Q_inflow   = h_eff_inflow   * A_inflow   * dT
    Q_out_dist = h_eff_out_dist * A_out_dist * dT
    Q_out_prox = h_eff_out_prox * A_out_prox * dT
    Q_cool_raw = Q_inflow + Q_out_dist + Q_out_prox

    # Cooling is capped by saline thermal capacity (cannot extract more than mdotCp*ΔT)
    Q_cool_max = MDOT_CP * dT if dT > 0 else 0
    Q_cool     = min(Q_cool_raw, Q_cool_max) if dT > 0 else Q_cool_raw

    Qrad_arr[i]  = Q_rad
    Qconv_arr[i] = Q_surf
    Qcool_arr[i] = Q_cool
    Qnet_arr[i]  = Q_METABOLIC - Q_rad - Q_surf - Q_cool

    T += Qnet_arr[i] / C * DT_S

t_target = next((t_arr[i] for i in range(N) if T_arr[i] <= T_TARGET), None)
t_min    = t_arr / 60

#  PRINT DERIVED PARAMETERS
print("Derived thermal parameters")
print(f"  Nu inflow                 = {NU_INFLOW:.4f}")
print(f"  Nu outflow dist           = {NU_OUT_DIST:.4f}")
print(f"  Nu outflow prox           = {NU_OUT_PROX:.4f}")
print(f"  h_internal inflow         = {h_in_inflow:.1f} W/(m^2*K)")
print(f"  h_internal outflow distal = {h_in_out_dist:.1f} W/(m^2*K)")
print(f"  h_internal outflow prox   = {h_in_out_prox:.1f} W/(m^2*K)")
print(f"  R_wall                    = {R_wall:.5f} m^2*K/W")
print(f"  h_eff inflow              = {h_eff_inflow:.1f} W/(m^2*K)")
print(f"  h_eff outflow distal      = {h_eff_out_dist:.1f} W/(m^2*K)")
print(f"  h_eff outflow prox        = {h_eff_out_prox:.1f} W/(m^2*K)")
print(f"  A_inflow                  = {A_inflow*1e4:.3f} cm^2")
print(f"  A_out_dist                = {A_out_dist*1e4:.3f} cm^2")
print(f"  A_out_prox                = {A_out_prox*1e4:.3f} cm^2")
print(f"  Saline mdot                  = {MDOT*1000:.4f} g/s")
print(f"  Saline mdotCp                = {MDOT_CP:.4f} W/K")
print(f"  Q_cool @ T=37°C           = {(h_eff_inflow*A_inflow + h_eff_out_dist*A_out_dist + h_eff_out_prox*A_out_prox)*(37-T_COOLANT):.4f} W")

#  SUMMARY TABLE
idx = N - 1
col_labels = ["Time", "T (°C)", "Q_met (W)", "Q_rad (W)", "Q_surf (W)", "Q_cool (W)", "Q_net (W)"]
table_data = [[
    f"{t_arr[idx]/60:.0f} min",
    f"{T_arr[idx]:.3f}",
    f"{Q_METABOLIC:+.4f}",
    f"{-Qrad_arr[idx]:+.4f}",
    f"{-Qconv_arr[idx]:+.4f}",
    f"{-Qcool_arr[idx]:+.4f}",
    f"{Qnet_arr[idx]:+.4f}",
]]

#  PARAMETER LEGEND
param_text = "\n".join([
    "── Cord ──",
    f"R={RADIUS_CYLINDER*100:.1f}cm  H={HEIGHT*100:.0f}cm  m={MASS_KG*1000:.1f}g",
    f"Cp={CP_TISSUE:.0f} J/(kg*K)   ε={EMISSIVITY}",
    f"Q_met={Q_METABOLIC:.4f} W",
    "── Catheter ──",
    f"T_cool={T_COOLANT}°C  Flow={FLOWRATE*1e6*60:.0f} ml/min",
    f"Nu={NU_INFLOW:.3f}/{NU_OUT_DIST:.3f}/{NU_OUT_PROX:.3f}  (in/out_d/out_p)",    f"h_eff_in   ={h_eff_inflow:.1f} W/(m^2*K)",
    f"h_eff_out_d={h_eff_out_dist:.1f} W/(m^2*K)",
    f"h_eff_out_p={h_eff_out_prox:.1f} W/(m^2*K)",
    f"R_wall={R_wall:.5f} m^2K/W",
])

#  PLOTS
fig, axes = plt.subplots(3, 1, figsize=(11, 13),
                         gridspec_kw={"height_ratios": [2.5, 2, 0.8]})
fig.suptitle(
    f"Spinal Cord Cooling — 5 Fr Tri-Lumen Catheter  |  "
    f"T_coolant={T_COOLANT}°C  |  Flow={FLOWRATE*1e6*60:.0f} ml/min",
    fontsize=12)

# ── Temperature ───────────────────────────────────────────────────────────────
ax1 = axes[0]
ax1.plot(t_min, T_arr, color="tab:red", linewidth=2, label="Cord temperature")
ax1.axhline(T_TARGET,  color="tab:green", linestyle="--", linewidth=1.3,
            label=f"Target {T_TARGET} °C")
ax1.axhline(T_COOLANT, color="tab:blue",  linestyle=":",  linewidth=1.2,
            label=f"Coolant {T_COOLANT} °C")
if t_target:
    ax1.axvline(t_target/60, color="tab:green", linestyle="--",
                linewidth=1.0, alpha=0.7,
                label=f"Target reached at {t_target/60:.1f} min")

param_patch = Patch(facecolor="lightyellow", edgecolor="grey",
                    label=f"Parameters:\n{param_text}")
handles = [
    plt.Line2D([0],[0], color="tab:red",   linewidth=2,   label="Cord temperature"),
    plt.Line2D([0],[0], color="tab:green", linestyle="--", linewidth=1.3,
               label=f"Target {T_TARGET} °C"),
    plt.Line2D([0],[0], color="tab:blue",  linestyle=":",  linewidth=1.2,
               label=f"Coolant {T_COOLANT} °C"),
    param_patch,
]
if t_target:
    handles.insert(3, plt.Line2D([0],[0], color="tab:green", linestyle="--",
        linewidth=1.0, alpha=0.7,
        label=f"Target reached at {t_target/60:.1f} min"))
ax1.legend(handles=handles, fontsize=8.5, loc="upper right")
ax1.set_xlabel("Time (min)")
ax1.set_ylabel("Temperature (°C)")
ax1.set_title("Spinal Cord Temperature vs Time")
ax1.set_xlim(0, T_TOTAL_S/60)
ax1.grid(True, linestyle="--", alpha=0.4)

# ── Cooling Power ─────────────────────────────────────────────────────────────
ax2 = axes[1]
ax2.plot(t_min, Qcool_arr, color="tab:blue", linewidth=2.0,
         label="Q_catheter cooling")
ax2.axhline(0, color="grey", linewidth=0.8, linestyle=":")
if t_target:
    ax2.axvline(t_target/60, color="tab:green", linestyle="--",
                linewidth=1.0, alpha=0.6, label=f"Target reached at {t_target/60:.1f} min")
ax2.set_xlabel("Time (min)")
ax2.set_ylabel("Cooling Power (W)")
ax2.set_title("Catheter Cooling Power vs Time")
ax2.set_xlim(0, T_TOTAL_S/60)
ax2.legend(fontsize=8.5, loc="right")
ax2.grid(True, linestyle="--", alpha=0.4)

# ── Table ─────────────────────────────────────────────────────────────────────
ax3 = axes[2]
ax3.axis("off")
tbl = ax3.table(cellText=table_data, colLabels=col_labels,
                cellLoc="center", loc="center")
tbl.auto_set_font_size(False)
tbl.set_fontsize(9)
tbl.scale(1.0, 1.8)

plt.tight_layout()
plt.show()
print("Done.")