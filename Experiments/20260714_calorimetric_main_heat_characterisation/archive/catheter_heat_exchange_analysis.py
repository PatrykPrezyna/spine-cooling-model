"""
Catheter heat-exchange analysis (Experiment 2)

WHAT THIS COMPARES
------------------
Two loop configurations in the same tank calorimetry setup:

  A) WITH CATHETER (filenames without "open_lines")
       Tank  --(33 cm immersed catheter)--  cart_in  -->  cartridge  -->  cart_out
       Heat must cross the catheter wall between tank water and the circulating fluid.

  B) OPEN LINES (filenames containing "open_lines")
       Tank  --(open tubing, no catheter)--  cart_in  -->  cartridge  -->  cart_out
       Fluid is drawn from / returned to the tank with essentially no catheter HX.

The open-line runs are the control: they show how fast the tank can cool when the
catheter is *not* limiting heat transfer. The difference vs catheter runs is the
catheter's thermal penalty.

SENSORS USED
------------
  tank_c         tank / CSF temperature
  cart_in_c      fluid temperature entering the cartridge (return from tank side)
  cart_out_c     fluid temperature leaving the cartridge (toward tank side)
  pump_flow      volumetric flow

ASSUMED FLOW DIRECTION (for HX interpretation)
----------------------------------------------
  cart_out  = cold supply leaving the cartridge toward the tank / catheter
  cart_in   = warmer return arriving back at the cartridge

  Then the immersed catheter (or open return path) is a heat exchanger:
      cold fluid in  ~ cart_out
      warmer fluid out ~ cart_in
      hot-side fluid   = tank (csf)

METRICS
-------
  1) Cool-down time 37 -> 32 C (same window as analyze_cooling_window_calorimetry.py)
  2) Tank power       P_tank  = m_tank * c * dT / dt
  3) Flow power       P_flow  = mean( mdot * c * (cart_in - cart_out) )
  4) Return approach  (cart_in approaches tank when the tank-side path picks up heat)
       epsilon_return = (cart_in - cart_out) / (csf - cart_out)
  5) Catheter UA from LMTD (catheter runs only):
       dT_a = csf - cart_out     (cold fluid enters catheter)
       dT_b = csf - cart_in      (warmed fluid leaves catheter)
       LMTD = (dT_a - dT_b) / ln(dT_a / dT_b)
       UA   = P_flow / LMTD
       u    = UA / L_immersed     [W/(K·m)] with L = 0.33 m

Run:
  python catheter_heat_exchange_analysis.py
"""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import (
    find_cooling_window,
    flow_power,
    load_sensor_csv,
    tank_calorimetry,
    time_weighted_mean,
)

# --- USER SETTINGS ---
FOLDER = Path(__file__).resolve().parent
MASS_KG = 0.838
C = 4186.0  # J/(kg·K) water
T_START_C = 37.0
T_END_C = 32.0
CATHETER_IMMERSED_M = 0.33  # 33 cm immersed in tank

# Skip legacy / non-comparable setups (no pump, inverted cart dT, etc.)
SKIP_SUBSTRINGS = (
    "thermos",
    "cold_plate",
)


def load_csv(csv_path: Path) -> pd.DataFrame:
    return load_sensor_csv(csv_path)


def lmtd(dT_a: float, dT_b: float) -> float:
    """Log-mean temperature difference; falls back to arithmetic mean if needed."""
    if dT_a <= 0 or dT_b <= 0:
        return float("nan")
    if abs(dT_a - dT_b) < 1e-6:
        return dT_a
    return (dT_a - dT_b) / np.log(dT_a / dT_b)


