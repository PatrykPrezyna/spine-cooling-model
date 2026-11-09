# Type of control (temp based vs flowrate based)

**Decision ID:** DD-003  
**Date:** 2026-07-17  
**Author:** Patryk Prezyna

## Background

This document explains why the device uses temperature-based control rather than flow-based control for patient temperature management. It also explains how flow is still controlled by the system, but indirectly through the selected temperature target.

The goal of the system is not to deliver a specific flow rate. The clinical goal is to achieve and maintain a specific patient temperature. Therefore, temperature is the controlled variable and flow rate is the manipulated variable used to reach that goal.

## Description

### How flow is influenced by temperature

The selected temperature setpoint determines how much cooling is required.

When the difference between measured temperature and target temperature is large:

- More cooling is required.
- Flow increases.

When the temperature difference becomes smaller:

- Less cooling is required.
- Flow decreases.

Thus, temperature directly determines the required cooling demand, and the controller automatically adjusts flow to satisfy that demand.

Flow is therefore not ignored. Instead, flow acts as the mechanism used by the controller to achieve the desired temperature outcome.

## Decision

Temperature-based control provides a direct link between the therapy objective and the control system.

With temperature-based control:

- The clinician selects the desired patient temperature.
- The system continuously measures patient temperature.
- The system automatically adjusts flow rate to achieve and maintain the selected temperature.
- The system compensates for changes in patient physiology and heat generation.

In contrast, flow-based control delivers a fixed flow rate regardless of the patient's actual temperature response.

Because patients have different body sizes, metabolic rates, blood flow characteristics, and heat production, the same flow rate can produce very different temperatures in different patients.

As a result, flow-based control does not reliably achieve the intended therapeutic temperature.

## Option comparison

Left blank in the source note.

| Criteria | Option A | Option B | Option C | Comments |
| --- | --- | --- | --- | --- |
| | | | | |

## Results

None attached to this decision. No experiment folder or measurement set was cited in the source note.

## Conclusion

Temperature-based control is the choice: the clinician selects the desired patient temperature, and the system adjusts flow to achieve and maintain it. Flow-based control delivers a fixed flow rate and does not reliably achieve the intended therapeutic temperature, because the same flow can produce different temperatures in different patients.

## Follow-up actions

The source note left this table empty.

| Action | Owner | Due date |
| --- | --- | --- |
| | | |
