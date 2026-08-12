"""Plot catheter input/output pressure and pump speed over time.

Two stacked panels sharing the time axis: pressures (psi) on top, commanded
pump speed (rpm, with the equivalent flow in ml/min) below. Writes one PNG per
sensor_log_*.csv in raw_data/ to output_data/.

Skips a CSV when its corresponding output already exists; delete that PNG to
force a re-run.
"""

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
)

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"

PRESSURE_SERIES = {
    "catheter_input_psi": ("Catheter input", "tab:blue"),
    "catheter_output_psi": ("Catheter output", "tab:orange"),
}
PUMP_COLOR = "tab:green"
SMOOTH_WINDOW = "3s"  # peristaltic pulsation is faster than this


def _output_path(csv_path: Path) -> Path:
    stem = csv_path.stem.removeprefix("sensor_log_")
    return OUTPUT_DATA / f"pressure_pump_{stem}.png"


def plot_file(csv_path: Path) -> Path:
    df = load_sensor_csv(csv_path)
    minutes = elapsed_time(df["timestamp"], unit="min")

    fig, (ax_p, ax_rpm) = plt.subplots(
        2, 1, figsize=(11, 7), sharex=True, height_ratios=[2, 1]
    )

    smoothed = df.set_index("timestamp")[list(PRESSURE_SERIES)].rolling(
        SMOOTH_WINDOW, center=True
    ).mean()
    for column, (label, color) in PRESSURE_SERIES.items():
        # Raw trace shows the pulsation envelope; the mean shows the trend.
        ax_p.plot(minutes, df[column], color=color, linewidth=0.6, alpha=0.25)
        ax_p.plot(
            minutes,
            smoothed[column].to_numpy(),
            color=color,
            linewidth=1.6,
            label=f"{label} ({SMOOTH_WINDOW} mean)",
        )
    ax_p.set_ylabel("Pressure (psi)")
    ax_p.set_title(f"Catheter pressure and pump speed\n{csv_path.name}")
    ax_p.grid(True, alpha=0.3)
    ax_p.axhline(0.0, color="0.5", linewidth=0.8, alpha=0.6)
    ax_p.margins(y=0.05)
    top = float(df[list(PRESSURE_SERIES)].to_numpy().max())
    ax_p.set_ylim(top=top * 1.22)  # headroom so the legend clears the traces
    ax_p.legend(loc="upper right", ncol=2, framealpha=0.9)

    ax_rpm.plot(
        minutes,
        df["peristaltic_pump_set_speed_rpm"],
        color=PUMP_COLOR,
        linewidth=1.2,
    )
    ax_rpm.set_ylabel("Pump set speed (rpm)")
    ax_rpm.set_xlabel("Elapsed time (min)")
    ax_rpm.grid(True, alpha=0.3)
    ax_rpm.set_ylim(bottom=0)

    # Same series, second unit: flow implied by the gravimetric calibration.
    ax_flow = ax_rpm.secondary_yaxis(
        "right",
        functions=(
            lambda rpm: rpm * ML_PER_MIN_PER_RPM,
            lambda ml: ml / ML_PER_MIN_PER_RPM,
        ),
    )
    ax_flow.set_ylabel("Flow (ml/min)")

    ax_rpm.set_xlim(minutes.iloc[0], minutes.iloc[-1])

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = _output_path(csv_path)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)

    summary = df[list(PRESSURE_SERIES) + ["peristaltic_pump_set_speed_rpm"]]
    print(f"\n{csv_path.name}  ({minutes.iloc[-1]:.1f} min, {len(df)} samples)")
    print(summary.describe().loc[["min", "mean", "max"]].to_string(
        float_format=lambda x: f"{x:8.2f}"
    ))
    return out


def plot_logs(csv_paths: list[Path] | None = None) -> list[Path]:
    if csv_paths is None:
        csv_paths = sorted(RAW_DATA.glob("sensor_log_*.csv"))
    if not csv_paths:
        raise FileNotFoundError(f"No sensor_log_*.csv in {RAW_DATA}")

    written: list[Path] = []
    for csv_path in csv_paths:
        out = _output_path(csv_path)
        if out.exists():
            print(f"skip {csv_path.name} (exists: {out.name})")
            continue
        written.append(plot_file(csv_path))
        print(f"-> {out}")
    return written


if __name__ == "__main__":
    plot_logs()
