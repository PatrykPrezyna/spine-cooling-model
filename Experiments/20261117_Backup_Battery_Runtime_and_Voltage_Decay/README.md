# Backup battery runtime and voltage decay

**Date:** 2026-11-17  
**Operator:** Patryk Prezyna  
**Goal:** Run the Cool Spine system on the backup battery and record how long it keeps running and how battery voltage falls. This checks hold-up against REQ-CP-003 (at least 30 minutes without wall power; up to 90 minutes acceptable).

## Protocol

1. Start the system on the backup battery (wall power disconnected).
2. Every 10 minutes, fill one row in `battery_voltage_log_template.csv`: clock time, battery voltage, and whether the system is still running.
3. Keep logging until the system can no longer hold. Note the stop time in the last row.
4. If it is still running past 180 minutes, add more rows in 10-minute steps.
5. When the run is finished, copy the completed sheet into `raw_data/` as `sensor_log_YYYYMMDD_HHMMSS_backup_battery.csv`. Do not edit that copy afterward.

## Setup

- Hardware / fixture / materials: Cool Spine system on its backup battery. TODO: battery identity, state of charge at start, and whether the UPS is in the path.
- Sensors and channels logged: battery voltage, written by hand every 10 minutes (no automated voltage channel in this run).
- Key setpoints (flow, temp, RPM, …): TODO — record the load the system is under while on battery (pump, refrigeration, UI).
- Photo or schematic: place under `setup/`.

Raw logs: prefer `sensor_log_YYYYMMDD_HHMMSS_<condition>.csv`. Never hand-edit files in `raw_data/`; regenerate plots and tables into `output_data/`. Commit the final result figure(s) cited in Results; regenerate the rest locally.

## Results

- TODO: voltage vs elapsed time (from `output_data/`)
- TODO: hold time (minutes until the system stops) and voltage at start and at stop
- Raw log: the completed copy of the 10-minute sheet in `raw_data/`

## Conclusion

- TODO: what we learned about hold time and the voltage curve
- TODO: implications for the battery / UPS design versus the 30-minute requirement
- TODO: open questions or follow-ups
