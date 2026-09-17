"""Plot catheter inlet/outlet temperature and flow vs time.

Reads every CSV in raw_data/ and writes one PNG per log to output_data/.
Marks the flow-on pulse, the last 15 s of pumping as steady state, and the
time from flow on until ΔT stays within 5% of that plateau.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import (
    ML_PER_MIN_PER_RPM,
    elapsed_time,
    load_sensor_csv,
    rpm_to_flow_ml_min,
)

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"

RPM_ON_THRESHOLD = 1.0
STEADY_TAIL_S = 15.0
SETTLE_BAND = 0.05  # fraction of the ΔT step


@dataclass(frozen=True)
class SteadyState:
    t_on_s: float
    t_off_s: float
    t_settle_s: float
    t_steady_start_s: float
    delta_t_c: float
    t_in_c: float
    t_out_c: float
    delta_t_at_on_c: float


def _output_path(csv_path: Path) -> Path:
    stem = csv_path.stem.replace(" ", "_")
    return OUTPUT_DATA / f"catheter_temp_flow_{stem}.png"


def _longest_flow_on_hold(df: pd.DataFrame) -> pd.DataFrame | None:
    on = df["peristaltic_pump_set_speed_rpm"] > RPM_ON_THRESHOLD
    if not on.any():
        return None
    block = on.ne(on.shift()).cumsum()
    on_id = block[on].value_counts().idxmax()
    return df.loc[block == on_id]


def measure_steady_state(df: pd.DataFrame) -> SteadyState | None:
    hold = _longest_flow_on_hold(df)
    if hold is None or len(hold) < 2:
        return None

    t_s = elapsed_time(df["timestamp"], unit="s")
    t_on_s = float(t_s.loc[hold.index[0]])
    t_off_s = float(t_s.loc[hold.index[-1]])
    t_steady_start_s = max(t_on_s, t_off_s - STEADY_TAIL_S)
    in_hold = (t_s >= t_on_s) & (t_s <= t_off_s)
    in_steady = (t_s >= t_steady_start_s) & (t_s <= t_off_s)

    delta = df["catheter_out_c"] - df["catheter_in_c"]
    delta_t_c = float(delta.loc[in_steady].mean())
    t_in_c = float(df.loc[in_steady, "catheter_in_c"].mean())
    t_out_c = float(df.loc[in_steady, "catheter_out_c"].mean())
    delta_t_at_on_c = float(delta.loc[hold.index[0]])
    band = abs(delta_t_c - delta_t_at_on_c) * SETTLE_BAND

    hold_delta = delta.loc[in_hold]
    hold_t = t_s.loc[in_hold]
    within = (hold_delta - delta_t_c).abs() <= band
    t_settle_s = t_off_s
    for idx, ok in within.items():
        if bool(within.loc[idx:].all()):
            t_settle_s = float(hold_t.loc[idx])
            break

    return SteadyState(
        t_on_s=t_on_s,
        t_off_s=t_off_s,
        t_settle_s=t_settle_s,
        t_steady_start_s=t_steady_start_s,
        delta_t_c=delta_t_c,
        t_in_c=t_in_c,
        t_out_c=t_out_c,
        delta_t_at_on_c=delta_t_at_on_c,
    )


def plot_file(csv_path: Path) -> Path:
    df = load_sensor_csv(csv_path)
    minutes = elapsed_time(df["timestamp"], unit="min")
    commanded_ml_min = rpm_to_flow_ml_min(
        df["peristaltic_pump_set_speed_rpm"], ML_PER_MIN_PER_RPM
    )
    delta = df["catheter_out_c"] - df["catheter_in_c"]
    ss = measure_steady_state(df)

    fig, (ax_t, ax_dt, ax_q) = plt.subplots(
        3, 1, figsize=(11, 9), sharex=True, height_ratios=[2, 1.2, 1]
    )

    ax_t.plot(
        minutes,
        df["catheter_in_c"],
        color="tab:blue",
        linewidth=1.2,
        label="Catheter input",
    )
    ax_t.plot(
        minutes,
        df["catheter_out_c"],
        color="tab:orange",
        linewidth=1.2,
        label="Catheter output",
    )
    ax_t.set_ylabel("Temperature (°C)")
    ax_t.set_title(f"Catheter temperature and flow\n{csv_path.name}")
    ax_t.grid(True, alpha=0.3)

    ax_dt.plot(minutes, delta, color="tab:red", linewidth=1.2, label="ΔT = out − in")
    ax_dt.set_ylabel("ΔT (°C)")
    ax_dt.grid(True, alpha=0.3)

    if ss is not None:
        t_on_min = ss.t_on_s / 60.0
        t_off_min = ss.t_off_s / 60.0
        t_settle_min = ss.t_settle_s / 60.0
        t_steady_min = ss.t_steady_start_s / 60.0
        settle_s = ss.t_settle_s - ss.t_on_s

        for ax in (ax_t, ax_dt, ax_q):
            ax.axvline(t_on_min, color="0.35", linestyle=":", linewidth=1.0)
            ax.axvspan(t_steady_min, t_off_min, color="tab:gray", alpha=0.18)

        ax_t.axvline(
            t_settle_min,
            color="tab:purple",
            linestyle="--",
            linewidth=1.1,
            label="Steady state reached",
        )
        ax_dt.axvline(t_settle_min, color="tab:purple", linestyle="--", linewidth=1.1)
        ax_dt.axhline(
            ss.delta_t_c,
            color="0.2",
            linestyle="--",
            linewidth=1.0,
            label=f"Steady ΔT = {ss.delta_t_c:.2f} °C",
        )

        y_arrow = float(df[["catheter_in_c", "catheter_out_c"]].to_numpy().max()) + 0.35
        ax_t.annotate(
            "",
            xy=(t_settle_min, y_arrow),
            xytext=(t_on_min, y_arrow),
            arrowprops=dict(arrowstyle="<->", color="0.2", lw=1.2),
        )
        ax_t.text(
            (t_on_min + t_settle_min) / 2.0,
            y_arrow + 0.15,
            f"{settle_s:.0f} s to steady state",
            ha="center",
            va="bottom",
            fontsize=9,
        )
        ax_t.set_ylim(top=y_arrow + 1.4)

        ax_t.text(
            0.98,
            0.05,
            (
                f"Steady state (last {STEADY_TAIL_S:.0f} s of flow)\n"
                f"ΔT = {ss.delta_t_c:.2f} °C   "
                f"(in {ss.t_in_c:.2f} °C, out {ss.t_out_c:.2f} °C)\n"
                f"Flow on → {SETTLE_BAND:.0%} settle: {settle_s:.0f} s"
            ),
            transform=ax_t.transAxes,
            ha="right",
            va="bottom",
            fontsize=9,
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.85, edgecolor="0.8"),
        )

    ax_t.legend(loc="upper right", framealpha=0.9)
    ax_dt.legend(loc="lower right", framealpha=0.9)

    ax_q.plot(
        minutes,
        df["flow_sensor_ml_per_min"],
        color="tab:green",
        linewidth=1.2,
        label="Keyence",
    )
    ax_q.plot(
        minutes,
        commanded_ml_min,
        color="0.35",
        linewidth=1.2,
        linestyle="--",
        label=f"Commanded (calculated, {ML_PER_MIN_PER_RPM:.4f} ml/min per rpm)",
    )
    ax_q.set_ylabel("Flow (ml/min)")
    ax_q.set_xlabel("Elapsed time (min)")
    ax_q.grid(True, alpha=0.3)
    ax_q.set_ylim(bottom=0)
    ax_q.legend(loc="best", framealpha=0.9)
    ax_q.set_xlim(minutes.iloc[0], minutes.iloc[-1])
    ax_rpm = ax_q.secondary_yaxis(
        "right",
        functions=(
            lambda ml: ml / ML_PER_MIN_PER_RPM,
            lambda rpm: rpm * ML_PER_MIN_PER_RPM,
        ),
    )
    ax_rpm.set_ylabel("Pump set speed (rpm)")

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = _output_path(csv_path)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"\n{csv_path.name}  ({minutes.iloc[-1]:.1f} min, {len(df)} samples)")
    summary = df[
        ["catheter_in_c", "catheter_out_c", "flow_sensor_ml_per_min"]
    ].copy()
    summary["commanded_ml_per_min"] = commanded_ml_min
    print(
        summary.describe()
        .loc[["min", "mean", "max"]]
        .to_string(float_format=lambda x: f"{x:8.2f}")
    )
    if ss is not None:
        print(
            f"Steady dT (out-in) = {ss.delta_t_c:.2f} C  "
            f"(in {ss.t_in_c:.2f} C, out {ss.t_out_c:.2f} C)"
        )
        print(
            f"Time flow on -> {SETTLE_BAND:.0%} settle = "
            f"{ss.t_settle_s - ss.t_on_s:.1f} s"
        )
    return out


def main() -> None:
    csv_paths = sorted(RAW_DATA.glob("*.csv"))
    if not csv_paths:
        print(f"No input files yet - add a CSV under {RAW_DATA.relative_to(HERE)}")
        return

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    for csv_path in csv_paths:
        out = plot_file(csv_path)
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
