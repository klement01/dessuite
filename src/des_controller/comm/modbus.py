"""Modbus client for Discrete Event System (DES)."""

import collections
import enum
import pathlib
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from typing import Iterator

import pymodbus.client

import des_controller.model.des as des

type Address = int


class ModbusRole(enum.StrEnum):
    MASTER = "master"


@dataclass
class SlaveAddress:
    host: str
    port: int

    @staticmethod
    def parse_str(host_str: str, default_port: int = 1502) -> SlaveAddress:
        host, *port_maybe = host_str.split(":", 1)
        port = int(port_maybe[0]) if port_maybe else default_port
        return SlaveAddress(host=host, port=port)


@dataclass
class ModbusRemoteImage:
    @dataclass
    class ModbusRemoteImageEntry:
        mbaddr: Address
        count: int

    inputs: ModbusRemoteImageEntry
    outputs: ModbusRemoteImageEntry


class ModbusActionType(enum.StrEnum):
    SET = "Set"
    CLEAR = "Clr"


@dataclass(frozen=True)
class ModbusAction:
    action_type: ModbusActionType
    address: Address


class ModbusTriggerType(enum.StrEnum):
    POSITIVE_EDGE = "PositiveEdge"
    NEGATIVE_EDGE = "NegativeEdge"


@dataclass(frozen=True)
class ModbusTrigger:
    trigger_type: ModbusTriggerType
    address: Address


class ModbusIOType(enum.StrEnum):
    OUTPUT = "output"
    INPUT = "input"


@dataclass
class ModbusEvent:
    des_event: des.Event
    iotype: ModbusIOType
    actions: list[ModbusAction]
    triggers: list[ModbusTrigger]

    def set_actions(self) -> Iterator[ModbusAction]:
        return (action for action in self.actions if action.action_type == ModbusActionType.SET)

    def clear_actions(self) -> Iterator[ModbusAction]:
        return (action for action in self.actions if action.action_type == ModbusActionType.CLEAR)

    def positive_edge_triggers(self) -> Iterator[ModbusTrigger]:
        return (trigger for trigger in self.triggers if trigger.trigger_type == ModbusTriggerType.POSITIVE_EDGE)

    def negative_edge_triggers(self) -> Iterator[ModbusTrigger]:
        return (trigger for trigger in self.triggers if trigger.trigger_type == ModbusTriggerType.NEGATIVE_EDGE)


type ModbusEventConfiguration = list[ModbusEvent]


@dataclass
class ModbusDevice:
    name: str
    time_scale: int
    sample_interval: int
    synchronous_write: bool
    role: ModbusRole
    slave_address: SlaveAddress
    remote_image: ModbusRemoteImage
    event_configuration: ModbusEventConfiguration

    def output_modbus_events(self) -> Iterator[ModbusEvent]:
        return (event for event in self.event_configuration if event.iotype == ModbusIOType.OUTPUT)

    def input_modbus_events(self) -> Iterator[ModbusEvent]:
        return (event for event in self.event_configuration if event.iotype == ModbusIOType.INPUT)

    def controllable_events(self) -> set[des.Event]:
        return set((event.des_event for event in self.output_modbus_events()))

    @staticmethod
    def import_device_file(path: pathlib.Path | str) -> ModbusDevice:
        """Construct an instance of a ModbusDevice from a Modbus Device file (.dev)."""
        # TODO: proper error handling.
        tree = ElementTree.parse(str(path))
        name = str(tree.getroot().get("name"))  # pyright: ignore[reportOptionalMemberAccess]
        time_scale = int(tree.find("TimeScale").get("value").strip())  # pyright: ignore[reportOptionalMemberAccess]
        sample_interval = int(tree.find("SampleInterval").get("value").strip())  # pyright: ignore[reportOptionalMemberAccess]
        synchronous_write = {"true": True, "false": False}[tree.find("SynchronousWrite").get("value").strip()]  # pyright: ignore[reportOptionalMemberAccess]
        role = ModbusRole(tree.find("Role").get("value").strip())  # pyright: ignore[reportOptionalMemberAccess]
        slave_address = SlaveAddress.parse_str(tree.find("SlaveAddress").get("value").strip())  # pyright: ignore[reportOptionalMemberAccess]
        remote_image = ModbusRemoteImage(
            inputs=ModbusRemoteImage.ModbusRemoteImageEntry(
                mbaddr=int(tree.find("RemoteImage/Inputs").get("mbaddr").strip()),  # pyright: ignore[reportOptionalMemberAccess]
                count=int(tree.find("RemoteImage/Inputs").get("count").strip()),  # pyright: ignore[reportOptionalMemberAccess]
            ),
            outputs=ModbusRemoteImage.ModbusRemoteImageEntry(
                mbaddr=int(tree.find("RemoteImage/Outputs").get("mbaddr").strip()),  # pyright: ignore[reportOptionalMemberAccess]
                count=int(tree.find("RemoteImage/Outputs").get("count").strip()),  # pyright: ignore[reportOptionalMemberAccess]
            ),
        )

        def parse_modbus_event(element: ElementTree.Element[str]) -> ModbusEvent:
            event = des.Event(element.get("name").strip())  # pyright: ignore[reportOptionalMemberAccess]
            iotype = ModbusIOType(element.get("iotype").strip())  # pyright: ignore[reportOptionalMemberAccess]
            match iotype:
                case ModbusIOType.OUTPUT:
                    actions = [parse_modbus_action(element) for element in element.findall("Actions/*")]
                    triggers = []
                case ModbusIOType.INPUT:
                    actions = []
                    triggers = [parse_modbus_trigger(element) for element in element.findall("Triggers/*")]
            return ModbusEvent(des_event=event, iotype=iotype, actions=actions, triggers=triggers)

        def parse_modbus_action(element: ElementTree.Element[str]) -> ModbusAction:
            action_type = ModbusActionType(element.tag)
            address = int(element.get("address").strip())  # pyright: ignore[reportOptionalMemberAccess]
            return ModbusAction(address=address, action_type=action_type)

        def parse_modbus_trigger(element: ElementTree.Element[str]) -> ModbusTrigger:
            trigger_type = ModbusTriggerType(element.tag)
            address = int(element.get("address").strip())  # pyright: ignore[reportOptionalMemberAccess]
            return ModbusTrigger(address=address, trigger_type=trigger_type)

        event_configuration = [parse_modbus_event(element) for element in tree.findall("EventConfiguration/Event")]

        return ModbusDevice(
            name=name,
            time_scale=time_scale,
            sample_interval=sample_interval,
            synchronous_write=synchronous_write,
            role=role,
            slave_address=slave_address,
            remote_image=remote_image,
            event_configuration=event_configuration,
        )


