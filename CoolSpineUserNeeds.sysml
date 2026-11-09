package CoolSpineUserNeeds {

    // Stakeholder / user needs
    // System requirements in CoolSpineRequirements refine these needs.

    private import ScalarValues::*;

    requirement def CoolSpineUserNeed;

    requirement <'UN-CS-001'> LocalisedSpinalHypothermia : CoolSpineUserNeed {
        doc /*
        Safe, rapidly deployable, precise way to
        induce localized spinalhypothermia in the spinal cord.
        */
    }

    requirement <'UN-CS-002'> LocalizedNeuroprotection : CoolSpineUserNeed {
        doc /*
        Clinicians need targeted cooling of spinal tissue during
        ischemic injury (e.g. thoracic aortic surgery, stroke, trauma,
        cardiac arrest) while the rest of the patient stays normothermic —
        avoiding arrhythmia, coagulopathy, and pneumonia from whole-body
        cooling. Target CSF temperature is between 30–36 °C.
        */
    }

    requirement <'UN-CS-004'> ClinicianAdjustableControl : CoolSpineUserNeed {
        doc /*
        Clinicians (typically the anesthesiologist) need adjustable control
        to fine-tune CSF temperature during the procedure — not a fixed
        cooling setting.
        */
    }

    requirement <'UN-CS-005'> ReliableCatheterInterface : CoolSpineUserNeed {
        doc /*
        The controller must connect reliably to the multi-lumen cooling
        catheter (closed saline loop isolated from CSF; third lumen may drain
        CSF by gravity to hospital equipment). Provided by Sage.
        */
    }

    requirement <'UN-CS-006'> ContinuousTemperatureMonitoring : CoolSpineUserNeed {
        doc /*
        Temperature must be displayed continuously at the critical points in
        the system so staff can see that cooling is working and safe.
        */
    }

    requirement <'UN-CS-007'> FollowPatientThroughCare : CoolSpineUserNeed {
        doc /*
        The system must be able to follow the patient from surgery into
        recovery and also be usable in emergent situations — not only a
        stationary OR cart.
        */
    }

    requirement <'UN-CS-008'> CompactMobileFootprint : CoolSpineUserNeed {
        doc /*
        Footprint must be compact and mobile enough for operating rooms,
        ICUs, and patient transport.
        */
    }

    requirement <'UN-CS-009'> OperationalSafetyMonitoring : CoolSpineUserNeed {
        doc /*
        Operational safety must be ensured through status monitoring so
        unsafe conditions are visible and the device can fail safe.
        Charter high-level item 7.
        */
    }
}
