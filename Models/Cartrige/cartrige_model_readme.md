# Disposable Cooling Cartridge Sizing Model

## Purpose

This script provides a first-pass engineering estimate of the size of a disposable polypropylene cooling cartridge.

The cartridge is assumed to:

- Contain a single flow channel.
- Be manufactured from polypropylene (PP).
- Be compressed between two cooling plates.
- Have a fluid inlet (Luer connection) on one side and an outlet on the opposite side.
- Cool a liquid from a specified inlet temperature to a target outlet temperature.

The script estimates:

- Required heat transfer area
- Internal volume
- Cooling duty
- Fluid-side heat transfer coefficient
- Reynolds number
- Nusselt number
- Flow regime (laminar, transitional, turbulent)

---

# Design Inputs


The cartridge thickness is automatically calculated as:

Thickness = Channel Gap + 2 × Wall Thickness

---

# Geometry Assumptions

The model assumes a rectangular cartridge.

A fixed aspect ratio constraint is imposed:

Length = 2 × Height

The cooling area is provided by the two large cartridge faces:

Area = 2 × Length × Height

---

# Thermal Model

The model is based on a steady-state heat exchanger formulation:

Q = m × Cp × ΔT

where:

- Q = cooling load [W]
- m = mass flow rate [kg/s]
- Cp = specific heat [J/kg·K]

The required heat transfer area is determined from:

Q = U × A × LMTD

which is rearranged internally into an exponential cooling model.

---

# Heat Transfer Resistances

Heat must travel through three resistances:

1. Fluid-side convection
2. Polypropylene wall conduction
3. Cooling-plate-side convection

The overall heat transfer coefficient is:

1/U = 1/h_fluid + t_pp/k_pp + 1/h_plate

where:

- U = overall heat transfer coefficient
- h_fluid = fluid-side heat transfer coefficient
- h_plate = plate-side heat transfer coefficient
- t_pp = PP wall thickness
- k_pp = PP thermal conductivity

---

# Flow Model

The channel is treated as a rectangular duct.

The script calculates:

## Hydraulic Diameter

Dh = 4A/P

For a rectangular channel:

Dh = 2WH/(W+H)

where:

- W = channel width
- H = channel gap

---

## Reynolds Number

Re = ρVDh / μ

where:

- ρ = density
- V = fluid velocity
- Dh = hydraulic diameter
- μ = viscosity

---

## Flow Regime

The following criteria are used:

### Laminar

Re < 2300

### Transitional

2300 ≤ Re ≤ 4000

### Turbulent

Re > 4000

---

# Nusselt Number

The script estimates Nusselt number using simplified correlations.

### Laminar

Nu = 7.54

Assumes:

- Fully developed flow
- Constant wall temperature
- Rectangular channel

### Transitional

Nu = 15

Approximate interpolation value.

### Turbulent

Dittus-Boelter correlation:

Nu = 0.023 × Re^0.8 × Pr^0.4

---

# Fluid Properties

The default fluid is assumed to be water-like.

| Property | Value |
|-----------|---------|
| Density | 1000 kg/m³ |
| Specific Heat | 4180 J/kg·K |
| Viscosity | 0.001 Pa·s |
| Thermal Conductivity | 0.60 W/m·K |

These values are only approximations.

For other fluids, the properties should be updated.


---

# Cooling Plate Assumptions

The cooling plates are treated as an infinite thermal reservoir.

Assumptions:

- Plate temperature remains constant at -1°C.
- No temperature gradient inside the plate.
- Perfect thermal contact between cartridge and plate.

The plate-side heat transfer coefficient is fixed at:

5000 W/m²·K

---

# Engineering Notes

For the current design point:

- Flow rate is relatively low.
- The flow is likely strongly laminar.
- Heat transfer is therefore dominated by conduction through the fluid layer and PP wall.
- Reducing channel gap usually improves cooling performance more effectively than increasing cartridge area.
- PP thermal conductivity is relatively poor; thinner walls can significantly improve performance.
