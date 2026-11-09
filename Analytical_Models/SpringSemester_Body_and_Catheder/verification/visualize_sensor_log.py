# visualize_sensor_log_with_cooling.py
import argparse
import pandas as pd
import matplotlib.pyplot as plt


def parse_value(v: str):
    v = v.strip().strip('"')
    try:
        return float(v)
    except ValueError:
        return v


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if "timestamp" not in df.columns:
        raise ValueError("No 'timestamp' column found.")

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    for c in df.columns:
        if c != "timestamp":
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df["t_s"] = (df["timestamp"] - df["timestamp"].iloc[0]).dt.total_seconds()
    return df


def load_sensor_file(path: str) -> pd.DataFrame:
    # Try normal CSV first
    try:
        df = pd.read_csv(path)
        if "timestamp" in df.columns:
            return clean_dataframe(df)
    except Exception:
        pass

    # Fallback: key:value log format
    records = []
    current = {}
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, val = line.split(":", 1)
            key, val = key.strip(), val.strip()

            if key == "timestamp":
                if current.get("timestamp"):
                    records.append(current)
                current = {"timestamp": val}
            else:
                current[key] = parse_value(val)

    if current.get("timestamp"):
        records.append(current)

    if not records:
        raise ValueError("Could not parse file.")

    return clean_dataframe(pd.DataFrame(records))


def detect_cooling_time(
    df: pd.DataFrame,
    csf_col="csf_c",
    set_col="set_temperature_c",
    pump_col="peristaltic_pump_set_speed_rpm",
    tol_c=0.1,
):
    if csf_col not in df.columns:
        raise ValueError(f"Missing column: {csf_col}")

    # Cooling start
    if pump_col in df.columns:
        nz = df.index[df[pump_col] > 0]
        start_idx = int(nz[0]) if len(nz) else 0
    else:
        start_idx = 0

    start_t = df.loc[start_idx, "t_s"]
    start_ts = df.loc[start_idx, "timestamp"]

    # Target set temp (final setpoint)
    target = None
    if set_col in df.columns and df[set_col].notna().any():
        target = float(df[set_col].dropna().iloc[-1])

    # Try success case: first time csf reaches setpoint
    reach_idx = None
    if target is not None:
        hits = df.index[(df.index >= start_idx) & (df[csf_col] <= target + tol_c)]
        if len(hits):
            reach_idx = int(hits[0])

    if reach_idx is not None:
        end_idx = reach_idx
        success = True
        reason = "Reached set temperature (first reach used)."
        coolest_temp = float(df.loc[end_idx, csf_col])
        coolest_idx = end_idx
    else:
        # Failure case: use coolest point reached (first occurrence)
        phase = df.loc[start_idx:, csf_col].dropna()
        if len(phase) == 0:
            end_idx = len(df) - 1
            coolest_idx = end_idx
            coolest_temp = float("nan")
            reason = "No valid csf data after cooling start."
        else:
            coolest_temp = float(phase.min())
            coolest_idx = int(phase[phase == coolest_temp].index[0])  # first time min is reached
            end_idx = coolest_idx
            reason = "Did not reach set temperature; using coolest temperature reached."
        success = False

    end_t = df.loc[end_idx, "t_s"]
    end_ts = df.loc[end_idx, "timestamp"]

    return {
        "start_idx": start_idx,
        "end_idx": end_idx,
        "start_t_s": float(start_t),
        "end_t_s": float(end_t),
        "start_timestamp": start_ts,
        "end_timestamp": end_ts,
        "cooling_time_s": float(end_t - start_t),
        "success": success,
        "reason": reason,
        "target_set_temp_c": target,
        "coolest_temp_c": coolest_temp,
        "coolest_idx": coolest_idx,
        "coolest_timestamp": df.loc[coolest_idx, "timestamp"] if len(df) else None,
        "time_to_coolest_s": float(df.loc[coolest_idx, "t_s"] - start_t) if len(df) else float("nan"),
    }


def plot_data(df: pd.DataFrame, cooling_result: dict, csf_col="csf_c"):
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

    plot_cols(axes[0], ["csf_c", "csf_2_c", "set_temperature_c"], "CSF / Set Temperature")
    axes[0].set_ylabel("°C")

    plot_cols(axes[1], ["cart_in_c", "cart_out_c"], "Cartridge In/Out")
    axes[1].set_ylabel("°C")

    plot_cols(axes[2], ["heat_ex_c", "heat_ex_2_c", "temp_7_c", "temp_8_c"], "Other Temps")
    axes[2].set_ylabel("°C")

    ax4 = axes[3]
    if "peristaltic_pump_set_speed_rpm" in df.columns:
        ax4.step(x, df["peristaltic_pump_set_speed_rpm"], where="post", label="pump_rpm")
    ax4.set_ylabel("Pump RPM")
    ax4.grid(alpha=0.3)

    if "compressor_cooling" in df.columns:
        ax4b = ax4.twinx()
        ax4b.step(x, df["compressor_cooling"], where="post", color="tab:red", label="compressor")
        ax4b.set_ylabel("Compressor (0/1)")
        ax4b.set_ylim(-0.1, 1.1)

    # Mark cooling start/end
    ts = cooling_result["start_t_s"]
    te = cooling_result["end_t_s"]
    for ax in axes:
        ax.axvline(ts, color="gray", linestyle="--", alpha=0.7)
        ax.axvline(te, color="magenta", linestyle="--", alpha=0.8)

    if csf_col in df.columns:
        axes[0].scatter([te], [df.loc[cooling_result["end_idx"], csf_col]], color="magenta", zorder=5)

    status = "SUCCESS" if cooling_result["success"] else "COOLING FAILED"
    txt = (
        f"{status}\n"
        f"Cooling time: {cooling_result['cooling_time_s']:.2f} s\n"
        f"Start: {cooling_result['start_timestamp']}\n"
        f"End: {cooling_result['end_timestamp']}"
    )
    axes[0].text(0.01, 0.03, txt, transform=axes[0].transAxes,
                 bbox=dict(boxstyle="round", facecolor="white", alpha=0.85), fontsize=9)

    axes[-1].set_xlabel("Time from start [s]")
    plt.show()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("file")
    p.add_argument("--tol", type=float, default=0.1, help="Setpoint reach tolerance in °C")
    p.add_argument("--stable-window", type=float, default=5.0, help="Stability window in seconds")
    p.add_argument("--stable-range", type=float, default=0.05, help="Max range in stability window (°C)")
    p.add_argument("--stable-drift", type=float, default=0.03, help="Max drift over stability window (°C)")
    args = p.parse_args()

    df = load_sensor_file(args.file)

    result = detect_cooling_time(
        df,
        csf_col="csf_c",
        set_col="set_temperature_c",
        pump_col="peristaltic_pump_set_speed_rpm",
        tol_c=args.tol,
    )

    print("\n=== Cooling analysis ===")
    print(f"Cooling start : {result['start_timestamp']} (t={result['start_t_s']:.3f}s)")
    if result["target_set_temp_c"] is not None:
        print(f"Target set temp: {result['target_set_temp_c']:.3f} °C (±{args.tol} °C)")
    print(f"Cooling end   : {result['end_timestamp']} (t={result['end_t_s']:.3f}s)")
    print(f"Cooling time  : {result['cooling_time_s']:.3f} s")
    print(f"Status        : {'SUCCESS' if result['success'] else 'COOLING FAILED'}")
    print(f"Reason        : {result['reason']}")

    plot_data(df, result, csf_col="csf_c")


if __name__ == "__main__":
    main()