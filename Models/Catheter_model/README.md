# Dual-lumen catheter thermal model

Transient 1-D heat-transfer model of a dual-lumen cooling catheter fully
submerged in a mixed water tank. Cold water enters the inlet lumen at the
proximal end, turns at the distal end, and returns through the outlet lumen.
The quantity of interest is the **proximal outlet temperature** as a function
of time (and, at long times, of flow rate).

The physics live in `dual_lumen_catheter.py`. Calibration and validation
against benchtop logs are separate scripts that import that file.

```
  proximal                                              distal
  ─────────────────────────────────────────────────────────────
  inlet  →  →  →  →  →  →  →  →  →  →  →  →  →  ╮
  (cold)                                        │ turn
  outlet ←  ←  ←  ←  ←  ←  ←  ←  ←  ←  ←  ←  ←  ╯V=
  ─────────────────────────────────────────────────────────────
        outer wall exchanging heat with the tank
```

## What the model is for

Cool Spine catheters pick up heat from the surroundings as coolant travels
down one lumen and back the other. This model estimates that pickup for a
catheter sitting in a large stirred bath at a known temperature — the
benchtop analogue of a well-mixed environment around the catheter.

It answers:

- How warm is the returning water after a given flow, inlet temperature, and
  tank temperature?
- How long does the catheter take to settle after a step change (residence
  time plus wall thermal mass)?

It does **not** resolve tissue, CSF, or a surrounding tube. Those live in
other models (for example `Models/Tube_with_Catheder_model/`). This file is
the catheter as a heat exchanger by itself.

## Physical picture

Two parallel circular lumens sit inside a circular polymer outer wall.
Along a diameter through both lumen centres the thicknesses add up as:

```
2 · t_outer + t_septum + 2 · D_lumen = D_outer
```

The outer wall and the septum are assumed to have the same thickness, so:

```
t_wall = (D_outer − 2 · D_lumen) / 3
```

Default geometry (edit the constants at the top of
`dual_lumen_catheter.py`):

| Quantity | Default |
|---|---|
| Catheter length | 33 cm |
| Outer diameter | 3.0 mm |
| Lumen inner diameter | 1.0 mm (uncertain; calibration absorbs this) |

The catheter is divided into `N_AXIAL_SEGMENTS` stations (default 30). At
each station there are **three lumped temperatures**:

- inlet-lumen water
- outlet-lumen water
- polymer wall (one node shared by both lumens)

Mass flow is the same in both lumens. Index 0 is the **upstream** end of
each lumen, so the distal turn is simply “last inlet segment feeds first
outlet segment.” The turn itself has no extra volume, transit time, or
heat-transfer area.

The tank is an infinite reservoir: its temperature is a boundary condition
and is never updated.

## Heat path

Per axial station the wall is a single polymer node with thermal mass,
placed in the middle of the conduction path:

```
tank  --[1/h_tank + t_wall/2 / k_p, outer area]-->  wall
wall  --[t_wall/2 / k_p + 1/h_inner, lumen area]-->  each lumen
```

The wall is crossed once in total; the half/half split only locates the
polymer heat capacity in the middle of that path. Both lumens exchange with
the **same** wall node, which is also how lumen-to-lumen heat leak is
represented (there is no separate septum conductance).

### Inner film (lumen water)

Laminar, thermally developing flow. Hausen correlation:

```
Gz = Re · Pr · D / L
Nu = 3.66 + 0.0668 · Gz / (1 + 0.04 · Gz^(2/3))
h_inner = Nu · k_water / D_lumen
```

The model refuses to run if `Re ≥ 2300` (it assumes laminar flow).

### Outer film (tank)

A constant stirred-bath coefficient `h_tank = 1000 W/m²·K` on a 3 mm
cylinder. That value is an order-of-magnitude assumption, not a
measurement; the calibration factor `K` absorbs the uncertainty.

### Energy update (explicit Euler)

