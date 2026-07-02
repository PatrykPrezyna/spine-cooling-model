import pandas as pd
import matplotlib.pyplot as plt

# --- USER SETTINGS ---
# Each entry: label shown in the legend -> CSV file for that use case.
# Add the third run (e.g. "Thermos + lines + cooling") here when you have it.
FILES = {
    "Thermos only": "sensor_log_20260629_090646_Thermos.csv",
    "Thermos + lines (pumping)": "sensor_log_20260629_120443_Termos_lines.csv",
    # "Thermos + lines + cooling": "sensor_log_XXXX.csv",
}

# Cooling band of interest. We are COOLING, so temperature falls from TEMP_HIGH
# toward TEMP_LOW. Analysis/plotting focuses on this window.
TEMP_HIGH = 37.0
TEMP_LOW = 30.0

FOCUS_BAND = True      # re-zero time at the 37 °C crossing and plot only the band onward
SHOW_SENSORS = False   # also draw the individual csf / csf_2 sensors (faint)


def load(path):
    df = pd.read_csv(path)
    df.columns = [c.strip().replace("\\", "").lower() for c in df.columns]
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df["csf_avg"] = (df["csf_c"] + df["csf_2_c"]) / 2.0
    t0 = df["timestamp"].iloc[0]
    df["elapsed_min"] = (df["timestamp"] - t0).dt.total_seconds() / 60.0
    return df


def find_cooling_segment(df):
    """Return the cooling segment from band-top down toward TEMP_LOW.

    Cooling starts at the peak (hottest) sample. If the run is hotter than
    TEMP_HIGH we enter the band where it crosses TEMP_HIGH on the way down;
    otherwise we start at the peak (a partial run that never got as hot as
    TEMP_HIGH). The segment ends when it first reaches TEMP_LOW, or at the end
    of the record if it never gets that cold.
    """
    peak_pos = df["csf_avg"].values.argmax()
    after = df.iloc[peak_pos:]

    if df["csf_avg"].iloc[peak_pos] >= TEMP_HIGH:
        below = after.index[after["csf_avg"] <= TEMP_HIGH]
        if len(below) == 0:
            return None
        entry = below[0]
    else:
        entry = after.index[0]

    seg = df.loc[entry:].copy()
    reached = seg.index[seg["csf_avg"] <= TEMP_LOW]
    complete = len(reached) > 0
    if complete:
        seg = seg.loc[:reached[0]]
    return seg, complete


fig, ax = plt.subplots(figsize=(10, 6))
colors = ["tab:blue", "tab:red", "tab:green", "tab:orange", "tab:purple"]

for (label, path), color in zip(FILES.items(), colors):
    try:
        df = load(path)
    except FileNotFoundError:
        print(f"Skipping (not found): {path}")
        continue

    if FOCUS_BAND:
        result = find_cooling_segment(df)
        if result is None:
            print(f"{label:<32} no cooling segment in band (max {df['csf_avg'].max():.2f} C)")
            continue
        seg, complete = result
        seg["t_min"] = (seg["timestamp"] - seg["timestamp"].iloc[0]).dt.total_seconds() / 60.0

        T_in = seg["csf_avg"].iloc[0]
        T_out = seg["csf_avg"].iloc[-1]
        t_band = seg["t_min"].iloc[-1]
        rate = (T_in - T_out) / t_band if t_band > 0 else float("nan")

        if complete:
            note = f"{T_in:.1f}->{TEMP_LOW:.0f} C in {t_band:.1f} min ({rate:.3f} C/min)"
        else:
            note = (f"incomplete: {T_in:.1f}->{T_out:.1f} C in {t_band:.1f} min "
                    f"({rate:.3f} C/min), did not reach {TEMP_LOW:.0f} C")

        ax.plot(seg["t_min"], seg["csf_avg"], color=color, linewidth=2, label=f"{label}")
        if SHOW_SENSORS:
            ax.plot(seg["t_min"], seg["csf_c"], color=color, alpha=0.3, linewidth=1)
            ax.plot(seg["t_min"], seg["csf_2_c"], color=color, alpha=0.3, linewidth=1, linestyle="--")
        print(f"{label:<32} {note}")
    else:
        ax.plot(df["elapsed_min"], df["csf_avg"], color=color, linewidth=2,
                label=f"{label}  (CSF avg)")
        print(f"{label:<32} start={df['csf_avg'].iloc[0]:6.2f} C  "
              f"end={df['csf_avg'].iloc[-1]:6.2f} C  duration={df['elapsed_min'].iloc[-1]:5.1f} min")

# Reference lines for the band
ax.axhline(TEMP_HIGH, color="gray", linestyle="--", alpha=0.6, label=f"{TEMP_HIGH:.0f} °C")
ax.axhline(TEMP_LOW, color="black", linestyle="--", alpha=0.6, label=f"{TEMP_LOW:.0f} °C")

ax.set_xlabel("Time since cooling through 37 °C (min)" if FOCUS_BAND else "Elapsed time (min)")
ax.set_ylabel("CSF temperature (°C)")
ax.set_title(f"CSF Cooling Behaviour ({TEMP_HIGH:.0f} -> {TEMP_LOW:.0f} °C) - Heat Transfer Characterisation"
             if FOCUS_BAND else "CSF Temperature - Heat Transfer Characterisation")
ax.grid(True, alpha=0.3)
ax.legend()

fig.tight_layout()
plt.show()
