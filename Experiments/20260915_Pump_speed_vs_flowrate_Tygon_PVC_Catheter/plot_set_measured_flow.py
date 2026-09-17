"""Plot commanded (set) vs Keyence-measured flow from sensor logs.

Reads timestamped sensor CSVs in raw_data/ and writes one PNG per log under
output_data/. Uses the logged pump_flow (Service UI set point), not the
legacy gravimetric factor in experiment_tools.
"""

from __future__ import annotations

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import elapsed_time, load_sensor_csv

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"

RPM_ON_THRESHOLD = 1.0
MIN_HOLD_S = 10.0


def sensor_logs() -> list[Path]:
    return sorted(
        p
        for p in RAW_DATA.glob("*sensors*.csv")
        if p.is_file() and "copy" not in p.stem.lower()
    )


def set_flow_ml_min(df: pd.DataFrame) -> pd.Series:
    return df["pump_flow_ml_per_s"] * 60.0


def hold_summary(df: pd.DataFrame) -> pd.DataFrame:
    rpm = df["peristaltic_pump_set_speed_rpm"]
    block = rpm.ne(rpm.shift()).cumsum()
    t_s = elapsed_time(df["timestamp"], unit="s")
    set_q = set_flow_ml_min(df)
    rows = []
    for _, idx in df.groupby(block).groups.items():
        part = df.loc[idx]
        dur_s = float(t_s.loc[idx].iloc[-1] - t_s.loc[idx].iloc[0])
        rpm_val = float(part["peristaltic_pump_set_speed_rpm"].iloc[0])
        if dur_s < MIN_HOLD_S:
            continue
        rows.append(
            {
                "set_speed_rpm": rpm_val,
                "duration_s": dur_s,
                "set_ml_per_min": float(set_q.loc[idx].mean()),
                "keyence_ml_per_min": float(
                    part["flow_sensor_ml_per_min"].mean()
                ),
            }
        )
    return pd.DataFrame(rows)


def plot_file(csv_path: Path) -> Path:
    df = load_sensor_csv(csv_path, recalibrate_pump_flow=False)
    minutes = elapsed_time(df["timestamp"], unit="min")
    set_q = set_flow_ml_min(df)
    meas = df["flow_sensor_ml_per_min"]

    fig, (ax_t, ax_s) = plt.subplots(
        1, 2, figsize=(12, 4.8), gridspec_kw={"width_ratios": [1.7, 1]}
    )

    ax_t.plot(
        minutes,
        set_q,
        color="0.35",
        linewidth=1.3,
        linestyle="--",
        label="Set (Service UI)",
        zorder=3,
    )
    ax_t.plot(
        minutes,
        meas,
        color="tab:green",
        linewidth=1.1,
        label="Measured (Keyence)",
        zorder=2,
    )
    ax_t.set_xlabel("Elapsed time (min)")
    ax_t.set_ylabel("Flow rate (ml/min)")
    ax_t.set_title("Set vs measured flow")
    ax_t.grid(True, alpha=0.3)
    ax_t.legend(loc="best", fontsize=8)
    ax_t.set_xlim(float(minutes.iloc[0]), float(minutes.iloc[-1]))
    y_max = float(np.nanmax(np.concatenate([set_q.to_numpy(), meas.to_numpy()])))
    ax_t.set_ylim(-2.0, max(y_max * 1.08, 1.0))

    on = df["peristaltic_pump_set_speed_rpm"] > RPM_ON_THRESHOLD
    ax_s.scatter(
        set_q.loc[on],
        meas.loc[on],
        s=8,
        alpha=0.35,
        color="tab:green",
        edgecolors="none",
        label="Samples (pump on)",
    )
    lim = max(
        float(np.nanmax(set_q.loc[on].to_numpy())) if on.any() else 1.0,
        float(np.nanmax(meas.loc[on].to_numpy())) if on.any() else 1.0,
        1.0,
    )
    ax_s.plot([0, lim * 1.05], [0, lim * 1.05], color="0.4", linestyle=":", label="1:1")
    ax_s.set_xlabel("Set flow (ml/min)")
    ax_s.set_ylabel("Measured flow (ml/min)")
    ax_s.set_title("Keyence vs set point")
    ax_s.grid(True, alpha=0.3)
    ax_s.legend(loc="upper left", fontsize=8)
    ax_s.set_xlim(0, lim * 1.05)
    ax_s.set_ylim(0, lim * 1.05)
    ax_s.set_aspect("equal", adjustable="box")

    fig.suptitle(csv_path.name, fontsize=10)
    fig.tight_layout()

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DATA / f"set_vs_measured_flow_{csv_path.stem}.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)

    holds = hold_summary(df)
    print(f"\n{csv_path.name}  ({minutes.iloc[-1]:.1f} min, {len(df)} samples)")
    if not holds.empty:
        print(holds.to_string(index=False, float_format=lambda x: f"{x:8.2f}"))
        on_hold = holds["set_speed_rpm"] > RPM_ON_THRESHOLD
        if on_hold.any() and (holds.loc[on_hold, "keyence_ml_per_min"] > 1).any():
            valid = on_hold & (holds["keyence_ml_per_min"] > 1)
            err = (
                holds.loc[valid, "keyence_ml_per_min"]
                - holds.loc[valid, "set_ml_per_min"]
            )
            print(
                f"Holds with flow: mean (Keyence - set) = {err.mean():+.2f} ml/min"
            )
    return out


def main() -> None:
    paths = sensor_logs()
    if not paths:
        print(
            f"No sensor logs yet - add a *sensors*.csv under "
            f"{RAW_DATA.relative_to(HERE)}"
        )
        return

    for path in paths:
        out = plot_file(path)
        print(f"Wrote {out}")


if __name__ == "__main__":
    main()
