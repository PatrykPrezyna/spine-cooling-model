"""Plot power draining from the thermos for one ice-bucket run."""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

FOLDER = Path(__file__).resolve().parent
CSV_PATH = FOLDER / "sensor_log_20260717_091508_ice_bucket_with_catheder_60rmp.csv"
OUT_PNG = FOLDER / "thermos_power_20260717_091508_ice_bucket_with_catheder_60rmp.png"

MASS_KG = 0.838
C = 4186.0
T_START_C = 37.0
T_END_C = 32.0
SMOOTH_S = 30.0


def active_window(temp: pd.Series) -> tuple[pd.Timestamp, pd.Timestamp]:
    peak_time = temp.idxmax()
    after_peak = temp.loc[peak_time:]
    crossed_start = after_peak[
        (after_peak.shift(1) > T_START_C) & (after_peak <= T_START_C)
    ]
    if len(crossed_start) == 0:
        raise RuntimeError("No downward crossing of T_START_C")
    start_time = crossed_start.index[-1]
    after_start = temp.loc[start_time:]
    crossed_end = after_start[
        (after_start.shift(1) > T_END_C) & (after_start <= T_END_C)
    ]
    if len(crossed_end) == 0:
        raise RuntimeError("No downward crossing of T_END_C")
    end_time = crossed_end.index[-1]
    if (end_time - start_time).total_seconds() <= 0:
        raise RuntimeError("Invalid active window duration")
    return start_time, end_time


def main() -> None:
    df = pd.read_csv(CSV_PATH)
    df.columns = [c.strip().replace("\\", "").lower() for c in df.columns]
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    temp = df.set_index("timestamp")["tank_c"].dropna()
    start_time, end_time = active_window(temp)
    duration_s = (end_time - start_time).total_seconds()
    period = temp.loc[start_time:end_time]
    dT_tank = float(period.iloc[0] - period.iloc[-1])
    p_tank_avg = (MASS_KG * C * dT_tank) / duration_s

    t0 = df["timestamp"].iloc[0]
    df["t_s"] = (df["timestamp"] - t0).dt.total_seconds()
    dt_med = float(df["t_s"].diff().median())
    win = max(3, int(SMOOTH_S / max(dt_med, 1e-6)))
    tank_s = df["tank_c"].rolling(win, center=True, min_periods=max(3, win // 3)).mean()
    dTdt = np.gradient(tank_s.to_numpy(), df["t_s"].to_numpy())
    df["p_thermos_w"] = -MASS_KG * C * dTdt

    df["mdot"] = df["pump_flow_ml_per_s"] / 1000.0
    df["p_flow_w"] = df["mdot"] * C * (df["cart_in_c"] - df["cart_out_c"])

    active = (df["timestamp"] >= start_time) & (df["timestamp"] <= end_time)
    a = df.loc[active].dropna(subset=["p_flow_w"])
    t_rel = (a["timestamp"] - a["timestamp"].iloc[0]).dt.total_seconds().to_numpy()
    p_flow_avg = float(np.trapezoid(a["p_flow_w"].to_numpy(), t_rel) / duration_s)

    print(f"Active window: {start_time} -> {end_time} ({duration_s:.0f} s)")
    print(f"dT_tank={dT_tank:.2f} C")
    print(f"P_tank_avg={p_tank_avg:.1f} W")
    print(f"P_flow_avg={p_flow_avg:.1f} W")
    print(f"P_thermos median in window={df.loc[active, 'p_thermos_w'].median():.1f} W")

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(10, 7))

    ax1.plot(df["timestamp"], df["tank_c"], color="tab:orange", lw=1.2, label="tank")
    ax1.axvspan(start_time, end_time, color="tab:gray", alpha=0.15, label="Active 37→32 °C")
    ax1.axhline(T_START_C, color="k", ls=":", alpha=0.45)
    ax1.axhline(T_END_C, color="k", ls=":", alpha=0.45)
    ax1.set_ylabel("Temperature (°C)")
    ax1.set_title("Thermos (tank) temperature")
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="best")

    ax2.plot(
        df["timestamp"],
        df["p_thermos_w"],
        color="tab:purple",
        lw=1.0,
        label=rf"$P_{{\mathrm{{thermos}}}}=-m\,c\,dT/dt$ ({SMOOTH_S:.0f}s smooth)",
    )
    ax2.plot(
        df["timestamp"],
        df["p_flow_w"],
        color="tab:cyan",
        lw=0.8,
        alpha=0.75,
        label=r"$P_{\mathrm{flow}}=\dot{m}\,c\,(T_{\mathrm{in}}-T_{\mathrm{out}})$",
    )
    ax2.axhline(
        p_tank_avg,
        color="tab:purple",
        ls="--",
        lw=1.5,
        label=f"P_tank avg (37→32) = {p_tank_avg:.1f} W",
    )
    ax2.axhline(
        p_flow_avg,
        color="tab:cyan",
        ls="--",
        lw=1.2,
        label=f"P_flow avg (37→32) = {p_flow_avg:.1f} W",
    )
    ax2.axvspan(start_time, end_time, color="tab:gray", alpha=0.15)
    ax2.axhline(0, color="k", lw=0.6, alpha=0.4)
    ax2.set_ylabel("Power (W)")
    ax2.set_xlabel("Time")
    ax2.set_title("Power draining from the thermos")
    y_hi = max(80.0, float(np.nanpercentile(df["p_thermos_w"], 99)) * 1.1)
    ax2.set_ylim(-10, y_hi)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="best", fontsize=8)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    fig.suptitle(
        f"Ice bucket + catheter @ 60 rpm — thermos drain power\n{CSV_PATH.name}",
        fontsize=11,
    )
    footer = (
        rf"$m={MASS_KG}\,\mathrm{{kg}},\ c={C:.0f}\,\mathrm{{J/kg^\circ C}}$"
        "   |   "
        rf"$\Delta T={dT_tank:.2f}\,\mathrm{{^\circ C}},\ \Delta t={duration_s:.0f}\,\mathrm{{s}}$"
        "   |   "
        rf"$P_{{\mathrm{{tank,avg}}}}=m\,c\,\Delta T/\Delta t={p_tank_avg:.1f}\,\mathrm{{W}}$"
    )
    fig.text(
        0.5,
        0.01,
        footer,
        ha="center",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.9),
    )
    fig.tight_layout()
    fig.subplots_adjust(top=0.90, bottom=0.10)
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {OUT_PNG}")


if __name__ == "__main__":
    main()
