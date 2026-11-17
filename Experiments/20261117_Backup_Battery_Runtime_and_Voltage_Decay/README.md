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
6. Every 10 minutes, fill one row in `battery_voltage_log_template.csv`.
7. Keep logging until the system can no longer keep operating. Note the stop time in the last row.
8. When the run is finished, copy the completed sheet into `raw_data/` as `sensor_log_YYYYMMDD_HHMMSS_backup_battery.csv`. Do not edit that copy afterward.


Raw logs: prefer `sensor_log_YYYYMMDD_HHMMSS_<condition>.csv`. Never hand-edit files in `raw_data/`; regenerate plots and tables into `output_data/`. Commit the final result figure(s) cited in Results; regenerate the rest locally.

## Results

- The standstill current on the plug is 0.36A
- Battery Actual output power is 0.55A 
TODO: voltage vs elapsed time (from `output_data/`)
- TODO: hold time (minutes until the system stops) and voltage at start and at stop
- Raw log: the completed copy of the 10-minute sheet in `raw_data/`

## Conclusion

- TODO: what we learned about hold time and the voltage curve
- TODO: implications for the battery / UPS design versus the 30-minute requirement
- TODO: open questions or follow-ups

## Comments

- The standstill current on the plug is 0.36A
- Battery Actual output power is 0.55A 