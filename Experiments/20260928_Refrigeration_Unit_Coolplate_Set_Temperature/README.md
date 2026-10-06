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
- [Overnight plot](output_data/coolplate_temperatures_20260929_230421_sensors.png) — [log](raw_data/20260929_230421_sensors.csv). No `set_<value>C` in the filename. Compressor on: **0.49–2.68 min**, **5.99–7.92 min**, **14.68–16.65 min**, **23.36–25.37 min**, **33.04–35.01 min**, **41.99–43.99 min**, **51.27–53.28 min**, **60.56–62.45 min**, **68.75–70.69 min**, **77.41–79.38 min**, **86.00–87.91 min**, **93.95–95.87 min**, **102.03–103.97 min**, **110.10–112.01 min**, **118.11–120.02 min**, **126.70–128.62 min**, **134.86–136.83 min**, **143.24–145.18 min**, **151.65–153.67 min**, **160.39–162.42 min**, **169.08–171.06 min**, **177.19–179.12 min**, **185.23–188.29 min**, **193.66–195.66 min**, **202.93–204.94 min**, **212.43–214.42 min**, **220.38–222.36 min**, **228.69–230.64 min**, **236.65–237.19 min**. Off after that, through the end of the log (735 min). Plate 1 swings 0–5 °C on each cycle; both plates then warm to about 19 °C.
- [14:52 hold](output_data/coolplate_temperatures_20260930_145204_sensors.png) — [log](raw_data/20260930_145204_sensors.csv). 15 min, plates already cold. No `set_<value>C` in the filename. Compressor on: **0.27–15.22 min**. Plate 1 holds near 1.5 °C, plate 2 near 2.5 °C, backups near 8.5 °C.
- [17:03 cycling](output_data/coolplate_temperatures_20260930_170338_sensors.png) — [log](raw_data/20260930_170338_sensors.csv). 17.5 h (30 Sep 17:03 to 1 Oct 10:34). No `set_<value>C` in the filename. Compressor on in short pulses (about 2 min) grouped into blocks: **0.20–6.69 min**, **9.29–12.37 min**, **15.01–17.81 min**, **20.29–22.81 min**, **25.96–28.75 min**, **31.92–34.12 min**, **37.19–39.58 min**, **42.44–44.58 min**, **47.56–49.72 min**, **52.51–54.66 min**, **57.39–59.53 min**, **62.21–64.38 min**, **67.07–69.40 min**, **72.33–74.49 min**, **77.38–79.84 min**, **82.93–85.12 min**, **88.05–90.35 min**, **93.56–95.93 min**, **98.86–101.05 min**, **103.58–106.12 min**, **109.29–111.44 min**, **114.03–116.60 min**, **119.93–122.11 min**, **124.92–127.20 min**, **133.73–135.91 min**, **138.88–141.45 min**, **176.15–178.29 min**, **211.32–214.56 min**, **218.06–220.24 min**, **223.19–225.34 min**, **229.07–231.23 min**, **278.98–281.07 min**, **284.30–286.33 min**, **289.24–291.38 min**, **294.10–296.27 min**, **298.67–300.78 min**, **303.58–305.78 min**, **308.43–310.72 min**, **313.31–315.40 min**, **318.39–320.60 min**, **323.12–325.32 min**, **328.06–330.38 min**, **333.25–335.39 min**, **338.25–340.46 min**, **342.93–345.05 min**, **347.80–349.90 min**, **352.29–354.37 min**, **356.74–358.86 min**, **361.33–363.57 min**, **366.09–368.26 min**, **370.65–372.79 min**, **375.46–377.91 min**, **380.69–383.06 min**, **386.09–388.29 min**, **390.84–393.02 min**, **395.84–398.11 min**, **400.75–402.94 min**, **405.83–407.99 min**, **410.66–413.12 min**, **416.12–418.65 min**, **452.77–454.92 min**, **457.73–459.82 min**, **462.31–464.37 min**, **467.29–469.46 min**, **472.26–474.45 min**, **477.02–479.21 min**, **481.93–484.18 min**, **487.23–489.40 min**, **492.20–494.61 min**, **526.53–528.69 min**, **531.46–533.58 min**, **538.16–540.27 min**, **568.24–570.32 min**, **574.65–576.79 min**, **580.52–582.73 min**, **585.76–587.87 min**, **637.09–639.31 min**, **642.13–644.21 min**, **647.02–649.15 min**, **651.71–653.83 min**, **656.24–658.34 min**, **661.10–663.26 min**, **665.97–668.32 min**, **671.52–673.67 min**, **676.58–678.86 min**, **681.62–683.91 min**, **686.62–688.78 min**, **691.43–693.62 min**, **696.19–698.32 min**, **701.05–703.59 min**, **707.11–709.31 min**, **712.28–714.52 min**, **717.23–719.47 min**, **722.33–724.60 min**, **727.29–729.48 min**, **732.09–734.67 min**, **774.76–776.96 min**, **780.22–782.27 min**, **785.18–787.32 min**, **790.06–792.21 min**, **795.01–797.12 min**, **800.00–802.13 min**, **805.02–807.22 min**, **810.18–812.60 min**, **815.79–818.06 min**, **820.73–822.90 min**, **825.76–827.98 min**, **830.71–832.98 min**, **835.65–838.14 min**, **841.73–844.11 min**, **847.16–849.40 min**, **852.72–854.92 min**, **857.48–859.75 min**, **862.87–865.30 min**, **868.51–871.06 min**, **915.53–917.71 min**, **920.63–922.75 min**, **925.62–927.76 min**, **931.90–934.06 min**, **937.32–939.67 min**, **978.97–981.13 min**, **984.23–986.28 min**, **989.28–992.48 min**, **995.00–997.14 min**, **1000.18–1002.30 min**, **1005.35–1007.48 min**, **1010.37–1012.47 min**, **1015.04–1017.11 min**, **1020.43–1022.58 min**, **1025.44–1027.56 min**, **1030.31–1032.49 min**, **1035.56–1037.65 min**. During the long gaps between those blocks the cooling command is off and both plates fall to about −12 to −16 °C. The log ends with the compressor off and the plates still near −7 °C.
- [2 Oct pull-down](output_data/coolplate_temperatures_20261002_131346_sensors.png) — [log](raw_data/20261002_131346_sensors.csv). 197 min (13:13–16:30). No `set_<value>C` in the filename. Compressor on: **2.80–13.12 min**, **14.12–23.39 min**, **24.39–42.72 min**, **43.72–87.07 min**, **88.07–146.55 min**, **148.68–196.73 min**. Off gaps are about 1 min (the 60 s lockout). Plates swing between about −5 °C and 7 °C and do not settle; backups move between about 5 °C and 14 °C. The log ends with the compressor still on.

