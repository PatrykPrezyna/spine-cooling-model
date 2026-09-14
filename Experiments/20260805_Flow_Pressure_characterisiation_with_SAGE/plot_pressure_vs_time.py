"""Plot raw pressure logs vs time with a 1 s rolling average.

Same layout as Experiments/20260715_Eperiment1_pressure_sensors:
pump input, pump output, catheter in/out, and commanded flow.

Reads pressure_log_*.csv from raw_data/; writes one plot per log to
output_data/. Skips a CSV when its corresponding output already exists;
delete that PNG to force a re-run.

CONNECTION MISTAKE (do not edit raw_data/):
If logged catheder_output_psi is higher than catheder_input_psi, the catheter
pressure fittings / channels were swapped on the bench. Columns are swapped
for plotting so input = upstream (higher P) and output = downstream (lower P).
"""

from pathlib import Path
import sys

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import (
    ML_PER_MIN_PER_RPM,
    add_rolling_means,
    load_sensor_csv,
    rpm_to_flow_ml_min,
)
from plot_flow_pressure import correct_swapped_catheter_pressures

RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"
AVERAGE_WINDOW = "1s"


def _output_path(csv_path: Path) -> Path:
    stem = csv_path.stem.removeprefix("pressure_log_")
    return OUTPUT_DATA / f"pressure_vs_time_{stem}.png"


def plot_file(csv_path: Path) -> Path:
    df, swapped = correct_swapped_catheter_pressures(
        load_sensor_csv(csv_path, index_timestamp=True), csv_path
    )

    avg = AVERAGE_WINDOW
    pressure_columns = [
        "pump_input_psi",
        "pump_output_psi",
        "catheder_input_psi",
        "catheder_output_psi",
    ]
    df = add_rolling_means(
        df, pressure_columns, avg, suffix="_avg"
    )

    fig, axes = plt.subplots(4, 1, sharex=True, figsize=(11, 10))
    title = f"Pressure Sensors and Pump Speed vs Time\n{csv_path.name}"
    if swapped:
        title += "\nplotted with catheter in/out swapped (connection mistake in log)"
    fig.suptitle(title)

    axes[0].plot(
        df.index, df["pump_input_psi"], color="tab:green", linewidth=0.5, alpha=0.35, label="raw"
    )
    axes[0].plot(
        df.index,
        df["pump_input_psi_avg"],
        color="tab:green",
        linewidth=1.5,
        label=f"{avg} average",
    )
    axes[0].set_ylabel("Pump input (psi)")
    axes[0].legend(loc="upper right")
    axes[0].grid(True, alpha=0.3)

    axes[1].plot(
        df.index,
        df["pump_output_psi"],
        color="tab:red",
        linewidth=0.5,
        alpha=0.35,
        label="raw",
    )
    axes[1].plot(
        df.index,
        df["pump_output_psi_avg"],
        color="tab:red",
        linewidth=1.5,
        label=f"{avg} average",
    )
    axes[1].set_ylabel("Pump output (psi)")
    axes[1].legend(loc="upper right")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(
        df.index,
        df["catheder_input_psi"],
        color="tab:blue",
        linewidth=0.5,
        alpha=0.35,
        label="input raw",
    )
    axes[2].plot(
        df.index,
        df["catheder_input_psi_avg"],
        color="tab:blue",
        linewidth=1.5,
        label=f"input {avg} avg",
    )
    axes[2].plot(
        df.index,
        df["catheder_output_psi"],
        color="tab:orange",
        linewidth=0.5,
        alpha=0.35,
        label="output raw",
    )
    axes[2].plot(
        df.index,
        df["catheder_output_psi_avg"],
        color="tab:orange",
        linewidth=1.5,
        label=f"output {avg} avg",
    )
    axes[2].set_ylabel("Catheter (psi)")
    axes[2].legend(loc="upper right")
    axes[2].grid(True, alpha=0.3)
    if swapped:
        axes[2].text(
            0.01,
            0.97,
            "CONNECTION MISTAKE in log: output > input. "
            "Plotted with channels swapped. raw_data/ not modified.",
            transform=axes[2].transAxes,
            va="top",
            ha="left",
            fontsize=8,
            color="tab:red",
        )

    flow_ml_per_min = rpm_to_flow_ml_min(
        df["peristaltic_pump_set_speed_rpm"], ML_PER_MIN_PER_RPM
    )
    axes[3].plot(df.index, flow_ml_per_min, color="tab:purple", linewidth=0.8)
    axes[3].set_ylabel("Pump flow (ml/min)")
    axes[3].set_xlabel("Time")
    axes[3].grid(True, alpha=0.3)
    axes[3].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = _output_path(csv_path)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


if __name__ == "__main__":
    csv_paths = sorted(RAW_DATA.glob("pressure_log_*.csv"))
    if not csv_paths:
        raise FileNotFoundError(f"No pressure_log_*.csv in {RAW_DATA}")
    for csv_path in csv_paths:
        out = _output_path(csv_path)
        if out.exists():
            print(f"skip {csv_path.name} (exists: {out.name})")
            continue
        plot_file(csv_path)
        print(f"{csv_path.name} -> {out}")
