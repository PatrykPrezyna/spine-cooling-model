package CoolSpineUseCases {

    // Clinical scenarios. People come from CoolSpineSystemContext; the machine
    // is CoolSpineDevice from CoolSpineSystem.
    private import CoolSpineRequirements::*;
    private import CoolSpineSystem::*;
    private import CoolSpineSystemContext::*;

    // ------------------------------------------------------------------
    // Use cases
    // ------------------------------------------------------------------

    use case def PatientTransfer {
        doc /*
        Move the patient with CoolSpine: the surgeon first decides whether
        cooling should continue after transfer. If not, the anesthesiologist
        switches the device off. If yes, they unplug it and CoolSpine
        automatically runs from battery. After the move, the anesthesiologist
        plugs wall power back in and the device returns to charging mode.
        */

        actor surgeon : Surgeon {
            perform transferPatient.decideCoolAfterTransfer;
        }

        actor anesthesiologist : Anesthesiologist {
            perform transferPatient.switchDeviceOff;
            perform transferPatient.unplugFromWall;
            perform transferPatient.movePatient;
            perform transferPatient.reconnectWallPower;
        }

        subject coolSpine : CoolSpineDevice {
            perform transferPatient.enterBatteryMode;
            perform transferPatient.enterChargingMode;
        }

        actor patient : Patient;

        objective {
            doc /*
            Keep the device in a safe power state during the move: either
            powered down, or on battery if cooling continues; restore wall
            power and charging afterwards.
            */
        }

        satisfy 'REQ-CP-003';  // OperationWithoutGroundPower
        satisfy 'REQ-CP-004';  // PortableFormFactor
        satisfy 'REQ-CP-007';  // AppropriateUserInterface
        satisfy 'REQ-CP-008';  // SafetyMonitoringAndFailSafes

        perform action transferPatient {
            doc /*
            Surgeon decides → switch off, or unplug and auto battery →
            transfer → plug back in → charging mode.
            */

            action decideCoolAfterTransfer {
                doc /*
                Surgeon decides whether the patient should still be cooled
                after they are transferred.
                */
            }

            action switchDeviceOff {
                doc /*
                Anesthesiologist switches CoolSpine off because cooling will
                not continue after transfer.
                */
            }
            then movePatient;

            action unplugFromWall {
                doc /*
                Anesthesiologist pulls the power plug so the cart can move,
                expecting cooling to continue.
                */
            }
            then enterBatteryMode;

            action enterBatteryMode {
                doc /*
                Unplugged from the wall, CoolSpine automatically switches to
                battery mode.
                */
            }
            then movePatient;

            action movePatient {
                doc /*
                Patient is transferred with the device (off, or running on
                battery).
                */
            }
            then reconnectWallPower;

            action reconnectWallPower {
                doc /*
                After the transfer, the anesthesiologist plugs wall power
                back in.
                */
            }
            then enterChargingMode;

            action enterChargingMode {
                doc /*
                With the plug attached again, CoolSpine returns to charging
                mode.
                */
            }
            then done;

            first start;
            then decideCoolAfterTransfer;
            then decide;
              if yes then unplugFromWall;
              else switchDeviceOff;
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
