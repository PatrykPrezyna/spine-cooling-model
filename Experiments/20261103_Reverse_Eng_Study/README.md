# Reverse Eng Study

**Date:** 2026-11-03  
**Operator:**  
**Goal:** Test an old prototype as a reverse-engineering study.

## Protocol

1. TODO

## Setup

- Old white cartridge. It started leaking during the run.
- Only one cold plate was active.
- Cooling was on for the whole run.
- Sensors and channels logged: cartridge inlet and outlet, flow
- Photo or schematic: place under `setup/`

Prefer raw logs named `sensor_log_YYYYMMDD_HHMMSS_<condition>.csv` or `pressure_log_YYYYMMDD_HHMMSS_<condition>.csv`. Do not hand-edit `raw_data/`; regenerate analysis into `output_data/`.

## Results

- Plot: `output_data/cooling_power_20261103_120906_sensors.png` from `plot_cooling_power.py`. The figure shows only samples with cooling power above 0 W.
- Raw log: `raw_data/20261103_120906_sensors.csv`
- While power is above 0 W, flow is about 46 ml/min. Cartridge input stays near 20 °C until about 18 min, then steps to about 23.6 °C. Output falls from about 20 °C to about 11 °C. From 20–29 min the median cooling power is 38.5 W (`P = m_dot * 4186 * (T_in - T_out)`).
- A brief output dip to 4.5 °C at 18.3 min spikes power to 51 W. The status log records `CSF_LOW_TEMP` about 10 s after the session starts; cooling stayed on.

Commit the final result figure(s) cited here; regenerate the rest locally.

## Conclusion

- What we learned: TODO
- Implications for the next design / test: TODO
- Open questions or follow-ups: TODO
