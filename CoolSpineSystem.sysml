package CoolSpineSystem {

    private import ScalarValues::*;
    private import CoolSpineRequirements::*;

    // ------------------------------------------------------------------
    // Device hardware (clinical people / OR setup: CoolSpineSystemContext)
    // ------------------------------------------------------------------

    part def UPS {
        doc /*
        Wall-power box for the device. Takes AC from the room, outputs DC
        for the controller, and can keep running from the battery if wall
        power is lost.
        */
    }

    part def Battery {
        doc /*
        Design output for REQ-CP-003: one K2 Energy K2B24V11EB
        (LiFePO4, datasheet Rev C) on the UPS battery input. The
        requirement only sets the time without mains (at least 30
        minutes). Which battery, and the ratings below, are the design.

        Runtime is not a rating of this part. It is nominal capacity
        divided by whatever current the device actually draws, checked
        in VER-CP-003. At a steady 9 A — inside the 11.1 A recommended
        continuous discharge — the Rev C constant-current table still
        delivers the full 11.1 Ah (it gives 60 min at 11.1 A), so
        11.1 Ah / 9 A = 74 min down to the 20.0 V battery cutoff.
        */

        attribute nominalCapacity_Ah : Real = 11.1;                 // at C/5
        attribute averageOperatingVoltage_V : Real = 25.6;          // at C/5
        attribute recommendedContinuousDischarge_A : Real = 11.1;
        attribute dischargeCutoff_V : Real = 20.0;

        satisfy 'REQ-CP-003';  // OperationWithoutGroundPower
    }

    part def Compressor {
        doc /*
        Small compressor in the cooling module. Pushes refrigerant through
        the cold plate so heat can be pulled out of the saline.
        */
    }

    part def CoolPlate {
        doc /*
        Metal cold plate where saline is chilled. Heat moves from the saline
        into the refrigerant loop on the other side of the plate.
        */
    }

    part def CustomMicroRefrigerationUnit {
        doc /*
        On-board fridge for the saline. The controller turns it on/off.
        Inside: compressor + cold plate, plus two temperature probes on the
        heat exchanger so software can watch cooling performance.
        */

        satisfy 'REQ-CP-001';  // PeakCoolingPower
        satisfy 'REQ-CP-002';  // SteadyStateCoolingPower

        part compressor : Compressor;
        part coolPlate : CoolPlate;
        part heatExchange1 : Thermistor;
        part heatExchange2 : Thermistor;

        connection refrigerantLoop
            connect compressor to coolPlate {
            doc /* Refrigerant circulates between compressor and cold plate. */
        }
        connection senseHeatExchange1
            connect coolPlate to heatExchange1 {
            doc /* Temperature probe 1 on the cold-plate heat exchanger. */
        }
        connection senseHeatExchange2
            connect coolPlate to heatExchange2 {
            doc /* Temperature probe 2 on the cold-plate heat exchanger. */
        }
    }

    part def FluidReservoir {
        doc /*
        Saline tanks on the device: cold saline goes out to the patient
        catheter; warmer saline comes back from the pump. Two thermistors
        measure saline temperature on the way in and out.
        */

        satisfy 'REQ-CP-005';  // OperatingPressure

        part inputTempSensor : Thermistor;
        part outputTempSensor : Thermistor;
    }

    part def Catheter {
        doc /*
        Tube placed in the patient. Cold saline flows in, takes up heat from
        tissue / CSF, and returns warmer toward the pump. Tip sensor measures
        CSF temperature for the controller.
        */

        part csfTempSensor : Thermistor;
    }

    part def PeristalticPump {
        doc /*
        Pump that moves saline around the closed loop (catheter → reservoir).
        Speed/flow is set by the controller and must stay at or below
        50 mL/min. Pressure sensors sit before and after the pump head for
        safety monitoring.
        */

        satisfy 'REQ-CP-005';  // OperatingPressure
        satisfy 'REQ-CP-006';  // MaximumFlowRate

        part inputPressureSensor : PressureSensor;
        part outputPressureSensor : PressureSensor;

        connection salineThroughPump
            connect inputPressureSensor to outputPressureSensor {
            doc /* Saline path through the pump (inlet → outlet). */
        }
    }

    part def PressureSensor {
        doc /*
        Fluid pressure sensor in the saline circuit (used at the pump inlet
        and outlet). Controller reads it for operating pressure limits.
        */

        satisfy 'REQ-CP-005';  // OperatingPressure
    }

    part def CartridgeInPlaceSensor {
        doc /*
        Sensor that reports whether the disposable cartridge is seated
        in the device. The controller reads it before running the fluid loop.
        */
    }

    abstract part def TemperatureSensor {
        doc /*
        Any temperature probe the controller can read. Every probe in this
        design is a thermistor (saline, CSF, and the cooling-module heat
        exchanger).
        */

        attribute accuracy : Real;  // measurement accuracy, ± °C
    }

    part def Thermistor :> TemperatureSensor {
        doc /*
        Cheap, accurate temperature sensor (±0.1 °C). Resistance changes with
        temperature; the Pi reads it through the analog ADC. Used for saline,
        CSF, and refrigeration heat-exchanger temperatures.
        */

        attribute :>> accuracy = 0.1;  // ± 0.1 °C

        satisfy 'REQ-CP-009';  // UncalibratedTemperatureAccuracy
        satisfy 'REQ-CP-010';  // TemperatureSensorSize
        satisfy 'REQ-CP-011';  // CommonTemperatureSensorTechnology
        satisfy 'REQ-CP-012';  // AssemblyTemperatureResilience
    }

    // ------------------------------------------------------------------
    // Controller stack (Pi + power + ADC + screen)
    // ------------------------------------------------------------------

    part def RaspberryPi {
        doc /*
        Computer that runs CoolSpine control software (setpoints, sensing,
        safety). Hardware details: Spec/Pi & Screen/.
        */
    }

    part def PowerHat {
        doc /*
        Board that takes DC from the UPS and cleanly powers the Raspberry Pi.
        */
    }

    part def AdafruitAnalogInput {
        doc /*
        Multi-channel ADC (ADS1115 or equivalent) that digitizes temperature
        and pressure analog signals for the Pi. See Spec/ads1115/.
        */
    }

    part def TouchDisplay {
        doc /*
        Touch screen for the clinician: start/stop, setpoints, status and
        alarms. Driven by the Pi.
        */

        satisfy 'REQ-CP-007';  // AppropriateUserInterface
    }

    part def Controller {
        doc /*
        Brain of the device: Raspberry Pi + power board + ADC + touch screen.
        Powered from the UPS. Reads all sensors, shows the UI, sets pump flow
        (never above 50 mL/min), and switches the refrigeration module on/off.
        */

        satisfy 'REQ-CP-006';  // MaximumFlowRate

        part raspberryPi : RaspberryPi;
        part powerHat : PowerHat;
        part adc : AdafruitAnalogInput;
        part touchDisplay : TouchDisplay;

        connection supplyPiPower
            connect powerHat to raspberryPi {
            doc /* DC power from the power board to the Pi. */
        }

        connection adcInterface
            connect raspberryPi to adc {
            doc /* Digital bus (I2C) from Pi to the ADC chip. */
        }

        connection operatorInterface
            connect raspberryPi to touchDisplay {
            doc /* Screen and touch input between Pi and display. */
        }
    }

    // ------------------------------------------------------------------
    // Whole CoolSpine device
    // ------------------------------------------------------------------

    part def CoolSpineDevice {
        doc /*
        CoolSpine — portable device that cools a patient during spinal /
        neurosurgery by circulating cold saline through a catheter.

        How the fluid moves (closed loop):
          cold reservoir → catheter (in the patient) → pump → reservoir

        What the controller does: powered from UPS (+ battery backup), reads
        pressures, temperatures, and whether the cartridge is in place,
        shows the touch UI, sets pump flow, and turns the mini-fridge
        (micro-ref) on/off.

        People and the OR setup are modeled separately (operating context);
        this block is only the machine.
        */

        satisfy 'REQ-CP-004';  // PortableFormFactor
        satisfy 'REQ-CP-008';  // SafetyMonitoringAndFailSafes

        part ups : UPS;
        part battery : Battery;
        part controller : Controller;
        part microRef : CustomMicroRefrigerationUnit;
        part reservoir : FluidReservoir;
        part catheter : Catheter;
        part pump : PeristalticPump;
        part cartridgeInPlaceSensor : CartridgeInPlaceSensor;

        // Power
        connection supplyBackupPower
            connect battery to ups {
            doc /* Battery feeds the UPS when wall power is gone. */
        }
        connection supplyControllerPower
            connect ups to controller {
            doc /* UPS provides DC power to the controller. */
        }

        // Commands
        connection setFlowRate
            connect controller to pump {
            doc /* Software commands how fast the pump runs. */
        }
        connection enableRefrigeration
            connect controller to microRef {
            doc /* Software turns the cooling module on or off. */
        }

        // Sensing (sensors sit on the parts they measure)
        connection sensePumpInletPressure
            connect pump.inputPressureSensor to controller {
            doc /* Pump inlet pressure → controller. */
        }
        connection sensePumpOutletPressure
            connect pump.outputPressureSensor to controller {
            doc /* Pump outlet pressure → controller. */
        }
        connection senseReservoirInputTemp
            connect reservoir.inputTempSensor to controller {
            doc /* Warmer return saline temperature into the reservoir. */
        }
        connection senseReservoirOutputTemp
            connect reservoir.outputTempSensor to controller {
            doc /* Cold saline temperature leaving the reservoir. */
        }
        connection senseCsfTemp
            connect catheter.csfTempSensor to controller {
            doc /* CSF temperature at the catheter tip → controller. */
        }
        connection senseHeatExchange1Temp
            connect microRef.heatExchange1 to controller {
            doc /* Cooling-module temperature probe 1 → controller. */
        }
        connection senseHeatExchange2Temp
            connect microRef.heatExchange2 to controller {
            doc /* Cooling-module temperature probe 2 → controller. */
        }
        connection senseCartridgeInPlace
            connect cartridgeInPlaceSensor to controller {
            doc /* Cartridge seated / not seated → controller. */
        }

        // Closed saline loop
        connection coldSalineSupply
            connect reservoir to catheter {
            doc /* Cold saline out to the patient catheter. */
        }
        connection warmSalineReturn
            connect catheter to pump {
            doc /* Warmer saline from the catheter into the pump. */
        }
        connection warmSalineToReservoir
            connect pump to reservoir {
            doc /* Pump returns saline to the reservoir. */
        }
    }
}
