import collections

import serial

import dessuite.model.des as des
import dessuite.generator as generator
import dessuite.generator_tools.modules.hal_uart as hal_uart


class DesSerialClient:
    client: serial.Serial

    message_size: int
    incoming_events: dict[int, set[des.Event]]
    outgoing_events: dict[des.Event, list[int]]

    def __init__(self, generator_spec: generator.GeneratorSpec, port: str, baud_rate: int, **kwargs):
        for module in generator_spec.modules.values():
            if isinstance(module, hal_uart.ModuleHalUart):
                hal_uart_module = module
                break
        else:
            raise ValueError("generator spec has no HalUart module")

        self.message_size = hal_uart_module.settings.message_size

        # TODO: multi transmit semantics.
        incoming_events: collections.defaultdict[int, list[des.Event]] = collections.defaultdict(list)
        for event, ns in hal_uart_module.transmit_actions.items():
            for n in ns:
                incoming_events[n].append(event)
        self.incoming_events = {k: set(v) for k, v in incoming_events.items()}

        outgoing_events: collections.defaultdict[des.Event, list[int]] = collections.defaultdict(list)
        for n, event in hal_uart_module.recv_triggers.items():
            outgoing_events[event].append(n)
        self.outgoing_events = dict(outgoing_events)

        self.client = serial.Serial(port=port, baudrate=baud_rate, **kwargs)

    def send_event(self, event: des.Event):
        for n in self.outgoing_events.get(event, []):
            self.client.write(n.to_bytes(self.message_size))

    def receive_events(self) -> set[des.Event]:
        recv = int.from_bytes(self.client.read(self.message_size))
        return self.incoming_events.get(recv, set())
