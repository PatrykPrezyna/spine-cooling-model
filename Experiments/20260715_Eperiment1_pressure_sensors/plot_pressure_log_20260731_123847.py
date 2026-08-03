"""Plot pressure_log_20260731_123847.csv (pump + catheter pressures vs time)."""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "pressure_log_20260731_123847.csv"
PUMP_OUTPUT_AVERAGE_WINDOW = "1s"


def plot_file(csv_path: Path) -> Path:
    df = pd.read_csv(csv_path)
    df = df.loc[:, ~df.columns.duplicated()]
    df.columns = [c.strip().replace("\\", "").lower() for c in df.columns]
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()

    df["pump_output_avg_psi"] = (
        df["pump_output_psi"].rolling(PUMP_OUTPUT_AVERAGE_WINDOW, center=True).mean()
    )

    fig, axes = plt.subplots(4, 1, sharex=True, figsize=(11, 10))
    fig.suptitle(f"Pressure Sensors and Pump Speed vs Time\n{csv_path.name}")

    axes[0].plot(df.index, df["pump_input_psi"], color="tab:green", linewidth=0.8)
    axes[0].set_ylabel("Pump input (psi)")
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
        label=f"{PUMP_OUTPUT_AVERAGE_WINDOW} average",
    )
    axes[1].set_ylabel("Pump output (psi)")
    axes[1].legend(loc="upper right")
    axes[1].grid(True, alpha=0.3)

    axes[2].plot(
        df.index,
        df["catheder_input_psi"],
        color="tab:blue",
        linewidth=0.8,
        label="input",
    )
    axes[2].plot(
        df.index,
        df["catheder_output_psi"],
        color="tab:orange",
        linewidth=0.8,
        label="output",
    )
    axes[2].set_ylabel("Catheter (psi)")
    axes[2].legend(loc="upper right")
    axes[2].grid(True, alpha=0.3)

    axes[3].plot(
        df.index,
        df["peristaltic_pump_set_speed_rpm"],
        color="tab:purple",
        linewidth=0.8,
    )
    axes[3].set_ylabel("Pump set speed (rpm)")
    axes[3].set_xlabel("Time")
    axes[3].grid(True, alpha=0.3)
    axes[3].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    out = HERE / f"pressure_pump_flow_{csv_path.stem}.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


if __name__ == "__main__":
    out = plot_file(CSV_PATH)
    print(f"{CSV_PATH.name} -> {out.name}")