class DesModbusTcpClient:
    client: pymodbus.client.ModbusTcpClient

    type State = list[bool]
    state: State | None = None

    remote_image: ModbusRemoteImage

    actions_set: dict[des.Event, list[Address]]
    actions_clear: dict[des.Event, list[Address]]
    triggers_positive_edge: dict[Address, list[des.Event]]
    triggers_negative_edge: dict[Address, list[des.Event]]

    def __init__(self, modbus_device: ModbusDevice, *args, slave_address: SlaveAddress | None = None, **kwargs):
        # Create the underlying client.
        if slave_address is None:
            slave_address = modbus_device.slave_address
        self.client = pymodbus.client.ModbusTcpClient(host=slave_address.host, *args, port=slave_address.port, **kwargs)

        self.remote_image = modbus_device.remote_image

        # Convert outputs to format more appropriate for real time use.
        self.actions_set = {
            modbus_event.des_event: [action.address for action in modbus_event.set_actions()]
            for modbus_event in modbus_device.output_modbus_events()
        }
        self.actions_clear = {
            modbus_event.des_event: [action.address for action in modbus_event.clear_actions()]
            for modbus_event in modbus_device.output_modbus_events()
        }

        # Convert inputs to format more appropriate for real time use.
        triggers_positive_edge: dict[Address, list[des.Event]] = collections.defaultdict(list)
        triggers_negative_edge: dict[Address, list[des.Event]] = collections.defaultdict(list)
        for modbus_event in modbus_device.input_modbus_events():
            for trigger in modbus_event.positive_edge_triggers():
                triggers_positive_edge[trigger.address].append(modbus_event.des_event)
            for trigger in modbus_event.negative_edge_triggers():
                triggers_negative_edge[trigger.address].append(modbus_event.des_event)
        self.triggers_positive_edge = dict(triggers_positive_edge)
        self.triggers_negative_edge = dict(triggers_negative_edge)

    def connect(self):
        if not self.client.connect():
            raise pymodbus.ModbusException("failed to connect")
        self.state = self.read_state()

    def disconnect(self):
        self.client.close()

    def read_state(self) -> State:
        rr = self.client.read_coils(self.remote_image.inputs.mbaddr, count=self.remote_image.inputs.count)
        if rr.isError():
            raise pymodbus.ModbusException("invalid response")
        return rr.bits[: self.remote_image.inputs.count]

    def send_event(self, event: des.Event):
        """Write to coils based on event."""
        assert self.state is not None, "Modbus client not started"

        base_address = self.remote_image.outputs.mbaddr
        for address in self.actions_clear.get(event, []):
            self.state[address - base_address] = False
        for address in self.actions_set.get(event, []):
            self.state[address - base_address] = False
        self.client.write_coils(self.remote_image.outputs.mbaddr, self.state)

    def receive_events(self) -> set[des.Event]:
        """Read coils and translate to events."""
        assert self.state is not None, "Modbus client not started"

        new_state = self.read_state()
        events: set[des.Event] = set()
        for address_offset, (old, new) in enumerate(zip(self.state, new_state)):
            address: Address = self.remote_image.inputs.mbaddr + address_offset + 1
            if not old and new:
                events.update(self.triggers_positive_edge.get(address, ()))
            elif old and not new:
                events.update(self.triggers_negative_edge.get(address, ()))
        self.state = new_state
        return events
