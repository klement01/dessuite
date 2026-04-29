import abc
import dataclasses
import xml.etree.ElementTree as ElementTree

from csnake import CodeWriter, Function

import dessuite.generator_tools.core as core


@dataclasses.dataclass
class GeneratorModule(abc.ABC):
    def update_settings_from_element_tree(self, et: ElementTree.Element[str]):
        pass

    def add_trigger(self, core_event: core.CoreEvent, et: ElementTree.Element[str]):
        pass

    def add_action(self, core_event: core.CoreEvent, et: ElementTree.Element[str]):
        pass

    def write_actions(self, core_event: core.CoreEvent, function: Function):
        pass

    def write_includes(self, writer: CodeWriter):
        pass

    def write_data(self, writer: CodeWriter):
        pass

    def write_variables(self, writer: CodeWriter):
        pass

    def write_function_definitions(self, writer: CodeWriter):
        pass

    def write_input_interface_functions(self, writer: CodeWriter):
        pass

    def write_output_interface_functions(self, writer: CodeWriter):
        pass

    def write_init_function_calls(self, writer: CodeWriter):
        pass
