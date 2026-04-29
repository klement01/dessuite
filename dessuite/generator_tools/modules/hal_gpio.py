import enum
import xml.etree.ElementTree as ElementTree
from collections import defaultdict
from dataclasses import dataclass, field

from csnake import CodeWriter, Function

import dessuite.generator_tools.core as core
import dessuite.generator_tools.modules.common as common


@dataclass
class ModuleHalGpioSettings:
    pin_suffix: str = ""
    port_suffix: str = ""

    def update_from_element_tree(self, et: ElementTree.Element[str]):
        if (m := et.find("PinSuffix")) is not None:
            self.pin_suffix = m.text  # pyright: ignore[reportAttributeAccessIssue]
        if (m := et.find("PortSuffix")) is not None:
            self.port_suffix = m.text  # pyright: ignore[reportAttributeAccessIssue]


class ActionType(enum.StrEnum):
    SET = "Set"
    RESET = "Reset"


@dataclass
class Action:
    pin: str
    action_type: ActionType


@dataclass
class ModuleHalGpio(common.GeneratorModule):
    settings: ModuleHalGpioSettings = field(default_factory=ModuleHalGpioSettings)

    exti_triggers: defaultdict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    actions: defaultdict[str, list[Action]] = field(default_factory=lambda: defaultdict(list))

    def update_settings_from_element_tree(self, et: ElementTree.Element[str]):
        self.settings.update_from_element_tree(et)

    def add_trigger(self, core_event: core.CoreEvent, et: ElementTree.Element[str]):
        for et_interrupt in et.iterfind("Interrupt"):
            pin = str(et_interrupt.text)
            self.exti_triggers[pin].append(core_event.event_name)

    def add_action(self, core_event: core.CoreEvent, et: ElementTree.Element[str]):
        for et_action in et.iterfind("*"):
            action_type = ActionType(et_action.tag)
            self.actions[core_event.event_name].append(Action(pin=str(et_action.text), action_type=action_type))

    def write_input_interface_functions(self, writer: CodeWriter):
        if len(self.exti_triggers) == 0:
            return

        # Function declaration.
        writer.add_line("void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin)")
        writer.open_brace()

        writer.add_line("BaseType_t xHigherPriorityTaskWoken = pdFALSE;")
        writer.add_line("EventIdx_t eventIdx;")
        writer.add_line("switch (GPIO_Pin)")
        writer.open_brace()

        for pin, event_names in self.exti_triggers.items():
            writer.add_line(f"case {pin}{self.settings.pin_suffix}:")
            writer.indent()
            for event_name in event_names:
                writer.add_line(f"eventIdx = {event_name};")
                writer.add_line("xQueueSendToBackFromISR(PendingEventsQueue, &eventIdx, &xHigherPriorityTaskWoken);")
            writer.add_switch_break()

        writer.close_brace()
        writer.add_line("portYIELD_FROM_ISR(xHigherPriorityTaskWoken);")

        writer.close_brace()

    def write_actions(self, core_event: core.CoreEvent, function: Function):
        for action in self.actions[core_event.event_name]:
            value = "GPIO_PIN_SET" if action.action_type == ActionType.SET else "GPIO_PIN_RESET"
            function.add_code(
                f"HAL_GPIO_WritePin({action.pin}{self.settings.port_suffix}, {action.pin}{self.settings.pin_suffix}, {value});"
            )
