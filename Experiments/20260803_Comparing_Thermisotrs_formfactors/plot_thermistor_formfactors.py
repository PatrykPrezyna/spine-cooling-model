"""Plot thermistor form-factor comparison from sensor_log_20260803_135314.csv."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
CSV_PATH = HERE / "sensor_log_20260803_135314.csv"


def plot_file(csv_path: Path) -> Path:
    df = pd.read_csv(csv_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    t_s = (df.index - df.index[0]).total_seconds()
    err = df["White"] - df["Original"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    fig.suptitle(f"Thermistor form-factor comparison\n{csv_path.name}")

    ax1.plot(t_s, df["White"], color="tab:orange", linewidth=1.0, label="White")
    ax1.plot(t_s, df["Original"], color="tab:green", linewidth=1.0, label="Original")
    ax1.axhline(50, color="0.5", linestyle="--", linewidth=0.8, label="50 °C target")
    ax1.set_ylabel("Temperature (°C)")
    ax1.legend(loc="best")
    ax1.grid(True, alpha=0.3)

    ax2.plot(t_s, err, color="tab:red", linewidth=0.9, label="White − Original")
    ax2.axhline(0, color="k", linewidth=0.7, alpha=0.5)
    ax2.set_ylabel("Error (°C)")
    ax2.set_xlabel("Elapsed time (s)")
    ax2.legend(loc="best")
    ax2.grid(True, alpha=0.3)

    out = HERE / f"thermistor_compare_{csv_path.stem}.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out


if __name__ == "__main__":
    out = plot_file(CSV_PATH)
    print(f"{CSV_PATH.name} -> {out.name}")
