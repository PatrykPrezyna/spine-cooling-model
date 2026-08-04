# Pump speed vs flow rate (gravimetric)

**Date:** 2026-08-04  
**Operator:**  
**Goal:** Calibrate peristaltic pump speed (RPM) against volumetric flow by collecting water for a fixed hold time and weighing it on a scale. Produces the ml/min-per-rpm factor used in other experiments.

## Protocol

1. Set up an open discharge: pump draws from a reservoir and delivers into a collection vessel on a scale (tare the vessel before each run).
2. Choose a set speed (RPM). Start the pump and collection together; run for **exactly 2.0 min**.
3. Stop the pump and collection together. Record the collected mass (g).
4. Empty / re-tare the vessel. Repeat at the next speed.
5. Suggested sweep (adjust as needed): **20, 40, 60, 80, 100, 120, 160, 200, 240 rpm** — one 2 min hold each.
6. Enter each run in `raw_data/gravimetric_runs.csv` (copy from the template if needed).

Flow rate from mass (water ≈ 1.000 g/ml at room temperature):

\[
Q\ [\mathrm{ml/min}] = \frac{m\ [\mathrm{g}]}{\rho\ [\mathrm{g/ml}] \cdot t\ [\mathrm{min}]}
\]

With \(\rho = 1.0\) g/ml and \(t = 2.0\) min: \(Q = m / 2\).

## Setup

- Peristaltic pump (set speed in RPM)
- Reservoir and tubing (same ID / routing as the intended use case)
- Collection vessel on a bench scale (resolution ≤ 0.1 g preferred)
- Stopwatch or timed hold (2.0 min)
- Optional: note tube size, fluid (water), and ambient temperature in the CSV `notes` column

Photo or schematic: place under `setup/`.

## Results

Run the analysis script after filling the CSV:

```bash
python plot_speed_vs_flow.py
```

- Plot: `output_data/pump_speed_vs_flowrate.png`
- Fit summary printed to the console (slope ≈ ml/min per rpm)

| Finding | Value |
|---------|-------|
| ml/min per rpm (linear fit) | *TBD* |
| Prior estimate (for comparison) | ≈ 0.782 ml/min per rpm |

## Conclusion

- *TBD after data*
- Update other experiments that hard-code `ML_PER_MIN_PER_RPM` if the new fit differs meaningfully.
