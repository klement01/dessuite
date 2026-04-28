import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass


from dessuite.generator_tools.util import key_is_truthy
import dessuite.generator_tools.modules.common as common


@dataclass
class ModuleHalUartSettings:
    auto_enumerate: bool = True
    handle: str | None = None
    message_size: int = 1

    def update_from_element_tree(self, et: ElementTree.Element[str]):
        if (m := et.find("AutoEnumerate")) is not None:
            self.auto_enumerate = key_is_truthy(m.text)
        if (m := et.find("Handle")) is not None:
            self.handle = m.text
        if (m := et.find("MessageSize")) is not None:
            self.message_size = int(m.text)  # pyright: ignore[reportArgumentType]


@dataclass
class ModuleHalUart(common.GeneratorModule):
    def update_settings_from_element_tree(self, et: ElementTree.Element[str]): ...
