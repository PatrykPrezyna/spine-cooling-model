# Catheter flow–pressure characterisation (SAGE)

**Date:** 2026-08-05  
**Goal:** Characterise the catheter hydraulic resistance by sweeping flow rate from **10 → 100 ml/min** and recording **catheter input** and **catheter output** pressure. Run the sweep twice with **opposite catheter flow direction**, while the pump **always pushes**.

## Protocol

1. Build the closed loop: reservoir (bucket) ↔ catheter ↔ peristaltic pump. Keep the pump on the **discharge / push** side for both runs (do not switch to suction-through-catheter).
2. Log four pressures continuously:
   - `catheder_input_psi` / `catheder_output_psi` (primary)
   - `pump_input_psi` / `pump_output_psi` (loop diagnostics)
3. Step the pump so volumetric flow covers **~10–100 ml/min**. Hold each step long enough for a steady reading (~1–2 min).
4. Run once in each **catheter orientation** (pump always pushing):
   - **Forward** — flow enters the catheter input port and exits the catheter output port
   - **Reverse** — swap the catheter connections so flow enters the former output and exits the former input (sensors stay with their ports: what the log calls input/output follows the fittings)
5. Final deliverable: **pressure on X**, **flow rate (ml/min) on Y** — inlet, outlet, and ΔP = inlet − outlet for both orientations overlaid.

Pump speed ↔ flow uses the prior calibration **≈ 0.782 ml/min per rpm** (≈ 60 rpm → 47 ml/min). Target steps roughly:

| Flow (ml/min) | ≈ RPM |
|---------------|-------|
| 10 | 13 |
| 20 | 26 |
| 30 | 38 |
| 40 | 51 |
| 50 | 64 |
| 60 | 77 |
| 80 | 102 |
| 100 | 128 |

## Setup

![Benchtop test setup](Banchtop_test_setup.png)

Pump always drives flow into the loop (push). Between the two characterisation runs, only the **catheter inlet/outlet plumbing is swapped** so fluid travels the opposite way through the catheter; pump placement and push direction stay the same.

## Preliminary data

| File | Notes |
|------|--------|
| `pressure_log_20260803_163716.csv` | Early sweep, **~11 min**, RPM steps **13 → 77** (~**10–60 ml/min**). One catheter orientation only — still need **80–100 ml/min** and the **reverse** (swapped in/out) run. |

Logged columns: `timestamp`, `peristaltic_pump_set_speed_rpm`, `pump_output_psi`, `pump_input_psi`, `catheder_input_psi`, `catheder_output_psi`.

Steady-ish means by set speed (full-step average):

| ≈ Flow (ml/min) | RPM | Cath in (psi) | Cath out (psi) | ΔP (psi) |
|-----------------|-----|---------------|----------------|----------|
| 10 | 13 | 1.23 | 0.43 | 0.81 |
| 20 | 26 | 2.46 | 0.76 | 1.70 |
| 30 | 38 | 3.67 | 1.11 | 2.54 |
| 40 | 51 | 5.18 | 1.53 | 3.64 |
| 50 | 64 | 6.90 | 2.00 | 4.90 |
| 60 | 77 | 8.86 | 2.51 | 6.34 |

ΔP rises roughly linearly with flow in this range — expected for laminar lumen resistance.

## Scripts

```bash
python plot_flow_pressure.py
python plot_pressure_vs_time.py
```

| Script | Output |
|--------|--------|
| `plot_flow_pressure.py` | Steady P–Q curve: **pressure (X) vs flow (Y)** for cath in/out/ΔP (last 30% of each RPM hold; 0.782 ml/min per rpm) |
| `plot_pressure_vs_time.py` | Time series of raw + **1 s** rolling average (pump in/out, catheter in/out, commanded flow) |

Both process every `pressure_log_*.csv` in the folder. Flow–pressure overlays multiple runs and labels `forward`/`reverse` from the filename.

## Files

| File | Role |
|------|------|
| `Banchtop_test_setup.png` | Loop schematic |
| `pressure_log_YYYYMMDD_HHMMSS.csv` | Raw pressure + pump-speed logs |
| `plot_flow_pressure.py` | Flow–pressure characterisation plot |
| `plot_pressure_vs_time.py` | Raw + 1 s avg time-series plot |
| `flow_pressure_*.png` | Generated P–Q plot |
| `pressure_vs_time_*.png` | Generated time-series plot |
| `README.md` | This note |

Name completed runs clearly, e.g. `*_forward.csv` / `*_reverse.csv`.
