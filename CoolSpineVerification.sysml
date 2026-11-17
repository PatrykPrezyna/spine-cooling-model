package CoolSpineVerification {

    // Design verification (ISO 13485 7.3.6 / 21 CFR 820.30(f)):
    // objective evidence that a design output meets a design input.
    // These are not requirements, and they are not design validation
    // (that would show the device meets the user need in clinical use).

    private import VerificationCases::*;
    private import CoolSpineRequirements::*;
    private import CoolSpineSystem::*;

    verification def <'VER-CP-003'> InternalElectricalPowerSourceOperatingTime {
        doc /*
        Design verification of REQ-CP-003 by test. The device must still
        be operating 30 minutes after supply mains are disconnected,
        running from the backup battery. Not design validation of UN-CS-007.

        Steps, expected runtime, and the raw log are in the linked
        experiment README.
        */

        subject device : CoolSpineDevice;

        objective {
            doc /*
            Pass if the device is still operating 30 minutes after supply
            mains are disconnected.
            */
            verify requirement 'REQ-CP-003';
        }

        @VerificationMethod {
            kind = VerificationMethodKind::test;
        }
    }
}
