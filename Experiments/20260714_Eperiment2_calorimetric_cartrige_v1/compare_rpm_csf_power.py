"""
Compare CSF cool-down and average cooling power across RPM runs.
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

FOLDER = Path(__file__).resolve().parent
MASS_KG = 0.838
C = 4186.0
T_START_C = 37.0
T_END_C = 32.0

FILES = [
    "sensor_log_20260716_101625_60rmp_v3.csv",
    "sensor_log_20260716_094253_120rmp_v1.csv",
    "sensor_log_20260716_105927_240rmp_v1.csv",
    "sensor_log_20260716_112808_360rmp_v1.csv",
]

COLORS = {
    60: "tab:blue",
    120: "tab:orange",
    240: "tab:green",
    360: "tab:red",
}


def load_csv(csv_path: Path) -> pd.DataFrame:
    return load_sensor_csv(csv_path)


def rpm_label_from_name(name: str) -> int:
    for token in name.replace(".csv", "").split("_"):
        if token.endswith("rmp") or token.endswith("rpm"):
            digits = "".join(ch for ch in token if ch.isdigit())
            if digits:
                return int(digits)
    raise ValueError(f"Could not parse RPM from {name}")


def analyze(csv_path: Path) -> dict:
    df = load_csv(csv_path)
    temp = df.set_index("timestamp")["tank_c"]
    window = find_cooling_window(temp, T_START_C, T_END_C)
    if window is None:
        raise RuntimeError(f"No 37→32 window in {csv_path.name}")
    start_time, end_time = window.start, window.end
    duration_s = window.duration_s

    active = (df["timestamp"] >= start_time) & (df["timestamp"] <= end_time)
    a = df.loc[active].copy()
    a["mdot_kg_s"] = a["pump_flow_ml_per_s"] / 1000.0
    a["dT_cart"] = a["cart_in_c"] - a["cart_out_c"]
    a["power_w"] = flow_power(
        a["pump_flow_ml_per_s"], a["cart_in_c"], a["cart_out_c"],
        specific_heat_j_kg_k=C,
    )
    p_flow_w = time_weighted_mean(
        a["power_w"], a["timestamp"], duration_s=duration_s
    )

    tank_result = tank_calorimetry(
        temp, window, mass_kg=MASS_KG, specific_heat_j_kg_k=C
    )
    p_tank_w = tank_result.average_power_w

    rpm = rpm_label_from_name(csv_path.name)
    full = df.copy()
    t0 = full["timestamp"].iloc[0]
    full["t_min"] = (full["timestamp"] - t0).dt.total_seconds() / 60.0
    a["t_min_active"] = (a["timestamp"] - start_time).dt.total_seconds() / 60.0

    return {
        "file": csv_path.name,
        "label": f"{rpm} rpm",
        "rpm": rpm,
        "duration_s": duration_s,
        "flow_ml_min": float(a["pump_flow_ml_per_s"].mean() * 60.0),
        "P_tank_W": p_tank_w,
        "P_flow_W": p_flow_w,
        "df_full": full,
        "df_active": a,
        "start_time": start_time,
        "end_time": end_time,
    }


def main() -> None:
    rows = [analyze(FOLDER / name) for name in FILES]
    rows = sorted(rows, key=lambda r: r["rpm"])

    print("RPM comparison (active window 37 -> 32 C)")
    print("-" * 72)
    for r in rows:
        print(
            f"{r['label']:8s} | flow={r['flow_ml_min']:6.1f} ml/min | "
            f"dt={r['duration_s']:6.0f} s | "
            f"P_tank={r['P_tank_W']:5.1f} W | P_flow={r['P_flow_W']:5.1f} W"
        )

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [1.4, 1]}
    )

    # CSF cool-down overlay (aligned to active-window start)
    for r in rows:
        a = r["df_active"]
        color = COLORS.get(r["rpm"], "gray")
        ax1.plot(
            a["t_min_active"],
            a["tank_c"],
            color=color,
            lw=1.8,
            label=(
                f"{r['label']}  "
                f"({r['duration_s']:.0f} s, {r['P_tank_W']:.1f} W)"
            ),
        )
    ax1.axhline(T_START_C, color="k", ls=":", alpha=0.4)
    ax1.axhline(T_END_C, color="k", ls=":", alpha=0.4)
    ax1.set_xlabel("Time from 37 °C crossing (min)")
    ax1.set_ylabel("CSF / tank temperature (°C)")
    ax1.set_title("CSF cool-down by pump speed")
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=8, loc="best")

    # Average power bars
    x = np.arange(len(rows))
    w = 0.35
    p_tank = [r["P_tank_W"] for r in rows]
    p_flow = [r["P_flow_W"] for r in rows]
    labels = [r["label"] for r in rows]

    bars1 = ax2.bar(x - w / 2, p_tank, width=w, color="tab:purple", label="P_tank (calorimetry)")
    bars2 = ax2.bar(x + w / 2, p_flow, width=w, color="tab:cyan", label="P_flow (mdot·c·ΔT)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels)
    ax2.set_ylabel("Average power (W)")
    ax2.set_title(f"Average power over {T_START_C:.0f}→{T_END_C:.0f} °C window")
    ax2.grid(True, axis="y", alpha=0.3)
    ax2.legend(fontsize=8)

    for bars in (bars1, bars2):
        for bar in bars:
            h = bar.get_height()
            ax2.annotate(
                f"{h:.1f}",
                xy=(bar.get_x() + bar.get_width() / 2, h),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=8,
            )

    fig.suptitle(
        "Experiment 2 — cartridge + catheter: CSF temp vs average power by RPM",
        fontsize=12,
    )
    fig.tight_layout()
    out = FOLDER / "compare_rpm_csf_power.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
