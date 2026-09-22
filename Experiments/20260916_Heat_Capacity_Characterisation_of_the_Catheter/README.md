# Heat capacity characterisation of the catheter

**Date:** 2026-09-16, 2026-09-18, 2026-09-21  
**Operator:**  
**Goal:** Characterise the catheter heat pickup: P-power and UA-Thermal Conductance (The combined capacity of the equipment to transfer heat per degree of temperature difference), and response speed from inlet and outlet temperatures at constant flow.

Note: temp probes Plate 1, Plate 2, Body Temp and Probe 4 were not connected.

## Protocol

1. Use tubing lengths matching the final product, then repeat with a shortened pump-to-catheter line.
2. Replace the cartridge with a container of ice water.
3. Place the catheter in a controlled-temperature bath. Mix the bath and measure it with two sensors.
4. Pump at a constant **~50 ml/min** (57 rpm), then repeat at **27 rpm (~22 ml/min)** and **81 rpm (~70 ml/min)**.
5. Step the bath from **30 to 36 °C**. The logs actually hold at **~30, 32, 34, 36 °C** (2 °C), plus a 28 °C pre-hold on the shortened and 27 rpm runs.
6. Log catheter **input** and **output** temperature. From the settled tails, calculate heat power and UA.

Prefer raw logs named `sensor_log_YYYYMMDD_HHMMSS_<condition>.csv`. Never hand-edit `raw_data/`; regenerate into `output_data/`.

## Setup


Runs:

- **Original tubing, ~50 ml/min** — product-length line, 57 rpm, Keyence connected. Raw: [20260916_120302_sensors_50mlmin_original_tubing.csv](raw_data/20260916_120302_sensors_50mlmin_original_tubing.csv)
- **26 cm tubing, ~50 ml/min** — pump-to-catheter line cut to 26 cm, 57 rpm. **Keyence was not connected**; flow is from the rpm fit. Raw: [20260916_123901_sensors_50mlmin_26cm.csv](raw_data/20260916_123901_sensors_50mlmin_26cm.csv)
- **26 cm tubing, ~22 ml/min** — same bath steps at 27 rpm. Keyence connected. Inlet ~5.6 °C, matching the 26 cm ~50 ml/min run. Raw: [20260918_142602_sensors_22mlmin.csv](raw_data/20260918_142602_sensors_22mlmin.csv)
- **26 cm tubing, ~70 ml/min** — same bath steps at 81 rpm. Keyence connected. Inlet ~4.5 °C. Raw: [20260921_093450_sensors_70mlmin.csv](raw_data/20260921_093450_sensors_70mlmin.csv)
- **Other catheter, ~50 ml/min** — different catheter, 57 rpm, Keyence connected. Raw: [20260921_101547_sensors_50mlmin_other_catheter.csv](raw_data/20260921_101547_sensors_50mlmin_other_catheter.csv)

## Heat power calculation

Heat picked up by the coolant:

```
P = ṁ · c_p · (T_out − T_in)
```

with **c_p = 4186 J/(kg·K)** and **1 ml = 0.001 kg**. In the analysis script:

```text
ṁ = (flow_ml_min / 60) * 0.001
P       = ṁ * 4186 * (T_out - T_in)
```

T_in, T_out, and flow are means over the last **45 s** of each bath plateau.

Worked example (26 cm, 36.3 °C hold):

```
ΔT = T_out − T_in
   = 16.69 − 5.42
   = 11.27 °C

Q  = 50.09 ml/min

ṁ  = (Q / 60) × 0.001
   = (50.09 / 60) × 0.001
   = 0.8348 × 0.001
   = 8.35 × 10⁻⁴ kg/s

P  = ṁ × c_p × ΔT
   = (8.35 × 10⁻⁴) × 4186 × 11.27
   = 39.4 W
```

Heat-transfer capacity **UA = P / LMTD**. LMTD is the log-mean temperature difference: the driving gap between bath and coolant, accounting for the coolant warming as it flows. The bath is treated as a constant-temperature source:

```
ΔT_in  = T_bath − T_in
ΔT_out = T_bath − T_out
LMTD   = (ΔT_in − ΔT_out) / ln(ΔT_in / ΔT_out)
UA     = P / LMTD
```

## Results

```bash
python analyze_heat_power.py
```

### Original tubing (~50 ml/min)

![Original tubing — heat power vs bath temperature](output_data/heat_power_vs_bath_temperature_original_tubing.png)

![Original tubing — heat power vs bath step](output_data/heat_power_20260916_120302_sensors_50mlmin_original_tubing.png)

| Bath °C | T_in °C | T_out °C | ΔT °C | Q ml/min | P W | UA W/K | ε |
|--------:|--------:|---------:|------:|---------:|----:|-------:|--:|
| 30.22 | 7.45 | 16.08 | 8.64 | 49.7 | 30.0 | 1.65 | 0.38 |
| 32.24 | 7.88 | 17.02 | 9.15 | 50.2 | 32.0 | 1.65 | 0.38 |
| 34.29 | 7.44 | 17.44 | 10.00 | 50.8 | 35.5 | 1.65 | 0.37 |
| 36.33 | 7.68 | 18.13 | 10.46 | 51.1 | 37.2 | 1.62 | 0.36 |

Flow-on settle of the first 30 °C pulse: **78 s** to 5% of steady ΔT.

### 26 cm tubing (22 / 50 / 70 ml/min)

![26 cm tubing — heat power vs bath temperature](output_data/heat_power_vs_bath_temperature.png)

![26 cm tubing — heat power vs flow at 36 °C](output_data/heat_power_vs_flow_36C.png)

