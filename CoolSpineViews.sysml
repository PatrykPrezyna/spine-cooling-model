package CoolSpineViews {

    // SysML v2 views / viewpoints (Systems Library Views + StandardViewDefinitions).
    //
    // Why not one diagram with use cases + all requirements + all parts?
    // SysML v2 separates stakeholder concerns via viewpoints; each view
    // *exposes* only the elements that answer that concern. Dumping every
    // element onto a GeneralView recreates an unreadable "everything"
    // diagram. Prefer:
    //   1. Clinical use-case view — actors + use cases (+ subject system)
    //   2. Traceability view — use cases ↔ requirements ↔ key parts
    //   3. Structure views — already in explorer (Context / Internals)
    // Explorer `views/*.json` files are the practical canvas for (1)–(3);
    // the textual views below are the model-level source of truth.

    private import Views::*;
    private import StandardViewDefinitions::*;
    private import CoolSpineUseCases::*;
    private import CoolSpineRequirements::*;
    private import CoolSpineSystem::*;
    private import CoolSpineSystemContext::*;

    // ------------------------------------------------------------------
    // Concerns (subject must be the first parameter)
    // ------------------------------------------------------------------

    concern def ClinicalOperationConcern {
        doc /*
        How clinicians interact with CoolSpine during a procedure — who
        initiates therapy, who sets flow / temperature, who benefits.
        */
        subject coolSpine : CoolSpine;
        stakeholder anesthesiologist : Anesthesiologist;
        stakeholder surgeon : Surgeon;
    }

    concern def TraceabilityConcern {
        doc /*
        Which requirements each use case addresses, and which device parts
        implement those requirements — without showing full fluid / power
        interconnection detail.
        */
        subject coolSpine : CoolSpine;
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
    // Views (typed by GeneralView — graph of exposed elements / relations)
    // ------------------------------------------------------------------

    view clinicalUseCases : GeneralView {
        doc /*
        Clinical use-case presentation: CoolSpine as subject, clinical
        actors, and the two use cases. Intentionally omits requirements
        and internal parts so the interaction picture stays readable.
        */

        viewpoint vp : ClinicalUserViewpoint;

        expose CoolSpineUseCases::*;
        expose CoolSpineSystem::CoolSpine;
        expose CoolSpineSystemContext::Anesthesiologist;
        expose CoolSpineSystemContext::Surgeon;
        expose CoolSpineSystemContext::Patient;

        render asTreeDiagram;
    }

    view useCaseRequirementsTraceability : GeneralView {
        doc /*
        Traceability presentation: use cases, the requirements they
        satisfy, and the main parts that satisfy those same requirements.
        Prefer this over mixing full interconnection structure into the
        use-case picture.
        */

        viewpoint vp : TraceabilityViewpoint;

        expose CoolSpineUseCases::*;
        expose CoolSpineRequirements::*;
        expose CoolSpineSystem::CoolSpine;
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
