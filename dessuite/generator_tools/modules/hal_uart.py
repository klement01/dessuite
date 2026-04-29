import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field

from csnake import CodeWriter, Function

import dessuite.generator_tools.core as core
from dessuite.generator_tools.util import key_is_truthy
import dessuite.generator_tools.modules.common as common


@dataclass
class ModuleHalUartSettings:
    auto_enumerate: bool = True
    handle: str | None = None
    message_size: int = 1

    @property
    def recv_buffer(self) -> str:
        return f"{self.handle}_recv_buffer"

    @property
    def transmit_buffer(self) -> str:
        return f"{self.handle}_transmit_buffer"

    def update_from_element_tree(self, et: ElementTree.Element[str]):
        if (m := et.find("AutoEnumerate")) is not None:
            self.auto_enumerate = key_is_truthy(m.text)
        if (m := et.find("Handle")) is not None:
            self.handle = m.text
        if (m := et.find("MessageSize")) is not None:
            self.message_size = int(m.text)  # pyright: ignore[reportArgumentType]

        if not self.auto_enumerate:
            raise ValueError("hal_uart: AutoEnumerate=False is not supported yet")
        if self.message_size != 1:
            raise ValueError("hal_uart: MessageSize!=1 is not supported yet")


@dataclass
class ModuleHalUart(common.GeneratorModule):
    settings: ModuleHalUartSettings = field(default_factory=ModuleHalUartSettings)

    event_index_acc: int = 0
    recv_triggers: dict[int, core.CoreEvent] = field(default_factory=dict)
    transmit_actions: dict[core.CoreEvent, list[int]] = field(default_factory=dict)

    def update_settings_from_element_tree(self, et: ElementTree.Element[str]):
        self.settings.update_from_element_tree(et)

    def add_trigger(self, core_event: core.CoreEvent, et: ElementTree.Element[str]):
        for _ in et.iterfind("Receive"):
            self.recv_triggers[self.event_index_acc] = core_event
            self.event_index_acc += 1

    def add_action(self, core_event: core.CoreEvent, et: ElementTree.Element[str]):
        event_actions = []
        for _ in et.iterfind("Transmit"):
            event_actions.append(self.event_index_acc)
            self.event_index_acc += 1
        if event_actions:
            self.transmit_actions[core_event] = event_actions

    def write_variables(self, writer: CodeWriter):
        writer.add_line(f"extern UART_HandleTypeDef {self.settings.handle};")
        writer.add_line(f"uint8_t {self.settings.recv_buffer};")
        writer.add_line(f"uint8_t {self.settings.transmit_buffer};")

    def write_init_function_calls(self, writer: CodeWriter):
        writer.add_line(
            f"HAL_UART_Receive_IT(&{self.settings.handle}, &{self.settings.recv_buffer}, sizeof({self.settings.recv_buffer}));"
        )

    def write_input_interface_functions(self, writer: CodeWriter):
        if len(self.recv_triggers) == 0:
            return

        # Function declaration.
        writer.add_line("void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)")
        writer.open_brace()

        writer.add_line("BaseType_t xHigherPriorityTaskWoken = pdFALSE;")
        writer.add_line("EventIdx_t eventIdx;")
        writer.add_line(f"switch ({self.settings.recv_buffer})")
        writer.open_brace()

        for value, core_event in self.recv_triggers.items():
            writer.add_line(f"case {value}:")
            writer.indent()
            writer.add_line(f"eventIdx = {core_event.event_name};")
            writer.add_line("xQueueSendToBackFromISR(PendingEventsQueue, &eventIdx, &xHigherPriorityTaskWoken);")
            writer.add_switch_break()

        writer.close_brace()
        writer.add_line(
            f"HAL_UART_Receive_IT(&{self.settings.handle}, &{self.settings.recv_buffer}, sizeof({self.settings.recv_buffer}));"
        )
        writer.add_line("portYIELD_FROM_ISR(xHigherPriorityTaskWoken);")

        writer.close_brace()

    def write_actions(self, core_event: core.CoreEvent, function: Function):
        if core_event not in self.transmit_actions:
            return

        for value in self.transmit_actions[core_event]:
            function.add_code(f"{self.settings.transmit_buffer} = {value};")
            function.add_code(
                f"HAL_UART_Transmit_IT(&{self.settings.handle}, &{self.settings.transmit_buffer}, sizeof({self.settings.transmit_buffer}));;"
            )
