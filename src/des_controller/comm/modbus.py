"""Modbus client for Discrete Event System (DES)."""

import collections
import enum
import pathlib
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass

import pymodbus.client

import des_controller.model.des as des

type Address = int


class ModbusRole(enum.StrEnum):
    MASTER = "master"


@dataclass
class ModbusRemoteImage:
    @dataclass
    class ModbusRemoteImageEntry:
        mbaddr: int
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
    event: des.Event
    iotype: ModbusIOType
    actions: list[ModbusAction]
    triggers: list[ModbusTrigger]


type ModbusEventConfiguration = list[ModbusEvent]


@dataclass
class ModbusDevice:
    name: str
    time_scale: int
    sample_interval: int
    synchronous_write: bool
    role: ModbusRole
    slave_address: str
    remote_image: ModbusRemoteImage
    event_configuration: ModbusEventConfiguration

    @staticmethod
    def import_device_file(path: pathlib.Path | str) -> ModbusDevice:
        """Construct an instance of a ModbusDevice from a Modbus Device file (.dev)."""
        # TODO: proper error handling.
        tree = ElementTree.parse(str(path))
        name = tree.getroot().get("name").strip()  # pyright: ignore[reportOptionalMemberAccess]
        slave_address = tree.find("SlaveAddress").text.strip()  # pyright: ignore[reportOptionalMemberAccess]
        time_scale = int(tree.find("TimeScale").text.strip())  # pyright: ignore[reportOptionalMemberAccess]
        sample_interval = int(tree.find("SampleInterval").text.strip())  # pyright: ignore[reportOptionalMemberAccess]
        synchronous_write = {"true": True, "false": False}[tree.find("SynchronousWrite").text.strip()]  # pyright: ignore[reportOptionalMemberAccess]
        role = ModbusRole(tree.find("Role").text.strip())  # pyright: ignore[reportOptionalMemberAccess]
        remote_image = ModbusRemoteImage(
            inputs=ModbusRemoteImage.ModbusRemoteImageEntry(
                mbaddr=int(tree.find("RemoteImage/Inputs").get("@mbaddr").strip()),  # pyright: ignore[reportOptionalMemberAccess]
                count=int(tree.find("RemoteImage/Inputs").get("@count").strip()),  # pyright: ignore[reportOptionalMemberAccess]
            ),
            outputs=ModbusRemoteImage.ModbusRemoteImageEntry(
                mbaddr=int(tree.find("RemoteImage/Outputs").get("@mbaddr").strip()),  # pyright: ignore[reportOptionalMemberAccess]
                count=int(tree.find("RemoteImage/Outputs").get("@count").strip()),  # pyright: ignore[reportOptionalMemberAccess]
            ),
        )

        def parse_modbus_event(element: ElementTree.Element[str]) -> ModbusEvent:
            event = des.Event(element.get("name").strip())  # pyright: ignore[reportOptionalMemberAccess]
            iotype = ModbusIOType(element.get("iotype").strip())  # pyright: ignore[reportOptionalMemberAccess]
            actions = [parse_modbus_action(element) for element in element.findall("Actions/*")]
            triggers = [parse_modbus_trigger(element) for element in element.findall("Triggers/*")]
            return ModbusEvent(event=event, iotype=iotype, actions=actions, triggers=triggers)

        def parse_modbus_action(element: ElementTree.Element[str]) -> ModbusAction:
            action_type = ModbusActionType(element.tag)
            address = int(element.get("address").strip())  # pyright: ignore[reportOptionalMemberAccess]
            return ModbusAction(address=address, action_type=action_type)

        def parse_modbus_trigger(element: ElementTree.Element[str]) -> ModbusTrigger:
            trigger_type = ModbusTriggerType(element.tag)
            address = int(element.get("address").strip())  # pyright: ignore[reportOptionalMemberAccess]
            return ModbusTrigger(address=address, trigger_type=trigger_type)

        event_configuration = [parse_modbus_event(element) for element in tree.findall("EventConfiguration")]

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


class DesModbusTcpClient(pymodbus.client.ModbusTcpClient):
    state: list[bool]

    read_address: Address
    write_address: Address

    actions_set: dict[des.Event, list[Address]]
    actions_clear: dict[des.Event, list[Address]]
    triggers_positive_edge: dict[Address, list[des.Event]]
    triggers_negative_edge: dict[Address, list[des.Event]]

    def __init__(self, modbus_device: ModbusDevice, *args, **kwargs):
        if modbus_device.role != ModbusRole.MASTER:
            raise ValueError("Modbus client must be master")

        super().__init__(host=modbus_device.slave_address, *args, **kwargs)

        # Convert outputs to format more appropriate for real time use.
        actions_set = collections.defaultdict(list)
        actions_clear = collections.defaultdict(list)
        for event in modbus_device.event_configuration:
            if event.iotype != ModbusIOType.OUTPUT:
                continue
            for action in event.actions:
                match action.action_type:
                    case ModbusActionType.SET:
                        actions_set[event.event].append(action.address)
                    case ModbusActionType.CLEAR:
                        actions_clear[event.event].append(action.address)
        self.actions_set = dict(actions_set)
        self.actions_clear = dict(actions_clear)

        # Convert inputs to format more appropriate for real time use.
        triggers_positive_edge = collections.defaultdict(list)
        triggers_negative_edge = collections.defaultdict(list)
        for event in modbus_device.event_configuration:
            if event.iotype != ModbusIOType.INPUT:
                continue
            for trigger in event.triggers:
                match trigger.trigger_type:
                    case ModbusTriggerType.POSITIVE_EDGE:
                        triggers_positive_edge[event.event].append(trigger.address)
                    case ModbusTriggerType.NEGATIVE_EDGE:
                        triggers_negative_edge[event.event].append(trigger.address)
        self.triggers_positive_edge = dict(triggers_positive_edge)
        self.triggers_negative_edge = dict(triggers_negative_edge)

        # Save read/write addresses.
        self.read_address = modbus_device.remote_image.inputs.mbaddr
        self.write_address = modbus_device.remote_image.outputs.mbaddr

        # Get initial state of coils.
        rr = self.read_coils(self.read_address, count=modbus_device.remote_image.inputs.count)
        if rr.isError():
            raise pymodbus.ModbusException("invalid response")

        self.state = rr.bits

    def send_event(self, event: des.Event):
        """Write to coils based on event."""
        for address in self.actions_clear.get(event, []):
            self.state[address] = False
        for address in self.actions_set.get(event, []):
            self.state[address] = False
        self.write_coils(self.write_address, self.state)

    def receive_events(self) -> set[des.Event]:
        """Read coils and translate to events."""
        rr = self.read_coils(self.read_address, count=len(self.state))
        if rr.isError():
            raise pymodbus.ModbusException("invalid response")

        new_state = rr.bits
        events: set[des.Event] = set()
        for address, (old, new) in enumerate(zip(self.state, new_state)):
            if not old and new:
                # Positive edge.
                events.update(self.triggers_positive_edge.get(address, ()))
            elif old and not new:
                # Negative edge.
                events.update(self.triggers_negative_edge.get(address, ()))

        self.state = new_state
        return events
