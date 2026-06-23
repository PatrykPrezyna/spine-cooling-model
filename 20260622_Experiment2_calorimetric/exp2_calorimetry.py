import pandas as pd
import numpy as np

# --- USER SETTINGS ---
FILE = "sensor_log_20260622_153100.csv"
MASS_KG = 0.838
C = 4186  # J/kg°C
WINDOWS = ["2min", "5min", "10min"]  # averaging windows for windowed power

# --- LOAD DATA ---
df = pd.read_csv(FILE)

# Clean column names
df.columns = [c.strip().replace("\\", "").lower() for c in df.columns]

# Convert timestamp to datetime
df["timestamp"] = pd.to_datetime(df["timestamp"])

# --- COMPUTE BULK TEMPERATURE ---
# Average of two sensors to approximate tank temperature
df["temp_avg"] = (df["csf_c"] + df["csf_2_c"]) / 2.0

# --- COMPUTE dT/dt ---
# time difference in seconds
df["dt"] = df["timestamp"].diff().dt.total_seconds()

# temperature difference
df["dtemp"] = df["temp_avg"].diff()

# rate of change (°C/s)
df["dT_dt"] = df["dtemp"] / df["dt"]

# --- COMPUTE POWER (W) ---
# Negative sign → cooling gives positive power
df["power_w"] = -MASS_KG * C * df["dT_dt"]

# --- CLEAN INVALID VALUES ---
df = df.replace([np.inf, -np.inf], np.nan)
df = df.dropna(subset=["power_w"])

# --- RESULTS ---
avg_power = df["power_w"].mean()
max_power = df["power_w"].max()
min_power = df["power_w"].min()

print("=== Tank-based Cooling Power ===")
print(f"Mass: {MASS_KG} kg")
print(f"Average power: {avg_power:.2f} W")
print(f"Max power:     {max_power:.2f} W")
print(f"Min power:     {min_power:.2f} W")

# --- WINDOWED POWER ---
# Instead of differentiating sample-to-sample (noisy), measure the temperature
# drop across each fixed time window. Over several minutes the real change far
# exceeds sensor noise, so the average power per window is much more reliable.
ts = df.set_index("timestamp")


def windowed_power(window):
    b = ts["temp_avg"].resample(window).agg(["first", "last"])
    b["duration_s"] = ts["temp_avg"].resample(window).apply(
        lambda s: (s.index[-1] - s.index[0]).total_seconds() if len(s) > 1 else np.nan
    )
    b["delta_t_c"] = b["last"] - b["first"]
    b["power_w"] = -MASS_KG * C * b["delta_t_c"] / b["duration_s"]
    return b.dropna(subset=["power_w"])


binned_by_window = {w: windowed_power(w) for w in WINDOWS}

for w, b in binned_by_window.items():
    print(f"\n=== Windowed Cooling Power (per {w}) ===")
    print(f"{'window start':<22}{'dT (C)':>10}{'dur (s)':>10}{'power (W)':>12}")
    for t, row in b.iterrows():
        print(f"{str(t):<22}{row['delta_t_c']:>10.3f}{row['duration_s']:>10.1f}{row['power_w']:>12.2f}")
    print(f"Mean of windowed power: {b['power_w'].mean():.2f} W")

# --- SINGLE REPRESENTATIVE POWER OVER THE ACTIVE COOLING PERIOD ---
# The tank cools from a hot start toward an equilibrium plateau. A single,
# defensible cooling-power number is the energy removed across the *active*
# cooling phase divided by its duration. We auto-detect that phase as:
#   start = moment of peak (hottest) bulk temperature
#   end   = when the temperature has completed PLATEAU_FRAC of its total drop
# This trims the initial sensor settling and the flat equilibrium tail where
# dT/dt ~ 0 (which would otherwise dilute the average).
PLATEAU_MINUTES = 5     # window used to estimate the equilibrium temperature
PLATEAU_FRAC = 0.98     # fraction of total cooling that defines "active phase end"