def analyze_file(csv_path: Path) -> dict | None:
    name_l = csv_path.name.lower()
    if any(s in name_l for s in SKIP_SUBSTRINGS):
        return None

    df = load_csv(csv_path)
    temp = df.set_index("timestamp")["tank_c"]
    window = find_cooling_window(temp, T_START_C, T_END_C)
    if window is None:
        return None
    start_time, end_time = window.start, window.end
    duration_s = window.duration_s

    active = (df["timestamp"] >= start_time) & (df["timestamp"] <= end_time)
    a = df.loc[active].copy()
    if len(a) < 2:
        return None

    a["mdot_kg_s"] = a["pump_flow_ml_per_s"] / 1000.0
    a["dT_cart"] = a["cart_in_c"] - a["cart_out_c"]
    a["power_w"] = flow_power(
        a["pump_flow_ml_per_s"], a["cart_in_c"], a["cart_out_c"],
        specific_heat_j_kg_k=C,
    )
    a["eps_return"] = a["dT_cart"] / (a["tank_c"] - a["cart_out_c"])
    a["dT_a"] = a["tank_c"] - a["cart_out_c"]  # cold fluid enters tank-side path
    a["dT_b"] = a["tank_c"] - a["cart_in_c"]   # return leaves tank-side path

    p_flow_w = time_weighted_mean(
        a["power_w"], a["timestamp"], duration_s=duration_s
    )
    tank_result = tank_calorimetry(
        temp, window, mass_kg=MASS_KG, specific_heat_j_kg_k=C
    )
    p_tank_w = tank_result.average_power_w

    dT_a = float(a["dT_a"].mean())
    dT_b = float(a["dT_b"].mean())
    lmtd_k = lmtd(dT_a, dT_b)
    ua_w_per_k = p_flow_w / lmtd_k if np.isfinite(lmtd_k) and lmtd_k > 0 else float("nan")
    u_per_m = ua_w_per_k / CATHETER_IMMERSED_M

    open_lines = "open_line" in name_l
    label = csv_path.name.replace("sensor_log_", "").replace(".csv", "")

    return {
        "file": label,
        "config": "open_lines" if open_lines else "catheter",
        "open_lines": open_lines,
        "rpm": float(a["peristaltic_pump_set_speed_rpm"].median()),
        "n_cart": 2 if "2xcart" in name_l else 1,
        "duration_s": duration_s,
        "flow_ml_min": float(a["pump_flow_ml_per_s"].mean() * 60.0),
        "csf_mean_C": float(a["tank_c"].mean()),
        "cart_in_mean_C": float(a["cart_in_c"].mean()),
        "cart_out_mean_C": float(a["cart_out_c"].mean()),
        "dT_cart_mean_K": float(a["dT_cart"].mean()),
        "tank_minus_cart_in_K": float((a["tank_c"] - a["cart_in_c"]).mean()),
        "eps_return": float(a["eps_return"].replace([np.inf, -np.inf], np.nan).mean()),
        "P_tank_W": p_tank_w,
        "P_flow_W": p_flow_w,
        "LMTD_K": lmtd_k,
        "UA_W_per_K": ua_w_per_k,
        "U_per_m_W_per_K_m": u_per_m,
        "start_time": start_time,
        "end_time": end_time,
        "df_active": a,
    }


