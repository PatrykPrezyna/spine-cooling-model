---
name: create-new-experiment
description: >-
  Scaffold a new Cool Spine benchtop experiment under Experiments/ with the
  standard folder layout and README. Use when the user says "create a new
  experiment", asks to start/scaffold/set up a new experiment folder, or wants
  a new YYYYMMDD_* experiment directory.
---

# Create a new experiment

Scaffold one new experiment folder under `Experiments/` matching the repo convention in `Experiments/README.md`.

## Workflow

Copy this checklist and track progress:

```
Task Progress:
- [ ] Step 1: Collect details from the user
- [ ] Step 2: Confirm folder name
- [ ] Step 3: Create directories and placeholders
- [ ] Step 4: Write README.md from template
- [ ] Step 5: Show the user what was created
```

### Step 1: Collect details

Ask the user for anything missing. Do **not** invent a goal or protocol.

Required:

1. **Short descriptive name** — words for the folder suffix (e.g. `Flow_Pressure_characterisation_with_SAGE`)
2. **Goal** — one or two sentences (what decision / characterisation this supports)
3. **Date** — default to today as `YYYYMMDD` / `YYYY-MM-DD` unless they specify otherwise

Optional (ask, allow skip):

4. **Operator**
5. **Protocol** — numbered steps, or a short bullet list to flesh out later
6. **Setup notes** — hardware, sensors/channels, key setpoints
7. **Seed analysis script?** — yes/no; if yes, a one-line description of what it should plot (create a minimal stub only)

If they already gave some of this in the triggering message, do not re-ask those fields.

### Step 2: Confirm folder name

Build:

```
Experiments/YYYYMMDD_Short_descriptive_name/
```

Rules:

- Date prefix: `YYYYMMDD` (no hyphens)
- Name: spaces → underscores; keep letters, digits, underscores; avoid punctuation
- Prefer Title_Case_With_Underscores matching existing folders (e.g. `20260805_Flow_Pressure_characterisiation_with_SAGE`)
- If the path already exists, stop and ask for a different name or date

Show the full path and wait for a quick confirmation before creating files, unless they already said to proceed.

### Step 3: Create layout

Create exactly:

```
Experiments/YYYYMMDD_Short_descriptive_name/
├── README.md
├── raw_data/.gitkeep
├── output_data/.gitkeep
└── setup/.gitkeep
```

Do **not** add sample CSV/PNG data. Do **not** commit unless the user asks.

If they requested a seed script, add one top-level `plot_*.py` that:

- reads matching files from `raw_data/`
- writes into `output_data/`
- prints a short “no input files yet” message when `raw_data/` is empty
- matches style of nearby experiment scripts if useful; otherwise keep it a minimal stub

### Step 4: Write README.md

Use this template. Fill known fields; leave Protocol/Setup/Results/Conclusion as light stubs with TODOs only where the user gave nothing.

```markdown
# <Short title>

**Date:** YYYY-MM-DD  
**Operator:** <name or blank>  
**Goal:** <goal>

## Protocol

1. …

## Setup

- Hardware / fixture / materials
- Sensors and channels logged
- Key setpoints (flow, temp, RPM, …)
- Photo or schematic: place under `setup/`

## Results

- Key plots (from `output_data/`)
- Summary table or quantitative findings
- Links to raw logs used

## Conclusion

- What we learned
- Implications for the next design / test
- Open questions or follow-ups
```

Remind in Setup or Results (briefly) of repo conventions:

- Prefer raw logs named `sensor_log_YYYYMMDD_HHMMSS_<condition>.csv` or `pressure_log_YYYYMMDD_HHMMSS_<condition>.csv`
- Never hand-edit `raw_data/`; regenerate into `output_data/`
- Commit final result figure(s) cited in Results; regenerate the rest locally

### Step 5: Done

Reply with:

- Full path created
- List of files/dirs
- One-line next steps (drop logs in `raw_data/`, fill Protocol, add setup photo)

## Reference

Canonical conventions: `Experiments/README.md`  
Example folders: `Experiments/20260805_Flow_Pressure_characterisiation_with_SAGE`, `Experiments/20260804_Pump_speed_vs_flowrate`
