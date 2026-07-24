package CoolSpineSystemContext {

    // Load after CoolSpineRequirements + CoolSpineSystem (name-sorted order).
    private import ScalarValues::*;
    private import CoolSpineSystem::*;

    // ------------------------------------------------------------------
    // Clinical / environmental actors and the patient
    // Connections are simple part-to-part links (same style everywhere).
    // ------------------------------------------------------------------

    part def Patient {
        doc /*
        Patient receiving therapeutic temperature control via the CoolSpine
        catheter (inserted heat-exchange path). CSF drain path optional
        for monitoring.
        */
    }

    part def Surgeon {
        doc /*
        Operating surgeon who directs the procedure and may request changes
        to cooling / flow setpoints via the clinical team.
        */
    }

    part def Anesthesiologist {
        doc /*
        Anesthesiologist responsible for patient physiology during the
        procedure and primary operator of CoolSpine setpoints.
        */
    }

    // ------------------------------------------------------------------
    // CSF drain — internal structure
    // ------------------------------------------------------------------

    part def PressureSensor {
        doc /*
        Measures CSF pressure at the stopcock and provides readings
        to an optional display.
        */
    }

    part def Display {
        doc /* Optional display of pressure measurement data. */
    }

    part def Stopcock {
        doc /*
        Controls CSF flow into the burette; also provides a sense
        connection for the pressure sensor.
        */
    }

    part def Burette {
        doc /* Chamber that receives CSF from the stopcock and drains to the bag. */
    }

    part def CollectionBag {
        doc /* Collects CSF transferred from the burette. */
    }

    part def GraduatedScale {
        doc /*
        Scale associated with the burette for reading fluid level
        and pressure values.
        */
    }

    part def LevelingDevice {
        doc /*
        Aligns / positions the graduated scale relative to a
        reference level (e.g. external auditory meatus).
        */
    }

    part def CsfDrain {
        doc /*
        External ventricular drain / CSF collection set:
        Pressure Sensor — Stopcock — Burette — Collection Bag,
        with Graduated Scale and Leveling Device for level/pressure
        reference, and an optional Display for pressure readings.
        */

        part pressureSensor : PressureSensor;
        part display : Display [0..1];
        part stopcock : Stopcock;
        part burette : Burette;
        part collectionBag : CollectionBag;
        part graduatedScale : GraduatedScale;
        part levelingDevice : LevelingDevice;

        // Fluid path: Stopcock → Burette → Collection Bag
        connection csfIntoBurette
            connect stopcock to burette {
            doc /* Stopcock controls CSF flow into the burette. */
        }
        connection csfToCollectionBag
            connect burette to collectionBag {
            doc /* Burette transfers collected CSF to the bag. */
        }

        // Pressure Sensor connected to Stopcock
        connection senseCsfPressure
            connect stopcock to pressureSensor {
            doc /* Pressure sense connection at the stopcock. */
        }

        // Measurement path: Pressure Sensor → optional Display
        connection displayCsfPressure
            connect pressureSensor to display {
            doc /* Pressure measurement data to the optional display. */
        }

        // Measurement reference: Graduated Scale ↔ Burette
        connection indicateFluidLevel
            connect graduatedScale to burette {
            doc /* Scale used to read fluid level and pressure on the burette. */
        }

        // Reference / alignment: Leveling Device ↔ Graduated Scale
        connection alignScaleLevel
            connect levelingDevice to graduatedScale {
            doc /* Aligns the scale relative to a clinical reference level. */
        }
    }

    // ------------------------------------------------------------------
    // Operational context
    // ------------------------------------------------------------------

    part def Kontext {
        doc /*
        Operating context of CoolSpine: the device (including its catheter),
        the patient, clinical staff, and an optional CSF drain for
        intracranial pressure / drainage monitoring.
        Fluid circulation is closed inside CoolSpine (reservoir → catheter
        → pump → reservoir); the catheter is the patient-inserted segment.
        */

        part coolSpine : CoolSpine;
        part patient : Patient;
        part surgeon : Surgeon;
        part anesthesiologist : Anesthesiologist;
        part csfDrain : CsfDrain [0..1];

        connection drainPatientCsf
            connect patient to csfDrain {
            doc /* Patient CSF drain outlet to the CSF drain assembly. */
        }
    }

    // ------------------------------------------------------------------
    // Activity — clinical interaction with CoolSpine
    // ------------------------------------------------------------------

    part def ClinicalCoolingInteraction {
        doc /*
        Simple activity diagram: interaction among the surgeon,
        anesthesiologist, and CoolSpine during therapeutic cooling.
        Swimlanes are expressed via perform on each participant.
        */

        part surgeon : Surgeon {
            perform operateTherapy.requestCooling;
            perform operateTherapy.requestChange;
            perform operateTherapy.endProcedure;
        }

        part anesthesiologist : Anesthesiologist {
            perform operateTherapy.setSetpoints;
            perform operateTherapy.adjustSetpoints;
            perform operateTherapy.stopTherapy;
        }

        part coolSpine : CoolSpine {
            perform operateTherapy.deliverTherapy;
            perform operateTherapy.applyAdjustment;
            perform operateTherapy.shutdown;
        }

        perform action operateTherapy {
            doc /*
            Clinical cooling procedure:
            surgeon requests therapy → anesthesiologist configures CoolSpine →
            CoolSpine delivers cooling → surgeon may request a change →
            anesthesiologist adjusts → procedure ends → CoolSpine shuts down.
            */

            action requestCooling {
                doc /* Surgeon requests therapeutic cooling for the patient. */
            }

            action setSetpoints {
                doc /* Anesthesiologist sets initial flow and temperature on CoolSpine. */
            }

            action deliverTherapy {
                doc /* CoolSpine runs the saline loop and delivers cooling. */
            }

            action requestChange {
                doc /* Surgeon requests a setpoint change during the procedure. */
            }

            action adjustSetpoints {
                doc /* Anesthesiologist updates flow / temperature setpoints. */
            }

            action applyAdjustment {
                doc /* CoolSpine applies the new setpoints. */
            }

            action endProcedure {
                doc /* Surgeon indicates cooling is no longer required. */
            }

            action stopTherapy {
                doc /* Anesthesiologist commands end of therapy on CoolSpine. */
            }

            action shutdown {
                doc /* CoolSpine stops circulation and returns to standby. */
            }

            first start;
            then requestCooling;
            then setSetpoints;
            then deliverTherapy;
            then requestChange;
            then adjustSetpoints;
            then applyAdjustment;
            then endProcedure;
            then stopTherapy;
            then shutdown;
            then done;
        }
    }
}

