import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass


import dessuite.generator_tools.modules.common as common
import dessuite.model.des as des


@dataclass
class ModuleHalGpioSettings:
    pin_suffix: str = ""
    port_suffix: str = ""

    def update_from_element_tree(self, et: ElementTree.Element[str]):
        if (m := et.find("PinSuffix")) is not None:
            self.pin_suffix = m.text  # pyright: ignore[reportAttributeAccessIssue]
        if (m := et.find("PortSuffix")) is not None:
            self.port_suffix = m.text  # pyright: ignore[reportAttributeAccessIssue]


@dataclass
class ModuleHalGpio(common.GeneratorModule):
    def update_settings_from_element_tree(self, et: ElementTree.Element[str]):
        # TODO.
        ...

    def add_trigger(self, event: des.Event, event_idx: int, et: ElementTree.Element[str]):
        # TODO.
        ...

    def add_action(self, event: des.Event, command_idx: int, et: ElementTree.Element[str]):
        # TODO.
        ...
