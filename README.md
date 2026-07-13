# Spine Cooling - Tissue Cooling Simulation

Python toolkit for simulating and verifying thermal dynamics in tissue cooling systems using heat transfer principles.

## Quick Start

1. **Setup:** 
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Run simulation:** Open `Models/SpringSemester_Body_and_Catheder/finalcombined.ipynb`

3. **Validate with experiments:** Use notebooks in `Experiments/` to analyze sensor logs and compare against real measurements

## Features

- Counterflow heat exchanger modeling
- Tissue thermal dynamics (metabolic heat, radiation, convection, cooling)
- ODE solvers (Euler & SciPy)
- Temperature and power analysis visualization
- Hardware validation against experimental sensor data

## Structure

- **Models/** — Simulation models and core logic
- **Experiments/** — Hardware experiments with sensor logs and analysis scripts
- **Archive/** — Previous iterations and prototypes