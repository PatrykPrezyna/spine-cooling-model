# Heat capacity characterisation of the cartridge

**Date:** 2026-10-14  
**Operator:**  
**Goal:** Measure the cartridge cooling power while it sits between the cool plates, with the compressor on and the pump at a set speed. Power is calculated from cartridge inlet temperature, outlet temperature, flow rate, and the constant specific heat of water — the same water-side calculation used for the catheter.

## Protocol

1. Insert the cartridge between the cool plates.
2. Turn the compressor on. Initial set temperature is between **−2 and 0 °C**.
3. Run the pump at the set speed.
4. Log cartridge **input** and **output** temperature and flow. Calculate cooling power from those channels and the water heat capacity below.

Prefer raw logs named `sensor_log_YYYYMMDD_HHMMSS_<condition>.csv`. Never hand-edit `raw_data/`; regenerate into `output_data/`.

## Setup

- Cartridge clamped between the cool plates. Compressor on.
- Initial set temperature: **−2 to 0 °C** (later setpoints are whatever the log records).
- Pump running at a fixed set speed. Record the rpm and the measured flow with each run.
- Channels used for power: cartridge in (`cartrige_in_c`), cartridge out (`cartrige_out_c`), and flow (`flow_sensor_ml_per_min`, or pump flow if the flow sensor is absent).
- Photo or schematic: place under `setup/`.

## Cooling power calculation

Heat removed from the water as it passes through the cartridge:

```
P = ṁ · c_p · (T_in − T_out)
```

with **c_p = 4186 J/(kg·K)** and **1 ml = 0.001 kg**. Positive power means the outlet is colder than the inlet. This is the catheter formula with the temperature difference reversed, because the catheter run measures heat picked up by the coolant and this run measures heat taken out of it.

In the analysis script (`flow_power` in `Experiments/experiment_tools.py`):

```text
ṁ = (flow_ml_min / 60) * 0.001
P = ṁ * 4186 * (T_in - T_out)
```

Flow is the Keyence reading when `flow_sensor_ml_per_min` is above 5 ml/min. Otherwise it is the logged pump flow.

## Results

```bash
python plot_cooling_power.py
```

- Key plots (from `output_data/`): TODO once a sensor log is in `raw_data/`.
- Summary table: TODO.
- Raw logs: drop them in `raw_data/`.

Commit the final result figure(s) cited here; regenerate the rest locally.

## Conclusion

- What we learned: TODO
- Implications for the next design / test: TODO
- Open questions or follow-ups: TODO
