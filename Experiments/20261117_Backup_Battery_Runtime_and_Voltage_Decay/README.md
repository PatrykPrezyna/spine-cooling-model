# Backup battery runtime and voltage decay

**Date:** 2026-11-17  
**Operator:** Patryk Prezyna  
**Goal:** Design verification VER-CP-003, internal electrical power source operating time, for REQ-CP-003. Run the Cool Spine system on the backup battery and record how long it keeps operating and how battery voltage falls. Pass if it is still operating at 30 minutes without wall power (up to 90 minutes acceptable). Keep logging until it stops so the record shows the actual operating time. Voltage is evidence of how the source decays; the requirement sets no voltage limit.

## Protocol

1. Open the Power management suite client v1.6.84.495 and got ot the Batteris page
1. Start the system on the supply mains.
1. siwtch the comporessor(v1 - Rigit) (setpoint -0.5C to 1.3C)
1. switch the perystaltic pump to 50ml/min (no tubing or cartrige in pace, no sensors =other than cool plate 1 connected)
2. make sure the battery is fully charged (no chargin is taking place )and note the "Actual battery voltage" before sithing on the battery podus
2. Every 10 minutes, fill one row in `battery_voltage_log_template.csv`
3. Keep logging until the system can no longer hold. Note the stop time in the last row.
5. When the run is finished, copy the completed sheet into `raw_data/` as `sensor_log_YYYYMMDD_HHMMSS_backup_battery.csv`. Do not edit that copy afterward.


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