package CoolSpineViews {

    // Model-level view definitions (which stakeholder questions each picture
    // answers). Day-to-day diagrams you drag around live in views/*.json for
    // the explorer; keep these in sync when you change the story of a view.

    private import Views::*;
    private import StandardViewDefinitions::*;
    private import CoolSpineUseCases::*;
    private import CoolSpineRequirements::*;
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
        For engineers / QA: which requirements a use case covers, and which
        hardware blocks implement those requirements — without the full fluid
        / power schematic.
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
        and the two use cases. Leave requirements and internal parts out so
        the interaction stays readable.
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
        Traceability story: use cases ↔ requirements ↔ main implementing
        parts (controller, pump, fridge, power, sensors, UI). Prefer this over
        stuffing the full interconnect diagram into the use-case picture.
        */

        viewpoint vp : TraceabilityViewpoint;

        expose CoolSpineUseCases::*;
        expose CoolSpineRequirements::*;
        expose CoolSpineSystem::CoolSpineDevice;
        expose CoolSpineSystem::CustomMicroRefrigerationUnit;
        expose CoolSpineSystem::Battery;
        expose CoolSpineSystem::UPS;
        expose CoolSpineSystem::TouchDisplay;
        expose CoolSpineSystem::PeristalticPump;
        expose CoolSpineSystem::PressureSensor;
        expose CoolSpineSystem::TemperatureSensor;
        expose CoolSpineSystem::Controller;

        render asTreeDiagram;
    }
}
