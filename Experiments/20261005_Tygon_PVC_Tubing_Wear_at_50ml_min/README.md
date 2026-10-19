# Tygon PVC tubing wear at 50 ml/min

**Date:** 2026-10-05  
**Operator:**  
**Goal:** See how Tygon PVC pump tubing wears over a multi-hour run at a set 50 ml/min, and how that wear changes the measured flow rate and the pressure before and after the pump.

## Protocol

1. Set the pump to **50 ml/min**.
2. Run for a couple of hours.
3. Log the **measured flow rate** and the **pressure before and after the pump** for the whole run.

## Results

![Measured flow and pump pressure](output_data/flow_and_pump_pressure_20261005_090840.png)

The full log is kept. The three runs are also saved beside it:

- `raw_data/20261005_090841_tube1_first_on_sensors.csv`
- `raw_data/20261005_213631_tube1_second_on_sensors.csv`
- `raw_data/20261006_153226_tube2_first_on_sensors.csv`

each with a matching `*_pressure_100Hz.csv`. Regenerate with `python plot_flow_drop_by_period.py`.

The drop is from the flow just after the 50 ml/min run is up to the flow at the end of that continuous run. The dotted line is when 95% of that drop has happened.

### Start until pump off

![Start until pump off](output_data/flow_drop_20261005_090841_tube1_first_on.png)

- Fell from **50.7 to 44.7 ml/min** (6.0 ml/min, 11.8%).
- **95% of that drop in 175 min** (12:18, about 3.1 h from the start).
- It looks like the flow rate drops to 45ml/min (10%) within the first 1h and than reamins stable

### Old tubing, switched on after the pump-off

![Old tubing after pump-off](output_data/flow_drop_20261005_213631_tube1_second_on.png)

- After Switching the Pump off for several hours the flowrate goes up to about 47ml/min, here **48.6 ml/min**, then falls to **45.7 ml/min** (2.9 ml/min, 6.0%).
- **95% of that drop takes 16.9 h**, so it is still drifting down at the end of this run.

### New tubing

![New tubing](output_data/flow_drop_20261006_153226_tube2_first_on.png)

- The new-tubing run is `20261006_153226_tube2_first_on`. Over **23 min** measured flow rose to about **51 ml/min** and held there. No decrease, so there is no 95% time yet. 

Commit the final result figure(s) cited here. Regenerate other plots locally.

## Conclusion

- TODO: 