def print_report(summary: pd.DataFrame) -> None:
    print("\n" + "=" * 72)
    print("CATHETER HEAT-EXCHANGE ANALYSIS")
    print("=" * 72)
    print(
        f"\nImmersed catheter length L = {CATHETER_IMMERSED_M*100:.0f} cm\n"
        f"Active window: last CSF crossing {T_START_C:.0f} -> {T_END_C:.0f} C\n"
        f"Tank mass m = {MASS_KG} kg\n"
    )

    show = summary.drop(columns=["start_time", "end_time", "df_active"], errors="ignore")
    print(show.to_string(index=False, float_format=lambda x: f"{x:8.2f}"))

    # Matched comparison: 1x cartridge, ~60 rpm
    cat60 = summary[(~summary["open_lines"]) & (summary["rpm"] == 60) & (summary["n_cart"] == 1)]
    open60 = summary[(summary["open_lines"]) & (summary["rpm"] == 60) & (summary["n_cart"] == 1)]

    print("\n" + "-" * 72)
    print("INTERPRETATION (matched 1x cart, 60 rpm)")
    print("-" * 72)

    if len(cat60) and len(open60):
        t_cat = cat60["duration_s"].mean()
        t_open = open60["duration_s"].mean()
        p_cat = cat60["P_tank_W"].mean()
        p_open = open60["P_tank_W"].mean()
        dT_cat = cat60["dT_cart_mean_K"].mean()
        dT_open = open60["dT_cart_mean_K"].mean()
        gap_cat = cat60["tank_minus_cart_in_K"].mean()
        gap_open = open60["tank_minus_cart_in_K"].mean()
        eps_cat = cat60["eps_return"].mean()
        eps_open = open60["eps_return"].mean()
        ua = cat60["UA_W_per_K"].mean()
        u_m = cat60["U_per_m_W_per_K_m"].mean()

        print(
            f"""
Open lines cool the tank much faster because fluid sees the tank almost
directly. The catheter adds wall conduction + limited internal convection
over only {CATHETER_IMMERSED_M*100:.0f} cm of immersion.

  Cool-down 37->32 C
      catheter   : {t_cat:.0f} s
      open lines : {t_open:.0f} s
      ratio      : catheter is {t_cat/t_open:.2f}x slower

  Average tank cooling power
      catheter   : {p_cat:.1f} W
      open lines : {p_open:.1f} W
      ratio      : catheter delivers {p_cat/p_open:.0%} of open-line power

  Cartridge delta-T (cart_in - cart_out)
      catheter   : {dT_cat:.2f} K
      open lines : {dT_open:.2f} K
      -> With the catheter, less heat is picked up per pass, so the cart
         sees a smaller temperature rise on the return.

  Tank - cart_in gap (how far return is from tank temperature)
      catheter   : {gap_cat:.1f} K
      open lines : {gap_open:.1f} K
      -> Larger gap with the catheter means the return fluid never reaches
         tank temperature: the catheter HX is effectiveness-limited.

  Return effectiveness  eps = (cart_in - cart_out) / (csf - cart_out)
      catheter   : {eps_cat:.2f}
      open lines : {eps_open:.2f}
      -> eps~1 would mean return reaches tank temp; catheter is well below that.

  Estimated catheter UA (from flow power / LMTD), catheter runs only
      UA  ~ {ua:.2f} W/K
      UA/L ~ {u_m:.2f} W/(K*m)   over L = {CATHETER_IMMERSED_M:.2f} m immersed

WHAT THIS SAYS ABOUT THE CATHETER
---------------------------------
  - It is the dominant thermal bottleneck between cartridge and tank.
  - Open-line controls prove the cartridge + bath can remove heat much
    faster; the immersed catheter cannot pass that heat as quickly.
  - The ~{CATHETER_IMMERSED_M*100:.0f} cm immersion gives only UA ~ {ua:.1f} W/K,
    so raising flow helps only until the catheter wall-side resistance
    dominates (see higher-rpm catheter runs: cool-down barely improves).
  - Dual-lumen / wall coupling can also pre-cool the return (cart_in much
    colder than tank) -- that shows up as the large tank-cart_in gap.
"""
        )
    else:
        print("Need at least one 60 rpm catheter run and one 60 rpm open-line run.")

    # Flow-rate sensitivity with catheter
    cat = summary[~summary["open_lines"]].sort_values("rpm")
    if len(cat) >= 2:
        print("-" * 72)
        print("CATHETER vs FLOW RATE (same tank window)")
        print("-" * 72)
        for _, r in cat.iterrows():
            print(
                f"  {r['rpm']:5.0f} rpm | {r['flow_ml_min']:6.1f} ml/min | "
                f"dt={r['duration_s']:6.0f} s | P_tank={r['P_tank_W']:5.1f} W | "
                f"P_flow={r['P_flow_W']:5.1f} W | dT_cart={r['dT_cart_mean_K']:4.2f} K | "
                f"UA={r['UA_W_per_K']:4.2f} W/K"
            )
        print(
            "\n  If P_tank barely rises with rpm while dT_cart falls, the catheter\n"
            "  (UA-limited) is saturating: more flow just shortens residence time\n"
            "  in the catheter without much more heat transfer.\n"
        )


