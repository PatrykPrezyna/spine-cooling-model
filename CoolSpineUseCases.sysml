package CoolSpineUseCases {

    // Clinical scenarios. People come from CoolSpineSystemContext; the machine
    // is CoolSpineDevice from CoolSpineSystem.
    private import CoolSpineRequirements::*;
    private import CoolSpineSystem::*;
    private import CoolSpineSystemContext::*;

    // ------------------------------------------------------------------
    // Use cases
    // ------------------------------------------------------------------

    use case def DeliverTherapeuticCooling {
        doc /*
        Main clinical scenario: during spinal / neurosurgery the surgeon
        decides whether to use CoolSpine. If yes, the anesthesiologist powers
        it on, setpoints are agreed and entered, and CoolSpine cools until
        someone stops it. The patient benefits from the heat exchange.
        */

        actor surgeon : Surgeon {
            perform deliverCooling.decideWhetherToUse;
            perform deliverCooling.decideSetpoint;
        }

        actor anesthesiologist : Anesthesiologist {
            perform deliverCooling.switchDeviceOn;
            perform deliverCooling.enterSetpoint;
        }

        subject coolSpine : CoolSpineDevice {
            perform deliverCooling.completeSelfCheck;
            perform deliverCooling.startCoolingAndAwaitStop;
        }

        actor patient : Patient;

        objective {
            doc /*
            Keep commanded flow and cooling within safe pressure limits for
            as long as therapy is requested.
            */
        }

        satisfy 'REQ-CP-001';  // PeakCoolingPower
        satisfy 'REQ-CP-002';  // SteadyStateCoolingPower
        satisfy 'REQ-CP-005';  // OperatingPressure
        satisfy 'REQ-CP-006';  // MaximumPressure
        satisfy 'REQ-CP-007';  // AppropriateUserInterface
        satisfy 'REQ-CP-008';  // SafetyMonitoringAndFailSafes

        perform action deliverCooling {
            doc /*
            Happy path: decide to use → power on → self-check → setpoints →
            cool until stop. If the surgeon decides not to use CoolSpine,
            the flow ends immediately.
            */

            action decideWhetherToUse {
                doc /*
                Surgeon decides if CoolSpine will be used for this case.
                */
            }

            action switchDeviceOn {
                doc /* Anesthesiologist powers CoolSpine on. */
            }
            then completeSelfCheck;

            action completeSelfCheck {
                doc /*
                Device runs power-on checks; therapy continues only if OK.
                */
            }
            then decideSetpoint;

            action decideSetpoint {
                doc /* Surgeon picks the flow / temperature target. */
            }
            then enterSetpoint;

            action enterSetpoint {
                doc /* Anesthesiologist enters that target on the device UI. */
            }
            then startCoolingAndAwaitStop;

            action startCoolingAndAwaitStop {
                doc /*
                After setpoints are set, CoolSpine starts cooling and waits
                for a stop command.
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
        Keep therapy going when there is no wall power — moving between rooms
        or a short AC outage. UPS + battery must cover at least the required
        hold-up time while safety monitoring stays active.
        */

        subject coolSpine : CoolSpineDevice;

        actor anesthesiologist : Anesthesiologist;

        objective {
            doc /*
            Therapy continues without wall power for at least 30 minutes, with
            safety monitoring and fail-safes still working.
            */
        }

        satisfy 'REQ-CP-003';  // OperationWithoutGroundPower
        satisfy 'REQ-CP-004';  // PortableFormFactor
        satisfy 'REQ-CP-008';  // SafetyMonitoringAndFailSafes
    }
}
