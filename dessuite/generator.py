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
    for event_idx, event in enumerate(spec.ordered_events):
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
            f"EVENT_{event_idx}_INPUT_ARCS",
            primitive="struct TransitionArc",
            qualifiers="const",
            value=input_arcs.items(),  # type: ignore
            array=len(input_arcs),  # type: ignore
        )
        delta_arcs_var = Variable(
            f"EVENT_{event_idx}_DELTA_ARCS",
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
    for command_idx, command in enumerate(spec.ordered_commands):
        event_idx = spec.ordered_events.index(command)
        handler = Function(f"COMMAND_{command_idx}_HANDLER")
        for module in spec.modules.values():
            module.write_actions(command_idx, handler)
        command_handler_cw.add_function_definition(handler)
        command_handler_vector_entries.append("{" + ", ".join(str(i) for i in (event_idx, handler.name)) + "}")

    # Other module data.
    module_includes_cw = CodeWriter(indent=INDENT)
    module_data_cw = CodeWriter(indent=INDENT)
    module_variables_cw = CodeWriter(indent=INDENT)
    module_function_definitions_cw = CodeWriter(indent=INDENT)
    module_input_interface_functions_cw = CodeWriter(indent=INDENT)
    module_output_interface_functions_cw = CodeWriter(indent=INDENT)
    module_init_function_calls_cw = CodeWriter(indent=INDENT)
    module_init_function_calls_cw.indent()
    for module in spec.modules.values():
        module.write_includes(module_includes_cw)
        module.write_data(module_data_cw)
        module.write_variables(module_variables_cw)
        module.write_function_definitions(module_function_definitions_cw)
        module.write_input_interface_functions(module_input_interface_functions_cw)
        module.write_output_interface_functions(module_output_interface_functions_cw)
        module.write_init_function_calls(module_init_function_calls_cw)

    # Finalize.
    template_kv_pairs = [
        ("MODULE_INCLUDES", module_includes_cw),  # TODO
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
        ("CORE_EVENT_DATA", event_transitions_cw),
        ("CORE_EVENT_TRANSITION_VECTOR", f",\n{' ' * INDENT}".join(event_transition_vector_entries)),
        ("CORE_INITIAL_MARKINGS", ", ".join(str(spec.net.initial_state[p]) for p in spec.ordered_places)),
        ("MODULE_DATA", module_data_cw),
        ("MODULE_VARIABLES", module_variables_cw),
        ("MODULE_FUNCTION_DEFINITIONS", module_function_definitions_cw),
        ("MODULE_INPUT_INTERFACE_FUNCTIONS", module_input_interface_functions_cw),
        ("MODULE_OUTPUT_INTERFACE_FUNCTIONS", module_output_interface_functions_cw),
        ("CORE_COMMAND_HANDLER_FUNCTIONS", command_handler_cw),
        ("CORE_COMMAND_HANDLER_VECTOR", f",\n{' ' * INDENT}".join(command_handler_vector_entries)),
        ("MODULE_INIT_FUNCTION_CALLS", module_init_function_calls_cw),
    ]
    src = template
    for key, value in template_kv_pairs:
        src = src.replace(f"{{{key}}}", str(value), count=1)

    with out_c.open(mode="w", encoding="utf-8") as f:
        f.write(src)

    c_files.DES_CONTROLLER_H.copy(out_h)
