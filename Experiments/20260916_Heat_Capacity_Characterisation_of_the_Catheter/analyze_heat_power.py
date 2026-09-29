"""Steady heat power and UA for each bath-temperature plateau.

P = m_dot * cp * (T_out - T_in)
UA = P / LMTD, with the bath as a constant-temperature source.

Keyence flow is used when it is above noise. On the shortened-tubing log
the Keyence stays at the zero-flow floor, so flow is taken from the
2026-09-15 gravimetric fit (new Tygon PVC, catheter attached):
    Q [ml/min] = 0.8462 * rpm + 1.86
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({
    "axes.titlesize": 18,
    "axes.labelsize": 15,
    "xtick.labelsize": 15,
    "ytick.labelsize": 15,
})

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import (  # noqa: E402
    WATER_SPECIFIC_HEAT_J_KG_K,
    elapsed_time,
    load_sensor_csv,
)

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"

CP_J_KG_K = WATER_SPECIFIC_HEAT_J_KG_K
RHO_KG_PER_ML = 0.001
RPM_ON = 1.0
KEYENCE_MIN_ML_MIN = 5.0
# Experiments/20260915_Pump_speed_vs_flowrate_Tygon_PVC_Catheter
FLOW_SLOPE_ML_MIN_PER_RPM = 0.8462
FLOW_INTERCEPT_ML_MIN = 1.86
BATH_SMOOTH_S = 25.0
PLATEAU_STD_WIN_S = 40.0
PLATEAU_STD_MAX_C = 0.08
MIN_PLATEAU_S = 90.0
STEADY_TAIL_S = 45.0
SETTLE_BAND = 0.05
BATH_STAGES_C = (28.0, 30.0, 32.0, 34.0, 36.0)
BATH_STAGE_MATCH_C = 0.8
FLOW_COMPARE_RUNS = (
    "short_26cm_22mlmin",
    "short_26cm_50mlmin",
    "short_26cm_70mlmin",
)
CATHETER_COMPARE_RUNS = (
    "original_tubing_50mlmin",
    "short_26cm_50mlmin",
    "other_catheter_50mlmin",
)

RUNS = [
    {
        "name": "original_tubing_50mlmin",
        "label": "Original tubing, ~50 ml/min",
        "csv": RAW_DATA / "20260916_120302_sensors_50mlmin_original_tubing.csv",
        "tubing": "original product length",
        "compare": "original_tubing",
        "fit": False,
    },
    {
        "name": "short_26cm_50mlmin",
        "label": "26 cm tubing, ~50 ml/min",
        "csv": RAW_DATA / "20260916_123901_sensors_50mlmin_26cm.csv",
        "tubing": "26 cm pump-to-catheter",
        "compare": "26cm",
        "fit": True,
    },
    {
        "name": "short_26cm_22mlmin",
        "label": "26 cm tubing, ~22 ml/min",
        "csv": RAW_DATA / "20260918_142602_sensors_22mlmin.csv",
        "tubing": "inlet matches 26 cm run",
        "compare": "26cm",
        "fit": True,
    },
    {
        "name": "short_26cm_70mlmin",
        "label": "26 cm tubing, ~70 ml/min",
        "csv": RAW_DATA / "20260921_093450_sensors_70mlmin.csv",
        "tubing": "inlet matches 26 cm run",
        "compare": "26cm",
        "fit": True,
    },
    {
        "name": "other_catheter_50mlmin",
        "label": "Other catheter, ~50 ml/min",
        "csv": RAW_DATA / "20260921_101547_sensors_50mlmin_other_catheter.csv",
        "tubing": "different catheter",
        "compare": "26cm",
        "fit": False,
    },
]

COMPARE_PLOTS = [
    {
        "compare": "original_tubing",
        "out_name": "heat_power_vs_bath_temperature_original_tubing.png",
        "title": (
            "Original tubing — cooling power vs bath temperature\n"
            "~50 ml/min, last 45 s of each hold"
        ),
    },
    {
        "compare": "26cm",
        "out_name": "heat_power_vs_bath_temperature.png",
        "title": "Cooling power [W] vs Bath temperature",
        "tin_estimates_c": (0.0, -10.0),
    },
]


def commanded_flow_ml_min(rpm: pd.Series | float) -> pd.Series | float:
    return FLOW_SLOPE_ML_MIN_PER_RPM * rpm + FLOW_INTERCEPT_ML_MIN


def heat_power_w(flow_ml_min: pd.Series | float, delta_t_c: pd.Series | float):
    mdot_kg_s = (flow_ml_min / 60.0) * RHO_KG_PER_ML
    return mdot_kg_s * CP_J_KG_K * delta_t_c


def lmtd_c(t_bath: float, t_in: float, t_out: float) -> float:
    d_in = t_bath - t_in
    d_out = t_bath - t_out
    if d_in <= 0 or d_out <= 0:
        return float("nan")
    if abs(d_in - d_out) < 1e-6:
        return d_in
    return (d_in - d_out) / np.log(d_in / d_out)


def load_run(csv_path: Path) -> pd.DataFrame:
    df = load_sensor_csv(csv_path)
    df = df.copy()
    df["t_s"] = elapsed_time(df["timestamp"], unit="s")
    df["t_min"] = df["t_s"] / 60.0
    df["bath_c"] = (df["hot_bath1_c"] + df["hot_bath2_c"]) / 2.0
    df["delta_t_c"] = df["catheter_out_c"] - df["catheter_in_c"]
    df["cmd_ml_min"] = commanded_flow_ml_min(df["peristaltic_pump_set_speed_rpm"])
    keyence = df["flow_sensor_ml_per_min"]
    df["keyence_ok"] = keyence > KEYENCE_MIN_ML_MIN
    df["flow_ml_min"] = np.where(df["keyence_ok"], keyence, df["cmd_ml_min"])
    df["power_w"] = heat_power_w(df["flow_ml_min"], df["delta_t_c"])
    return df


def detect_plateaus(df: pd.DataFrame) -> list[tuple[float, float, float]]:
    """Return (t_start_s, t_end_s, mean_bath_c) while the pump is on."""
    flowing = df["peristaltic_pump_set_speed_rpm"] > RPM_ON
    if not flowing.any():
        return []

    dt = float(np.median(np.diff(df["t_s"].to_numpy())))
    smooth_n = max(3, int(round(BATH_SMOOTH_S / max(dt, 1e-3))))
    std_n = max(5, int(round(PLATEAU_STD_WIN_S / max(dt, 1e-3))))
    bath_smooth = df["bath_c"].rolling(smooth_n, center=True, min_periods=5).mean()
    roll_std = bath_smooth.rolling(std_n, center=True, min_periods=5).std()
    is_plateau = flowing & (roll_std <= PLATEAU_STD_MAX_C)
    is_plateau = is_plateau.fillna(False)

    block = is_plateau.ne(is_plateau.shift()).cumsum()
    plateaus: list[tuple[float, float, float]] = []
    for _, g in df.loc[is_plateau].groupby(block.loc[is_plateau]):
        t0 = float(g["t_s"].iloc[0])
        t1 = float(g["t_s"].iloc[-1])
        if t1 - t0 < MIN_PLATEAU_S:
            continue
        plateaus.append((t0, t1, float(g["bath_c"].mean())))

    merged: list[tuple[float, float, float]] = []
    for t0, t1, bath in plateaus:
        if merged and t0 - merged[-1][1] < 90 and abs(bath - merged[-1][2]) < 0.55:
            p0, _, pb = merged[-1]
            span = df[(df["t_s"] >= p0) & (df["t_s"] <= t1)]
            merged[-1] = (p0, t1, float(span["bath_c"].mean()))
        else:
            merged.append((t0, t1, bath))
    return merged


def settle_s(df: pd.DataFrame, t0_s: float, t1_s: float, delta_ss: float) -> float:
    window = df[(df["t_s"] >= t0_s) & (df["t_s"] <= t1_s)]
    if window.empty:
        return float("nan")
    band = abs(delta_ss) * SETTLE_BAND
    within = (window["delta_t_c"] - delta_ss).abs() <= band
    for idx, ok in within.items():
        if bool(within.loc[idx:].all()):
            return float(window.loc[idx, "t_s"] - t0_s)
    return float("nan")


def measure_steps(df: pd.DataFrame) -> list[dict]:
    steps = []
    for t0, t1, _bath_guess in detect_plateaus(df):
        tail_start = max(t0, t1 - STEADY_TAIL_S)
        tail = df[(df["t_s"] >= tail_start) & (df["t_s"] <= t1)]
        if len(tail) < 8:
            continue
        t_in = float(tail["catheter_in_c"].mean())
        t_out = float(tail["catheter_out_c"].mean())
        t_bath = float(tail["bath_c"].mean())
        t_tip = float(tail["tip_c"].mean())
        q = float(tail["flow_ml_min"].mean())
        q_key = float(tail["flow_sensor_ml_per_min"].mean())
        q_cmd = float(tail["cmd_ml_min"].mean())
        keyence_ok = bool(tail["keyence_ok"].mean() > 0.8)
        dt = t_out - t_in
        power = float(heat_power_w(q, dt))
        dt_lmtd = lmtd_c(t_bath, t_in, t_out)
        ua = power / dt_lmtd if dt_lmtd == dt_lmtd and dt_lmtd > 0 else float("nan")
        eps = dt / (t_bath - t_in) if (t_bath - t_in) > 0.05 else float("nan")
        ntu = -np.log(1.0 - eps) if 0.0 < eps < 0.999 else float("nan")
        mdot_cp = (q / 60.0) * RHO_KG_PER_ML * CP_J_KG_K
        steps.append(
            {
                "t_start_min": t0 / 60.0,
                "t_end_min": t1 / 60.0,
                "duration_s": t1 - t0,
                "steady_start_min": tail_start / 60.0,
                "t_bath_c": t_bath,
                "t_tip_c": t_tip,
                "t_in_c": t_in,
                "t_out_c": t_out,
                "delta_t_c": dt,
                "flow_ml_min": q,
                "flow_keyence_ml_min": q_key,
                "flow_cmd_ml_min": q_cmd,
                "flow_source": "keyence" if keyence_ok else "20260915_fit",
                "rpm": float(tail["peristaltic_pump_set_speed_rpm"].mean()),
                "power_w": power,
                "lmtd_c": dt_lmtd,
                "ua_w_per_k": ua,
                "effectiveness": eps,
                "ntu": ntu,
                "mdot_cp_w_per_k": mdot_cp,
                "settle_s": settle_s(df, t0, t1, dt),
            }
        )
    return steps


def plot_run(df: pd.DataFrame, steps: list[dict], csv_path: Path, label: str) -> Path:
    minutes = df["t_min"]
    fig, axes = plt.subplots(4, 1, figsize=(11, 11), sharex=True, height_ratios=[2, 1.1, 1.1, 1])
    ax_t, ax_dt, ax_p, ax_q = axes

    ax_t.plot(minutes, df["bath_c"], color="tab:red", lw=1.2, label="Bath (mean of 2)")
    ax_t.plot(minutes, df["tip_c"], color="tab:pink", lw=0.9, alpha=0.8, label="Tip")
    ax_t.plot(minutes, df["catheter_in_c"], color="tab:blue", lw=1.2, label="Catheter in")
    ax_t.plot(minutes, df["catheter_out_c"], color="tab:orange", lw=1.2, label="Catheter out")
    ax_t.set_ylabel("Temperature (°C)")
    ax_t.set_title(f"Cooling power vs bath step\n{label} — {csv_path.name}")
    ax_t.grid(True, alpha=0.3)

    ax_dt.plot(minutes, df["delta_t_c"], color="tab:purple", lw=1.2, label="ΔT = out − in")
    ax_dt.set_ylabel("ΔT (°C)")
    ax_dt.grid(True, alpha=0.3)

    ax_p.plot(minutes, df["power_w"], color="tab:brown", lw=1.1, label="P = ṁ cp ΔT")
    ax_p.set_ylabel("Cooling power (W)")
    ax_p.grid(True, alpha=0.3)

    ax_q.plot(minutes, df["flow_sensor_ml_per_min"], color="tab:green", lw=1.1, label="Keyence")
    ax_q.plot(
        minutes,
        df["cmd_ml_min"],
        color="0.35",
        lw=1.1,
        ls="--",
        label=f"Fit {FLOW_SLOPE_ML_MIN_PER_RPM:.4f}·rpm + {FLOW_INTERCEPT_ML_MIN:.2f}",
    )
    ax_q.set_ylabel("Flow (ml/min)")
    ax_q.set_xlabel("Elapsed time (min)")
    ax_q.set_ylim(bottom=-2)
    ax_q.grid(True, alpha=0.3)

    for step in steps:
        for ax in axes:
            ax.axvspan(step["steady_start_min"], step["t_end_min"], color="tab:gray", alpha=0.16)
        ax_p.axhline(step["power_w"], color="0.25", ls=":", lw=0.8)
        ax_p.text(
            (step["steady_start_min"] + step["t_end_min"]) / 2.0,
            step["power_w"] + 0.8,
            f"{step['power_w']:.1f} W\n{step['t_bath_c']:.1f} °C",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    ax_t.legend(loc="center right", framealpha=0.9, fontsize=8)
    ax_dt.legend(loc="lower right", framealpha=0.9)
    ax_p.legend(loc="lower right", framealpha=0.9)
    ax_q.legend(loc="best", framealpha=0.9)
    ax_q.set_xlim(minutes.iloc[0], minutes.iloc[-1])

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DATA / f"heat_power_{csv_path.stem}.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_power_vs_bath(
    results: pd.DataFrame,
    *,
    out_name: str,
    title: str,
    style_overrides: dict | None = None,
    tin_estimates_c: tuple[float, ...] | None = None,
    estimate_run: str = "short_26cm_70mlmin",
    estimate_flow_ml_min: float = 70.0,
) -> Path:
    """Heat power (y) vs measured bath temperature (x) for a comparison group."""
    fig, ax = plt.subplots(figsize=(8, 5))
    styles = {
        "original_tubing_50mlmin": {
            "color": "tab:blue",
            "marker": "o",
            "label": "Original tubing, ~50 ml/min",
            "offset_y": 8,
            "va": "bottom",
        },
        "short_26cm_50mlmin": {
            "color": "tab:orange",
            "marker": "s",
            "label": "50 ml/min",
            "offset_y": -14,
            "va": "top",
        },
        "short_26cm_22mlmin": {
            "color": "tab:green",
            "marker": "^",
            "label": "25 ml/min",
            "offset_y": -14,
            "va": "top",
        },
        "short_26cm_70mlmin": {
            "color": "tab:red",
            "marker": "D",
            "label": "70 ml/min",
            "offset_y": 8,
            "va": "bottom",
        },
        "other_catheter_50mlmin": {
            "color": "tab:brown",
            "marker": "P",
            "label": "Other catheter, ~50 ml/min",
            "offset_y": 8,
            "va": "bottom",
        },
    }
    if style_overrides:
        for run_name, override in style_overrides.items():
            styles[run_name] = {**styles.get(run_name, {}), **override}
    fallback_cycle = [
        {"color": "tab:purple", "marker": "D", "offset_y": 8, "va": "bottom"},
        {"color": "tab:red", "marker": "v", "offset_y": -14, "va": "top"},
    ]
    run_names = [name for name in styles if name in set(results["run"])]
    run_names.extend(name for name in results["run"].unique() if name not in styles)
    for i, run_name in enumerate(run_names):
        group = results[results["run"] == run_name].sort_values("t_bath_c")
        if group.empty:
            continue
        style = styles.get(run_name, {
            **fallback_cycle[i % len(fallback_cycle)],
            "label": str(group["label"].iloc[0]),
        })
        ax.plot(
            group["t_bath_c"],
            group["power_w"],
            color=style["color"],
            marker=style["marker"],
            markersize=8,
            linewidth=1.4,
            label=style["label"],
            zorder=3,
        )
        for _, row in group.iterrows():
            ax.annotate(
                f"{row['power_w']:.1f} W",
                (row["t_bath_c"], row["power_w"]),
                textcoords="offset points",
                xytext=(0, style["offset_y"]),
                ha="center",
                va=style["va"],
                fontsize=8,
                color=style["color"],
            )

    ymax = float(results["power_w"].max())
    estimate_styles = (
        {"color": "tab:red", "ls": "--", "marker": "o", "offset_y": 8, "va": "bottom"},
        {"color": "0.25", "ls": ":", "marker": "v", "offset_y": 8, "va": "bottom"},
    )
    if tin_estimates_c:
        ref = results[results["run"] == estimate_run].sort_values("t_bath_c")
        if not ref.empty:
            t_bath = ref["t_bath_c"].to_numpy()
            ua = ref["ua_w_per_k"].to_numpy()
            for t_in, est in zip(tin_estimates_c, estimate_styles):
                p_est = predicted_power_w(estimate_flow_ml_min, t_bath, t_in, ua)
                ymax = max(ymax, float(np.max(p_est)))
                tin_label = f"{t_in:.0f}" if t_in == int(t_in) else f"{t_in:g}"
                ax.plot(
                    t_bath,
                    p_est,
                    color=est["color"],
                    ls=est["ls"],
                    marker=est["marker"],
                    markersize=7,
                    markerfacecolor="white",
                    linewidth=1.4,
                    label=f"estimation, T_in = {tin_label} °C",
                    zorder=2,
                )
                for x, y in zip(t_bath, p_est):
                    ax.annotate(
                        f"{y:.1f} W",
                        (x, y),
                        textcoords="offset points",
                        xytext=(0, est["offset_y"]),
                        ha="center",
                        va=est["va"],
                        fontsize=8,
                        color=est["color"],
                    )
                print(
                    f"70 ml/min estimate T_in={t_in:.0f} C: "
                    + ", ".join(
                        f"{tb:.1f}C={p:.1f} W" for tb, p in zip(t_bath, p_est)
                    )
                )

    ax.set_xlabel("Bath temperature (°C)")
    ax.set_ylabel("Cooling power (W)")
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(
        loc="lower right" if tin_estimates_c else "upper left",
        framealpha=0.9,
        fontsize=9,
    )
    ax.set_ylim(0, ymax * 1.14)
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DATA / out_name
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def mdot_cp_w_per_k(flow_ml_min: pd.Series | float):
    return (flow_ml_min / 60.0) * RHO_KG_PER_ML * CP_J_KG_K


def predicted_power_w(flow_ml_min, t_bath_c: float, t_in_c: float, ua_w_per_k: float):
    """P = ṁ cp (T_bath − T_in) (1 − exp(−UA / ṁ cp)) for a constant-T bath."""
    cap = mdot_cp_w_per_k(flow_ml_min)
    ntu = ua_w_per_k / cap
    eps = 1.0 - np.exp(-ntu)
    return cap * eps * (t_bath_c - t_in_c)


def steps_at_bath_stages(
    results: pd.DataFrame,
    stages: tuple[float, ...] = BATH_STAGES_C,
    max_abs_c: float = BATH_STAGE_MATCH_C,
) -> pd.DataFrame:
    """Nearest hold to each nominal bath stage, per run."""
    rows = []
    for _, group in results.groupby("run"):
        for target in stages:
            idx = (group["t_bath_c"] - target).abs().idxmin()
            row = group.loc[idx]
            if abs(float(row["t_bath_c"]) - target) <= max_abs_c:
                rec = row.to_dict()
                rec["bath_stage_c"] = target
                rows.append(rec)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def plot_delta_t_vs_bath(results: pd.DataFrame) -> Path:
    """Catheter out − in at each bath hold for the 26 cm flow-rate set."""
    measured = steps_at_bath_stages(results)
    measured = measured[measured["run"].isin(FLOW_COMPARE_RUNS)]
    if measured.empty:
        raise ValueError("no ΔT steps to plot")

    styles = {
        "short_26cm_22mlmin": {
            "color": "tab:green",
            "marker": "^",
            "label": "26 cm tubing, ~22 ml/min",
            "offset_y": 8,
            "va": "bottom",
        },
        "short_26cm_50mlmin": {
            "color": "tab:orange",
            "marker": "s",
            "label": "26 cm tubing, ~50 ml/min",
            "offset_y": 8,
            "va": "bottom",
        },
        "short_26cm_70mlmin": {
            "color": "tab:red",
            "marker": "D",
            "label": "26 cm tubing, ~70 ml/min",
            "offset_y": -14,
            "va": "top",
        },
    }

    fig, ax = plt.subplots(figsize=(8, 5))
    for run_name in FLOW_COMPARE_RUNS:
        group = measured[measured["run"] == run_name].sort_values("t_bath_c")
        if group.empty:
            continue
        style = styles[run_name]
        ax.plot(
            group["t_bath_c"],
            group["delta_t_c"],
            color=style["color"],
            marker=style["marker"],
            markersize=8,
            linewidth=1.4,
            label=style["label"],
            zorder=3,
        )
        for _, row in group.iterrows():
            ax.annotate(
                f"{row['delta_t_c']:.2f} °C",
                (row["t_bath_c"], row["delta_t_c"]),
                textcoords="offset points",
                xytext=(0, style["offset_y"]),
                ha="center",
                va=style["va"],
                fontsize=8,
                color=style["color"],
            )

    ax.set_xlabel("Bath temperature (°C)")
    ax.set_ylabel("Catheter out − catheter in (°C)")
    ax.set_title(
        "26 cm tubing — catheter out − in vs bath temperature\n"
        "28 / 30 / 32 / 34 / 36 °C holds, last 45 s"
    )
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", framealpha=0.9)
    ax.set_ylim(0, float(measured["delta_t_c"].max()) * 1.18)
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DATA / "delta_t_vs_bath_temperature.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_ua_vs_bath(results: pd.DataFrame) -> Path:
    """UA at each bath hold for the 26 cm flow-rate set."""
    measured = steps_at_bath_stages(results)
    measured = measured[measured["run"].isin(FLOW_COMPARE_RUNS)]
    if measured.empty:
        raise ValueError("no UA steps to plot")

    styles = {
        "short_26cm_22mlmin": {
            "color": "tab:green",
            "marker": "^",
            "label": "26 cm tubing, ~22 ml/min",
            "offset_y": -14,
            "va": "top",
        },
        "short_26cm_50mlmin": {
            "color": "tab:orange",
            "marker": "s",
            "label": "26 cm tubing, ~50 ml/min",
            "offset_y": -14,
            "va": "top",
        },
        "short_26cm_70mlmin": {
            "color": "tab:red",
            "marker": "D",
            "label": "26 cm tubing, ~70 ml/min",
            "offset_y": 8,
            "va": "bottom",
        },
    }

    fig, ax = plt.subplots(figsize=(8, 5))
    for run_name in FLOW_COMPARE_RUNS:
        group = measured[measured["run"] == run_name].sort_values("t_bath_c")
        if group.empty:
            continue
        style = styles[run_name]
        ax.plot(
            group["t_bath_c"],
            group["ua_w_per_k"],
            color=style["color"],
            marker=style["marker"],
            markersize=8,
            linewidth=1.4,
            label=style["label"],
            zorder=3,
        )
        for _, row in group.iterrows():
            ax.annotate(
                f"{row['ua_w_per_k']:.2f}",
                (row["t_bath_c"], row["ua_w_per_k"]),
                textcoords="offset points",
                xytext=(0, style["offset_y"]),
                ha="center",
                va=style["va"],
                fontsize=8,
                color=style["color"],
            )

    ax.set_xlabel("Bath temperature (°C)")
    ax.set_ylabel("UA (W/K)")
    ax.set_title(
        "26 cm tubing — UA vs bath temperature\n"
        "28 / 30 / 32 / 34 / 36 °C holds, last 45 s"
    )
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower left", framealpha=0.9)
    ua_min = float(measured["ua_w_per_k"].min())
    ua_max = float(measured["ua_w_per_k"].max())
    ax.set_ylim(max(0.0, ua_min - 0.25), ua_max + 0.25)
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DATA / "ua_vs_bath_temperature.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


def nearest_bath_steps(results: pd.DataFrame, t_bath_c: float) -> pd.DataFrame:
    rows = []
    for run_name, group in results.groupby("run"):
        idx = (group["t_bath_c"] - t_bath_c).abs().idxmin()
        rows.append(group.loc[idx])
    return pd.DataFrame(rows).sort_values("flow_ml_min")


def plot_power_vs_flow(
    results: pd.DataFrame,
    *,
    t_bath_c: float = 36.0,
    flow_step_ml_min: float = 10.0,
) -> Path:
    """Measured 36 °C setpoints plus predicted P every 10 ml/min."""
    measured = nearest_bath_steps(results, t_bath_c)
    measured = measured[measured["run"] != "other_catheter_50mlmin"]
    if measured.empty:
        raise ValueError("no bath steps to plot")

    t_bath = float(measured["t_bath_c"].mean())
    fit = measured[measured["fit"] == True] if "fit" in measured.columns else measured
    if fit.empty:
        fit = measured
    q_max = max(
        80.0,
        float(np.ceil(measured["flow_ml_min"].max() / flow_step_ml_min) * flow_step_ml_min),
    )
    q_pred = np.arange(flow_step_ml_min, q_max + 0.1, flow_step_ml_min)
    t_in_pred = np.interp(q_pred, fit["flow_ml_min"], fit["t_in_c"])
    ua_pred = np.interp(q_pred, fit["flow_ml_min"], fit["ua_w_per_k"])
    p_pred = predicted_power_w(q_pred, t_bath, t_in_pred, ua_pred)

    styles = {
        "short_26cm_50mlmin": {"color": "tab:orange", "marker": "s", "label": "50 ml/min"},
        "short_26cm_22mlmin": {"color": "tab:green", "marker": "^", "label": "25 ml/min"},
        "short_26cm_70mlmin": {"color": "tab:red", "marker": "D", "label": "70 ml/min"},
    }

    fig, ax = plt.subplots(figsize=(8.5, 5))
    (h_p,) = ax.plot(
        q_pred,
        p_pred,
        color="0.35",
        ls="--",
        lw=1.3,
        marker="o",
        markersize=6,
        markerfacecolor="white",
        label="estimation",
        zorder=2,
    )
    for q, p in zip(q_pred, p_pred):
        ax.annotate(
            f"{p:.1f}",
            (q, p),
            textcoords="offset points",
            xytext=(0, 7),
            ha="center",
            fontsize=7,
            color="0.35",
        )

    measured_handles = []
    for _, row in measured.iterrows():
        style = styles.get(row["run"], {"color": "tab:blue", "marker": "o"})
        h = ax.scatter(
            row["flow_ml_min"],
            row["power_w"],
            color=style["color"],
            marker=style["marker"],
            s=80,
            zorder=4,
            label=style.get("label", row["label"]),
        )
        ax.annotate(
            f"{row['power_w']:.1f} W",
            (row["flow_ml_min"], row["power_w"]),
            textcoords="offset points",
            xytext=(8, 6),
            ha="left",
            fontsize=8,
            color=style["color"],
        )
        measured_handles.append(h)

    ax.set_xlabel("Flow (ml/min)")
    ax.set_ylabel("Cooling power (W)")
    ax.set_title(f"Catheter cooling power vs flow at {t_bath:.1f} °C bath")
    ax.grid(True, alpha=0.3)
    ax.set_xlim(0, q_max + flow_step_ml_min)
    ax.set_ylim(0, max(float(p_pred.max()), float(measured["power_w"].max())) * 1.18)
    ax.legend(
        [h_p, *measured_handles],
        [h_p.get_label(), *[h.get_label() for h in measured_handles]],
        loc="lower right",
        framealpha=0.9,
        fontsize=9,
    )
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DATA / "heat_power_vs_flow_36C.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"36 °C traces: T_bath={t_bath:.2f} °C")
    return out


def print_steps(label: str, steps: list[dict]) -> None:
    print(f"\n{label}")
    print(
        f"{'bath':>6} {'t_min':>13} {'Tin':>6} {'Tout':>6} {'dT':>6} "
        f"{'Q':>6} {'P':>6} {'UA':>6} {'eps':>6} {'src':>12}"
    )
    for s in steps:
        print(
            f"{s['t_bath_c']:6.2f} {s['t_start_min']:5.1f}-{s['t_end_min']:5.1f} "
            f"{s['t_in_c']:6.2f} {s['t_out_c']:6.2f} {s['delta_t_c']:6.2f} "
            f"{s['flow_ml_min']:6.1f} {s['power_w']:6.2f} {s['ua_w_per_k']:6.3f} "
            f"{s['effectiveness']:6.3f} {s['flow_source']:>12}"
        )


def main() -> None:
    rows = []
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)

    for run in RUNS:
        csv_path = run["csv"]
        if not csv_path.exists():
            print(f"missing {csv_path}")
            continue
        df = load_run(csv_path)
        steps = measure_steps(df)
        out_png = plot_run(df, steps, csv_path, run["label"])
        print_steps(run["label"], steps)
        print(f"Wrote {out_png}")

        for step in steps:
            rows.append(
                {
                    "run": run["name"],
                    "label": run["label"],
                    "tubing": run["tubing"],
                    "compare": run["compare"],
                    "fit": run.get("fit", True),
                    **step,
                }
            )

    results = pd.DataFrame(rows)
    csv_out = OUTPUT_DATA / "heat_power_by_bath_step.csv"
    results.to_csv(csv_out, index=False, float_format="%.4f")
    print(f"Wrote {csv_out}")
    if results.empty:
        return
    for plot in COMPARE_PLOTS:
        subset = results[results["compare"] == plot["compare"]]
        if plot["compare"] == "26cm":
            subset = subset[subset["run"] != "other_catheter_50mlmin"]
        if subset.empty:
            continue
        out_xy = plot_power_vs_bath(
            subset,
            out_name=plot["out_name"],
            title=plot["title"],
            tin_estimates_c=plot.get("tin_estimates_c"),
        )
        print(f"Wrote {out_xy}")

    cm26 = results[results["compare"] == "26cm"]
    if not cm26.empty:
        out_q = plot_power_vs_flow(cm26, t_bath_c=36.0)
        print(f"Wrote {out_q}")
        out_dt = plot_delta_t_vs_bath(cm26)
        print(f"Wrote {out_dt}")
        out_ua = plot_ua_vs_bath(cm26)
        print(f"Wrote {out_ua}")

    catheters = results[results["run"].isin(CATHETER_COMPARE_RUNS)]
    if not catheters.empty:
        out_cat = plot_power_vs_bath(
            catheters,
            out_name="heat_power_vs_bath_temperature_catheters_50mlmin.png",
            title=(
                "Original vs other catheter at ~50 ml/min\n"
                "last 45 s of each hold"
            ),
            style_overrides={
                "short_26cm_50mlmin": {
                    "label": "26 cm tubing, ~50 ml/min",
                    "offset_y": 8,
                    "va": "bottom",
                },
                "original_tubing_50mlmin": {"offset_y": -14, "va": "top"},
                "other_catheter_50mlmin": {"offset_y": -14, "va": "top"},
            },
        )
        print(f"Wrote {out_cat}")


if __name__ == "__main__":
    main()
