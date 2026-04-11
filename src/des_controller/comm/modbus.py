"""Modbus client for Discrete Event System (DES)."""

import collections
import enum
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
    address: Address
    action_type: ModbusActionType


class ModbusTriggerType(enum.StrEnum):
    POSITIVE_EDGE = "PositiveEdge"
    NEGATIVE_EDGE = "NegativeEdge"


@dataclass(frozen=True)
class ModbusTrigger:
    address: Address
    trigger_type: ModbusTriggerType


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
    role: ModbusRole
    slave_address: str
    remote_image: ModbusRemoteImage
    event_configuration: ModbusEventConfiguration


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
        for address in self.actions_clear.get(event, []):
            self.state[address] = False
        for address in self.actions_set.get(event, []):
            self.state[address] = False
        self.write_coils(self.write_address, self.state)

    def receive_events(self) -> set[des.Event]:
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
