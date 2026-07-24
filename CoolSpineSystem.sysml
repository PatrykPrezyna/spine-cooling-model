package CoolSpineSystem {

    private import ScalarValues::*;
    private import CoolSpineRequirements::*;

    // ------------------------------------------------------------------
    // Part definitions (device only — clinical context is in CoolSpineSystemContext)
    // Connections are simple part-to-part links (same style everywhere).
    // ------------------------------------------------------------------

    part def UPS {
        doc /*
        Uninterruptible power supply: AC input conditioning and DC distribution
        with battery-backed hold-up. Supplies the controller and other DC loads.
        */
    }

    part def Battery {
        doc /* Backup battery pack for operation without ground power. */

        satisfy 'REQ-CP-003';  // OperationWithoutGroundPower
    }

    part def Compressor {
        doc /* Refrigerant compressor driving the micro-refrigeration loop. */
    }

    part def CoolPlate {
        doc /* Cold plate that transfers heat from the saline to the refrigerant loop. */
    }

    part def CustomMicroRefrigerationUnit {
        doc /*
        Compact refrigeration loop that cools saline; switched by the
        controller. Compressor and cold plate, instrumented with a
        temperature sensor on each side of the heat exchange.
        */

        satisfy 'REQ-CP-001';  // PeakCoolingPower
        satisfy 'REQ-CP-002';  // SteadyStateCoolingPower

        part compressor : Compressor;
        part coolPlate : CoolPlate;
        part heatExchange1TempSensor : Thermocouple;
        part heatExchange2TempSensor : Thermocouple;

        connection refrigerantLoop
            connect compressor to coolPlate {
            doc /* Compressed refrigerant into the cold plate and back. */
        }
        connection senseHeatExchange1
            connect coolPlate to heatExchange1TempSensor {
            doc /* Heat Exchange 1 temperature at the cold plate. */
        }
        connection senseHeatExchange2
            connect coolPlate to heatExchange2TempSensor {
            doc /* Heat Exchange 2 temperature at the cold plate. */
        }
    }

    part def FluidReservoir {
        doc /*
        Warm and cold saline reservoirs. Cold supply leaves toward the
        catheter; warm return arrives from the pump. Instrumented with an
        input and an output saline temperature sensor.
        */

        satisfy 'REQ-CP-005';  // OperatingPressure
        satisfy 'REQ-CP-006';  // MaximumPressure

        part inputTempSensor : Thermistor;
        part outputTempSensor : Thermistor;
    }

    part def Catheter {
        doc /*
        Patient-inserted catheter. Cold saline enters, exchanges heat with
        tissue, and leaves as warm saline toward the pump. Carries a CSF
        temperature sensor at the tip.
        */

        part csfTempSensor : Thermistor;
    }

    part def PeristalticPump {
        doc /*
        Circulates warm return saline from the catheter back to the reservoir.
        Flow rate is commanded by the controller. Pressure is measured on the
        pump inlet and outlet.
        */

        satisfy 'REQ-CP-005';  // OperatingPressure
        satisfy 'REQ-CP-006';  // MaximumPressure

        part inputPressureSensor : PressureSensor;
        part outputPressureSensor : PressureSensor;

        connection salineThroughPump
            connect inputPressureSensor to outputPressureSensor {
            doc /* Saline path across the pump head, inlet to outlet. */
        }
    }

    part def PressureSensor {
        doc /* In-line fluid pressure sensor on the saline circuit. */

        satisfy 'REQ-CP-005';  // OperatingPressure
        satisfy 'REQ-CP-006';  // MaximumPressure
    }

    abstract part def TemperatureSensor {
        doc /*
        Temperature probe read by the controller. Realization may be either
        a thermistor or a thermocouple (see specializations).
        */

        attribute accuracy : Real;  // measurement accuracy, ± °C
    }

    part def Thermistor :> TemperatureSensor {
        doc /*
        Resistance-based temperature sensor (e.g. NTC). Analog voltage from a
        divider / conditioning circuit is read by the controller ADC.
        */

        attribute :>> accuracy = 0.1;  // ± 0.1 °C
    }

    part def Thermocouple :> TemperatureSensor {
        doc /*
        Thermoelectric temperature sensor. Requires cold-junction compensation
        and a thermocouple DAQ front-end (see Spec/Thermocouples
        DAQ 8-Layer Stackable HAT/).
        */

        attribute :>> accuracy = 1.0;  // ± 1 °C
    }

    // ------------------------------------------------------------------
    // Controller internals (Pi + power HAT + Adafruit ADC + GPIO)
    // ------------------------------------------------------------------

    part def RaspberryPi {
        doc /*
        Single-board computer hosting control / monitoring software.
        See Spec/Pi & Screen/.
        */
    }

    part def PowerHat {
        doc /* Power HAT that conditions UPS DC and supplies the Raspberry Pi. */
    }

    part def AdafruitAnalogInput {
        doc /*
        Adafruit ADS1115 (or equivalent) multi-channel ADC for temperature
        and pressure analog inputs. See Spec/ads1115/.
        */
    }

    part def TouchDisplay {
        doc /* Operator touch display: controls and status, driven by the controller. */

        satisfy 'REQ-CP-007';  // AppropriateUserInterface
    }

    part def Controller {
        doc /*
        Device controller: Raspberry Pi with power HAT, Adafruit analog
        inputs for temp/pressure, operator touch display, and digital GPIO
        to switch the micro-refrigeration unit. Powered from the UPS; wired
        to all sensors.
        */

        part raspberryPi : RaspberryPi;
        part powerHat : PowerHat;
        part adc : AdafruitAnalogInput;
        part touchDisplay : TouchDisplay;

        connection supplyPiPower
            connect powerHat to raspberryPi {
            doc /* Power HAT supplies the Raspberry Pi. */
        }

        connection adcInterface
            connect raspberryPi to adc {
            doc /* I2C between Raspberry Pi and Adafruit ADS1115. */
        }

        connection operatorInterface
            connect raspberryPi to touchDisplay {
            doc /* Operator controls and status between the Pi and the touch display. */
        }
    }

    // ------------------------------------------------------------------
    // System composition
    // ------------------------------------------------------------------

    part def CoolSpine {
        doc /*
        Therapeutic temperature-control device. Closed fluid loop:
        reservoir (cold) → catheter (warms) → pump → reservoir. Pressure is
        measured inside the pump (inlet/outlet), saline temperature inside
        the reservoir (input/output), CSF temperature in the catheter, and
        heat-exchange temperature in the micro-refrigeration unit. Controller
        (Pi-based) is powered from the UPS, reads sensors, hosts the
        operator touch display, drives pump setpoints, and switches the
        micro-refrigeration unit.
        Patient and clinical staff live in CoolSpineSystemContext::Kontext.
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
            doc /* Battery backup into the UPS. */
        }
        connection supplyControllerPower
            connect ups to controller {
            doc /* UPS DC supply to the controller. */
        }

        // Commands
        connection setFlowRate
            connect controller to pump {
            doc /* Controller commands pump flow rate. */
        }
        connection enableRefrigeration
            connect controller to microRef {
            doc /* Digital on/off control of the micro-refrigeration unit. */
        }

        // Sensing (probes live inside the parts they instrument)
        connection sensePumpInletPressure
            connect pump.inputPressureSensor to controller {
            doc /* Pump inlet pressure read by controller ADC. */
        }
        connection sensePumpOutletPressure
            connect pump.outputPressureSensor to controller {
            doc /* Pump outlet pressure read by controller ADC. */
        }
        connection senseReservoirInputTemp
            connect reservoir.inputTempSensor to controller {
            doc /* Warm saline temperature entering the reservoir. */
        }
        connection senseReservoirOutputTemp
            connect reservoir.outputTempSensor to controller {
            doc /* Cooled saline temperature leaving the reservoir. */
        }
        connection senseCsfTemp
            connect catheter.csfTempSensor to controller {
            doc /* CSF temperature at the catheter, read by the controller. */
        }
        connection senseHeatExchange1Temp
            connect microRef.heatExchange1TempSensor to controller {
            doc /* Heat Exchange 1 temperature read by controller ADC. */
        }
        connection senseHeatExchange2Temp
            connect microRef.heatExchange2TempSensor to controller {
            doc /* Heat Exchange 2 temperature read by controller ADC. */
        }

        // Closed saline loop
        connection coldSalineSupply
            connect reservoir to catheter {
            doc /* Cold saline from reservoir to catheter. */
        }
        connection warmSalineReturn
            connect catheter to pump {
            doc /* Warm return saline from catheter into the pump inlet. */
        }
        connection warmSalineToReservoir
            connect pump to reservoir {
            doc /* Warm saline from the pump outlet back to the reservoir. */
        }
    }

    part coolSpine : CoolSpine;
}