Per segment, water and wall temperatures advance as:

```
C_water · dT_in/dt   = ṁ cp (T_upstream_in  − T_in)  + G_lw (T_wall − T_in)
C_water · dT_out/dt  = ṁ cp (T_upstream_out − T_out) + G_lw (T_wall − T_out)
C_wall  · dT_wall/dt = G_wt (T_tank − T_wall) − G_lw (T_wall − T_in)
                                                      − G_lw (T_wall − T_out)
```

Advection is first-order upwind. The time step is a fraction
(`SAFETY_FACTOR = 0.4`) of the smallest of the CFL limit and the water and
polymer thermal time constants.

Water and polymer properties are constant, evaluated at ~15 °C (mid-range
between cold catheter water and the tank). Polymer properties are typical
medical-grade polyurethane, not measured on this catheter.

## Calibration

Uncertain lumen diameter, tank-side `h`, real (non-circular, off-centre)
lumen geometry, and correlation error are lumped into one flow-dependent
factor that multiplies **every** heat-transfer conductance:

```
K(Q) = k_ref · (Q / Q_ref)^n
```

`dual_lumen_catheter.py` reads `calibration.json` if it exists; otherwise
it runs uncalibrated (`K = 1`). Current coefficients:

```
k_ref   = 1.8856
n       = 0.3254
Q_ref   = 60 mL/min
```

fitted from `20260821_144040_sensors_calibration.csv`.

`K` corrects the **total** heat transfer. It cannot say *where* the
geometry-plus-correlations model is wrong.

To refit:

```
python calibrate.py                     # newest *_calibration.csv
python calibrate.py 20260821            # date prefix
python calibrate.py path\to\file.csv    # explicit file
```

For each pump-speed step the settled tail is averaged to one steady point
(flow, tank = mean of probes 1 and 2, catheter inlet, catheter outlet).
Bisection finds the `K` that makes the modelled outlet match that point,
then a power law is fitted through those `K` values and written to
`calibration.json`. The script also plots measured outlets against the
uncalibrated (`K = 1`) and calibrated models (`calibration_fit.png`).

## Validation

```
python validate.py                      # newest *_validation.csv
python validate.py 20260821
python validate.py path\to\file.csv
```

Runs the **calibrated** model to steady state at every measured
pump-speed step using the measured boundary conditions, prints a
comparison table, and passes if the mean absolute outlet error is below
1 °C.

## How to run the model itself

From this folder:

```
python dual_lumen_catheter.py
```

That runs the nominal transient case (5 °C inlet, 36 °C tank, 60 mL/min,
20 s) and writes `dual_lumen_catheter_outlet.png`.

From other scripts, import `simulate` and `calibration_k_for_flow`
(or `steady_outlet_C` for a single operating point):

```python
from dual_lumen_catheter import simulate, steady_outlet_C

# Transient: returns (time_s, proximal_outlet_C)
time_s, outlet_C = simulate(inlet_C=5.0, tank_C=36.0,
                            flow_m3_s=60e-6/60.0, duration_s=20.0)

# Steady proximal outlet for one operating point
T_out = steady_outlet_C(inlet_C=5.0, tank_C=36.0, flow_m3_s=60e-6/60.0)
```

Pass `calibration_k=1.0` to either function to force the uncalibrated
geometry-plus-correlations model.

Operating conditions and numerics to change are the named constants at
the top of `dual_lumen_catheter.py` (geometry, inlet/tank temperatures,
flow, initial temperatures, segment count, duration).

## Simplifications

- One lumped polymer temperature per axial station; lumen-to-lumen
  interaction only through that shared node.
- Distal turn has no extra volume, delay, or area.
- Constant properties; no temperature dependence of `k`, `μ`, or `cp`.
- Tank-side convection is a single assumed `h`, not a correlation.
- Laminar flow only.
- `K(Q)` is a bulk correction and does not isolate individual error
  sources.
