# Tygon PVC tubing wear at 50 ml/min

**Date:** 2026-11-03  
**Operator:** Patryk Prezyna  
**Goal:** Characterise how delivered flow (ml/min) changes over time as McMaster Tygon PVC 1/8" ID × 1/4" OD pump tubing wears at a set 50 ml/min.

## Protocol

1. Cut one length of **McMaster Tygon PVC, 1/8" ID × 1/4" OD** and mark it from inlet to outlet: **3 cm + 11 cm + 1 cm + 1 cm + 1 cm + 1 cm + 2 cm + 2 cm + 3 cm** (25 cm total).
2. Fit the tube on the peristaltic-pump section. Fill with water and purge air until flow is steady.
3. Leave the **Keyence FD-X** in the flow path, mounted flow-upward (inlet at the bottom, outlet at the top), display in **ml/min**.
4. Set **50 ml/min** and run for **X h** in the starting position.
5. Advance the tube **1 cm** and continue the run.
6. Advance the tube another **1 cm** and continue.
7. Advance the tube to the end mark and continue.
8. At the joint between the Tygon tube and the pressure-sensor inlet connector, open the fitting, release the pressure, and close it again.
9. Cut a new tube with the same marks and repeat steps 2-3
10. Disconnect the catheter outlet. Hold both open ends under water so they stay full.
11. Put the original tube back on the pump. (about 1011min after the experiement start)
12. Disconnect the catheter outlet. Hold both open ends under water so they stay full.
13. Reconnect the catheter outlet.
14. run egain 

## Setup

- Pump tube: McMaster Tygon PVC, 1/8" ID × 1/4" OD, marked as in step 1
- Setpoint: **50 ml/min**
- Flow check: Keyence FD-X (ml/min, flow upward)
- Catheter stays in the loop for the pressure-release and reconnect steps
- Save each sensor log and the matching 100 Hz pressure log in `raw_data/`. Do not hand-edit those files.

## Results

```bash
python plot_flow_by_protocol_step.py
```

![Keyence flow by protocol step](output_data/flow_by_protocol_step_20261102_164405.png)

![Flow and pressure by protocol step](output_data/flow_pressure_by_protocol_step_20261102_164405.png)

Log: [20261102_164405_sensors.csv](raw_data/20261102_164405_sensors.csv), 2026-11-02 16:44 to 2026-11-03 09:48 (17.08 h). Set flow is 50 ml/min. The trace is the Keyence reading while the pump is on.

The bands follow the protocol. Steps 1–3 are the opening 25 min. Step 4 is the long hold with no pump stop. Each of steps 5–10 is the next pump stop and the run after it, in the written order. Steps 11–13 share the stop at 1011 min, and step 14 is the run after that stop.

| Step | Elapsed (min) | Pump-on flow (ml/min) |
|---|---:|---:|
| 1–3 Setup | 0–25.5 | several starts, about 33–49 |
| 4 Starting position | 25.5–978.5 | 48.4 early, 42.1 at the end |
| 5 Advance 1 cm | 978.5–981.1 | 42.4 |
| 6 Advance another 1 cm | 981.1–982.6 | 43.2 |
| 7 Advance to the end | 982.6–992.3 | 42.9 |
| 8 Bleed the inlet fitting | 992.3–998.0 | 40.1 |
| 9 New tube | 998.0–1005.2 | 37.4 |
| 10 Catheter outlet | 1005.2–1010.2 | 46.6 |
| 11–13 Original tube back | 1010.2–1011.0 | pump off |
| 14 Run again | 1011.0–1024.8 | 46.0 |

On step 4, once flow was up (minutes 28–38) the median was **48.4 ml/min**. Over the last 10 min of the hold it was **42.1 ml/min**. That is a drop of **6.2 ml/min** in 15.8 h, about **0.39 ml/min per hour**, with the setpoint held at 50.

Advancing the tube (steps 5–7) left flow near 42–43 ml/min. Bleeding the inlet fitting and fitting a new tube (steps 8–9) was followed by 40.1 then 37.4 ml/min. The run after the next stop (step 10) recovered to 46.6 ml/min. From the 1011 min restart, flow stayed near 46 ml/min and was 45.7 ml/min at the end of the log.

Pressure on the lower panels is the 10 s mean of the 100 Hz log. The tint on the pump traces is the 10 s min–max. On step 4, pressure after the pump fell from **1.23 to 1.02 bar** and catheter inlet from **1.18 to 0.89 bar**. Suction before the pump increased from **−0.15 to −0.34 bar**. After the pump, the later steps read 0.93, 0.85, 0.76, 0.53, then 0.28 bar. Step 10 and the final run brought it back to about **1.19–1.22 bar**.

## Conclusion

- At a set 50 ml/min, flow on the starting tube position fell from 48.4 to 42.1 ml/min over 15.8 h (about 0.39 ml/min per hour).
- Shifting that tube by 1 cm, another 1 cm, and to the end did not restore the starting flow.
- Flow returned to about 46 ml/min only after step 10, and the final run stayed there.
- Pressure after the pump moved with that flow: down from 1.23 to 1.02 bar on the long hold, down to 0.28 bar on the new tube, then back to about 1.2 bar on the last two runs.