## Archive

Superseded runs from 2026-09-28, before the probe rename and backup-probe move. Do not mix these with the rerun.

Old logger headers `ice_water_c` and `hot_bath2_c` were renamed in the −3 °C file to `cool_plate_backup_sensor_1_c` and `cool_plate_backup_sensor_2_c`. The −1 °C file still has the original headers. After the renumber, `ice_water_c` is cool plate 2 backup and `hot_bath2_c` is cool plate 1 backup. Logged `set_temperature_c` is 32 °C in both; the refrigeration set temperature is in the filename.

- [−3 °C plot](archive/output_data/coolplate_temperatures_20260928_094635_sensors_set_-3C.png) — [log](archive/raw_data/20260928_094635_sensors_set_-3C.csv). Compressor on: **0.22–5.60 min**, **6.60–8.68 min**, **9.69–54.07 min**.
- [−1 °C plot](archive/output_data/coolplate_temperatures_20260928_104911_sensors_set_-1C.png) — [log](archive/raw_data/20260928_104911_sensors_set_-1C.csv). Compressor on: **0.18–2.68 min**, **3.69–5.15 min**, **6.15–8.35 min**, **9.35–11.15 min**, **12.15–13.92 min**, **14.93–16.68 min**, **17.69–19.46 min**, **20.46–22.23 min**.

## Conclusion

- What we learned
- Implications for the next design / test
- Open questions or follow-ups
