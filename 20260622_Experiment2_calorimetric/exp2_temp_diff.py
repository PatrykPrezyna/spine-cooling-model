import pandas as pd

# --- USER SETTINGS ---
print("Starting experiment 2")
FILE = "sensor_log_20260622_153100.csv"
FLOW_ML_PER_MIN = 46.0
C = 4186  # J/kg°C for water

# --- CONVERSIONS ---
flow_kg_s = (FLOW_ML_PER_MIN / 1000.0) / 60.0  # ml/min → kg/s

# --- LOAD DATA ---
df = pd.read_csv(FILE)

# --- CLEAN COLUMN NAMES (in case of formatting issues) ---
df.columns = [c.strip().replace("\\", "").lower() for c in df.columns]

# Expected columns (based on your file)
# cart_in_c = hot fluid entering HX
# cart_out_c = cooled fluid leaving HX

# --- COMPUTE DELTA T ---
df["delta_t"] = df["cart_in_c"] - df["cart_out_c"]

# --- COMPUTE INSTANTANEOUS POWER (W) ---
df["power_w"] = flow_kg_s * C * df["delta_t"]

# --- RESULTS ---
avg_power = df["power_w"].mean()
max_power = df["power_w"].max()
min_power = df["power_w"].min()

print("=== Cooling Power Results ===")
print(f"Flow rate: {FLOW_ML_PER_MIN} ml/min ({flow_kg_s:.6f} kg/s)")
print(f"Average power: {avg_power:.2f} W")
print(f"Max power:     {max_power:.2f} W")
print(f"Min power:     {min_power:.2f} W")

# --- OPTIONAL: save results ---
df.to_csv("calculated_power.csv", index=False)

# --- OPTIONAL: simple plot ---
try:
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(9, 6))

    ax1.plot(df["cart_in_c"], color="tab:red", label="cart_in (°C)")
    ax1.plot(df["cart_out_c"], color="tab:green", label="cart_out (°C)")
    ax1.set_ylabel("Temperature (°C)")
    ax1.set_title("Cart Temperatures and Cooling Power vs Time")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    ax2.plot(df["power_w"], color="tab:blue")
    ax2.set_ylabel("Cooling Power (W)")
    ax2.set_xlabel("Sample")
    ax2.grid(True, alpha=0.3)

    # Power equation + parameters used in the calculation
    eq_text = (
        r"$P = \dot{m}\,c\,\Delta T = \dot{m}\,c\,(T_{in}-T_{out})$" "        "
        rf"$\dot{{m}} = {flow_kg_s:.6f}$ kg/s ({FLOW_ML_PER_MIN:.1f} ml/min)," 
        rf"  $c = {C}$ J/kg$\degree$C" "        "
        rf"avg = {avg_power:.1f} W,  max = {max_power:.1f} W,  min = {min_power:.1f} W"
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