package CoolSpineRequirements {

    // Source numbers: Spec/functional_requirements.csv
    private import ScalarValues::*;

    requirement def CoolSpineRequirement;

    requirement <'SYS-CS-001'> CoolSpineSystemRequirements : CoolSpineRequirement {
        doc /*
        Top-level need: CoolSpine must meet the cooling power, battery /
        portability, fluid pressure, user interface, and safety rules listed
        below. Use this as the checklist for the whole product.
        */
    }

    // --- Cooling performance ---

    requirement <'REQ-CP-001'> PeakCoolingPower : CoolSpineRequirement {
        doc /*
        Must be able to remove heat at 250 W peak (never less; up to +500 W
        is acceptable). Comes from sponsor animal studies / modeling — drives
        sizing of the micro-refrigeration unit.
        */
        attribute peakCoolingPower_W : Real default 250.0;
    }

    requirement <'REQ-CP-002'> SteadyStateCoolingPower : CoolSpineRequirement {
        doc /*
        Must sustain 150 W of cooling in steady state (never less; up to
        +300 W acceptable). Same study basis as peak power; this is the
        continuous duty the fridge and loop must hold.
        */
        attribute steadyStateCoolingPower_W : Real default 150.0;
    }

    // --- Power and portability ---

    requirement <'REQ-CP-003'> OperationWithoutGroundPower : CoolSpineRequirement {
        doc /*
        Must run at least 30 minutes without wall power (never less; up to
        +60 min acceptable) — e.g. moving the patient or brief AC loss.
        Battery + UPS design; aligned with clinical practice / IEC 60601-2-24.
        */
        attribute batteryRuntime_min : Real default 30.0;
    }

    requirement <'REQ-CP-004'> PortableFormFactor : CoolSpineRequirement {
        doc /*
        Device must be small / wheeled enough to move with the patient between
        rooms. Influences packaging, weight, and cable layout — not just the
        fridge performance.
        */
    }

    // --- Fluid pressure ---

    requirement <'REQ-CP-005'> OperatingPressure : CoolSpineRequirement {
        doc /*
        Normal saline-loop pressure: 15 PSI (−2 / +10 PSI). Sized for the
        catheter design; pump and sensors must stay in this band in use.
        */
        attribute operatingPressure_psi : Real default 15.0;
    }

    requirement <'REQ-CP-006'> MaximumPressure : CoolSpineRequirement {
        doc /*
        Hard ceiling: fluid circuit must not exceed 1.2 KSI. Protects catheter
        and patient; software and hardware limits should enforce this.
        */
        attribute maximumPressure_ksi : Real default 1.2;
    }

    // --- Usability and safety ---

    requirement <'REQ-CP-007'> AppropriateUserInterface : CoolSpineRequirement {
        doc /*
        Touch UI and controls must be usable and compliant for a medical
        electrical device (IEC 60601-1). Think alarms, labels, and operable
        by the anesthesiologist under OR conditions.
        */
    }

    requirement <'REQ-CP-008'> SafetyMonitoringAndFailSafes : CoolSpineRequirement {
        doc /*
        Must monitor for unsafe conditions and fail safe (alarms / shutdown)
        per IEC 60601-1-8 and IEC 60601-1-10. Covers sensor faults, pressure
        trips, and loss of control — not only the happy path.
        */
    }
}
