import abc
import dataclasses
import xml.etree.ElementTree as ElementTree

import dessuite.model.des as des


@dataclasses.dataclass
class GeneratorModule(abc.ABC):
    @abc.abstractmethod
    def update_settings_from_element_tree(self, et: ElementTree.Element[str]): ...

    @abc.abstractmethod
    def add_trigger(self, event: des.Event, event_idx: int, et: ElementTree.Element[str]): ...

    @abc.abstractmethod
    def add_action(self, event: des.Event, command_idx: int, et: ElementTree.Element[str]): ...
