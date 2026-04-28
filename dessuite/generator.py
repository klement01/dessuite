import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from pathlib import Path

from csnake import CodeWriter, Function, Variable

import dessuite.generator_tools.core as core
import dessuite.generator_tools.modules as modules
import dessuite.generator_tools.c as c_files
import dessuite.model.des as des
import dessuite.model.petri as petri


@dataclass
class GeneratorSpec:
    # Base net.
    net: petri.Petri
    ordered_events: list[des.Event]
    ordered_commands: list[des.Event]
    ordered_places: list[petri.Place]

    # Other configs.
    core_settings: core.CoreSettings = field(default_factory=core.CoreSettings)
    modules: dict[str, modules.GeneratorModule] = field(default_factory=dict)

    @staticmethod
    def initialize_from_net(net: petri.Petri) -> GeneratorSpec:
        ordered_events = sorted(net.events, key=lambda e: str(e.id))
        ordered_commands = []
        ordered_places = sorted(net.places, key=lambda p: str(p.id))
        return GeneratorSpec(
            net=net, ordered_events=ordered_events, ordered_commands=ordered_commands, ordered_places=ordered_places
        )

    def import_dessuite_file(self, path: Path):
        tree = ElementTree.parse(str(path))

        if (et_core := tree.find("Core")) is not None:
            self.core_settings.update_from_element_tree(et_core)

        for et_module in tree.iterfind("Modules/*"):
            module_name = et_module.tag
            module = modules.get_module_from_name(module_name)()
            module.update_settings_from_element_tree(et_module)
            self.modules[module_name] = module

        for et_event in tree.iterfind("Events/Event"):
            event = des.Event(str(et_event.find("Name").text))  # pyright: ignore[reportOptionalMemberAccess]
            try:
                event_index = self.ordered_events.index(event)
            except ValueError:
                raise ValueError(f"event in spec but not in net: {event.id}")

            event_controllable = bool(et_event.findall("Controllable")) or bool(et_event.findall("Actions"))
            if event_controllable:
                self.ordered_commands.append(event)
                command_index = self.ordered_commands.index(event)
                for et_action in et_event.iterfind("Actions/*"):
                    module = self.modules[et_action.tag]
                    module.add_action(event, command_index, et_action)

            for et_trigger in et_event.iterfind("Triggers/*"):
                module = self.modules[et_trigger.tag]
                module.add_trigger(event, event_index, et_trigger)


