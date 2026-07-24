package CoolSpineRequirements {

    // Source: Spec/functional_requirements.csv
    // Spec note: `satisfy` targets requirement *usages* (Features), not
    // `requirement def`s — match the RoboticArm example style.
    private import ScalarValues::*;

    requirement def CoolSpineRequirement;

    requirement <'SYS-CS-001'> CoolSpineSystemRequirements : CoolSpineRequirement {
        doc /*
        The CoolSpine therapeutic temperature-control system shall satisfy
        the cooling, power, pressure, form-factor, UI, and safety requirements
        defined in this package.
        */
    }

    // --- Cooling performance ---

    requirement <'REQ-CP-001'> PeakCoolingPower : CoolSpineRequirement {
        doc /*
        The system shall provide a peak cooling power of 250 W
        (tolerance: −0 W / +500 W).
        Justification: Sponsor's animal studies and modeling.
        */
        attribute peakCoolingPower_W : Real default 250.0;
    }

    requirement <'REQ-CP-002'> SteadyStateCoolingPower : CoolSpineRequirement {
        doc /*
        The system shall provide a steady-state cooling power of 150 W
        (tolerance: −0 W / +300 W).
        Justification: Sponsor's animal studies and modeling.
        */
        attribute steadyStateCoolingPower_W : Real default 150.0;
    }

    // --- Power and portability ---

    requirement <'REQ-CP-003'> OperationWithoutGroundPower : CoolSpineRequirement {
        doc /*
        The system shall operate without ground power for at least 30 minutes
        (tolerance: −0 min / +60 min).
        Justification: Clinical standard and IEC 60601-2-24.
        */
        attribute batteryRuntime_min : Real default 30.0;
    }

    requirement <'REQ-CP-004'> PortableFormFactor : CoolSpineRequirement {
        doc /*
        The system shall have a portable form factor suitable for movement
        with the patient between clinical settings.
        Justification: Movement with patient between clinical settings.
        */
    }

    // --- Fluid pressure ---

    requirement <'REQ-CP-005'> OperatingPressure : CoolSpineRequirement {
        doc /*
        The fluid circuit shall operate at 15 PSI
        (tolerance: −2 PSI / +10 PSI).
        Justification: Sponsor's modeling for developed catheter.
        */
        attribute operatingPressure_psi : Real default 15.0;
    }

    requirement <'REQ-CP-006'> MaximumPressure : CoolSpineRequirement {
        doc /*
        The fluid circuit maximum pressure shall not exceed 1.2 KSI.
        Justification: Sponsor's modeling.
        */
        attribute maximumPressure_ksi : Real default 1.2;
    }

    // --- Usability and safety ---

    requirement <'REQ-CP-007'> AppropriateUserInterface : CoolSpineRequirement {
        doc /*
        The system shall provide an appropriate user interface that meets
        the applicable standard (IEC 60601-1).
        Justification: IEC 60601-1.
        */
    }

    requirement <'REQ-CP-008'> SafetyMonitoringAndFailSafes : CoolSpineRequirement {
        doc /*
        The system shall provide safety monitoring and fail-safes that meet
        the applicable standards (IEC 60601-1-8 and IEC 60601-1-10).
        Justification: IEC 60601-1-8 and IEC 60601-1-10.
        */
    }
}
