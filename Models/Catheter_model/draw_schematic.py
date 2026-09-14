"""Draw a PNG schematic of how dual_lumen_catheter.py is discretized.

Layout matches the U-loop reference sketch, then annotates the actual
compartments, heat path, and every model input / constant next to the
part of the picture it belongs to.
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle, FancyBboxPatch, FancyArrowPatch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dual_lumen_catheter as m  # noqa: E402

OUT = HERE / "dual_lumen_catheter_schematic.png"

BG = "#EAF3F8"
TANK_FILL = "#F8E4C8"
TANK_EDGE = "#D9A066"
WALL_FILL = "#C5D0D8"
WALL_EDGE = "#7A8B99"
SEPTUM = "#8A9AAA"
INLET = "#2F6FED"
OUTLET = "#E23B3B"
HEAT = "#DC2626"
TEAL = "#165E6A"
NODE_WALL = "#5C6B78"
TEXT = "#1F2A33"
MUTED = "#5A6A78"
BOX = dict(boxstyle="round,pad=0.18", fc="white", ec="none", alpha=0.82)

T_WALL_MM = m.wall_thickness_m * 1.0e3
DZ_CM = m.segment_length_m * 100.0
K_NOM = m.calibration_k_for_flow(m.nominal_flow_m3_s)


def nominal_inner_film():
    velocity = m.nominal_flow_m3_s / m.lumen_cross_section_m2
    reynolds = (m.WATER_DENSITY_KG_M3 * velocity * m.lumen_diameter_m
                / m.WATER_DYNAMIC_VISCOSITY_PA_S)
    prandtl = (m.WATER_DYNAMIC_VISCOSITY_PA_S * m.WATER_SPECIFIC_HEAT_J_KG_K
               / m.WATER_THERMAL_CONDUCTIVITY_W_M_K)
    graetz = reynolds * prandtl * m.lumen_diameter_m / m.catheter_length_m
    nusselt = 3.66 + 0.0668 * graetz / (1.0 + 0.04 * graetz ** (2.0 / 3.0))
    h_inner = nusselt * m.WATER_THERMAL_CONDUCTIVITY_W_M_K / m.lumen_diameter_m
    return reynolds, prandtl, graetz, nusselt, h_inner


RE, PR, GZ, NU, H_INNER = nominal_inner_film()


def hex_to_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def lerp_color(c0, c1, t):
    return (1.0 - t) * hex_to_rgb(c0) + t * hex_to_rgb(c1)


def flow_polyline(ax, xs, ys, colors, lw=3.8, z=6):
    pts = np.column_stack([xs, ys])
    segs = np.concatenate([pts[:-1, None, :], pts[1:, None, :]], axis=1)
    ax.add_collection(LineCollection(
        segs, colors=colors, linewidths=lw,
        capstyle="round", joinstyle="round", zorder=z,
    ))


def draw_thermometer(ax, x, y, radius=0.30, z=12):
    ax.add_patch(Circle((x, y), radius, facecolor=TEAL, edgecolor="none", zorder=z))
    ax.plot(
        [x, x], [y - radius * 0.08, y + radius * 0.42],
        color="white", linewidth=2.4, solid_capstyle="round", zorder=z + 1,
    )
    ax.add_patch(Circle(
        (x, y - radius * 0.38), radius * 0.22,
        facecolor="#E23B3B", edgecolor="white", linewidth=0.8, zorder=z + 2,
    ))


def heat_arrow(ax, x0, y0, x1, y1, color=HEAT):
    ax.add_patch(FancyArrowPatch(
        (x0, y0), (x1, y1),
        arrowstyle="-|>", mutation_scale=11, linewidth=1.5,
        color=color, zorder=5, shrinkA=0, shrinkB=0,
    ))


def dim_arrow(ax, x0, y0, x1, y1, color=MUTED, scale=9):
    ax.add_patch(FancyArrowPatch(
        (x0, y0), (x1, y1),
        arrowstyle="<->", mutation_scale=scale, linewidth=1.0,
        color=color, zorder=6, shrinkA=0, shrinkB=0,
    ))


def draw_longitudinal(ax):
    ax.set_xlim(0.0, 10.0)
    ax.set_ylim(0.05, 11.25)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.add_patch(FancyBboxPatch(
        (0.35, 0.55), 9.3, 10.15,
        boxstyle="round,pad=0.04,rounding_size=0.35",
        facecolor=TANK_FILL, edgecolor=TANK_EDGE, linewidth=1.4, zorder=0,
    ))
    ax.text(
        5.0, 10.32,
        rf"mixed water tank"
        rf"    $T_{{\mathrm{{tank}}}}={m.TANK_WATER_TEMPERATURE_C:.0f}\,\mathrm{{^\circ C}}$"
        "\n"
        rf"$h_{{\mathrm{{tank}}}}={m.TANK_CONVECTION_COEFFICIENT_W_M2_K:.0f}"
        rf"\,\mathrm{{W/m^2 \cdot K}}$  (assumed, stirred bath)",
        ha="center", va="center", color="#8A4B12", fontsize=8.4, zorder=1,
    )

    body_x, body_w = 3.15, 3.70
    body_y, body_h = 1.70, 7.20
    ax.add_patch(FancyBboxPatch(
        (body_x, body_y), body_w, body_h,
        boxstyle="round,pad=0.02,rounding_size=0.38",
        facecolor=WALL_FILL, edgecolor=WALL_EDGE, linewidth=1.6, zorder=2,
    ))

    n_drawn = 8
    y0, y1 = 1.98, 8.38
    for i in range(n_drawn + 1):
        yy = y0 + (y1 - y0) * i / n_drawn
        ax.plot(
            [body_x + 0.18, body_x + body_w - 0.18], [yy, yy],
            color="white", linewidth=0.7, alpha=0.55, zorder=3,
        )

    mid_x = body_x + body_w / 2.0
    ax.plot(
        [mid_x, mid_x], [y0, y1],
        color=SEPTUM, linewidth=1.3, linestyle=(0, (3, 2.5)), zorder=4,
    )

    left_x = body_x + 0.95
    right_x = body_x + body_w - 0.95
    y_bot = 1.48
    y_top = 8.55
    n_up, n_turn, n_down = 40, 24, 40
    xs_up = np.full(n_up, left_x)
    ys_up = np.linspace(y_bot, y_top, n_up)
    theta = np.linspace(np.pi, 0.0, n_turn)
    r_turn = (right_x - left_x) / 2.0
    cx_turn = (left_x + right_x) / 2.0
    xs_turn = cx_turn + r_turn * np.cos(theta)
    ys_turn = y_top + 0.55 * r_turn * np.sin(theta)
    xs_down = np.full(n_down, right_x)
    ys_down = np.linspace(y_top, y_bot, n_down)
    xs = np.concatenate([xs_up, xs_turn[1:], xs_down[1:]])
    ys = np.concatenate([ys_up, ys_turn[1:], ys_down[1:]])
    t = np.linspace(0.0, 1.0, len(xs) - 1)
    flow_polyline(ax, xs, ys, [lerp_color(INLET, OUTLET, ti) for ti in t])

    ax.add_patch(FancyArrowPatch(
        (left_x, 5.45), (left_x, 6.55),
        arrowstyle="-|>", mutation_scale=12, linewidth=0,
        color=INLET, zorder=7, shrinkA=0, shrinkB=0,
    ))
    ax.add_patch(FancyArrowPatch(
        (right_x, 6.55), (right_x, 5.45),
        arrowstyle="-|>", mutation_scale=12, linewidth=0,
        color=OUTLET, zorder=7, shrinkA=0, shrinkB=0,
    ))

    for yy in np.linspace(2.55, 7.65, 5):
        heat_arrow(ax, body_x - 0.85, yy, body_x + 0.12, yy)

    ax.text(
        1.45, 5.15, "heat in\nfrom tank",
        ha="center", va="center", fontsize=7.6, color=HEAT, fontweight="medium",
    )

    dim_arrow(ax, 8.55, y0, 8.55, y1)
    ax.text(
        8.78, 5.15,
        rf"$L={m.CATHETER_LENGTH_CM:.0f}\,\mathrm{{cm}}$"
        "\n"
        rf"$N={m.N_AXIAL_SEGMENTS}$"
        "\n"
        rf"$\Delta z={DZ_CM:.2f}\,\mathrm{{cm}}$",
        ha="left", va="center", fontsize=7.6, color=MUTED,
    )

    ax.annotate(
        "distal turn\n(no extra volume\nor heat-transfer area)",
        xy=(mid_x, 8.95), xytext=(8.35, 9.72),
        fontsize=7.2, color=MUTED, ha="center",
        arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8),
        zorder=8,
    )

    draw_thermometer(ax, left_x, 1.05)
    draw_thermometer(ax, right_x, 1.05)
    ax.text(
        left_x, 0.58,
        rf"$T_{{\mathrm{{in}}}}={m.INLET_WATER_TEMPERATURE_C:.0f}\,\mathrm{{^\circ C}}$",
        ha="center", va="top", fontsize=8.2, color=INLET, fontweight="bold",
    )
    ax.text(
        right_x, 0.58,
        r"$T_{\mathrm{out}}$  (computed)",
        ha="center", va="top", fontsize=8.2, color=OUTLET, fontweight="bold",
    )
    ax.text(
        mid_x, 0.22,
        rf"$Q={m.VOLUMETRIC_FLOW_RATE_ML_MIN:.0f}\,\mathrm{{mL/min}}$",
        ha="center", va="bottom", fontsize=8.5, color=TEXT, fontweight="medium",
        bbox=BOX, zorder=9,
    )

    label_kw = dict(
        ha="center", va="center", fontsize=8.2, fontweight="medium", zorder=8,
        bbox=BOX,
    )
    ax.text(left_x, 3.70, "inlet\nlumen", color=INLET, **label_kw)
    ax.text(right_x, 3.70, "outlet\nlumen", color=OUTLET, **label_kw)
    ax.text(
        mid_x, 7.55, "polymer wall",
        ha="center", va="center", fontsize=7.4, color=NODE_WALL, zorder=8,
        bbox=BOX,
    )

    ax.set_title(
        "A   Longitudinal view  —  geometry, flow, and tank",
        loc="left", fontsize=11, color=TEXT, pad=8, fontweight="medium",
    )


def draw_cross_section(ax):
    r_outer = 1.50
    r_lumen = 0.50
    r_tank = 2.0 * 2.35
    t_wall = (m.CATHETER_OUTER_DIAMETER_MM - 2.0 * m.LUMEN_INNER_DIAMETER_MM) / 3.0
    cx = r_outer - t_wall - r_lumen

    ax.set_xlim(-5.9, 7.4)
    ax.set_ylim(-5.7, 6.0)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.add_patch(Circle((0, 0), r_tank, facecolor=TANK_FILL, edgecolor=TANK_EDGE,
                        linewidth=1.2, zorder=0))
    ax.add_patch(Circle((0, 0), r_outer, facecolor=WALL_FILL, edgecolor=WALL_EDGE,
                        linewidth=1.6, zorder=1))
    ax.add_patch(Circle((-cx, 0), r_lumen, facecolor="#D6E6FB",
                        edgecolor=INLET, linewidth=1.6, zorder=2))
    ax.add_patch(Circle((cx, 0), r_lumen, facecolor="#FAD4D4",
                        edgecolor=OUTLET, linewidth=1.6, zorder=2))

    for ang in (30.0, 90.0, 150.0, 210.0, 270.0, 330.0):
        rad = np.radians(ang)
        heat_arrow(
            ax,
            0.88 * r_tank * np.cos(rad), 0.88 * r_tank * np.sin(rad),
            1.08 * r_outer * np.cos(rad), 1.08 * r_outer * np.sin(rad),
        )
    heat_arrow(ax, -0.12, 0.55, -cx + 0.18, 0.16)
    heat_arrow(ax, 0.12, 0.55, cx - 0.18, 0.16)

    ax.text(-3.35, 4.05, "tank", ha="center", va="center",
            fontsize=8, color="#8A4B12")
    ax.text(-cx, 0, "in", ha="center", va="center", fontsize=8.5,
            color=INLET, fontweight="bold", zorder=5)
    ax.text(cx, 0, "out", ha="center", va="center", fontsize=8.5,
            color=OUTLET, fontweight="bold", zorder=5)

    dim_arrow(ax, -r_outer, -1.78, r_outer, -1.78, scale=8)
    ax.text(
        0, -2.08,
        rf"$D_{{\mathrm{{outer}}}}={m.CATHETER_OUTER_DIAMETER_MM:.1f}\,\mathrm{{mm}}$",
        ha="center", va="top", fontsize=7.6, color=MUTED,
    )
    dim_arrow(ax, -cx - r_lumen, 0.92, -cx + r_lumen, 0.92, scale=7)
    ax.text(
        -cx, 1.18,
        rf"$D_{{\mathrm{{lumen}}}}={m.LUMEN_INNER_DIAMETER_MM:.1f}\,\mathrm{{mm}}$",
        ha="center", va="bottom", fontsize=7.4, color=INLET,
    )
    ax.text(
        0, -1.28,
        rf"$t_w=(D_o-2D_\ell)/3={T_WALL_MM:.3f}\,\mathrm{{mm}}$",
        ha="center", va="top", fontsize=7.2, color=NODE_WALL,
    )

    ax.text(
        5.15, -2.35,
        "polymer  (typical PU,\nnot measured)\n"
        rf"$\rho_p={m.CATHETER_DENSITY_KG_M3:.0f}\,\mathrm{{kg/m^3}}$" "\n"
        rf"$c_{{p,p}}={m.CATHETER_SPECIFIC_HEAT_J_KG_K:.0f}\,\mathrm{{J/kg \cdot K}}$" "\n"
        rf"$k_p={m.CATHETER_THERMAL_CONDUCTIVITY_W_M_K:.2f}\,\mathrm{{W/m \cdot K}}$",
        ha="left", va="center", fontsize=7.4, color=NODE_WALL,
        bbox=BOX, zorder=8,
    )

    ax.set_title(
        "B   Cross-section of one station",
        loc="left", fontsize=11, color=TEXT, pad=8, fontweight="medium",
    )


def draw_equations(ax):
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title(
        "C   Governing equations  (per axial station)",
        loc="left", fontsize=11, color=TEXT, pad=8, fontweight="medium",
    )

    blocks = [
        (9.55, "Energy", [
            r"$C_{\mathrm{water}}\,\mathrm{d}T_{\mathrm{in}}/\mathrm{d}t"
            r"=\dot{m}c_{p,w}(T_{\mathrm{up,in}}-T_{\mathrm{in}})"
            r"+G_{\mathrm{lw}}(T_{\mathrm{wall}}-T_{\mathrm{in}})$",
            r"$C_{\mathrm{water}}\,\mathrm{d}T_{\mathrm{out}}/\mathrm{d}t"
            r"=\dot{m}c_{p,w}(T_{\mathrm{up,out}}-T_{\mathrm{out}})"
            r"+G_{\mathrm{lw}}(T_{\mathrm{wall}}-T_{\mathrm{out}})$",
            r"$C_{\mathrm{wall}}\,\mathrm{d}T_{\mathrm{wall}}/\mathrm{d}t"
            r"=G_{\mathrm{wt}}(T_{\mathrm{tank}}-T_{\mathrm{wall}})"
            r"-G_{\mathrm{lw}}(T_{\mathrm{wall}}-T_{\mathrm{in}})"
            r"-G_{\mathrm{lw}}(T_{\mathrm{wall}}-T_{\mathrm{out}})$",
        ]),
        (6.85, "Heat capacity and conductance", [
            r"$C_{\mathrm{water}}=\rho_w A_\ell\,\Delta z\,c_{p,w}"
            r"\qquad C_{\mathrm{wall}}=\rho_p A_p\,\Delta z\,c_{p,p}$",
            r"$G_{\mathrm{lw}}=K\,U_{\mathrm{lw}}A_{\mathrm{inner}}"
            r"\qquad G_{\mathrm{wt}}=K\,U_{\mathrm{wt}}A_{\mathrm{outer}}$",
            r"$U_{\mathrm{lw}}^{-1}=1/h_{\mathrm{inner}}+t_w/(2k_p)"
            r"\qquad U_{\mathrm{wt}}^{-1}=t_w/(2k_p)+1/h_{\mathrm{tank}}$",
        ]),
        (4.15, "Inner film  (Hausen, laminar thermally developing)", [
            r"$\mathrm{Gz}=\mathrm{Re}\,\mathrm{Pr}\,D_\ell/L"
            r"\qquad \mathrm{Nu}=3.66+0.0668\,\mathrm{Gz}"
            r"/(1+0.04\,\mathrm{Gz}^{2/3})$",
            r"$h_{\mathrm{inner}}=\mathrm{Nu}\,k_w/D_\ell"
            rf"\qquad\mathrm{{nominal:\ Re}}={RE:.0f},\ "
            rf"\mathrm{{Nu}}={NU:.2f},\ "
            rf"h_{{\mathrm{{inner}}}}={H_INNER:.0f}\,\mathrm{{W/m^2 \cdot K}}$",
        ]),
        (1.70, "Calibration  (scales every $G$)", [
            rf"$K(Q)=k_{{\mathrm{{ref}}}}(Q/Q_{{\mathrm{{ref}}}})^n"
            rf"={m.CALIBRATION_K_REF:.4f}\,"
            rf"(Q/{m.CALIBRATION_REFERENCE_FLOW_ML_MIN:.0f})^{{{m.CALIBRATION_N_EXPONENT:.4f}}}$",
            rf"Both lumens share $T_{{\mathrm{{wall}}}}$ (lumen-to-lumen leak).  "
            rf"$K={K_NOM:.2f}$ at $Q={m.VOLUMETRIC_FLOW_RATE_ML_MIN:.0f}\,\mathrm{{mL/min}}$.",
        ]),
    ]
    for y, heading, lines in blocks:
        ax.text(0.25, y, heading, ha="left", va="top",
                fontsize=8.4, color=TEXT, fontweight="medium")
        ax.text(
            0.25, y - 0.38, "\n".join(lines),
            ha="left", va="top", fontsize=8.0, color=MUTED, linespacing=1.65,
        )


def draw_constants(ax):
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3.15)
    ax.axis("off")
    ax.set_title(
        "D   Remaining inputs and assumed constants  (read from dual_lumen_catheter.py)",
        loc="left", fontsize=11, color=TEXT, pad=6, fontweight="medium",
    )

    cols = [
        (0.15, "Water  (assumed at ~15 °C)", MUTED, [
            rf"$\rho_w = {m.WATER_DENSITY_KG_M3:.0f}\,\mathrm{{kg/m^3}}$",
            rf"$c_{{p,w}} = {m.WATER_SPECIFIC_HEAT_J_KG_K:.0f}\,\mathrm{{J/kg \cdot K}}$",
            rf"$k_w = {m.WATER_THERMAL_CONDUCTIVITY_W_M_K:.3f}\,\mathrm{{W/m \cdot K}}$",
            rf"$\mu_w = {m.WATER_DYNAMIC_VISCOSITY_PA_S * 1e3:.2f}\times 10^{{-3}}"
            rf"\,\mathrm{{Pa \cdot s}}$",
        ]),
        (4.10, "Initial conditions and numerics", MUTED, [
            rf"$T_{{\mathrm{{water}}}}(0) = {m.INITIAL_INTERNAL_WATER_TEMPERATURE_C:.0f}\,\mathrm{{^\circ C}}$",
            rf"$T_{{\mathrm{{wall}}}}(0) = {m.INITIAL_CATHETER_TEMPERATURE_C:.0f}\,\mathrm{{^\circ C}}$",
            rf"$t_{{\mathrm{{end}}}} = {m.SIMULATION_DURATION_S:.0f}\,\mathrm{{s}}$"
            rf"    safety factor $={m.SAFETY_FACTOR}$",
            "explicit Euler, first-order upwind;  laminar only ($Re<2300$)",
        ]),
        (8.05, "Calibration  $K(Q)$  (scales every $G$)", MUTED, [
            rf"$k_{{\mathrm{{ref}}}} = {m.CALIBRATION_K_REF:.4f}$"
            rf"    $n = {m.CALIBRATION_N_EXPONENT:.4f}$",
            rf"$Q_{{\mathrm{{ref}}}} = {m.CALIBRATION_REFERENCE_FLOW_ML_MIN:.0f}\,\mathrm{{mL/min}}$",
            rf"$K(Q) = k_{{\mathrm{{ref}}}}\,(Q/Q_{{\mathrm{{ref}}}})^n$",
            rf"source: {m.CALIBRATION_SOURCE}",
        ]),
    ]
    for x, title, color, lines in cols:
        ax.add_patch(FancyBboxPatch(
            (x, 0.12), 3.75, 2.72,
            boxstyle="round,pad=0.04,rounding_size=0.12",
            facecolor="#F4F7FA", edgecolor="#D0D7DE", linewidth=1.0, zorder=1,
        ))
        ax.text(x + 0.18, 2.52, title, ha="left", va="top",
                fontsize=8.0, color=TEXT, fontweight="medium", zorder=2)
        ax.text(
            x + 0.18, 2.12, "\n".join(lines),
            ha="left", va="top", fontsize=7.5, color=color, zorder=2,
            linespacing=1.55,
        )


def main():
    fig = plt.figure(figsize=(15.6, 11.0), facecolor="white")
    fig.suptitle(
        "Dual-lumen catheter model  —  compartments, equations, and inputs",
        fontsize=15, color=TEXT, fontweight="medium", y=0.985,
    )
    fig.text(
        0.5, 0.948,
        "Cold water enters at the proximal end, turns at the distal end, and returns.  "
        "The tank heats the polymer wall along the entire length; the wall heats both lumens.",
        ha="center", va="top", fontsize=9, color=MUTED,
    )

    gs = fig.add_gridspec(
        3, 2, width_ratios=[1.02, 1.08], height_ratios=[1.12, 1.08, 0.52],
        left=0.025, right=0.985, top=0.905, bottom=0.025,
        wspace=0.06, hspace=0.18,
    )
    ax_long = fig.add_subplot(gs[0:2, 0])
    ax_cs = fig.add_subplot(gs[0, 1])
    ax_eq = fig.add_subplot(gs[1, 1])
    ax_const = fig.add_subplot(gs[2, :])
    for a in (ax_long, ax_cs, ax_eq, ax_const):
        a.set_facecolor(BG)
        for spine in a.spines.values():
            spine.set_visible(False)

    draw_longitudinal(ax_long)
    draw_cross_section(ax_cs)
    draw_equations(ax_eq)
    draw_constants(ax_const)

    fig.savefig(OUT, dpi=200, facecolor="white")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
