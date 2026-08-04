"""Plot raw pressure logs vs time with a 1 s rolling average.

Same layout as Experiments/20260715_Eperiment1_pressure_sensors:
pump input, pump output, catheter in/out, and commanded flow.

Reads pressure_log_*.csv from raw_data/; writes one plot per log to
output_data/. Skips a CSV when its corresponding output already exists;
delete that PNG to force a re-run.
"""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"
AVERAGE_WINDOW = "1s"
ML_PER_MIN_PER_RPM = 0.7823


def _output_path(csv_path: Path) -> Path:
    stem = csv_path.stem.removeprefix("pressure_log_")
    return OUTPUT_DATA / f"pressure_vs_time_{stem}.png"


def plot_file(csv_path: Path) -> Path:
    df = pd.read_csv(csv_path)
    df = df.loc[:, ~df.columns.duplicated()]
    df.columns = [c.strip().replace("\\", "").lower() for c in df.columns]
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()

    avg = AVERAGE_WINDOW
    df["pump_input_avg_psi"] = df["pump_input_psi"].rolling(avg, center=True).mean()
    df["pump_output_avg_psi"] = df["pump_output_psi"].rolling(avg, center=True).mean()
    df["catheder_input_avg_psi"] = (
        df["catheder_input_psi"].rolling(avg, center=True).mean()
    )
    df["catheder_output_avg_psi"] = (
        df["catheder_output_psi"].rolling(avg, center=True).mean()
    )

    fig, axes = plt.subplots(4, 1, sharex=True, figsize=(11, 10))
    fig.suptitle(f"Pressure Sensors and Pump Speed vs Time\n{csv_path.name}")

    axes[0].plot(
        df.index, df["pump_input_psi"], color="tab:green", linewidth=0.5, alpha=0.35, label="raw"
    )
    axes[0].plot(
        df.index,
        df["pump_input_avg_psi"],
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
        df["pump_output_avg_psi"],
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
        df["catheder_input_avg_psi"],
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
        df["catheder_output_avg_psi"],
        color="tab:orange",
        linewidth=1.5,
        label=f"output {avg} avg",
    )
    axes[2].set_ylabel("Catheter (psi)")
    axes[2].legend(loc="upper right")
    axes[2].grid(True, alpha=0.3)

    flow_ml_per_min = df["peristaltic_pump_set_speed_rpm"] * ML_PER_MIN_PER_RPM
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
