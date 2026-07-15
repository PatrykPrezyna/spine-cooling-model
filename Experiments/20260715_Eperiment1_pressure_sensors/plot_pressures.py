from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent

pressure_series = [
    ("cartridge_input_psi", "Cartridge input (psi)", "tab:blue"),
    ("cartridge_output_psi", "Cartridge output (psi)", "tab:orange"),
    ("pump_input_psi", "Pump input (psi)", "tab:green"),
    ("pump_output_psi", "Pump output (psi)", "tab:red"),
]


def plot_file(csv_path: Path) -> Path:
    df = pd.read_csv(csv_path)
    df.columns = [c.strip().replace("\\", "").lower() for c in df.columns]
    df["timestamp"] = pd.to_datetime(df["timestamp"])
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

    out = HERE / f"pressure_pump_flow_{csv_path.stem.replace('sensor_log_', '')}.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


csv_files = sorted(HERE.glob("*.csv"))
if not csv_files:
    raise SystemExit(f"No CSV files found in {HERE}")

for csv_path in csv_files:
    out = plot_file(csv_path)
    print(f"{csv_path.name} -> {out.name}")
