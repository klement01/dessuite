import itertools
import pathlib
import pprint
from datetime import datetime
from typing import Iterable

import des_controller.comm.modbus as modbus
import des_controller.model.des as des
import des_controller.model.dfa as dfa
import des_controller.model.petri as petri


def control_loop(modbus_device_file: pathlib.Path, model_files: Iterable[pathlib.Path]):

    modbus_device = modbus.ModbusDevice.import_device_file(modbus_device_file)

    slave_address = modbus_device.slave_address
    controllable_events = modbus_device.controllable_events()

    models = [parse_model_file(model_file, controllable_events) for model_file in model_files]
    __display__(f"Loaded ({len(models)}) models:")
    for model in models:
        __display__(f"Model ({model.name}):")
        pprint.pprint(model)

    modbus_client = modbus.DesModbusTcpClient(modbus_device=modbus_device, slave_address=slave_address)
    modbus_client.connect()
    __display__(f"Connected to: {slave_address.host}:{slave_address.port}")

    try:
        while True:
            # Receive events from server.
            new_events = modbus_client.receive_events()
            if new_events:
                __display__(f"Received events: {new_events}")

            # Update models.
            for model, event in itertools.product(models, new_events):
                if model.update(event):
                    __display__(f"Updated ({model.name}) with event ({event})")

            # Get enabled controllable events.
            enabled_controllable_events = controllable_events.copy()
            for model in models:
                enabled_controllable_events -= model.disabled_controllable_events()

            # Send controller event, if applicable.
            if len(enabled_controllable_events) > 0:
                control_event = enabled_controllable_events.pop()
                modbus_client.send_event(control_event)
                __display__(f"Sent event: {control_event}")
                for model in models:
                    if model.update(control_event):
                        __display__(f"Updated ({model.name}) with event ({control_event})")
    except ConnectionAbortedError:
        __display__("Connection closed by server; restart controller")
    except KeyboardInterrupt:
        __display__("Connection closed by user")
        modbus_client.disconnect()


def parse_model_file(model_file: pathlib.Path, controllable_events: set[des.Event]) -> des.Controller:
    match model_file.suffix:
        case ".gen":
            return dfa.DFA.import_faudes_file(model_file)
        case ".net":
            return petri.Petri.import_tina_file(model_file, controllable_events=controllable_events)
    raise ValueError(f"invalid model file: {model_file}")


def __display__(message):
    print(datetime.now(), message, sep="\t")
