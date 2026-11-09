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
        Backup battery so CoolSpine can keep running when unplugged or
        during transport (target: at least 30 minutes).
        */

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
        part heatExchange1 : Thermocouple;
        part heatExchange2 : Thermocouple;

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
        satisfy 'REQ-CP-006';  // MaximumPressure

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
        Speed/flow is set by the controller. Pressure sensors sit before and
        after the pump head for safety monitoring.
        */

        satisfy 'REQ-CP-005';  // OperatingPressure
        satisfy 'REQ-CP-006';  // MaximumPressure

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
        and outlet). Controller reads it for operating / max pressure limits.
        */

        satisfy 'REQ-CP-005';  // OperatingPressure
        satisfy 'REQ-CP-006';  // MaximumPressure
    }

    abstract part def TemperatureSensor {
        doc /*
        Any temperature probe the controller can read. Two kinds are used
        in this design: thermistor (more accurate, saline/CSF) and
        thermocouple (cooling module heat exchanger).
        */

        attribute accuracy : Real;  // measurement accuracy, ± °C
    }

    part def Thermistor :> TemperatureSensor {
        doc /*
        Cheap, accurate temperature sensor (±0.1 °C). Resistance changes with
        temperature; the Pi reads it through the analog ADC. Used for saline
        and CSF temperatures.
        */

        attribute :>> accuracy = 0.1;  // ± 0.1 °C
    }

    part def Thermocouple :> TemperatureSensor {
        doc /*
        Temperature sensor for the refrigeration heat exchanger (±1 °C).
        Needs a thermocouple input board (see Spec/Thermocouples DAQ …/).
        */

        attribute :>> accuracy = 1.0;  // ± 1 °C
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
        Powered from the UPS. Reads all sensors, shows the UI, sets pump flow,
        and switches the refrigeration module on/off.
        */

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
        pressures and temperatures, shows the touch UI, sets pump flow, and
        turns the mini-fridge (micro-ref) on/off.

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