Predicted P is interpolated every **10 ml/min** from the 22 / 50 / 70 ml/min holds at 36 °C.

```
P = ṁ · c_p · (T_bath − T_in) · (1 − exp(−UA / (ṁ · c_p)))
```

![26 cm tubing, ~50 ml/min — heat power vs bath step](output_data/heat_power_20260916_123901_sensors_50mlmin_26cm.png)

Keyence was not connected on this run; Q is from the rpm fit (50.1 ml/min at 57 rpm).

| Bath °C | T_in °C | T_out °C | ΔT °C | Q ml/min | P W | UA W/K | ε |
|--------:|--------:|---------:|------:|---------:|----:|-------:|--:|
| 28.19 | 5.14 | 13.69 | 8.55 | 50.1 | 29.9 | 1.62 | 0.37 |
| 30.22 | 5.22 | 14.44 | 9.22 | 50.1 | 32.2 | 1.61 | 0.37 |
| 32.23 | 5.46 | 15.34 | 9.88 | 50.1 | 34.5 | 1.61 | 0.37 |
| 34.29 | 5.28 | 16.01 | 10.73 | 50.1 | 37.5 | 1.61 | 0.37 |
| 36.33 | 5.42 | 16.69 | 11.27 | 50.1 | 39.4 | 1.58 | 0.36 |

![26 cm tubing, ~22 ml/min — heat power vs bath step](output_data/heat_power_20260918_142602_sensors_22mlmin.png)

Keyence connected; Q is **21–23 ml/min** at 27 rpm.

| Bath °C | T_in °C | T_out °C | ΔT °C | Q ml/min | P W | UA W/K | ε |
|--------:|--------:|---------:|------:|---------:|----:|-------:|--:|
| 28.17 | 5.52 | 18.74 | 13.22 | 23.1 | 21.3 | 1.41 | 0.58 |
| 30.22 | 5.62 | 19.88 | 14.26 | 22.3 | 22.2 | 1.35 | 0.58 |
| 32.25 | 5.78 | 21.04 | 15.27 | 22.0 | 23.4 | 1.32 | 0.58 |
| 34.28 | 5.93 | 22.21 | 16.28 | 21.7 | 24.7 | 1.29 | 0.57 |
| 36.35 | 5.97 | 23.35 | 17.38 | 21.3 | 25.8 | 1.26 | 0.57 |

![26 cm tubing, ~70 ml/min — heat power vs bath step](output_data/heat_power_20260921_093450_sensors_70mlmin.png)

Keyence connected; Q is **65–67 ml/min** at 81 rpm (fit 70.4 ml/min).

| Bath °C | T_in °C | T_out °C | ΔT °C | Q ml/min | P W | UA W/K | ε |
|--------:|--------:|---------:|------:|---------:|----:|-------:|--:|
| 28.15 | 4.71 | 11.55 | 6.84 | 66.7 | 31.8 | 1.60 | 0.29 |
| 30.19 | 4.43 | 12.31 | 7.88 | 66.3 | 36.4 | 1.69 | 0.31 |
| 32.21 | 4.45 | 12.85 | 8.40 | 66.1 | 38.7 | 1.66 | 0.30 |
| 34.24 | 4.48 | 13.47 | 8.99 | 65.7 | 41.2 | 1.65 | 0.30 |
| 36.31 | 4.56 | 14.08 | 9.53 | 65.2 | 43.3 | 1.62 | 0.30 |

![Other catheter, ~50 ml/min — heat power vs bath step](output_data/heat_power_20260921_101547_sensors_50mlmin_other_catheter.png)

Different catheter at 57 rpm; Keyence **46–48 ml/min**.

| Bath °C | T_in °C | T_out °C | ΔT °C | Q ml/min | P W | UA W/K | ε |
|--------:|--------:|---------:|------:|---------:|----:|-------:|--:|
| 28.13 | 4.77 | 10.35 | 5.58 | 47.7 | 18.5 | 0.91 | 0.24 |
| 30.16 | 4.65 | 10.85 | 6.20 | 47.8 | 20.7 | 0.93 | 0.24 |
| 32.16 | 4.67 | 11.50 | 6.83 | 47.4 | 22.6 | 0.94 | 0.25 |
| 34.22 | 4.62 | 11.97 | 7.35 | 47.1 | 24.1 | 0.94 | 0.25 |
| 36.21 | 4.69 | 12.84 | 8.15 | 46.1 | 26.2 | 0.96 | 0.26 |

Table: [heat_power_by_bath_step.csv](output_data/heat_power_by_bath_step.csv)


## Conclusion

- At ~50 ml/min the catheter picks up **30–39 W** over the 30–36 °C bath range. Power rises with bath temperature; **UA stays ~1.61–1.65 W/K** (effectiveness ~0.37).
- Cutting the pump-to-catheter line to **26 cm** makes the inlet ~2.3 °C colder and raises power **6–8%** at the same bath temperature. UA does not increase, so the extra power is less inlet-line warming, not a change in the catheter.
- At **~22 ml/min** (27 rpm, 26 cm line) power falls to **21–26 W**. ΔT and effectiveness rise (~0.57); UA drops to **1.26–1.41 W/K**.
- At **~70 ml/min** (81 rpm, Keyence 65–67 ml/min) power rises to **32–43 W**. ΔT and effectiveness fall (~0.30); UA stays **~1.60–1.69 W/K**, similar to the 50 ml/min 26 cm run.
- A **different catheter** at ~50 ml/min (Keyence 46–48 ml/min) picks up only **19–26 W**, with UA **~0.91–0.96 W/K** — well below the first catheter at the same pump speed.
