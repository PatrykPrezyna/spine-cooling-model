# Refrigeration unit cool-plate set temperature

**Date:** 2026-09-28, 2026-09-29  
**Operator:**  
**Goal:** Characterise the refrigeration unit (compressor and cool plates) at a commanded set temperature, with one temperature probe on each cool plate. Later runs will add the cartridge and extra temperature sensors.

## Protocol

1. Command a set temperature on the refrigeration unit. The refrigeration set / off temperature is not logged (`set_temperature_c` stays at 32 °C, the controller setpoint). Name each log `..._set_<value>C.csv`.
2. Log one temperature probe on each cool plate, plus the backup probe on each plate, while the unit holds that setpoint.
3. Later: include the cartridge, and add further temperature sensors.

Prefer raw logs named `sensor_log_YYYYMMDD_HHMMSS_<condition>.csv`. Never hand-edit `raw_data/`; regenerate into `output_data/`. Commit final result figure(s) cited in Results; regenerate the rest locally.

## Setup

- Hardware: refrigeration unit (compressor and two cool plates). Cartridge to be added in later runs.
- Probe names and backup-probe placement were changed after the archived runs. Current channels: `plate_1_c`, `plate_1b_c`, `plate_2_c`, `plate_2b_c`. Cool plate sensor 1 was renumbered to cool plate 2, and cool plate 2 to cool plate 1; the backup on each plate was renumbered the same way. Headers in `raw_data/` and `archive/raw_data/` use those corrected numbers. Placement:

![Probe placement](setup/probes_location.png)

- The compressor stays off for **60 s** after each real off, even if `compressor_cooling` returns to 1. Command pulses shorter than 2 s are ignored.

## Results

New probe names and backup placement. Single-sample grounding spikes are removed in the plot only. Regenerate with `python plot_coolplate_temperatures.py` from this folder. Each log also writes an interactive HTML file next to the PNG: open it in a browser to zoom, hide series from the legend, and hover for the clock time and temperature.

- [−1 °C plot](output_data/coolplate_temperatures_20260929_085741_sensors_sensors_set_-1C.png) — [log](raw_data/20260929_085741_sensors_sensors_set_-1C.csv). Compressor on: **0.32–4.68 min**, **5.68–7.42 min**, **8.42–10.32 min**, **11.32–14.62 min**, **15.62–17.52 min**, **18.52–20.53 min**, **21.53–23.35 min**, **24.36–26.15 min**, **27.16–28.96 min**, **29.97–31.74 min**, **32.75–34.50 min**, **35.50–37.28 min**, **38.29–40.04 min**, **41.04–42.85 min**, **43.86–45.66 min**, **46.66–48.44 min**, **49.44–51.21 min**.
- [−2 °C plot](output_data/coolplate_temperatures_20260929_095055_sensors_sensors_set_-2C.png) — [log](raw_data/20260929_095055_sensors_sensors_set_-2C.csv). Compressor on: **0.48–2.77 min**, **3.77–5.53 min**, **6.53–8.46 min**, **9.46–11.44 min**, **12.44–14.47 min**, **15.47–17.60 min**, **18.60–20.66 min**, **21.66–23.79 min**, **24.79–26.87 min**, **27.87–30.09 min**, **31.09–33.21 min**.

## Archive

Superseded runs from 2026-09-28, before the probe rename and backup-probe move. Do not mix these with the rerun.

Old logger headers `ice_water_c` and `hot_bath2_c` were renamed in the −3 °C file to `cool_plate_backup_sensor_1_c` and `cool_plate_backup_sensor_2_c`. The −1 °C file still has the original headers. After the renumber, `ice_water_c` is cool plate 2 backup and `hot_bath2_c` is cool plate 1 backup. Logged `set_temperature_c` is 32 °C in both; the refrigeration set temperature is in the filename.

- [−3 °C plot](archive/output_data/coolplate_temperatures_20260928_094635_sensors_set_-3C.png) — [log](archive/raw_data/20260928_094635_sensors_set_-3C.csv). Compressor on: **0.22–5.60 min**, **6.60–8.68 min**, **9.69–54.07 min**.
- [−1 °C plot](archive/output_data/coolplate_temperatures_20260928_104911_sensors_set_-1C.png) — [log](archive/raw_data/20260928_104911_sensors_set_-1C.csv). Compressor on: **0.18–2.68 min**, **3.69–5.15 min**, **6.15–8.35 min**, **9.35–11.15 min**, **12.15–13.92 min**, **14.93–16.68 min**, **17.69–19.46 min**, **20.46–22.23 min**.

## Conclusion

- What we learned
- Implications for the next design / test
- Open questions or follow-ups
