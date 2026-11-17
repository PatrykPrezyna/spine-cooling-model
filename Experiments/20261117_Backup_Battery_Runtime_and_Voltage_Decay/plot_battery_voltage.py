"""Plot backup-battery voltage against elapsed minutes.

Reads sensor_log_*backup_battery.csv from raw_data/. Writes one PNG per log
into output_data/. Empty template rows are dropped. The raw header typo
"bettery" is accepted and not rewritten. Output current stays in the log
and is not plotted.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW_DATA = HERE / "raw_data"
OUTPUT_DATA = HERE / "output_data"

REQ_MIN = 30
CUTOFF_V = 20.0


def load_log(path: Path) -> pd.DataFrame:
    # Data rows have one more trailing comma than the header. index_col=False
    # keeps elapsed_min as a column instead of turning it into the row index.
    df = pd.read_csv(path, index_col=False)
    df = df.dropna(axis=1, how="all")
    renamed = {}
    for col in df.columns:
        key = str(col).strip().lower()
        if "elapsed" in key:
            renamed[col] = "elapsed_min"
        elif "volt" in key:
            renamed[col] = "voltage_v"
        elif "note" in key:
            renamed[col] = "notes"
    df = df.rename(columns=renamed)
    missing = {"elapsed_min", "voltage_v"} - set(df.columns)
    if missing:
        raise KeyError(f"Missing columns in {path.name}: {sorted(missing)}")
    df["elapsed_min"] = pd.to_numeric(df["elapsed_min"], errors="coerce")
    df["voltage_v"] = pd.to_numeric(df["voltage_v"], errors="coerce")
    df = df.dropna(subset=["elapsed_min"]).sort_values("elapsed_min")
    return df.reset_index(drop=True)


def plot_file(path: Path) -> Path:
    df = load_log(path)
    volts = df.dropna(subset=["voltage_v"])

    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DATA / f"battery_voltage_{path.stem}.png"

    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    fig.suptitle("Backup battery voltage\nK2B24V11EB, compressor and pump on battery")

    ax.plot(volts["elapsed_min"], volts["voltage_v"], color="tab:blue", marker="o")
    ax.axhline(CUTOFF_V, color="tab:red", linestyle="--", linewidth=1, label="20 V threshold")
    ax.axvline(REQ_MIN, color="0.45", linestyle=":", linewidth=1, label="30 min requirement")
    ax.set_ylabel("Battery voltage (V)")
    ax.set_xlabel("Elapsed time (min)")
    ax.legend(loc="lower left")
    ax.grid(True, alpha=0.3)

    stop = volts.iloc[-1]
    ax.annotate(
        f"switched off\n{stop['voltage_v']:.1f} V",
        xy=(stop["elapsed_min"], stop["voltage_v"]),
        xytext=(-70, 18),
        textcoords="offset points",
        fontsize=8,
        arrowprops={"arrowstyle": "->", "color": "0.3"},
    )

    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(out)
    return out


def main() -> None:
    logs = sorted(RAW_DATA.glob("sensor_log_*backup_battery.csv"))
    if not logs:
        print(f"No backup-battery logs in {RAW_DATA}")
        return
    for path in logs:
        plot_file(path)


if __name__ == "__main__":
    main()
