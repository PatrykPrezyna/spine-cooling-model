import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.widgets import Slider

# ------------------------------
# Physical constants
# ------------------------------
RHO  = 999.7    # water density [kg/m3]
CP   = 4182.0   # water specific heat [J/(kg*K)]
MU   = 0.001752 # water viscosity [Pa*s]
K_F  = 0.569    # water thermal conductivity [W/(m*K)]
PR   = 12.9     # Prandtl number

# HDPE properties
RHO_HDPE = 950
CP_HDPE  = 1900
K_WALL   = 0.4    # W/m*K
T_TARGET = -5.9   # °C
T_ROOM   = 20.0   # °C

# ------------------------------
# Nusselt number
# ------------------------------
def nusselt(Re, D, L):
    Nu_lam = max(3.66, 1.86 * (Re * PR * D / L) ** (1/3))
    if Re > 4000:
        f = (0.790 * np.log(Re) - 1.64) ** -2
        Nu_turb = (f/8 * (Re-1000)*PR) / (1 + 12.7*np.sqrt(f/8)*(PR**(2/3)-1))
    else:
        Nu_turb = Nu_lam
    return max(Nu_lam, Nu_turb)

# ------------------------------
# Coupled transient simulation — adaptive power
# ------------------------------
def simulate_coupled(T_in, D_mm, L,volumerate, P_ext, efficiency=0.5, t_max=600, nt=600, nx=100):
    D    = D_mm / 1000
    A    = np.pi * (D/2)**2
    P    = np.pi * D
    q = volumerate * 1e-6
    q2 = q/60
    new_v = q2/A
    # mdot = RHO * v * A
    mdot = RHO * new_v * A

    #Re = RHO * v * D / MU
    Re = RHO * new_v * D / MU
    Nu = nusselt(Re, D, L)
    h  = Nu * K_F / D

    t  = np.linspace(0, t_max, nt)
    x  = np.linspace(0, L, nx)
    dx = L / (nx - 1)
    dt = t_max / (nt - 1)

    # Wall geometry
    t_wall = 1.5e-3
    D_out  = D + 2*t_wall
    V_wall = np.pi * L * (D_out**2 - D**2) / 4
    m_wall = RHO_HDPE * V_wall

    # Effective heat transfer coefficient (conv + cond in series)
    R_conv = 1 / (h * np.pi * D)
    R_cond = np.log(D_out/D) / (2 * np.pi * K_WALL)
    R_tot  = R_conv + R_cond
    h_eff  = 1 / (R_tot * np.pi * D)

    # State arrays
    T_wall  = np.ones(nt) * T_ROOM
    T_fluid = np.ones((nt, nx)) * T_in
    P_applied = np.zeros(nt)          # actual power used at each time step [W]
    phase     = np.zeros(nt, dtype=int)  # 0 = pull-down, 1 = maintenance

    P_ext_full = P_ext
    reached_target = False

    for i in range(1, nt):
        # Fluid temperature profile along pipe
        T_fluid[i, 0] = T_in
        for j in range(1, nx):
            dTdx = -(h_eff * P / (mdot * CP)) * (T_fluid[i, j-1] - T_wall[i-1])
            T_fluid[i, j] = T_fluid[i, j-1] + dTdx * dx

        T_avg   = np.mean(T_fluid[i])
        Q_fluid = h_eff * P * L * (T_avg - T_wall[i-1])  # heat from saline to wall [W]
        #Q_fluid = mdot * CP * (T_fluid[i, -1] - T_in)
        if not reached_target:
            # Phase 1: Pull-down 
            # Efficiency scales how much of the input power actually removes heat
            P_use = P_ext_full * efficiency
            dTdt  = (Q_fluid - P_use) / (m_wall * CP_HDPE)
            T_new = T_wall[i-1] + dTdt * dt

            if T_new <= T_TARGET:
                T_wall[i]   = T_TARGET
                reached_target = True
            else:
                T_wall[i] = T_new

            phase[i]     = 0
            print("Q_fluid", Q_fluid,"P_use", P_use)
            P_applied[i] = P_use

        else:
            # Phase 2: Maintenance only offset the saline heat gain
            # Efficiency reduces effective cooling; need more input to achieve Q_maintain
            
            P_maintain = max(Q_fluid, 0.0) * efficiency
            print("Q_fluid", Q_fluid,"P_maintain", P_maintain)
            T_wall[i]  = T_TARGET
            phase[i]     = 1
            P_applied[i] = P_maintain

    # Split indices for phase stats
    idx1 = np.where(phase == 0)[0]
    idx2 = np.where(phase == 1)[0]
    P_mean1 = float(np.mean(P_applied[idx1])) if len(idx1) else 0.0
    P_mean2 = float(np.mean(P_applied[idx2])) if len(idx2) else 0.0

    # Transition time
    t_transition = float(t[idx2[0]]) if len(idx2) else t_max

    T_exit = float(T_fluid[-1, -1])

    return dict(
        t=t, x=x,
        T_fluid=T_fluid, T_wall=T_wall,
        P_applied=P_applied, phase=phase,
        P_mean1=P_mean1, P_mean2=P_mean2,
        t_transition=t_transition,
        T_exit=T_exit, h_eff=h_eff
    )

