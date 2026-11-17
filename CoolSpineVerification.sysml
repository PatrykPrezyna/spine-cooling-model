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
        Design verification test of REQ-CP-003. Confirms the device keeps
        operating for at least 30 minutes from its internal electrical power
        source (the backup battery) after supply mains (wall power) are
        disconnected. In the lab this is the backup-battery runtime run.

        Not design validation: a bench run does not show that the device
        meets user need UN-CS-007 in actual patient transfer.

        Method: test. The written steps, sheet, and raw log live in
        Experiments/20261117_Backup_Battery_Runtime_and_Voltage_Decay.

        Preconditions recorded with the run, because they change the result:
        battery identity, state of charge at the start, whether the UPS is
        in the path, and the load (pump, refrigeration, user interface).

        Steps:
        1. Start the system on the backup battery with wall power disconnected.
        2. Every 10 minutes, record clock time, battery voltage, and whether
           the system is still operating.
        3. Continue until the system can no longer hold, and record the stop
           time. If it is still operating past 180 minutes, keep adding
           10-minute rows.
        4. File the completed log as raw data and do not edit that copy.

        Pass: still operating at 30 minutes (REQ-CP-003 minimum). Keep the
        log until stop so the record shows the actual operating time.
        Battery voltage is objective evidence of how the source decays.
        This requirement sets no voltage limit, so the curve is recorded
        and is not itself pass or fail.
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
