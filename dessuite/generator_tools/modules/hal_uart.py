from dataclasses import dataclass, field
from xml.etree import ElementTree

from csnake import CodeWriter, Function

from dessuite.generator_tools import core
from dessuite.generator_tools.modules import common
from dessuite.generator_tools.util import key_is_truthy


@dataclass
class ModuleHalUartSettings:
    handle: str | None = None
    message_size: int = 1
    auto_enumerate: bool = False

    @property
    def recv_buffer(self) -> str:
        return f"{self.handle}_recv_buffer"

    @property
    def transmit_buffer(self) -> str:
        return f"{self.handle}_transmit_buffer"

    def update_from_element_tree(self, et: ElementTree.Element[str]):
        if (m := et.find("Handle")) is not None:
            self.handle = m.text
        if (m := et.find("AutoEnumerate")) is not None:
            self.auto_enumerate = key_is_truthy(m.text, default=True)


@dataclass
class ModuleHalUart(common.GeneratorModule):
    settings: ModuleHalUartSettings = field(default_factory=ModuleHalUartSettings)

    event_auto_enumerate_counter: int = 0
    recv_triggers: dict[int, core.CoreEvent] = field(default_factory=dict)
    transmit_actions: dict[core.CoreEvent, list[int]] = field(default_factory=dict)

    def name(self):
        return "HAL UART"

    def parse_settings_from_element_tree(self, et: ElementTree.Element[str]):
        self.settings.update_from_element_tree(et)

    def register_trigger(self, core_event: core.CoreEvent, et: ElementTree.Element[str]):
        for m in et.iterfind("Receive"):
            if self.settings.auto_enumerate:
                idx = self.event_auto_enumerate_counter
                self.event_auto_enumerate_counter += 1
            else:
                if m.text is None:
                    raise ValueError("missing receive value")
                try:
                    idx = int(m.text)
                except ValueError:
                    raise ValueError(f"invalid receive value: {m.text}")

            self.recv_triggers[idx] = core_event

    def register_action(self, core_event: core.CoreEvent, et: ElementTree.Element[str]):
        event_actions = []
        for m in et.iterfind("Transmit"):
            if self.settings.auto_enumerate:
                idx = self.event_auto_enumerate_counter
                self.event_auto_enumerate_counter += 1
            else:
                if m.text is None:
                    raise ValueError("missing transmit value")
                try:
                    idx = int(m.text)
                except ValueError:
                    raise ValueError(f"invalid transmit value: {m.text}")

            event_actions.append(idx)
        if event_actions:
            self.transmit_actions[core_event] = event_actions

    def write_variables(self, writer: CodeWriter):
        writer.add_line(f"extern UART_HandleTypeDef {self.settings.handle};")
        writer.add_line(f"uint8_t {self.settings.recv_buffer};")
        writer.add_line(f"uint8_t {self.settings.transmit_buffer};")

    def write_init(self, writer: CodeWriter):
        writer.add_line(
            f"HAL_UART_Receive_IT(&{self.settings.handle}, &{self.settings.recv_buffer}, sizeof({self.settings.recv_buffer}));"
        )

    def write_triggers(self, writer: CodeWriter):
        if len(self.recv_triggers) == 0:
            return

        # Function declaration.
        writer.add_line("void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)")
        writer.open_brace()

        writer.add_line("TraceInterruptStart();")
        writer.add_line("const TickType_t tick = xTaskGetTickCountFromISR();")
        writer.add_line("BaseType_t xHigherPriorityTaskWoken = pdFALSE;")
        writer.add_line(f"configASSERT(huart == &{self.settings.handle});")
        writer.add_line(f"switch ({self.settings.recv_buffer})")
        writer.open_brace()

        for value, core_event in self.recv_triggers.items():
            writer.add_line(f"case {value}:")
            writer.indent()
            writer.add_line(f"QueueNewIncomingEventFromISR({core_event.event_name}, tick, &xHigherPriorityTaskWoken);")
            writer.add_switch_break()

        writer.close_brace()
        writer.add_line(
            f"HAL_UART_Receive_IT(&{self.settings.handle}, &{self.settings.recv_buffer}, sizeof({self.settings.recv_buffer}));"
        )
        writer.add_line("TraceInterruptEnd();")
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
