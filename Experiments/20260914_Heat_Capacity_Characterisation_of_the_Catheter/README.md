# Heat capacity characterisation of the catheter

**Date:** 2026-09-14  
**Operator:**  
**Goal:** Characterise the catheter heat capacity and response speed (stabilisation time) from inlet and outlet temperatures at constant flow.

## Protocol

1. Use tubing lengths matching the final product.
2. Replace the cartridge with a container of ice water.
3. Place the catheter in a controlled-temperature bath. Mix the bath and measure it with two sensors.
4. Pump at a constant **50 ml/min** (may vary in later runs).
5. Log catheter **input** and **output** temperature. From the traces, calculate heat capacity and stabilisation time.
6. **Run 1 — original catheter.** Sensors on the existing tubing.
7. **Later runs — shortened tubing.** Move the temperature sensors as close as possible to the ports (~**1 cm**).

Prefer raw logs named `sensor_log_YYYYMMDD_HHMMSS_<condition>.csv`. Never hand-edit `raw_data/`; regenerate into `output_data/`.

## Setup

- Loop tubing: same lengths as the final product
- Cold source: ice-water container (no cartridge)
- Catheter bath: controlled temperature, mixed, two sensors
- Pump setpoint: **50 ml/min** (constant; may change later)
- Logged: catheter inlet and outlet temperature; bath temperatures (2 sensors)
- Photo or schematic: place under `setup/`

## Results

```bash
python plot_catheter_temp_flow.py
```

![Original tubing — catheter temperature and flow](output_data/catheter_temp_flow_20260914_160338_sensors_oryginal_tubing.png)

Original tubing, first 50 rpm pulse (~40 ml/min calculated):

- Steady-state **ΔT = T_out − T_in = 8.77 °C** (in 9.78 °C, out 18.55 °C), from the last 15 s of flow
- Time from flow on to 5% settle: **77 s**

Raw log: [20260914_160338_sensors_oryginal tubing.csv](raw_data/20260914_160338_sensors_oryginal%20tubing.csv)

Commit final result figure(s) cited here; regenerate the rest locally.

## Conclusion

- What we learned
- Implications for the next design / test
- Open questions or follow-ups
