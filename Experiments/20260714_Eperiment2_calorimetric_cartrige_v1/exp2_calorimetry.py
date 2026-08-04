from pathlib import Path
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

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
C = 4186  # J/kg°C (water)
T_START_C = 37.0  # active cooling phase start (tank)
T_END_C = 32.0    # active cooling phase end (tank)
# Water density ~1000 kg/m^3 -> 1 ml = 0.001 kg, so mdot [kg/s] = flow [ml/s] / 1000


TEMP_FAULT_C = -20.0  # readings at/below this are treated as sensor failure


def blank_after_temp_fault(series: pd.Series, limit_c: float = TEMP_FAULT_C) -> pd.Series:
    """Keep values until the first fault; NaN from that point onward."""
    out = series.astype(float).copy()
    bad = out <= limit_c
    if bad.any():
        out.iloc[bad.argmax() :] = np.nan
    return out


def resolve_flow_cols(df: pd.DataFrame) -> tuple[str, str]:
    """Prefer cart_in/out; fall back to cath_in/out."""
    if "cart_in_c" in df.columns and "cart_out_c" in df.columns:
        return "cart_in_c", "cart_out_c"
    if "cath_in_c" in df.columns and "cath_out_c" in df.columns:
        return "cath_in_c", "cath_out_c"
    raise KeyError(
        "Need cart_in_c/cart_out_c or cath_in_c/cath_out_c columns"
    )


