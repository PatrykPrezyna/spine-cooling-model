package CoolSpineViews {

    // Model-level view definitions (which stakeholder questions each picture
    // answers). Day-to-day diagrams you drag around live in views/*.json for
    // the explorer; keep these in sync when you change the story of a view.

    private import Views::*;
    private import StandardViewDefinitions::*;
    private import CoolSpineUseCases::*;
    private import CoolSpineUserNeeds::*;
    private import CoolSpineRequirements::*;
    private import CoolSpineVerification::*;
    private import CoolSpineSystem::*;
    private import CoolSpineSystemContext::*;

    // ------------------------------------------------------------------
    // What question each picture answers
    // ------------------------------------------------------------------

    concern def ClinicalOperationConcern {
        doc /*
        For clinicians: who starts therapy, who sets flow / temperature, and
        who benefits — without diving into internal hardware wiring.
        */
        subject coolSpine : CoolSpineDevice;
        stakeholder anesthesiologist : Anesthesiologist;
        stakeholder surgeon : Surgeon;
    }

    concern def TraceabilityConcern {
        doc /*
        For engineers / QA: user needs on the left, system requirements in
        the middle, and the hardware that satisfies those requirements on
        the right — without the full fluid / power schematic.
        */
        subject coolSpine : CoolSpineDevice;
        stakeholder anesthesiologist : Anesthesiologist;
    }

    concern clinicalOperation : ClinicalOperationConcern {
        subject;
        stakeholder anesthesiologist;
        stakeholder surgeon;
    }

    concern requirementsTrace : TraceabilityConcern {
        subject;
        stakeholder anesthesiologist;
    }

    // ------------------------------------------------------------------
    // Viewpoints
    // ------------------------------------------------------------------

    viewpoint def ClinicalUserViewpoint {
        frame clinicalOperation;
    }

    viewpoint def TraceabilityViewpoint {
        frame requirementsTrace;
    }

    // ------------------------------------------------------------------
    // Named pictures
    // ------------------------------------------------------------------

    view clinicalUseCases : GeneralView {
        doc /*
        Clinical story only: CoolSpine, surgeon, anesthesiologist, patient,
        Patient Transfer, and Operate Without Ground Power. Leave
        requirements and internal parts out so the interaction stays readable.
        */

        viewpoint vp : ClinicalUserViewpoint;

        expose CoolSpineUseCases::*;
        expose CoolSpineSystem::CoolSpineDevice;
        expose CoolSpineSystemContext::Anesthesiologist;
        expose CoolSpineSystemContext::Surgeon;
        expose CoolSpineSystemContext::Patient;

        render asTreeDiagram;
    }

    view useCaseRequirementsTraceability : GeneralView {
        doc /*
        Traceability story, left to right: user needs → system requirements
        → implementing parts (fridge, pump, battery, sensors, UI, device).
        VER-CP-003 sits with the battery requirement it verifies. Refine,
        satisfy, and verify links are the connections; leave use cases and
        the full interconnect diagram out of this picture.
        */

        viewpoint vp : TraceabilityViewpoint;

        expose CoolSpineUserNeeds::*;
        expose CoolSpineRequirements::*;
        expose CoolSpineVerification::*;
        expose CoolSpineSystem::CoolSpineDevice;
        expose CoolSpineSystem::CustomMicroRefrigerationUnit;
        expose CoolSpineSystem::Battery;
        expose CoolSpineSystem::FluidReservoir;
        expose CoolSpineSystem::TouchDisplay;
        expose CoolSpineSystem::PeristalticPump;
        expose CoolSpineSystem::PressureSensor;
        expose CoolSpineSystem::Thermistor;
        expose CoolSpineSystem::Controller;

        render asTreeDiagram;
    }
}
