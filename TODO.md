## Modeling methodology enforcements (later)

Store/check rules here (or wire into `scripts/check_methodology.py`) so the model stays consistent for non-SE readers:

- **Singleton part usage** — if a `part def` has only one `part` usage in the model, keep the usage name the same as the def (e.g. `part ups : UPS`). If the grammar/style cannot use the exact same name, use a clearly similar form.
- **Multiple part usages** — if several parts share one type, name each usage by **role / intention**, not by repeating the type (e.g. `inputTempSensor` / `outputTempSensor`, `upperY` / `lowerY`), not `thermistor1` / `thermistor2`.
- **One device type** — `CoolSpineDevice` is the single device `part def`; it is *used* in context / use cases / concerns (`part coolSpine : CoolSpineDevice`). Do not add a redundant root `part coolSpine` next to the def in `CoolSpineSystem`.
