# Backup battery runtime and voltage decay

**Date:** 2026-11-17  
**Operator:** Patryk Prezyna  
**Goal:** Design verification VER-CP-003, internal electrical power source operating time, for REQ-CP-003. Run the Cool Spine system on the backup battery and record how long it keeps operating and how battery voltage falls. Pass if it is still operating at 30 minutes without wall power (up to 90 minutes acceptable). Keep logging until it stops so the record shows the actual operating time. Voltage is evidence of how the source decays; the requirement sets no voltage limit.

## Expected runtime

Design output under test: **K2 Energy K2B24V11EB** (LiFePO4, datasheet Rev C). Nominal capacity **11.1 Ah** at C/5, average voltage **25.6 V**, discharge cutoff **20.0 V**. Recommended continuous discharge is **≤ 11.1 A**.

The Rev C constant-current table still returns the full 11.1 Ah at 11.1 A (60 min), so a load of about **9 A** needs no capacity derate:

**11.1 Ah / 9 A = 74 min.**

That is the prediction for a steady 9 A draw down to the battery's own cutoff. REQ-CP-003 passes at 30 minutes; 74 minutes also sits inside the "up to 90 minutes acceptable" band. The same capacity at nearby currents: 8 A → 83 min, 10 A → 67 min, 11.1 A → 60 min. The measured time is shorter if the UPS disconnects above 20.0 V, and longer if the compressor cycles and the average current is below 9 A.

## Protocol

Battery: K2 Energy K2B24V11EB.

1. Open Power Management Suite client v1.6.84.495 and go to the Batteries page.
2. Start the system on mains power.
3. Switch on the compressor (v1 — Rigid). Setpoint −0.5 °C to 1.3 °C.
4. Set the peristaltic pump to 50 ml/min. No tubing or cartridge in place. No sensors connected other than cool plate 1.
5. Confirm the K2B24V11EB is fully charged (charging has stopped). Note "Actual battery voltage" and the battery current, then switch onto battery power.
6. Every 10 minutes, record elapsed time, actual output current, actual battery voltage, and a short note.
7. Keep logging until the system can no longer keep operating. Note the stop time in the last row.
8. Save the completed sheet in `raw_data/` as `sensor_log_YYYYMMDD_HHMMSS_backup_battery.csv`. Do not edit that copy afterward.

Raw logs: prefer `sensor_log_YYYYMMDD_HHMMSS_<condition>.csv`. Never hand-edit files in `raw_data/`; regenerate plots into `output_data/`. Commit the final result figure cited in Results.

## Setup

- Battery: K2 Energy K2B24V11EB, read from Power Management Suite client v1.6.84.495, Batteries page.
- Load: Rigid compressor v1, setpoint −0.5 °C to 1.3 °C, and the peristaltic pump at 50 ml/min. No tubing, no cartridge. Cool plate 1 is the only sensor connected.
- Logged columns: elapsed minutes, actual output current (A), actual battery voltage (V), notes. Samples are manual, about every 10 minutes, with extra rows at the start and at switch-off.
- Bench notes taken with the system not in the discharge run: standstill current on the plug **0.36 A**; battery actual output current **0.55 A**.

## Results

Regenerate with `python plot_battery_voltage.py` from this folder.

![Backup battery voltage](output_data/battery_voltage_sensor_log_20261117_backup_battery.png)

Raw log: [sensor_log_20261117_backup_battery.csv](raw_data/sensor_log_20261117_backup_battery.csv). The filename has no clock time; the sheet does not record one.

| Elapsed (min) | Current (A) | Voltage (V) | Note |
|---:|---:|---:|---|
| 0 | — | 28.61 | On mains, not running |
| 1 | 4.45 | 27.0 | On battery, compressor and pump running |
| 30 | 6.99 | 25.41 | After restart. Still operating |
| 60 | 9.47 | 24.3 | Cool plate 5.7 °C |
| 70 | 10.5 | 22.0 | |
| 72 | — | 17.1 | Under the 20 V threshold; switched off |

From 1 min to 70 min the trapezoidal average current is **8.9 A**, and the charge drawn over that span is **10.3 Ah** (about 93% of the 11.1 Ah nameplate). Current at 72 min was not written down. While the compressor was up to speed the current sat near **9.0–9.5 A**, then **10.5 A** at 70 min. The 30 min sample is the exception, at **6.99 A**, on the row marked "after restart".

Voltage left the mains reading of **28.61 V**, reached the LiFePO4 plateau near **25.1–25.4 V** by 3 min, and stayed there through 30 min. It was **24.9 V** at 40 min, **24.3 V** at 60 min, **22.0 V** at 70 min, and **17.1 V** at switch-off.

## Conclusion

- REQ-CP-003 is met on this run. The system was still operating at 30 minutes (6.99 A, 25.41 V) and kept operating until **72 minutes**, when the source switched off at **17.1 V**. That is inside the "up to 90 minutes acceptable" band.
- 72 minutes is 2 minutes under the 74 minute prediction
- The voltage curve is the LiFePO4 plateau, not a steady decline. From 3 min to 30 min the voltage moved only between 25.10 V and 25.41 V. The useful warning is the drop through 24 V after 60 min. A reading still near 25 V does not mean half the runtime remains.
- The 30 min row says "after restart", and the current there is about 2 A below the rest of the loaded run. This log shows 72 minutes on the battery, including a restart. It does not show one uninterrupted compressor run.
- Next run: no mid-test restart, with tubing and the cartridge installed,

- after the test the battery volteg went to 3v, the UPS refuse to charge, i had to diconnet the battery, the volteg wend to 22V i conenced again and chargin with 3A began
- 