import numpy as np
import matplotlib.pyplot as plt

# Parameters CHANGE MASS, AREA, METABO when change size
MASS_KG      = 1.0
CP           = 3500.0 # J/(kg*K)  specific heat of tissue
EMISSIVITY   = 0.98 # skin/tissue emissivity
SURFACE_AREA = 0.05 # m^2  — surface area of 1 kg tissue chunk
Q_METABOLIC  = 1.0 # W/kg  metabolic heat rate × mass = 1 W (human resting: ~1 W/kg)
SIGMA        = 5.67e-8  # W/(m^2*K^4)  Stefan-Boltzmann
H_CONV       = 5.0  # W/(m^2*K)   natural convection (~5 still air, ~10-15 light air)

# Temperatures [°C] TO MODIFY WHEN PARAM CHANGE
T_INITIAL    = 37.0
T_ENV        = 20.0
T_TARGET     = 35.0

Q_COOLING    = 5.0 # Cooling power
T_TOTAL_S    = 2 * 3600 # Duration of simulation
DT_S         = 1.0 # Time step [s]


# ODE integration
N     = int(T_TOTAL_S / DT_S) + 1 # amount of steps in the simulation
t_arr = np.zeros(N)
T_arr = np.zeros(N)
Qrad_arr  = np.zeros(N)
Qconv_arr = np.zeros(N)
Qnet_arr  = np.zeros(N)

T = T_INITIAL
C = MASS_KG * CP

for i in range(N):
   t_arr[i] = i * DT_S
   T_arr[i] = T
   Q_rad     = EMISSIVITY * SIGMA * SURFACE_AREA * ((T+273.15)**4 - (T_ENV+273.15)**4) #+273.15 to convert to ° K
   Q_surface = H_CONV * SURFACE_AREA * (T - T_ENV)
   Qrad_arr[i]  = Q_rad
   Qconv_arr[i] = Q_surface
   Qnet_arr[i]  = Q_METABOLIC - Q_rad - Q_surface - Q_COOLING
   T += Qnet_arr[i] / C * DT_S # extract the raise in temp

t_target = next((t_arr[i] for i in range(N) if T_arr[i] <= T_TARGET), None) #finds first point where temp is below the target
t_min = t_arr / 60 # converts to minutes

# Sample points
sample_times_s = [T_TOTAL_S]  # end (120 min)
sample_idx = [int(ts / DT_S) for ts in sample_times_s]

# Data
col_labels = ["Time", "T (°C)", "Q_met (W)", "Q_rad (W)", "Q_conv (W)", "Q_cool (W)", "Q_net (W)", "T_ENV (°C)"]
table_data = []
for idx in sample_idx:
   qnet = Qnet_arr[idx]
   table_data.append([

       f"{t_arr[idx]/60:.0f} min",
       f"{T_arr[idx]:.2f}",
       f"{Q_METABOLIC:+.3f}",
       f"{-Qrad_arr[idx]:+.3f}",
       f"{-Qconv_arr[idx]:+.3f}",
       f"{-Q_COOLING:+.3f}",
       f"{qnet:+.3f}",
       f"{T_ENV:.1f}",
   ])

# Plot
fig, (ax, ax_t) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={"height_ratios": [2, 1]})
fig.suptitle("Simple Tissue Cooling 1 kg Power Analysis", fontsize=13)

# Top: Temperature vs Time
ax.plot(t_min, T_arr, color="tab:red", linewidth=2, label="Tissue temp") #Actual plot
ax.axhline(T_TARGET, color="tab:green", linestyle="--", linewidth=1.3, label=f"Target {T_TARGET}°C") #Line for the target temp

if t_target:
   ax.axvline(t_target/60, color="tab:green", linestyle="--", linewidth=1.0, alpha=0.6)


ax.set_xlabel("Time (min)")
ax.set_ylabel("Temperature (°C)")
ax.set_title("Temperature vs Time")
ax.set_xlim(0, T_TOTAL_S/60)
ax.legend(fontsize=9)
ax.grid(True, linestyle="--", alpha=0.4)

# Bottom: Power table
ax_t.axis("off")
tbl = ax_t.table(
   cellText=table_data,
   colLabels=col_labels,
   cellLoc="center",
   loc="center",
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(9)
tbl.scale(1.0, 1.8)

plt.show()




