import glob
import pandas as pd
import matplotlib.pyplot as plt

T_HIGH = 37.0
T_LOW = 30.0
MASS_KG = 0.820   # 820 ml of water in the thermos
C = 4186          # J/kg°C for water

fig1, ax1 = plt.subplots()   # CSF cooling curves
fig2, ax2 = plt.subplots()   # cart_in - cart_out

for f in glob.glob("*.csv"):
    if f.startswith("_"):
        continue
    df = pd.read_csv(f)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    t = df["csf_c"]

    # Cooling starts at the peak (skips any initial warm-up). t=0 is the
    # downward 37 C crossing; end is the last time it's still at/above 30 C.
    peak_pos = t.values.argmax()
    after = t.iloc[peak_pos:]
    below_high = after.index[after <= T_HIGH]
    if len(below_high) == 0:
        continue
    start = below_high[0]
    above_low = t.loc[start:].index[t.loc[start:] >= T_LOW]
    if len(above_low) == 0:
        continue
    end = above_low[-1]
    if end <= start:
        continue

    minutes = (df["timestamp"].loc[start:end] - df["timestamp"].loc[start]).dt.total_seconds() / 60.0
    minutes = minutes.reset_index(drop=True)
    seg = t.loc[start:end].reset_index(drop=True)
    duration = minutes.iloc[-1]

    energy_kj = MASS_KG * C * (seg.iloc[0] - seg.iloc[-1]) / 1000.0
    avg_power = energy_kj * 1000.0 / (duration * 60.0) if duration > 0 else float("nan")

    # NOTE: for these tests the cart_in and cart_out sensors were physically
    # swapped, so we subtract in reverse (cart_out - cart_in) to recover the
    # correct temperature difference.
    cart_diff = (df["cart_out_c"] - df["cart_in_c"]).loc[start:end].reset_index(drop=True)

    label = "_".join(f.replace(".csv", "").split("_")[4:])
    print(f"{label:<24} 37->30 C took {duration:.1f} min  |  avg power {avg_power:.1f} W")
    ax1.plot(minutes, seg, label=f"{label} ({duration:.0f} min, {avg_power:.1f} W)")
    ax2.plot(minutes, cart_diff, label=label)

ax1.axhline(T_HIGH, color="gray", linestyle="--", alpha=0.6)
ax1.axhline(T_LOW, color="gray", linestyle="--", alpha=0.6)
ax1.set_xlabel("Time from 37 °C (min)")
ax1.set_ylabel("csf_c (°C)")
ax1.legend()

ax2.set_xlabel("Time from 37 °C (min)")
ax2.set_ylabel("cart_out − cart_in (°C, sensors swapped)")
ax2.set_title("Cart temperature difference")
ax2.grid(True, alpha=0.3)
ax2.legend()

plt.show()
