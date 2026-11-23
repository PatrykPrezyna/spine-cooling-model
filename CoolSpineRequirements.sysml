package CoolSpineRequirements {

    // Source numbers: Spec/functional_requirements.csv
    // User / stakeholder needs: CoolSpineUserNeeds. These requirements
    // satisfy those needs (sysml-explorer draws «satisfy» as the trace link).

    private import ScalarValues::*;
    private import CoolSpineUserNeeds::*;

    requirement def CoolSpineRequirement;

    requirement def <'SYS-CS-001'> CoolSpineSystemRequirements :> CoolSpineRequirement {
        doc /*
        Top-level need: CoolSpine must meet the cooling power, battery /
        portability, fluid pressure and flow, temperature sensing, user
        interface, and safety rules listed below. Use this as the checklist
        for the whole product.
        */
        satisfy 'UN-CS-001';  // LocalisedSpinalHypothermia
        satisfy 'UN-CS-002';  // LocalizedNeuroprotection
    }

    // --- Cooling performance ---

    requirement def <'REQ-CP-001'> PeakCoolingPower :> CoolSpineRequirement {
        doc /*
        Must be able to remove heat at 250 W peak (never less; up to +500 W
        is acceptable). Comes from sponsor animal studies / modeling — drives
        sizing of the micro-refrigeration unit.
        */
        attribute peakCoolingPower_W : Real default 250.0;
        satisfy 'UN-CS-002';  // LocalizedNeuroprotection
    }

    requirement def <'REQ-CP-002'> SteadyStateCoolingPower :> CoolSpineRequirement {
        doc /*
        Must sustain 150 W of cooling in steady state (never less; up to
        +300 W acceptable). Same study basis as peak power; this is the
        continuous duty the fridge and loop must hold.
        */
        attribute steadyStateCoolingPower_W : Real default 150.0;
        satisfy 'UN-CS-002';  // LocalizedNeuroprotection
    }

    // --- Power and portability ---

    requirement def <'REQ-CP-003'> OperationWithoutGroundPower :> CoolSpineRequirement {
        doc /*
        Must run at least 30 minutes without wall power (never less; up to
        +60 min acceptable) — e.g. moving the patient or brief AC loss.
        Battery + UPS design; aligned with clinical practice / IEC 60601-2-24.
        Design verification (bench test, not a second requirement): VER-CP-003
        InternalElectricalPowerSourceOperatingTime.
        */
        attribute batteryRuntime_min : Real default 30.0;
        satisfy 'UN-CS-007';  // FollowPatientThroughCare
    }

    requirement def <'REQ-CP-004'> PortableFormFactor :> CoolSpineRequirement {
        doc /*
        Device must be small / wheeled enough to move with the patient between
        rooms. Influences packaging, weight, and cable layout — not just the
        fridge performance.
        */
        satisfy 'UN-CS-007';  // FollowPatientThroughCare
        satisfy 'UN-CS-008';  // CompactMobileFootprint
    }

    // --- Fluid pressure and flow ---

    requirement def <'REQ-CP-005'> OperatingPressure :> CoolSpineRequirement {
        doc /*
        Normal saline-loop pressure: 15 PSI (−2 / +10 PSI). Sized for the
        catheter design; pump and sensors must stay in this band in use.
        */
        attribute operatingPressure_psi : Real default 15.0;
        satisfy 'UN-CS-005';  // ReliableCatheterInterface
    }

    requirement def <'REQ-CP-006'> MaximumFlowRate :> CoolSpineRequirement {
        doc /*
        Hard ceiling: saline-loop flow must not exceed 50 mL/min. Protects
        the catheter and patient; software and the pump must enforce this.
        */
        attribute maximumFlowRate_mL_min : Real default 50.0;
        satisfy 'UN-CS-005';  // ReliableCatheterInterface
    }

    // --- Usability and safety ---

    requirement def <'REQ-CP-007'> AppropriateUserInterface :> CoolSpineRequirement {
        doc /*
        Touch UI and controls must be usable and compliant for a medical
        electrical device (IEC 60601-1). Think alarms, labels, and operable
        by the anesthesiologist under OR conditions.
        */
        satisfy 'UN-CS-004';  // ClinicianAdjustableControl
    }

    requirement def <'REQ-CP-008'> SafetyMonitoringAndFailSafes :> CoolSpineRequirement {
        doc /*
        Must monitor for unsafe conditions and fail safe (alarms / shutdown)
        per IEC 60601-1-8 and IEC 60601-1-10. Covers sensor faults, pressure
        trips, and loss of control — not only the happy path.
        */
        satisfy 'UN-CS-006';  // ContinuousTemperatureMonitoring
        satisfy 'UN-CS-009';  // OperationalSafetyMonitoring
    }

    // --- Temperature sensing ---

    requirement def <'REQ-CP-009'> UncalibratedTemperatureAccuracy :> CoolSpineRequirement {
        doc /*
        Every temperature sensor must read within 0.2 °C (error strictly
        below 0.2 °C) from 30 °C to 36 °C with no calibration. That is the
        CSF target band the clinician is trying to hold.
        */
        attribute maxError_C : Real default 0.2;
        attribute rangeMin_C : Real default 30.0;
        attribute rangeMax_C : Real default 36.0;
        satisfy 'UN-CS-001';  // LocalisedSpinalHypothermia
        satisfy 'UN-CS-002';  // LocalizedNeuroprotection
    }

    requirement def <'REQ-CP-010'> TemperatureSensorSize :> CoolSpineRequirement {
        doc /*
        Every temperature sensor must be smaller than 0.5 mm in its largest
        dimension so it can sit in the catheter / saline path without
        blocking flow.
        */
        attribute maxSize_mm : Real default 0.5;
        satisfy 'UN-CS-005';  // ReliableCatheterInterface
    }

    requirement def <'REQ-CP-011'> CommonTemperatureSensorTechnology :> CoolSpineRequirement {
        doc /*
        All temperature sensors in the device must use the same sensing
        technology, so readings at the reservoir, catheter, and heat
        exchanger are comparable on one readout path.
        */
        satisfy 'UN-CS-006';  // ContinuousTemperatureMonitoring
    }

    requirement def <'REQ-CP-012'> AssemblyTemperatureResilience :> CoolSpineRequirement {
        doc /*
        Every temperature sensor must survive 230 °C during assembly
        (soldering / joining) and still meet its accuracy afterward.
        Manufacturing constraint; no matching clinical user need.
        */
        attribute assemblyTemperature_C : Real default 230.0;
    }

    // --- Cartridge requirements ---

    requirement def <'REQ-CP-013'> CartridgePhysicsRequirements :> CoolSpineRequirement {
        doc /*
        Disposable cartridge physics requirements: pump-noise isolation,
        no inlet suction, debubbling, thermal contact planes, and fluid
        volume / dwell time. These govern the cartridge's hydraulic and
        thermal behavior in the saline cooling loop. From 2026-11-23
        whiteboard.
        */
        satisfy 'UN-CS-002';  // LocalizedNeuroprotection
        satisfy 'UN-CS-005';  // ReliableCatheterInterface
        satisfy 'UN-CS-009';  // OperationalSafetyMonitoring
    }

    requirement def <'REQ-CP-014'> PeristalticPumpNoiseIsolatedFromOutlet :> CoolSpineRequirement {
        doc /*
        Peristaltic pump noise (pulsation / pressure spikes) must be
        isolated from the cartridge outlet so the downstream catheter and
        patient see steady flow. May imply pump placement as a middle
        step in the fluid path. From 2026-11-23 whiteboard.
        */
        satisfy 'UN-CS-005';  // ReliableCatheterInterface
        satisfy 'UN-CS-009';  // OperationalSafetyMonitoring
    }

    requirement def <'REQ-CP-015'> NoSuctionOnInlet :> CoolSpineRequirement {
        doc /*
        No suction on the cartridge inlet — avoids cavitation, air
        ingestion, and cartridge structure failure. May imply pump
        placement as a middle step in the fluid path. From 2026-11-23
        whiteboard.
        */
        satisfy 'UN-CS-005';  // ReliableCatheterInterface
        satisfy 'UN-CS-009';  // OperationalSafetyMonitoring
    }

    requirement def <'REQ-CP-016'> Debubbling :> CoolSpineRequirement {
        doc /*
        Cartridge must remove air bubbles from the saline loop so they
        cannot reach the patient catheter. Prevents air embolism and
        ensures predictable heat-transfer performance. From 2026-11-23
        whiteboard.
        */
        satisfy 'UN-CS-002';  // LocalizedNeuroprotection
        satisfy 'UN-CS-009';  // OperationalSafetyMonitoring
    }

    requirement def <'REQ-CP-017'> ThermalTransferContactPlanes :> CoolSpineRequirement {
        doc /*
        Cartridge must have 1–2 thermal transfer contact planes where
        saline exchanges heat with the cooling module (cold plate).
        Trade-off between cooling effectiveness and mechanical complexity.
        From 2026-11-23 whiteboard.
        */
        attribute minContactPlanes : Integer default 1;
        attribute maxContactPlanes : Integer default 2;
        satisfy 'UN-CS-002';  // LocalizedNeuroprotection
    }

    requirement def <'REQ-CP-018'> FluidVolumeAndDwellTime :> CoolSpineRequirement {
        doc /*
        Cartridge fluid volume directly determines saline dwell time at
        the cold plate, which affects cooling power and thermal response.
        Design must balance effective heat transfer against total fluid
        volume (priming, spillage, thermal mass). From 2026-11-23
        whiteboard: "fluid volume => dwell time".
        */
        satisfy 'UN-CS-002';  // LocalizedNeuroprotection
    }

    requirement def <'REQ-CP-019'> CartridgeManufacturingAndClinicalRequirements :> CoolSpineRequirement {
        doc /*
        Disposable cartridge manufacturing and clinical requirements:
        sterilizable, fillable, and simple installation / assembly / fill.
        These govern how the cartridge is produced, delivered, and used
        in the OR. From 2026-11-23 whiteboard.
        */
        satisfy 'UN-CS-004';  // ClinicianAdjustableControl
        satisfy 'UN-CS-005';  // ReliableCatheterInterface
        satisfy 'UN-CS-007';  // FollowPatientThroughCare
    }

    requirement def <'REQ-CP-020'> Sterilizable :> CoolSpineRequirement {
        doc /*
        Disposable cartridge must be sterilizable (autoclave, gamma, or
        EtO) so it arrives ready for single-use clinical deployment.
        Manufacturing / regulatory constraint; no matching clinical user need.
        From 2026-11-23 whiteboard.
        */
    }

    requirement def <'REQ-CP-021'> Fillable :> CoolSpineRequirement {
        doc /*
        Cartridge must be fillable with saline. Whether it ships prefilled
        is negotiable (manufacturing / supply-chain trade-off; noted "john"
        on the 2026-11-23 whiteboard). Design must support either prefill
        or clinical-site fill without excessive steps or risk of contamination.
        */
        satisfy 'UN-CS-005';  // ReliableCatheterInterface
    }

    requirement def <'REQ-CP-022'> SimpleInstallationAssemblyFill :> CoolSpineRequirement {
        doc /*
        Cartridge installation, assembly, and fill must be simple and fast
        for OR staff. Exact number of steps TBD. Cross-reference Zoll setup
        for usability benchmark (2026-11-23 whiteboard: "go through Zoll
        setup?"). Minimize training burden and opportunities for user error.
        */
        satisfy 'UN-CS-004';  // ClinicianAdjustableControl
        satisfy 'UN-CS-007';  // FollowPatientThroughCare
    }
}
