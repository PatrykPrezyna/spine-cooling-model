import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm

#  FLUID / CATHETER PARAMETERS
RHO_WATER  = 999.84     # kg/m^3   density of water @0°C
MU_WATER    = 0.001792      # Pa*s    dynamic viscosity @0°C
CP_WATER   = 4218.0     # specific heat of water @0°C This is very important!! It's the cargo capacity of the coolant.
K_WATER    = 0.569      # W/(m*K) thermal conductivity of water @0°C
FLOWRATE   = 50e-6 / 60 # m^3/s   50 ml/min i.e. 8.333e-7 m^3/s

# Reynolds numbers (from table — all laminar confirmed Re < 2300)

R_INFLOW   = 0.0004445  # m   inflow lumen inner radius  (0.445 mm)
R_OUT_DIST = 0.0005461  # m   outflow distal inner radius (0.546 mm)
R_OUT_PROX = 0.0004445  # m   outflow proximal inner radius (0.445 mm)

L_INFLOW   = 0.40   # m
L_OUT_DIST = 0.33   # m
L_OUT_PROX = 0.13   # m

T_WALL     = 0.000102   # m   (0.102 mm)
K_POLYMER  = 0.25       # W/(m*K)  Plastic catheter material
NU_LAMINAR = 3.66

# Nu calc
# ── Hydraulic diameter (circular lumens → D_h = 2*R) ─────────────────────────
D_INFLOW   = 2 * R_INFLOW
D_OUT_DIST = 2 * R_OUT_DIST
D_OUT_PROX = 2 * R_OUT_PROX
 
A_lumen_in = np.pi * R_INFLOW**2
A_lumen_od = np.pi * R_OUT_DIST**2
A_lumen_op = np.pi * R_OUT_PROX**2
 
# ── Nusselt number — Hausen correlation (one per lumen) ──────────────────────
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


D_INFLOW   = 2 * R_INFLOW
D_OUT_DIST = 2 * R_OUT_DIST
D_OUT_PROX = 2 * R_OUT_PROX

h_in_inflow   = NU_INFLOW * K_WATER / D_INFLOW
h_in_out_dist = NU_OUT_DIST * K_WATER / D_OUT_DIST
h_in_out_prox = NU_OUT_PROX * K_WATER / D_OUT_PROX

R_wall = T_WALL / K_POLYMER

h_eff_inflow   = 1 / (1/h_in_inflow   + R_wall)
h_eff_out_dist = 1 / (1/h_in_out_dist + R_wall)
h_eff_out_prox = 1 / (1/h_in_out_prox + R_wall)

A_inflow   = np.pi * D_INFLOW   * L_INFLOW
A_out_dist = np.pi * D_OUT_DIST * L_OUT_DIST
A_out_prox = np.pi * D_OUT_PROX * L_OUT_PROX

MDOT    = RHO_WATER * FLOWRATE
MDOT_CP = MDOT * CP_WATER

#  TISSUE PARAMETERS
RADIUS_CYLINDER = 0.025
HEIGHT          = 0.2
SURFACE_AREA    = 2 * np.pi * RADIUS_CYLINDER * HEIGHT
MASS_KG         = np.pi * RADIUS_CYLINDER**2 * HEIGHT * 1050

CP_TISSUE   = 3500.0
EMISSIVITY  = 0.98
SIGMA       = 5.67e-8
H_CONV      = 10.0
Q_METABOLIC = MASS_KG * 1.0

T_INITIAL = 37.0
T_ENV     = 20.0
T_TARGET  = 30.0
T_TOTAL_S = 1 * 3600
DT_S      = 1.0
N         = int(T_TOTAL_S / DT_S) + 1
C         = MASS_KG * CP_TISSUE

# COOLANT TEMPERATURES
T_COOLANT_RANGE = np.arange(-10, 11, 2)   # -10, -8, ..., +10 °C
t_min = np.arange(N) * DT_S / 60

