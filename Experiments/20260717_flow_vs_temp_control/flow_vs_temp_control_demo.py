"""
Two demos of cooling control:
  1) Temperature-based control (setpoint change 34 -> 33 C)
  2) Flow-rate control (manual flow change 30 -> 50 mL/min)

Aligned timeline and patient colors across both figures.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT_DIR = Path(__file__).resolve().parent

DT = 0.5
T_END = 250.0  # room for slower patient to return + short settle
t = np.arange(0.0, T_END + DT, DT)

# Shared timeline (similar-length stabilization phases)
T_COOL_START = 10.0
T_CHANGE = 95.0  # after first settle
T_DISTURBANCE = 155.0  # after second settle
events_tc = [
    (T_COOL_START, "Cooling\nstart", "#2ca02c"),
    (T_CHANGE, "Setpoint\nchange", "#ff7f0e"),
    (T_DISTURBANCE, "Body heat\nincrease", "#d62728"),
]
events_fr = [
    (T_COOL_START, "Cooling\nstart", "#2ca02c"),
    (T_CHANGE, "Flow\nchange", "#ff7f0e"),
    (T_DISTURBANCE, "Body heat\nincrease", "#d62728"),
]

# Shared plant / patient params
T_coolant, T_body = 4.0, 37.0
k_cool = 0.000133
k_warm_p1, k_warm_p2 = 0.040, 0.052
# Flow-based figure: open-loop heat bump (temps rise and stay up)
Q1_dist_fr, Q2_dist_fr = 0.23, 0.20
# Temp-based figure: rejectable bumps (both return to setpoint)
Q1_dist_tc, Q2_dist_tc = 0.10, 0.14

COLOR_P1 = "steelblue"
COLOR_P2 = "darkorange"


def annotate_events(ax, events, y_frac=0.92):
    ymin, ymax = ax.get_ylim()
    y = ymin + y_frac * (ymax - ymin)
    for x, label, color in events:
        ax.axvline(x, color=color, linestyle=":", linewidth=1.4, alpha=0.9)
        ax.text(x + 1.5, y, label, color=color, fontsize=8, va="top")


def flow_hold(setpoint, k_warm, Q=0.0):
    """Steady flow that holds `setpoint` for a given patient heat model."""
    return (k_warm * (T_body - setpoint) + Q) / (k_cool * (setpoint - T_coolant))


def simulate_temp_controlled(k_warm, Q_dist, Kp, Ki, tau_flow):
    """
    Soft PI tracking: approach setpoint from above (no undershoot).
    After the body-heat bump, integral action brings temp back to setpoint.
    Kp/Ki/tau_flow set how fast that recovery happens.
    """
    setpoint = np.full_like(t, 37.0)
    setpoint[t >= T_COOL_START] = 34.0
    setpoint[t >= T_CHANGE] = 33.0

    T = np.zeros_like(t)
    flow = np.zeros_like(t)
    T[0] = 37.0
    flow_eff = 0.0
    integral = 0.0
    flow_max = 100.0

    for i in range(1, len(t)):
        if t[i] < T_COOL_START:
            T[i] = 37.0
            flow[i] = 0.0
            flow_eff = 0.0
            continue

        Q = Q_dist if t[i] >= T_DISTURBANCE else 0.0
        sp = float(setpoint[i])
        error = T[i - 1] - sp  # >0 if too warm

        # Nominal hold ignores Q; PI builds the extra flow needed to reject Q.
        hold0 = flow_hold(sp, k_warm, 0.0)
        holdQ = flow_hold(sp, k_warm, Q)
        flow_unsat = hold0 + Kp * max(error, 0.0) + Ki * integral
        flow[i] = float(np.clip(flow_unsat, 0.0, flow_max))

        if error > 0.02 and abs(flow[i] - flow_unsat) < 1e-9:
            integral = float(np.clip(integral + error * DT, 0.0, 80.0))
        elif error <= 0.02 and Ki > 0.0:
            # Settle integral at the disturbance-rejecting value once back near SP
            i_needed = max(0.0, (holdQ - hold0) / Ki)
            integral = 0.9 * integral + 0.1 * i_needed

        flow_eff += DT * (flow[i] - flow_eff) / tau_flow
        # Allow enough cooling to hold against Q, but not enough to undershoot
        if T[i - 1] <= sp + 0.01:
            flow_eff = min(flow_eff, holdQ)

        dT = (
            -k_cool * flow_eff * (T[i - 1] - T_coolant)
            + k_warm * (T_body - T[i - 1])
            + Q
        )
        T[i] = T[i - 1] + DT * dT
        if T[i] < sp:
            T[i] = sp

    return setpoint, T, flow


# ---------------------------------------------------------------------------
# Figure 1 — Temperature-based control (two patients)
# ---------------------------------------------------------------------------
# Patient 1: faster recovery after heat bump (~195 min)
# Patient 2: slower recovery (~223 min) — lower gains, longer flow lag
setpoint, T_tc1, flow_tc1 = simulate_temp_controlled(
    k_warm_p1, Q1_dist_tc, Kp=22.0, Ki=2.0, tau_flow=1.5
)
_, T_tc2, flow_tc2 = simulate_temp_controlled(
    k_warm_p2, Q2_dist_tc, Kp=6.0, Ki=0.75, tau_flow=6.0
)

fig1, ax = plt.subplots(2, 1, figsize=(10, 7.5), sharex=True)

ax[0].plot(t, T_tc1, color=COLOR_P1, linewidth=2.4, label="Patient 1")
ax[0].plot(t, T_tc2, color=COLOR_P2, linewidth=2.4, label="Patient 2 (higher heat load)")
ax[0].plot(
    t, setpoint, color="black", linestyle="--", linewidth=1.6, label="Temperature setpoint"
)
ax[0].set_ylabel("Temperature (°C)")
ax[0].set_title("Temperature-Based Control")
ax[0].set_ylim(31.5, 38.0)
ax[0].legend(loc="upper right")
ax[0].grid(True, alpha=0.35)
annotate_events(ax[0], events_tc)

ax[1].step(t, flow_tc1, where="post", color=COLOR_P1, linewidth=2.0, label="Patient 1 flow")
ax[1].step(t, flow_tc2, where="post", color=COLOR_P2, linewidth=2.0, label="Patient 2 flow")
ax[1].set_ylabel("Flow rate (mL/min)")
ax[1].set_xlabel("Time (min)")
ax[1].set_ylim(-2, 105)
ax[1].legend(loc="upper right")
ax[1].grid(True, alpha=0.35)
annotate_events(ax[1], events_tc, y_frac=0.15)

fig1.tight_layout()
path1 = OUT_DIR / "temp_based_control_demo.png"
fig1.savefig(path1, dpi=300)
print(path1.name)


# ---------------------------------------------------------------------------
# Figure 2 — Flow-rate control (same timeline, same patient colors)
# ---------------------------------------------------------------------------
flow_fr = np.zeros_like(t)
flow_fr[t >= T_COOL_START] = 30.0
flow_fr[t >= T_CHANGE] = 50.0

T_p1 = np.zeros_like(t)
T_p2 = np.zeros_like(t)
T_p1[0] = T_p2[0] = 37.0

for i in range(1, len(t)):
    if t[i] < T_COOL_START:
        T_p1[i] = T_p2[i] = 37.0
        continue

    Q1 = Q1_dist_fr if t[i] >= T_DISTURBANCE else 0.0
    Q2 = Q2_dist_fr if t[i] >= T_DISTURBANCE else 0.0

    T_p1[i] = T_p1[i - 1] + DT * (
        -k_cool * flow_fr[i] * (T_p1[i - 1] - T_coolant)
        + k_warm_p1 * (T_body - T_p1[i - 1])
        + Q1
    )
    T_p2[i] = T_p2[i - 1] + DT * (
        -k_cool * flow_fr[i] * (T_p2[i - 1] - T_coolant)
        + k_warm_p2 * (T_body - T_p2[i - 1])
        + Q2
    )

fig2, ax = plt.subplots(2, 1, figsize=(10, 7.5), sharex=True)

ax[0].plot(t, T_p1, color=COLOR_P1, linewidth=2.4, label="Patient 1")
ax[0].plot(t, T_p2, color=COLOR_P2, linewidth=2.4, label="Patient 2 (higher heat load)")
ax[0].set_ylabel("Temperature (°C)")
ax[0].set_title("Flow-Rate Control")
ax[0].set_ylim(31.5, 38.0)
ax[0].legend(loc="upper right")
ax[0].grid(True, alpha=0.35)
annotate_events(ax[0], events_fr)

ax[1].step(t, flow_fr, where="post", color="dimgray", linewidth=2.2, label="Flow rate")
ax[1].set_ylabel("Flow rate (mL/min)")
ax[1].set_xlabel("Time (min)")
ax[1].set_ylim(-2, 105)
ax[1].legend(loc="upper right")
ax[1].grid(True, alpha=0.35)
annotate_events(ax[1], events_fr, y_frac=0.15)

fig2.tight_layout()
path2 = OUT_DIR / "flow_rate_control_demo.png"
fig2.savefig(path2, dpi=300)
print(path2.name)

plt.close("all")
