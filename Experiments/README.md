# Experiments

Benchtop characterisation and verification runs for the Cool Spine R&D prototype. Each folder is one experiment (or a tightly related set of runs under one goal). Simulation models live in `Models/`; this tree is for **measured** data, analysis scripts, and the write-up that ties them together.

**What is in git:** `raw_data/`, analysis scripts, the experiment README, and typically only the **final result figure(s)** referenced in Results (plus a setup photo when useful). Intermediate or per-run plots under `output_data/` are regenerated locally — run the Python scripts against all files in `raw_data/` to reproduce the full analysis.

---

## Standard experiment layout

```
YYYYMMDD_Short_descriptive_name/
├── README.md                 # Date, goal, protocol, setup, results, conclusion
├── raw_data/                 # As-recorded logs (do not edit)
├── output_data/              # Regenerated analysis (commit final result figure only)
├── *.py                      # Analysis / plotting scripts
└── setup/                    # Optional: photos, schematics, BOM notes
```

Scripts process **every** matching log in `raw_data/` and write plots/tables into `output_data/`. Only the final result figure(s) shown in the README need to be committed; re-run the scripts locally for the full set.

## Experiment README template

Copy into each new experiment and fill in:

```markdown
# <Short title>

**Date:** YYYY-MM-DD  
**Operator:** <name>  
**Goal:** <one or two sentences — what decision or characterisation this supports>

## Protocol

1. …
2. …

## Setup

- Hardware / fixture / materials
- Sensors and channels logged
- Key setpoints (flow, temp, RPM, …)
- Photo or schematic (link under `setup/` or inline)

## Results

- Key plots (from `output_data/`)
- Summary table or quantitative findings
- Links to raw logs used

## Conclusion

- What we learned
- Implications for the next design / test
- Open questions or follow-ups
```

Keep the README the **source of truth** for intent and interpretation; keep numbers that matter for later design (ΔP, power, time constants) in the Results section, not only in chat or notebooks.

---

## Conventions

**Raw logs**

- Prefer `sensor_log_YYYYMMDD_HHMMSS_<condition>.csv` or `pressure_log_YYYYMMDD_HHMMSS_<condition>.csv`.
- Never overwrite or hand-edit files in `raw_data/`. Re-process into `output_data/` instead.
- Note units and column meanings in the README if they are non-obvious.

**Scripts**

- One clear entry point per plot or analysis (e.g. `plot_flow_pressure.py`).
- Scripts should read **all** matching files in `raw_data/` and write to `output_data/`.
- Document the run command and any calibration constants (e.g. ml/min per rpm) in the README.

**Plots / derived data**

- Name outputs so they trace back to the source log when possible  
  (`flow_pressure_<same_suffix_as_log>.png`).
- Commit the final result figure(s) cited in Results; regenerate everything else with the scripts.

**Archive**

- `Experiments/archive/` and per-experiment `archive/` hold superseded runs or one-off notebooks. Prefer a short note in the README over deleting data.