plateau_start = ts.index[-1] - pd.Timedelta(minutes=PLATEAU_MINUTES)
plateau_temp = ts.loc[plateau_start:, "temp_avg"].mean()
peak_time = ts["temp_avg"].idxmax()
peak_temp = ts["temp_avg"].max()
total_drop = peak_temp - plateau_temp

threshold_temp = peak_temp - PLATEAU_FRAC * total_drop
after_peak = ts.loc[peak_time:, "temp_avg"]
reached = after_peak[after_peak <= threshold_temp]
end_time = reached.index[0] if len(reached) else after_peak.index[-1]

period = ts.loc[peak_time:end_time, "temp_avg"]
T_start = period.iloc[0]
T_end = period.iloc[-1]
duration_s = (period.index[-1] - period.index[0]).total_seconds()
q_removed_j = MASS_KG * C * (T_start - T_end)
power_single_w = q_removed_j / duration_s

print("\n=== Single Representative Cooling Power (active period) ===")
print(f"Equilibrium (plateau) temp : {plateau_temp:.2f} C  (last {PLATEAU_MINUTES} min)")
print(f"Active period              : {peak_time.strftime('%H:%M:%S')} -> {end_time.strftime('%H:%M:%S')}")
print(f"Duration                   : {duration_s:.0f} s  ({duration_s/60:.1f} min)")
print(f"Temperature drop           : {T_start:.2f} -> {T_end:.2f} C  ({T_start - T_end:.2f} C)")
print(f"Energy removed             : {q_removed_j/1000:.1f} kJ")
print(f"Average cooling power       : {power_single_w:.1f} W")

# --- OPTIONAL: Plot ---
try:
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(9, 6))

    ax1.plot(df["timestamp"], df["csf_c"], color="tab:orange", alpha=0.6, label="csf")
    ax1.plot(df["timestamp"], df["csf_2_c"], color="tab:green", alpha=0.6, label="csf_2")
    ax1.plot(df["timestamp"], df["temp_avg"], color="tab:purple", linewidth=2, label="CSF avg (csf, csf_2)")
    ax1.axvspan(peak_time, end_time, color="tab:gray", alpha=0.15, label="Active cooling period")
    ax1.axhline(plateau_temp, color="black", linestyle=":", alpha=0.6, label=f"Plateau {plateau_temp:.1f} °C")
    ax1.set_ylabel("Temperature (°C)")
    ax1.set_title("CSF Average Temperature and Cooling Power")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    colors = ["tab:blue", "tab:red", "tab:green", "tab:orange"]
    for (w, b), color in zip(binned_by_window.items(), colors):
        ax2.step(b.index, b["power_w"], where="post", color=color,
                 linewidth=2, label=f"Windowed power ({w})")
    ax2.axvspan(peak_time, end_time, color="tab:gray", alpha=0.15)
    ax2.axhline(power_single_w, color="black", linestyle="--", alpha=0.8,
                label=f"Active-period avg = {power_single_w:.1f} W")
    ax2.set_ylabel("Cooling Power (W)")
    ax2.set_xlabel("Time")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # Key equations used in the calorimetric calculation
    eq_text = (
        r"$T_{avg} = (T_{csf} + T_{csf2})\,/\,2$" "        "
        r"$P = -\,m\,c\,\dfrac{dT}{dt}$" "        "
        r"$P_{window} = -\,m\,c\,\dfrac{T_{end}-T_{start}}{\Delta t}$" "        "
        rf"$m = {MASS_KG}\ kg,\ c = {C}\ J/kg\degree C$"
    )

    fig.tight_layout(rect=[0, 0.08, 1, 1])
    fig.text(
        0.5, 0.02, eq_text,
        ha="center", va="bottom", fontsize=10,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
    )
    plt.show()

except ImportError:
    print("matplotlib not installed, skipping plot.")

# --- SAVE ---
df.to_csv("tank_calorimetry_results.csv", index=False)