def process_file(csv_path: Path) -> None:
    out_png = FOLDER / csv_path.name.replace("sensor_log_", "calorimetry_").replace(".csv", ".png")
    if out_png.exists():
        print(f"ERROR: output already exists, skipping: {out_png.name}")
        return

    df = load_sensor_csv(csv_path)

    in_col, out_col = resolve_flow_cols(df)
    in_label = in_col.replace("_c", "")
    out_label = out_col.replace("_c", "")

    temp_cols = ["tank_c", in_col, out_col]
    if "tubing_c" in df.columns:
        temp_cols.append("tubing_c")
    if "room_temp_c" in df.columns:
        temp_cols.append("room_temp_c")
    for col in temp_cols:
        df[col] = blank_after_temp_fault(df[col])

    ts = df.set_index("timestamp")
    temp = ts["tank_c"].dropna()
    if temp.empty:
        return

    # --- ACTIVE COOLING PERIOD: cool from 37°C down to 32°C (tank sensor) ---
    # Last crossings select the final pass if the log contains rewarming.
    window = find_cooling_window(temp, T_START_C, T_END_C)
    if window is None:
        return
    start_time, end_time = window.start, window.end

    # METHOD 1 - tank calorimetry
    tank_result = tank_calorimetry(
        temp, window, mass_kg=MASS_KG, specific_heat_j_kg_k=C
    )
    duration_tank_s = tank_result.duration_s
    delta_T_tank = tank_result.delta_temp_c
    q_tank_j = tank_result.energy_j
    p_tank_avg_w = tank_result.average_power_w

    # METHOD 2 - flow calorimetry
    df["mdot_kg_s"] = df["pump_flow_ml_per_s"] / 1000.0
    df["delta_T_flow"] = df[in_col] - df[out_col]
    df["power_w"] = flow_power(
        df["pump_flow_ml_per_s"], df[in_col], df[out_col],
        specific_heat_j_kg_k=C,
    )

    active = (df["timestamp"] >= start_time) & (df["timestamp"] <= end_time)
    df_active = df.loc[active].copy()
    df_active = df_active.dropna(subset=[in_col, out_col, "power_w"])
    if len(df_active) < 2:
        return

    duration_flow_s = (
        df_active["timestamp"].iloc[-1] - df_active["timestamp"].iloc[0]
    ).total_seconds()
    if duration_flow_s <= 0:
        return

    p_flow_avg_w = time_weighted_mean(
        df_active["power_w"], df_active["timestamp"]
    )
    q_flow_j = p_flow_avg_w * duration_flow_s

    mdot_mean = df_active["mdot_kg_s"].mean()
    delta_T_flow_mean = df_active["delta_T_flow"].mean()
    flow_ml_min_mean = df_active["pump_flow_ml_per_s"].mean() * 60.0

    # COMBINED PLOT
    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(9, 7))

    ax1.plot(df["timestamp"], df["tank_c"], color="tab:orange", label="tank")
    if "room_temp_c" in df.columns:
        room_avg = float(df["room_temp_c"].mean())
        ax1.plot([], [], " ", label=f"room avg = {room_avg:.2f} °C")
    ax1.axvspan(start_time, end_time, color="tab:gray", alpha=0.15, label="Active cooling period")
    ax1.axhline(T_START_C, color="black", linestyle=":", alpha=0.5)
    ax1.axhline(T_END_C, color="black", linestyle=":", alpha=0.5)
    ax1.set_ylabel("Temperature (°C)")
    ax1.set_title(f"Tank calorimetry — tank temperature\n{csv_path.name}")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="best")

    footer1 = (
        rf"$m = {MASS_KG}\,\mathrm{{kg}},\quad c = {C}\,\mathrm{{J/kg^\circ C}}$"
        "        "
        rf"$\Delta T = {delta_T_tank:.2f}\,\mathrm{{^\circ C}},\quad "
        rf"\Delta t = {duration_tank_s:.0f}\,\mathrm{{s}}$"
        "        "
        rf"$Q = m\,c\,\Delta T = {q_tank_j/1000:.1f}\,\mathrm{{kJ}}$"
        "        "
        rf"$P_{{\mathrm{{avg}}}} = \dfrac{{Q}}{{\Delta t}} = {p_tank_avg_w:.1f}\,\mathrm{{W}}$"
    )
    ax1.text(
        0.5, -0.18, footer1, transform=ax1.transAxes,
        ha="center", va="top", fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
    )

    ax2.plot(df["timestamp"], df[in_col], color="tab:red", label=in_label)
    ax2.plot(df["timestamp"], df[out_col], color="tab:green", label=out_label)
    if "tubing_c" in df.columns:
        ax2.plot(df["timestamp"], df["tubing_c"], color="tab:blue", label="tubing")
    ax2.axvspan(start_time, end_time, color="tab:gray", alpha=0.15, label="Active cooling period")
    ax2.set_ylabel("Temperature (°C)")
    ax2.set_xlabel("Time")
    ax2.set_title(f"Flow calorimetry — {in_label} / {out_label}")
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="best")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    footer2 = (
        rf"$\dot{{m}}_{{\mathrm{{avg}}}} = {mdot_mean:.5f}\,\mathrm{{kg/s}}"
        rf"\ ({flow_ml_min_mean:.1f}\,\mathrm{{ml/min}}),\quad "
        rf"c = {C}\,\mathrm{{J/kg^\circ C}}$"
        "        "
        rf"$\Delta T_{{\mathrm{{avg}}}} = {delta_T_flow_mean:.2f}\,\mathrm{{^\circ C}},\quad "
        rf"\Delta t = {duration_flow_s:.0f}\,\mathrm{{s}}$"
        "        "
        rf"$Q = \int \dot{{m}}\,c\,(T_{{\mathrm{{in}}}}-T_{{\mathrm{{out}}}})\,dt"
        rf" = {q_flow_j/1000:.1f}\,\mathrm{{kJ}}$"
        "        "
        rf"$P_{{\mathrm{{avg}}}} = \dfrac{{Q}}{{\Delta t}} = {p_flow_avg_w:.1f}\,\mathrm{{W}}$"
    )
    ax2.text(
        0.5, -0.28, footer2, transform=ax2.transAxes,
        ha="center", va="top", fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
    )

    fig.tight_layout()
    fig.subplots_adjust(hspace=0.55, bottom=0.14)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


for csv_path in sorted(FOLDER.glob("*.csv")):
    process_file(csv_path)