def generate(model_file: Path, spec_file: Path, out_c: Path, out_h: Path):
    INDENT = 2

    # Load data.
    net = petri.Petri.import_tina_file(model_file)
    spec = GeneratorSpec.initialize_from_net(net)
    spec.import_dessuite_file(spec_file)

    with c_files.DES_CONTROLLER_C_TEMPLATE.open(mode="r", encoding="utf-8") as f:
        template = f.read()

    # Event transitions.
    event_transitions_cw = CodeWriter(indent=INDENT)
    event_transition_vector_entries = []
    for idx, event in enumerate(spec.ordered_events):
        transition = spec.net.transitions[event]
        input_arcs = {
            p_idx: w
            for p_idx, p in enumerate(spec.ordered_places)
            if (w := max(transition.input_weights[p], transition.read_weights[p])) != 0
        }
        delta_arcs = {
            p_idx: w
            for p_idx, p in enumerate(spec.ordered_places)
            if (w := transition.output_weights[p] - transition.input_weights[p]) != 0
        }

        input_arcs_var = Variable(
            f"EVENT_{idx}_INPUT_ARCS",
            primitive="struct TransitionArc",
            qualifiers="const",
            value=input_arcs.items(),  # type: ignore
            array=len(input_arcs),  # type: ignore
        )
        delta_arcs_var = Variable(
            f"EVENT_{idx}_DELTA_ARCS",
            primitive="struct TransitionArc",
            qualifiers="const",
            value=delta_arcs.items(),  # type: ignore
            array=len(delta_arcs),  # type: ignore
        )
        event_transitions_cw.add_variable_initialization(input_arcs_var)
        event_transitions_cw.add_variable_initialization(delta_arcs_var)
        event_transition_vector_entries.append(
            "{"
            + ", ".join(
                str(i) for i in (input_arcs_var.array, delta_arcs_var.array, input_arcs_var.name, delta_arcs_var.name)
            )
            + "}"
        )

    # Commands.
    command_handler_cw = CodeWriter(indent=INDENT)
    command_handler_vector_entries = []
    for idx, command in enumerate(spec.ordered_commands):
        event_idx = spec.ordered_events.index(command)
        handler = Function(f"COMMAND_{idx}_HANDLER")
        # TODO: add module code.
        # module.add_actions(handler): handler.add_code(...) ...
        command_handler_cw.add_function_definition(handler)
        command_handler_vector_entries.append("{" + ", ".join(str(i) for i in (event_idx, handler.name)) + "}")

    # Finalize.
    template_kv_pairs = [
        ("MODULE_INCLUDES", "/* TODO */"),  # TODO
        ("CORE_EVENT_QUEUE_SIZE", spec.core_settings.event_queue_size),
        ("CORE_EXECUTE_COMMAND_NAME", f'"{spec.core_settings.task_execute_command.name}"'),
        ("CORE_EXECUTE_COMMAND_SDEPTH", spec.core_settings.task_execute_command.stack_depth),
        ("CORE_EXECUTE_COMMAND_PRIORITY", spec.core_settings.task_execute_command.priority),
        ("CORE_UPDATE_STATE_NAME", f'"{spec.core_settings.task_update_state.name}"'),
        ("CORE_UPDATE_STATE_SDEPTH", spec.core_settings.task_update_state.stack_depth),
        ("CORE_UPDATE_STATE_PRIORITY", spec.core_settings.task_update_state.priority),
        ("CORE_SET_COMMAND_NAME", f'"{spec.core_settings.task_set_command.name}"'),
        ("CORE_SET_COMMAND_SDEPTH", spec.core_settings.task_set_command.stack_depth),
        ("CORE_SET_COMMAND_PRIORITY", spec.core_settings.task_set_command.priority),
        ("CORE_EVENT_COUNT", len(spec.ordered_events)),
        ("CORE_COMMAND_COUNT", len(spec.ordered_commands)),
        ("CORE_PLACE_COUNT", len(spec.ordered_places)),
        ("CORE_EVENTS_IDS", f",\n{' ' * INDENT}".join(str(e.id) for e in spec.ordered_events)),
        ("CORE_EVENT_DATA", str(event_transitions_cw)),
        ("CORE_EVENT_TRANSITION_VECTOR", f",\n{' ' * INDENT}".join(event_transition_vector_entries)),
        ("CORE_INITIAL_MARKINGS", ", ".join(str(spec.net.initial_state[p]) for p in spec.ordered_places)),
        ("MODULE_DATA", "/* TODO */"),  # TODO
        ("MODULE_VARIABLES", "/* TODO */"),  # TODO
        ("MODULE_INIT_FUNCTION_DEFINITIONS", "/* TODO */"),  # TODO
        ("MODULE_INPUT_INTERFACE_FUNCTIONS", "/* TODO */"),  # TODO
        ("MODULE_OUTPUT_INTERFACE_FUNCTIONS", "/* TODO */"),  # TODO
        ("CORE_COMMAND_HANDLER_FUNCTIONS", str(command_handler_cw)),  # TODO
        ("CORE_COMMAND_HANDLER_VECTOR", f",\n{' ' * INDENT}".join(command_handler_vector_entries)),
        ("MODULE_INIT_FUNCTION_CALLS", "/* TODO */"),  # TODO
    ]
    src = template
    for key, value in template_kv_pairs:
        src = src.replace(f"{{{key}}}", str(value), count=1)

    with out_c.open(mode="w", encoding="utf-8") as f:
        f.write(src)

    c_files.DES_CONTROLLER_H.copy(out_h)
