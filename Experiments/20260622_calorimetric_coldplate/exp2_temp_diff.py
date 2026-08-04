from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from Experiments.experiment_tools import find_plateau_cooling_window, load_sensor_csv

# --- USER SETTINGS ---
print("Starting experiment 2")
HERE = Path(__file__).resolve().parent
#FILE = HERE / "sensor_log_20260622_153100.csv"
#FILE = HERE / "sensor_log_20260624_092838.csv"
FILE = HERE / "sensor_log_20260624_141620.csv"
FLOW_ML_PER_MIN = 46.0  # ~60 rpm from pump calibration (0.7823 ml/min per rpm)
C = 4186  # J/kg°C for water
MASS_KG = 0.838  # tank mass (used only to detect the active cooling phase)

# Active-cooling-phase detection (same definition as exp2_calorimetry.py)
USE_ACTIVE_PHASE = False  # set False to analyze/plot the full record only
PLATEAU_MINUTES = 5      # window used to estimate the equilibrium temperature
PLATEAU_FRAC = 0.98      # fraction of total cooling that defines "active phase end"

# --- CONVERSIONS ---
flow_kg_s = (FLOW_ML_PER_MIN / 1000.0) / 60.0  # ml/min → kg/s

# --- LOAD DATA ---
df = load_sensor_csv(FILE)

# Expected columns (based on your file)
# cart_in_c = hot fluid entering HX
# cart_out_c = cooled fluid leaving HX

# --- COMPUTE DELTA T ---
df["delta_t"] = df["cart_in_c"] - df["cart_out_c"]

# --- COMPUTE INSTANTANEOUS POWER (W) ---
df["power_w"] = flow_kg_s * C * df["delta_t"]

# --- AUTO-SELECT THE ACTIVE COOLING PERIOD (optional) ---
# Use the CSF tank temperature (same as the calorimetric script) so both methods
# report cooling power over the identical physical phase. The active phase runs
# from peak (hottest) bulk temperature to when PLATEAU_FRAC of the cooling is done.
peak_time = end_time = None
avg_power_active = max_power_active = min_power_active = None

if USE_ACTIVE_PHASE:
    ts = df.set_index("timestamp")
    temp_avg = (ts["csf_c"] + ts["csf_2_c"]) / 2.0

    window_result = find_plateau_cooling_window(
        temp_avg,
        plateau_minutes=PLATEAU_MINUTES,
        cooling_fraction=PLATEAU_FRAC,
    )
    if window_result is None:
        raise RuntimeError("Could not find an active cooling period")
    cooling_window, _ = window_result
    peak_time, end_time = cooling_window.start, cooling_window.end

    active = (df["timestamp"] >= peak_time) & (df["timestamp"] <= end_time)
    df_active = df[active]

    avg_power_active = df_active["power_w"].mean()
    max_power_active = df_active["power_w"].max()
    min_power_active = df_active["power_w"].min()

# --- RESULTS (full record) ---
avg_power = df["power_w"].mean()
max_power = df["power_w"].max()
min_power = df["power_w"].min()

print("=== Cooling Power Results ===")
print(f"Flow rate: {FLOW_ML_PER_MIN} ml/min ({flow_kg_s:.6f} kg/s)")
print(f"Average power (full record): {avg_power:.2f} W")
print(f"Max power:     {max_power:.2f} W")
print(f"Min power:     {min_power:.2f} W")

if USE_ACTIVE_PHASE:
    print("\n=== Cooling Power (active cooling phase) ===")
    print(f"Active period : {peak_time.strftime('%H:%M:%S')} -> {end_time.strftime('%H:%M:%S')}")
    print(f"Average power : {avg_power_active:.2f} W")
    print(f"Max power     : {max_power_active:.2f} W")
    print(f"Min power     : {min_power_active:.2f} W")

# --- OPTIONAL: save results ---
OUT_DIR = HERE / "output_data"
OUT_DIR.mkdir(exist_ok=True)
df.to_csv(OUT_DIR / "calculated_power.csv", index=False)
out_png = OUT_DIR / (FILE.stem.replace("sensor_log_", "flow_calorimetry_") + ".png")

# --- OPTIONAL: simple plot ---
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(9, 8))

    ax1.plot(df["timestamp"], df["cart_in_c"], color="tab:red", label="cart_in (°C)")
    ax1.plot(df["timestamp"], df["cart_out_c"], color="tab:green", label="cart_out (°C)")
    ax1.plot(df["timestamp"], df["heat_ex_c"], color="tab:blue", linestyle="--",
             alpha=0.8, label="heat_ex (°C)")
    if USE_ACTIVE_PHASE:
        ax1.axvspan(peak_time, end_time, color="tab:gray", alpha=0.15, label="Active cooling period")
    ax1.set_ylabel("Temperature (°C)")
    ax1.set_title("Cart Temperatures and Cooling Power vs Time")
    ax1.grid(True, alpha=0.3)

    ax1b = ax1.twinx()
    ax1b.plot(df["timestamp"], df["pump_flow_ml_per_s"] * 60.0, color="tab:purple",
              linestyle=":", alpha=0.8, label="pump flow (ml/min)")
    ax1b.set_ylabel("Pump flow (ml/min)", color="tab:purple")
    ax1b.tick_params(axis="y", labelcolor="tab:purple")

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines1b, labels1b = ax1b.get_legend_handles_labels()
    ax1.legend(lines1 + lines1b, labels1 + labels1b,
               loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)

    ax2.plot(df["timestamp"], df["power_w"], color="tab:blue", alpha=0.6, label="Instantaneous power")
    if USE_ACTIVE_PHASE:
        ax2.axvspan(peak_time, end_time, color="tab:gray", alpha=0.15)
        ax2.axhline(avg_power_active, color="black", linestyle="--", alpha=0.8,
                    label=f"Active-phase avg = {avg_power_active:.1f} W")
    ax2.set_ylabel("Cooling Power (W)")
    ax2.set_xlabel("Time")
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2)

    # Power equation + parameters used in the calculation
    avg_label = (
        f"active-phase avg = {avg_power_active:.1f} W"
        if USE_ACTIVE_PHASE else f"avg = {avg_power:.1f} W"
    )
    eq_text = (
        r"$P = \dot{m}\,c\,\Delta T = \dot{m}\,c\,(T_{in}-T_{out})$" "        "
        rf"$\dot{{m}} = {flow_kg_s:.6f}$ kg/s ({FLOW_ML_PER_MIN:.1f} ml/min)," 
        rf"  $c = {C}$ J/kg$\degree$C" "        "
        + avg_label
    )

    fig.tight_layout(rect=[0, 0.08, 1, 1])
    fig.subplots_adjust(hspace=0.45)
    fig.text(
        0.5, 0.02, eq_text,
        ha="center", va="bottom", fontsize=10,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
    )
    fig.savefig(out_png, dpi=150)
    print(f"Saved plot: {out_png}")
    plt.close(fig)

except ImportError:
    print("matplotlib not installed, skipping plot.")