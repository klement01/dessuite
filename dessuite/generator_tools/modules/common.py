import abc
import dataclasses
from xml.etree import ElementTree

from csnake import CodeWriter, Function

from dessuite.generator_tools import core


@dataclasses.dataclass
class GeneratorModule(abc.ABC):
    @abc.abstractmethod
    def name(self) -> str:
        pass

    def parse_settings_from_element_tree(self, et: ElementTree.Element[str]):
        pass

    def register_trigger(self, core_event: core.CoreEvent, et: ElementTree.Element[str]):
        pass

    def register_action(self, core_event: core.CoreEvent, et: ElementTree.Element[str]):
        pass

    def write_includes(self, writer: CodeWriter):
        pass

    def write_variables(self, writer: CodeWriter):
        pass

    def write_actions(self, core_event: core.CoreEvent, function: Function):
        pass

    def write_triggers(self, writer: CodeWriter):
        pass

    def write_init(self, writer: CodeWriter):
        pass
