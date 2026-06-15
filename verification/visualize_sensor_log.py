# visualize_sensor_log.py
import argparse
import pandas as pd
import matplotlib.pyplot as plt


def parse_value(v: str):
    v = v.strip().strip('"')
    if v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return v


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if "timestamp" not in df.columns:
        raise ValueError("No 'timestamp' column found.")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    # Convert non-timestamp columns to numeric if possible
    for c in df.columns:
        if c != "timestamp":
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Relative time in seconds (better for plotting)
    df["t_s"] = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds()
    return df


def load_sensor_file(path: str) -> pd.DataFrame:
    # --- Try standard CSV first ---
    try:
        df = pd.read_csv(path)
        if "timestamp" in df.columns:
            return clean_dataframe(df)
    except Exception:
        pass

    # --- Fallback: parse key:value log format ---
    records = []
    current = {}

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue

            key, val = line.split(":", 1)
            key, val = key.strip(), val.strip()

            if key == "timestamp":
                # Save previous record if it has timestamp
                if current.get("timestamp"):
                    records.append(current)
                current = {"timestamp": val}
            else:
                current[key] = parse_value(val)

    # Append last record
    if current.get("timestamp"):
        records.append(current)

    if not records:
        raise ValueError("Could not parse file as CSV or key:value sensor log.")

    df = pd.DataFrame(records)
    return clean_dataframe(df)


def plot_data(df: pd.DataFrame):
    fig, axes = plt.subplots(4, 1, figsize=(14, 11), sharex=True, constrained_layout=True)
    x = df["t_s"]

    def plot_cols(ax, cols, title):
        plotted = False
        for c in cols:
            if c in df.columns:
                ax.plot(x, df[c], label=c, linewidth=1.2)
                plotted = True
        ax.set_title(title)
        ax.grid(alpha=0.3)
        if plotted:
            ax.legend(loc="best", fontsize=8)

    # 1) CSF vs setpoint
    plot_cols(
        axes[0],
        ["csf_c", "csf_2_c", "set_temperature_c"],
        "CSF / Set Temperature"
    )
    axes[0].set_ylabel("°C")

    # 2) Cartridge temps
    plot_cols(
        axes[1],
        ["cart_in_c", "cart_out_c"],
        "Cartridge In/Out Temperature"
    )
    axes[1].set_ylabel("°C")

    # 3) Heat exchanger and extra sensors
    plot_cols(
        axes[2],
        ["heat_ex_c", "heat_ex_2_c", "temp_7_c", "temp_8_c"],
        "Heat Exchanger / Other Sensors"
    )
    axes[2].set_ylabel("°C")

    # 4) Actuators (pump + compressor)
    ax4 = axes[3]
    if "peristaltic_pump_set_speed_rpm" in df.columns:
        ax4.step(
            x,
            df["peristaltic_pump_set_speed_rpm"],
            where="post",
            label="peristaltic_pump_set_speed_rpm",
            linewidth=1.5
        )
    ax4.set_ylabel("Pump RPM")
    ax4.grid(alpha=0.3)

    if "compressor_cooling" in df.columns:
        ax4b = ax4.twinx()
        ax4b.step(
            x,
            df["compressor_cooling"],
            where="post",
            label="compressor_cooling",
            color="tab:red",
            linewidth=1.2
        )
        ax4b.set_ylabel("Compressor (0/1)")
        ax4b.set_ylim(-0.1, 1.1)

    # Mark pump start (if any)
    if "peristaltic_pump_set_speed_rpm" in df.columns:
        nonzero = df.index[df["peristaltic_pump_set_speed_rpm"] > 0]
        if len(nonzero) > 0:
            t_start = df.loc[nonzero[0], "t_s"]
            for ax in axes:
                ax.axvline(t_start, color="k", linestyle="--", alpha=0.4)
            axes[0].text(t_start, axes[0].get_ylim()[1], " Pump start", va="top", ha="left", fontsize=8)

    axes[-1].set_xlabel("Time from start [s]")
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="Visualize sensor log data.")
    parser.add_argument("file", help="Path to CSV/log file")
    args = parser.parse_args()

    df = load_sensor_file(args.file)
    print(f"Loaded {len(df)} records.")
    print("Columns:", ", ".join(df.columns))
    plot_data(df)


if __name__ == "__main__":
    main()