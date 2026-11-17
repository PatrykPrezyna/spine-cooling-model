package CoolSpineSystemContext {

    // Load after CoolSpineRequirements + CoolSpineSystem (name-sorted order).
    private import ScalarValues::*;
    private import CoolSpineSystem::*;

    // ------------------------------------------------------------------
    // People in the OR
    // ------------------------------------------------------------------

    part def Patient {
        doc /*
        Person at risk of acute ischemic injury to the spinal cord or brain
        (e.g. thoracic aortic surgery, stroke, traumatic injury, cardiac
        arrest) who receives localized therapeutic hypothermia from CoolSpine.

        The multi-lumen catheter is placed percutaneously into the
        intrathecal space (spinal cooling) and is the heat-exchange path in the patient: chilled saline
        circulating in a closed loop cools the CSF, which cools the targeted
        neural tissue to about 30–34 °C while the rest of the body stays
        normothermic. The saline never contacts the CSF.
        */
    }

    part def Surgeon {
        doc /*
        Lead clinician for the procedure (e.g. thoracic aortic repair or a
        neurosurgical case). Decides whether to use CoolSpine for
        neuroprotection and whether cooling should continue after a patient
        transfer; places or oversees placement of the cooling catheter, and
        may ask for changes to cooling or flow during the case; does not
        usually drive the device UI (that is the anesthesiologist).
        */
    }

    part def Anesthesiologist {
        doc /*
        Clinician who watches patient physiology and is the main operator of
        CoolSpine (power, setpoints, stop, unplug / replug for transfer)
        during the case. Uses the device's adjustable controls to fine-tune
        CSF temperature toward the 30–34 °C therapeutic range, and relies on
        the device's continuous temperature and status monitoring to confirm
        safe operation.
        */
    }

    // ------------------------------------------------------------------
    // Optional CSF drain (hospital equipment next to CoolSpine)
    // ------------------------------------------------------------------

    part def CsfPressureSensor {
        doc /*
        Measures CSF pressure at the stopcock. Reading can go to an optional
        bedside display. (Different from CoolSpine's saline pressure sensors.)
        */
    }

    part def Display {
        doc /* Optional screen showing CSF pressure from the drain set. */
    }

    part def Stopcock {
        doc /*
        Valve that controls CSF into the burette and is where the pressure
        sensor taps the line.
        */
    }

    part def Burette {
        doc /*
        Clear chamber that receives CSF from the stopcock before it drains
        into the collection bag; used with the scale to read level/pressure.
        */
    }

    part def CollectionBag {
        doc /* Bag that collects CSF from the burette. */
    }

    part def GraduatedScale {
        doc /*
        Ruler / scale next to the burette so staff can read fluid level and
        related pressure values.
        */
    }

    part def LevelingDevice {
        doc /*
        Helps align the scale to a clinical zero height (often near the ear
        canal) so pressure readings are meaningful.
        */
    }

    part def CsfDrain {
        doc /*
        Standard external CSF drain set used beside CoolSpine.
        It receives CSF that leaves the patient by gravity through the catheter's third (drainage) lumen.
        Fluid path: stopcock → burette → bag, with pressure sense, optional
        display, scale, and leveling.
        */

        part pressureSensor : CsfPressureSensor;
        part display : Display [0..1];
        part stopcock : Stopcock;
        part burette : Burette;
        part collectionBag : CollectionBag;
        part graduatedScale : GraduatedScale;
        part levelingDevice : LevelingDevice;

        connection csfIntoBurette
            connect stopcock to burette {
            doc /* CSF flows from stopcock into the burette. */
        }
        connection csfToCollectionBag
            connect burette to collectionBag {
            doc /* CSF drains from burette into the bag. */
        }

        connection senseCsfPressure
            connect stopcock to pressureSensor {
            doc /* Pressure is sensed at the stopcock. */
        }

        connection displayCsfPressure
            connect pressureSensor to display {
            doc /* Pressure value shown on the optional display. */
        }

        connection indicateFluidLevel
            connect graduatedScale to burette {
            doc /* Scale is read against the burette fluid level. */
        }

        connection alignScaleLevel
            connect levelingDevice to graduatedScale {
            doc /* Leveling sets the scale to the clinical reference height. */
        }
    }

    // ------------------------------------------------------------------
    // Operating room picture (who is there with the device)
    // ------------------------------------------------------------------

    part def Context {
        doc /*
        */

        part coolSpine : CoolSpineDevice {
            doc /*
            The CoolSpine control unit plus cooling catheter: chills saline,
            circulates it in a closed loop through the catheter, lets the
            clinician fine-tune CSF temperature, and continuously monitors
            temperatures and status for operational safety. Compact, mobile
            footprint suitable for OR, ICU, and transport.
            */
        }
        part patient : Patient {
            doc /*
            Recipient of localized cooling via the percutaneously placed
            intrathecal (or ventricular) catheter.
            */
        }
        part surgeon : Surgeon {
            doc /*
            Directs the case: orders cooling, oversees catheter placement,
            requests setpoint changes, calls the end of therapy.
            */
        }
        part anesthesiologist : Anesthesiologist {
            doc /*
            Hands on the device: sets and adjusts flow / temperature
            setpoints and stops therapy, while watching patient physiology.
            */
        }
        part csfDrain : CsfDrain [0..1] {
            doc /*
            Optional external drain set present when ICP / CSF-drainage
            monitoring is wanted; fed by gravity from the catheter's
            drainage lumen.
            */
        }

        connection drainPatientCsf
            connect patient to csfDrain {
            doc /*
            Gravity CSF line from the catheter's third (drainage) lumen into
            the optional external drain set. Carries CSF only — never the
            saline coolant.
            */
        }
    }

    // ------------------------------------------------------------------
    // Who does what during a cooling case (simple sequence)
    // ------------------------------------------------------------------

    part def ClinicalCoolingInteraction {
        doc /*
        Step-by-step clinical flow while CoolSpine is used: surgeon asks for
        cooling, anesthesiologist configures the device, CoolSpine delivers
        therapy, setpoints may change mid-case, then everyone shuts down.
        Same people and device as in the OR context — this is the workflow,
        not a second copy of the hardware.
        */

        ref part surgeon : Surgeon {
            perform operateTherapy.requestCooling;
            perform operateTherapy.requestChange;
            perform operateTherapy.endProcedure;
        }

        ref part anesthesiologist : Anesthesiologist {
            perform operateTherapy.setSetpoints;
            perform operateTherapy.adjustSetpoints;
            perform operateTherapy.stopTherapy;
        }

        ref part coolSpine : CoolSpineDevice {
            perform operateTherapy.deliverTherapy;
            perform operateTherapy.applyAdjustment;
            perform operateTherapy.shutdown;
        }

        perform action operateTherapy {
            doc /*
            Typical order of work:
            1) surgeon requests cooling
            2) anesthesiologist sets flow / temperature
            3) CoolSpine runs
            4) surgeon may ask for a change → anesthesiologist updates → device applies
            5) case ends → stop → device standby
            */

            action requestCooling {
                doc /* Surgeon asks for therapeutic cooling for this patient. */
            }

            action setSetpoints {
                doc /* Anesthesiologist enters initial flow and temperature. */
            }

            action deliverTherapy {
                doc /* CoolSpine runs the saline loop and cools. */
            }

            action requestChange {
                doc /* Surgeon asks for a different setpoint during the case. */
            }

            action adjustSetpoints {
                doc /* Anesthesiologist changes flow / temperature on the UI. */
            }

            action applyAdjustment {
                doc /* CoolSpine applies the new setpoints. */
            }

            action endProcedure {
                doc /* Surgeon says cooling is no longer needed. */
            }

            action stopTherapy {
                doc /* Anesthesiologist stops therapy on the device. */
            }

            action shutdown {
                doc /* CoolSpine stops the loop and goes to standby. */
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