# ------------------------------
# Default values
# ------------------------------
T_IN_INIT  = 35.0
D_MM_INIT  = 5.0
L_INIT     = 4.5
V_INIT     = 0.2
P_EXT_INIT = 290
VOL_INIT = 50

# ------------------------------
# Figure layout
# ------------------------------
fig = plt.figure(figsize=(13, 12))
fig.patch.set_facecolor("#f4f3ef")

gs = gridspec.GridSpec(3, 1, figure=fig, top=0.93, bottom=0.25, hspace=0.45)
ax_fluid = fig.add_subplot(gs[0])   # fluid temp along pipe
ax_wall  = fig.add_subplot(gs[1])   # wall temp over time
ax_pwr   = fig.add_subplot(gs[2])   # power over time

for ax in (ax_fluid, ax_wall, ax_pwr):
    ax.set_facecolor("#fafaf8")

# Sliders
SL_LEFT, SL_W = 0.15, 0.72
SL_H, SL_GAP  = 0.026, 0.03
SL_BOTTOM      = 0.17

ax_s_tin = fig.add_axes([SL_LEFT, SL_BOTTOM,            SL_W, SL_H])
ax_s_dia = fig.add_axes([SL_LEFT, SL_BOTTOM - SL_GAP,   SL_W, SL_H])
ax_s_len = fig.add_axes([SL_LEFT, SL_BOTTOM - 2*SL_GAP, SL_W, SL_H])

ax_s_vol = fig.add_axes([SL_LEFT, SL_BOTTOM - 3*SL_GAP, SL_W, SL_H])

ax_s_pwr = fig.add_axes([SL_LEFT, SL_BOTTOM - 4*SL_GAP, SL_W, SL_H])
ax_s_eff = fig.add_axes([SL_LEFT, SL_BOTTOM - 5*SL_GAP, SL_W, SL_H])

s_tin = Slider(ax_s_tin, "Inlet temp (°C)",    -5,  37,  valinit=T_IN_INIT)
s_dia = Slider(ax_s_dia, "Diameter (mm)",       1,  10,  valinit=D_MM_INIT)
s_len = Slider(ax_s_len, "Length (m)",         0.5,  5,  valinit=L_INIT)
s_vol = Slider(ax_s_vol, "Volume rate (ml/min)", 10, 60, valinit= VOL_INIT)
s_pwr = Slider(ax_s_pwr, "Power (W)", 100, 1000, valinit=P_EXT_INIT)
s_eff = Slider(ax_s_eff, "System Efficiency (%)", 30, 70, valinit=50, valstep=1)
s_eff.valtext.set_text("50 %")

