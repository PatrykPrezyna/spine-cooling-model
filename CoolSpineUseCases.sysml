package CoolSpineUseCases {

    // Spec-compliant SysML v2 use cases (see Systems Library UseCases / Cases).
    // Actors are part defs from the operational context — not `actor def`
    // (that form is non-standard and rejected by the official parser).
    private import CoolSpineRequirements::*;
    private import CoolSpineSystem::*;
    private import CoolSpineSystemContext::*;

    // ------------------------------------------------------------------
    // Use cases
    // ------------------------------------------------------------------

    use case def DeliverTherapeuticCooling {
        doc /*
        Primary clinical use case: during a spinal / neurosurgical procedure,
        the surgeon decides whether CoolSpine is used; if yes, the
        anesthesiologist powers it on, setpoints are agreed and entered, and
        CoolSpine delivers cooling until a stop command. The patient is the
        beneficiary of the heat exchange.
        */

        // Swimlane order (left → right): surgeon, anesthesiologist, CoolSpine
        actor surgeon : Surgeon {
            perform deliverCooling.decideWhetherToUse;
            perform deliverCooling.decideSetpoint;
        }

        actor anesthesiologist : Anesthesiologist {
            perform deliverCooling.switchDeviceOn;
            perform deliverCooling.enterSetpoint;
        }

        subject coolSpine : CoolSpine {
            perform deliverCooling.completeSelfCheck;
            perform deliverCooling.startCoolingAndAwaitStop;
        }

        actor patient : Patient;

        objective {
            doc /*
            CoolSpine maintains commanded flow and cooling within safe pressure
            limits for the duration of the therapy request.
            */
        }

        satisfy 'REQ-CP-001';  // PeakCoolingPower
        satisfy 'REQ-CP-002';  // SteadyStateCoolingPower
        satisfy 'REQ-CP-005';  // OperatingPressure
        satisfy 'REQ-CP-006';  // MaximumPressure
        satisfy 'REQ-CP-007';  // AppropriateUserInterface
        satisfy 'REQ-CP-008';  // SafetyMonitoringAndFailSafes

        // Activity with decision after the surgeon's use/no-use choice.
        // Swimlanes via perform on subject / actors above.
        perform action deliverCooling {
            doc /*
            Surgeon decides whether to use CoolSpine; yes → power on →
            self-check → setpoints → cooling until stop; no → done.
            */

            action decideWhetherToUse {
                doc /*
                Surgeon decides whether CoolSpine will be used for this
                procedure.
                */
            }

            action switchDeviceOn {
                doc /* Anesthesiologist switches CoolSpine on. */
            }
            then completeSelfCheck;

            action completeSelfCheck {
                doc /*
                CoolSpine runs power-on self-check; continues only when
                the check is OK.
                */
            }
            then decideSetpoint;

            action decideSetpoint {
                doc /* Surgeon decides the flow / temperature setpoint. */
            }
            then enterSetpoint;

            action enterSetpoint {
                doc /* Anesthesiologist enters the setpoint on the device. */
            }
            then startCoolingAndAwaitStop;

            action startCoolingAndAwaitStop {
                doc /*
                After the setpoint is written, CoolSpine starts cooling
                automatically and waits for a stop command.
                */
            }
            then done;

            first start;
            then decideWhetherToUse;
            then decide;
              if yes then switchDeviceOn;
              else done;
        }
    }

    use case def OperateWithoutGroundPower {
        doc /*
        Continuity use case: CoolSpine keeps delivering therapy when wall /
        ground power is unavailable (transport between clinical settings or
        temporary AC loss), drawing on UPS + battery for at least the required
        hold-up time.
        */

        subject coolSpine : CoolSpine;

        actor anesthesiologist : Anesthesiologist;

        objective {
            doc /*
            Therapy continues without ground power for at least 30 minutes
            while safety monitoring and fail-safes remain active.
            */
        }

        satisfy 'REQ-CP-003';  // OperationWithoutGroundPower
        satisfy 'REQ-CP-004';  // PortableFormFactor
        satisfy 'REQ-CP-008';  // SafetyMonitoringAndFailSafes
    }
}
