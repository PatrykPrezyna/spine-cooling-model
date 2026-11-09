# Solid-state plate cartridge prototype

**Date:** 2026-11-03  
**Operator:**  
**Goal:** Test the prototype fitted with the new cartridge that uses solid-state plates.

## Protocol

1. TODO

## Setup

- Hardware: prototype with the new cartridge and solid-state plates.
- Started with one plate only, then added the second plate.
- The set temp wa -21 but reached about -15C
- After 60 min, switched the set temperature on both plates to −10 °C.
- After 70 min (from experiment start), switched the set temperature on both plates to −5 °C.
- After 85 min (from experiment start), switched the set temperature on both plates to −1 °C.
- Sensors and channels logged: cartridge inlet and outlet, Keyence flow, pump speed. `plate_1_c` and `plate_2_c` are open-circuit in this log.
- Pump command settled at 50 ml/min (57 rpm). The initial plate set temperature is not in the log.
- Photo or schematic: place under `setup/`

Prefer raw logs named `sensor_log_YYYYMMDD_HHMMSS_<condition>.csv` or `pressure_log_YYYYMMDD_HHMMSS_<condition>.csv`. Do not hand-edit `raw_data/`; regenerate analysis into `output_data/`.

## Results

Preliminary, from `plot_cooling_power.py`.

- Plot: `output_data/cooling_power_20261103_141619_sensors.png`
- Raw log: `raw_data/20261103_141619_sensors.csv` (14:16–15:51, 94 min).
- `plate_1_c` and `plate_2_c` stay on the open-circuit sentinel (about −350 °C to −410 °C), so the solid-state plate temperatures are not in this log. Cooling power is water-side only: `P = m_dot * 4186 * (T_in - T_out)`, using the flow sensor when it reads above 5 ml/min.
- The flow sensor reads about 26 ml/min from 3–18 min, then about 44–46 ml/min from 20 min to the end. Commanded pump flow is 50 ml/min (57 rpm).
- The outlet is warmer than the inlet until about 8 min. Median cooling power is about 6 W at 8–15 min, about 18 W at 25 min, and about 27 W at 45 min.
- Near 50–54 min the outlet falls from about 10 °C to 4.8 °C and median power rises from about 32 W to 49 W. The inlet is about 17.9 °C at 53 min, then steps to about 22 °C.
- The dashed line is the plate set temperature from this README, not from `set_temperature_c` (that column stays at 32 °C). The value before 60 min was not recorded. Both plates are −10 °C from 60 min, −5 °C from 70 min, and −1 °C from 85 min.
- Labels on the power trace are the median of the last 2 min of each step. 60–70 min (−10 °C): 46 W. 70–85 min (−5 °C): 37 W. 85–94 min (−1 °C): 32 W.

Commit the final result figure(s) cited here; regenerate the rest locally.

## Conclusion

- What we learned: TODO
- Implications for the next design / test: TODO
- Open questions or follow-ups: TODO
