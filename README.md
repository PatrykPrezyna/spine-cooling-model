# Spine Cooling - Tissue Cooling Simulation

A Python-based simulation and verification toolkit for analyzing thermal dynamics of spine/tissue cooling using physical heat transfer principles.

## Overview

This project simulates temperature changes in tissue and cooling hardware over time, accounting for:

- **Metabolic heat generation** — internal heat production in living tissue
- **Radiative heat loss** — thermal radiation emitted by the tissue
- **Convective heat loss** — heat transfer through the surrounding medium
- **Applied cooling** — external cooling intervention (cartridge, heat exchanger, counterflow)
- **Experimental validation** — visualization of real sensor logs from hardware runs

The simulation tracks temperature changes and calculates power balance to determine how long it takes to cool tissue from its initial temperature to a target temperature.

## Project Structure

```
spine-cooling/
├── finalcombined.ipynb      # Main combined simulation (counterflow, tubular geometry)
├── archive/                 # Original student team work (Spring 2026)
│   ├── simple_power.py      # Basic 1 kg tissue lump ODE simulation
│   ├── finalcombined.ipynb  # Earlier notebook version
│   ├── Tubular_03-15.py
│   ├── Tubular_Tempchange_03-15.py
│   └── Material_volumerate.py
└── verification/            # Experimental data visualization
    ├── visualize_sensor_log.py
    └── sensor_log_*.csv     # Sample hardware sensor logs
```

## Features

- Numerical ODE integration (Euler method and SciPy BVP solvers)
- Customizable tissue parameters (mass, surface area, specific heat capacity)
- Environmental condition settings (ambient temperature, convection coefficient)
- Counterflow heat exchanger modeling in `finalcombined.ipynb`
- Visualization of temperature evolution over time
- Power analysis showing heat transfer at different time points
- Sensor log plotting for hardware experiment validation

## Requirements

- Python 3.7+
- NumPy — numerical computations
- Matplotlib — visualization
- SciPy — boundary-value problem solvers (used in `finalcombined.ipynb`)
- Pandas — sensor log loading and processing

## Installation

1. Clone or download this repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Combined simulation (notebook)

Open and run `finalcombined.ipynb` in Jupyter or VS Code. This notebook contains the full counterflow heat exchanger and tubular geometry models.

### Basic tissue simulation (archive)

For the simpler 1 kg tissue lump model:

```bash
python archive/simple_power.py
```

Edit the parameters at the top of `archive/simple_power.py` to modify:

- **MASS_KG** — tissue weight in kilograms
- **SURFACE_AREA** — tissue surface area in m²
- **Q_METABOLIC** — metabolic heat rate in W/kg
- **T_INITIAL** — starting temperature in °C
- **T_TARGET** — desired target temperature in °C
- **Q_COOLING** — applied cooling power in watts
- **T_TOTAL_S** — simulation duration in seconds
- **DT_S** — integration time step in seconds

### Sensor log visualization (verification)

The `verification/` folder is for visualizing experimental sensor data collected from hardware runs. Use it to compare simulation predictions against real measurements.

```bash
python verification/visualize_sensor_log.py verification/sensor_log_20260612_132816_Experiement_1.csv
```

The script accepts CSV files or key:value log formats and produces four stacked plots:

1. CSF temperatures and setpoint
2. Cartridge in/out temperatures
3. Heat exchanger and auxiliary sensor temperatures
4. Pump speed and compressor state (with pump-start marker)

## Archive

The `archive/` folder contains the original work done by the student team in Spring 2026, including early tubular geometry scripts and the standalone `simple_power.py` lumped-parameter model. These files are kept for reference; active development uses `finalcombined.ipynb` at the repository root.

## Output

Simulation scripts and notebooks generate:

- Plots showing temperature vs. time with target temperature lines
- Summary tables of heat flow components
- Console output with timing information for reaching target temperature

The verification script opens an interactive Matplotlib window with multi-panel sensor traces aligned to time from experiment start.