# Phase colours
C_PH1 = "#378ADD"   # blue 
C_PH2 = "#0F6E56"   # green 
C_TGT = "#E24B4A"   # red  
# ------------------------------
# Update function
# ------------------------------
def update(_=None):
    eff = s_eff.val / 100.0
    s_eff.valtext.set_text(f"{int(s_eff.val)} %")
    r = simulate_coupled(
        s_tin.val, s_dia.val, s_len.val,s_vol.val, s_pwr.val, efficiency=eff
    )

    t    = r['t']
    x    = r['x']
    idx1 = r['phase'] == 0
    idx2 = r['phase'] == 1
    t_tr = r['t_transition']

    # Top: fluid temperature along pipe 
    ax_fluid.clear()
    ax_fluid.plot(x, r['T_fluid'][-1], color=C_PH2, lw=2, label="Saline temperature along pipe")
    ax_fluid.axhline(-6, color=C_TGT, ls='--', label="Target -6 °C")
    ax_fluid.set_xlabel("Pipe length (m)")
    ax_fluid.set_ylabel("Temperature (°C)")
    ax_fluid.set_title(f"Fluid temperature along pipe   Exit = {r['T_exit']:.1f} °C   h_eff = {r['h_eff']:.1f} W/m^2*K")
    ax_fluid.legend(fontsize=8)
    ax_fluid.grid(True, alpha=0.3)

    #  Middle: wall temperature over time 
    ax_wall.clear()
    if idx1.any():
        ax_wall.plot(t[idx1], r['T_wall'][idx1], color=C_PH1, lw=2, label="Phase 1: Peak mode")
    if idx2.any():
        ax_wall.plot(t[idx2], r['T_wall'][idx2], color=C_PH2, lw=2, label="Phase 2: Maintenance mode")
    ax_wall.axhline(-6, color=C_TGT, ls='--', label="Target -6 °C")
    if t_tr < t[-1]:
        ax_wall.axvline(t_tr, color='gray', ls=':', lw=1.2, label=f"Transition: {t_tr:.0f} s")
    ax_wall.set_xlabel("Time (s)")
    ax_wall.set_ylabel("Wall Temperature (°C)")
    ax_wall.set_title("HDPE Wall Temperature over time")
    ax_wall.legend(fontsize=7)
    ax_wall.grid(True, alpha=0.3)

    #  Bottom: cooling power over time 
    ax_pwr.clear()
    P_W = r['P_applied']

    if idx1.any():
        ax_pwr.fill_between(t[idx1], P_W[idx1], alpha=0.25, color=C_PH1)
        ax_pwr.plot(t[idx1], P_W[idx1], color=C_PH1, lw=2, label="Phase 1: Peak mode")
        # Mean annotation — Phase 1
        ax_pwr.axhline(r['P_mean1'], xmin=0,
                       xmax=t_tr/t[-1] if t_tr < t[-1] else 1,
                       color=C_PH1, ls='--', lw=1.5)
        mid1 = t[idx1][len(t[idx1])//2]
        ax_pwr.text(mid1, r['P_mean1'] * 1.06,
                    f"mean = {r['P_mean1']:.3f} W",
                    color=C_PH1, fontsize=8, ha='center')

    if idx2.any():
        ax_pwr.fill_between(t[idx2], P_W[idx2], alpha=0.20, color=C_PH2)
        ax_pwr.plot(t[idx2], P_W[idx2], color=C_PH2, lw=2, label="Phase 2: Maintenance")
        # Mean annotation — Phase 2
        ax_pwr.axhline(r['P_mean2'],
                       xmin=t_tr/t[-1] if t_tr < t[-1] else 0,
                       xmax=1,
                       color=C_PH2, ls='--', lw=1.5)
        mid2 = t[idx2][len(t[idx2])//2]
        ax_pwr.text(mid2, r['P_mean2'] * 1.06,
                    f"mean = {r['P_mean2']:.3f} W",
                    color=C_PH2, fontsize=8, ha='center')

    if t_tr < t[-1]:
        ax_pwr.axvline(t_tr, color='gray', ls=':', lw=1.2)

    ax_pwr.set_xlabel("Time (s)")
    ax_pwr.set_ylabel("Cooling Power (W)")
    ax_pwr.set_title("Adaptive Cooling Power")
    ax_pwr.legend(fontsize=8)
    ax_pwr.grid(True, alpha=0.3)
    ax_pwr.set_ylim(bottom=0)

    fig.canvas.draw_idle()

# Connect sliders
for s in (s_tin, s_dia, s_len, s_vol, s_pwr, s_eff):
    s.on_changed(update)

update()
plt.suptitle("Cold Pipe Power Control", fontsize=13, fontweight='bold', y=0.98)
plt.show()