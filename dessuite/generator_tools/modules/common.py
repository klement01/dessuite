import abc
import dataclasses
import xml.etree.ElementTree as ElementTree


@dataclasses.dataclass
class GeneratorModule(abc.ABC):
    @abc.abstractmethod
    def update_settings_from_element_tree(self, et: ElementTree.Element[str]): ...