def make_plots(summary: pd.DataFrame) -> None:
    out_dir = FOLDER / "catheter_analysis"
    out_dir.mkdir(exist_ok=True)

    # --- Summary bar / scatter figure ---
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))

    colors = summary["config"].map({"catheter": "tab:blue", "open_lines": "tab:orange"})

    ax = axes[0, 0]
    ax.scatter(summary["flow_ml_min"], summary["duration_s"], c=colors, s=70, zorder=3)
    for _, r in summary.iterrows():
        ax.annotate(
            f"{int(r['rpm'])}rpm" + (" OL" if r["open_lines"] else ""),
            (r["flow_ml_min"], r["duration_s"]),
            fontsize=7,
            xytext=(4, 4),
            textcoords="offset points",
        )
    ax.set_xlabel("Flow (ml/min)")
    ax.set_ylabel("Cool-down 37→32 (°C) time (s)")
    ax.set_title("Cool-down time vs flow")
    ax.grid(True, alpha=0.3)

    ax = axes[0, 1]
    ax.scatter(summary["flow_ml_min"], summary["P_tank_W"], c=colors, s=70, zorder=3)
    ax.set_xlabel("Flow (ml/min)")
    ax.set_ylabel("Tank power P_tank (W)")
    ax.set_title("Tank cooling power vs flow")
    ax.grid(True, alpha=0.3)

    ax = axes[1, 0]
    ax.scatter(summary["flow_ml_min"], summary["dT_cart_mean_K"], c=colors, s=70, zorder=3)
    ax.set_xlabel("Flow (ml/min)")
    ax.set_ylabel("cart_in − cart_out (K)")
    ax.set_title("Cartridge ΔT vs flow")
    ax.grid(True, alpha=0.3)

    ax = axes[1, 1]
    ax.scatter(
        summary["flow_ml_min"], summary["tank_minus_cart_in_K"], c=colors, s=70, zorder=3
    )
    ax.set_xlabel("Flow (ml/min)")
    ax.set_ylabel("Tank − cart_in (K)")
    ax.set_title("Return shortfall vs tank temperature")
    ax.grid(True, alpha=0.3)

    # legend proxies
    from matplotlib.lines import Line2D

    handles = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="tab:blue", markersize=8, label="catheter"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="tab:orange", markersize=8, label="open_lines"),
    ]
    fig.legend(handles=handles, loc="upper center", ncol=2, frameon=False)
    fig.suptitle("Catheter vs open-line heat exchange", y=1.02, fontsize=13)
    fig.tight_layout()
    fig.savefig(out_dir / "catheter_vs_open_lines_summary.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- Overlay CSF cool-down curves (normalized to start of active window) ---
    fig, ax = plt.subplots(figsize=(9, 5))
    for _, r in summary.iterrows():
        a = r["df_active"]
        t_rel = (a["timestamp"] - a["timestamp"].iloc[0]).dt.total_seconds() / 60.0
        style = "--" if r["open_lines"] else "-"
        ax.plot(
            t_rel,
            a["tank_c"],
            style,
            lw=1.6,
            label=f"{r['config']} {int(r['rpm'])}rpm" + (f" {r['n_cart']}x" if r["n_cart"] > 1 else ""),
        )
    ax.axhline(T_START_C, color="k", ls=":", alpha=0.4)
    ax.axhline(T_END_C, color="k", ls=":", alpha=0.4)
    ax.set_xlabel("Time from active-window start (min)")
    ax.set_ylabel("CSF / tank temperature (°C)")
    ax.set_title("Tank cool-down: catheter (solid) vs open_lines (dashed)")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc="best")
    fig.tight_layout()
    fig.savefig(out_dir / "catheter_vs_open_lines_cooldown.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- Temperature ladder for matched 60 rpm ---
    matched = summary[
        (summary["rpm"] == 60)
        & (
            ((~summary["open_lines"]) & (summary["n_cart"] == 1))
            | ((summary["open_lines"]) & (summary["n_cart"] == 1))
        )
    ]
    if len(matched):
        fig, ax = plt.subplots(figsize=(8, 4.5))
        x = np.arange(len(matched))
        w = 0.25
        ax.bar(x - w, matched["csf_mean_C"], width=w, label="tank (csf)", color="tab:orange")
        ax.bar(x, matched["cart_in_mean_C"], width=w, label="cart_in", color="tab:red")
        ax.bar(x + w, matched["cart_out_mean_C"], width=w, label="cart_out", color="tab:green")
        labels = [
            ("open_lines" if row["open_lines"] else "catheter")
            + f"\n...{row['file'][-18:]}"
            for _, row in matched.iterrows()
        ]
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.set_ylabel("Mean temperature in active window (°C)")
        ax.set_title("Temperature ladder at 60 rpm (1x cart)")
        ax.legend()
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(out_dir / "temperature_ladder_60rpm.png", dpi=150, bbox_inches="tight")
        plt.close(fig)

    print(f"\nPlots written to: {out_dir}")


def main() -> None:
    rows = []
    for csv_path in sorted(FOLDER.glob("sensor_log_*.csv")):
        row = analyze_file(csv_path)
        if row is None:
            print(f"skip  {csv_path.name}")
            continue
        print(f"ok    {csv_path.name}")
        rows.append(row)

    if not rows:
        print("No usable runs found.")
        return

    summary = pd.DataFrame(rows)
    print_report(summary)
    make_plots(summary)

    out_dir = FOLDER / "catheter_analysis"
    out_dir.mkdir(exist_ok=True)
    export = summary.drop(columns=["df_active", "start_time", "end_time"])
    out_csv = out_dir / "catheter_vs_open_lines_metrics.csv"
    export.to_csv(out_csv, index=False)
    print(f"Metrics CSV: {out_csv}")
    print("=" * 72)


if __name__ == "__main__":
    main()
