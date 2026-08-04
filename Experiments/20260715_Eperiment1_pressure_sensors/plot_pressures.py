"""Plot pressure sensors and pump flow vs time for every sensor log.

Reads sensor_log_*.csv from raw_data/; writes one plot per log to
output_data/. Skips a CSV when its corresponding output already exists;
delete that PNG to force a re-run.
"""

from pathlib import Path
import sys

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import load_sensor_csv

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"

pressure_series = [
    ("cartridge_input_psi", "Cartridge input (psi)", "tab:blue"),
    ("cartridge_output_psi", "Cartridge output (psi)", "tab:orange"),
    ("pump_input_psi", "Pump input (psi)", "tab:green"),
    ("pump_output_psi", "Pump output (psi)", "tab:red"),
]


def _output_path(csv_path: Path) -> Path:
    stamp = csv_path.stem.removeprefix("sensor_log_")
    return OUTPUT_DATA / f"pressure_pump_flow_{stamp}.png"


def plot_file(csv_path: Path) -> Path:
    df = load_sensor_csv(csv_path)
    df["pump_flow_ml_per_min"] = df["pump_flow_ml_per_s"] * 60.0

    fig, axes = plt.subplots(5, 1, sharex=True, figsize=(11, 12))
    fig.suptitle(f"Pressure Sensors and Pump Flow vs Time\n{csv_path.name}")

    for ax, (col, ylabel, color) in zip(axes[:4], pressure_series):
        ax.plot(df["timestamp"], df[col], color=color)
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.3)

    axes[4].plot(df["timestamp"], df["pump_flow_ml_per_min"], color="tab:purple")
    axes[4].set_ylabel("Pump flow (ml/min)")
    axes[4].set_xlabel("Time")
    axes[4].grid(True, alpha=0.3)
    axes[4].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    out = _output_path(csv_path)
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


csv_files = sorted(RAW_DATA.glob("sensor_log_*.csv"))
if not csv_files:
    raise SystemExit(f"No sensor_log_*.csv files found in {RAW_DATA}")

for csv_path in csv_files:
    out = _output_path(csv_path)
    if out.is_file():
        print(f"{csv_path.name} -> {out.name} (exists, skip)")
        continue
    saved = plot_file(csv_path)
    print(f"{csv_path.name} -> {saved.name}")
