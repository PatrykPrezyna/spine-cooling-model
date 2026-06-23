# Spine Cooling - Tissue Cooling Simulation

A Python-based simulation and verification toolkit for analyzing thermal dynamics of spine/tissue cooling using physical heat transfer principles.

## Overview

This project simulates temperature changes in tissue and cooling hardware over time, accounting for:

- **Metabolic heat generation** — internal heat production in living tissue
- **Radiative heat loss** — thermal radiation emitted by the tissue
- **Convective heat loss** — heat transfer through the surrounding medium
- **Applied cooling** — external cooling intervention (cartridge, heat exchanger, counterflow)


The simulation tracks temperature changes and calculates power balance to determine how long it takes to cool tissue from its initial temperature to a target temperature.

## Project Structure

```
spine-cooling-model/
├── finalcombined.ipynb      # Main combined simulation (counterflow, tubular geometry)
├── archive/                 # Original student team work (Spring 2026)
└── verification/            # Experimental data visualization
```

## Features

- Numerical ODE integration (Euler method and SciPy BVP solvers)
- Customizable tissue parameters (mass, surface area, specific heat capacity)
- Environmental condition settings (ambient temperature, convection coefficient)
- Counterflow heat exchanger modeling in `finalcombined.ipynb`
- Visualization of temperature evolution over time
- Power analysis showing heat transfer at different time points
- Sensor log plotting for hardware experiment validation

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


### Sensor log visualization (verification)

The `verification/` folder is for visualizing experimental sensor data collected from hardware runs. Use it to compare simulation predictions against real measurements.

```bash
python verification/visualize_sensor_log.py verification/sensor_log_20260612_132816_Experiement_1.csv
```