colors = cm.coolwarm_r(np.linspace(0.05, 0.95, len(T_COOLANT_RANGE)))

results = []   # list of dicts per coolant temp

for T_COOLANT in T_COOLANT_RANGE:
    T_arr     = np.zeros(N)
    Qcool_arr = np.zeros(N)
    T = T_INITIAL

    for i in range(N):
        T_arr[i] = T
        Q_rad  = EMISSIVITY * SIGMA * SURFACE_AREA * (
            (T+273.15)**4 - (T_ENV+273.15)**4)
        Q_surf = H_CONV * SURFACE_AREA * (T - T_ENV)

        dT = T - T_COOLANT
        Q_cool_raw = (h_eff_inflow*A_inflow + h_eff_out_dist*A_out_dist +
                      h_eff_out_prox*A_out_prox) * dT
        Q_cool_max = MDOT_CP * dT if dT > 0 else 0
        Q_cool     = min(Q_cool_raw, Q_cool_max) if dT > 0 else Q_cool_raw

        Qcool_arr[i] = Q_cool
        Q_net = Q_METABOLIC - Q_rad - Q_surf - Q_cool
        T += Q_net / C * DT_S

    t_target = next((i*DT_S for i in range(N) if T_arr[i] <= T_TARGET), None)
    results.append({
        "T_cool":   T_COOLANT,
        "T_arr":    T_arr,
        "Qcool":    Qcool_arr,
        "t_target": t_target,
        "T_final":  T_arr[-1],
    })

#  PLOT
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 10), sharex=True)
fig.suptitle(
    f"Spinal Cord Cooling — Coolant Temperature Sweep (−10 °C to +10 °C)\n"
    f"5 Fr Tri-Lumen Catheter  |  Flow = {FLOWRATE*1e6*60:.0f} ml/min  |  "
    f"Nu (Hausen): {NU_INFLOW:.2f}/{NU_OUT_DIST:.2f}/{NU_OUT_PROX:.2f}  (in/out_d/out_p)",
    fontsize=11)

for res, color in zip(results, colors):
    Tc   = res["T_cool"]
    lw   = 2.2 if Tc == 4 else 1.4
    ls   = "-"
    lbl  = f"T_cool = {Tc:+.0f} °C"

    ax1.plot(t_min, res["T_arr"],  color=color, linewidth=lw, linestyle=ls, label=lbl)
    ax2.plot(t_min, res["Qcool"],  color=color, linewidth=lw, linestyle=ls, label=lbl)

# Target line on temperature plot
ax1.axhline(T_TARGET, color="black", linestyle="--", linewidth=1.5,
            label=f"Target {T_TARGET} °C", zorder=5)

# Mark time-to-target for each curve
for res, color in zip(results, colors):
    if res["t_target"] is not None:
        ax1.plot(res["t_target"]/60, T_TARGET, "o", color=color,
                 markersize=5, zorder=6)
        ax2.axvline(res["t_target"]/60, color=color, linewidth=0.7,
                    linestyle=":", alpha=0.6)

ax1.set_ylabel("Cord Temperature (°C)")
ax1.set_title("Spinal Cord Temperature vs Time")
ax1.set_xlim(0, T_TOTAL_S/60)
ax1.grid(True, linestyle="--", alpha=0.35)
ax1.legend(fontsize=8, loc="upper right", ncol=2,
           title="Coolant temperature", title_fontsize=8)

ax2.axhline(0, color="grey", linewidth=0.8, linestyle=":")
ax2.set_xlabel("Time (min)")
ax2.set_ylabel("Cooling Power (W)")
ax2.set_title("Catheter Cooling Power vs Time")
ax2.set_xlim(0, T_TOTAL_S/60)
ax2.grid(True, linestyle="--", alpha=0.35)
ax2.legend(fontsize=8, loc="upper right", ncol=2,
           title="Coolant temperature", title_fontsize=8)

plt.tight_layout()
plt.show()
print("Done.")