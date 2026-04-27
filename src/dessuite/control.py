import functools
import itertools
import pathlib
import pprint
from datetime import datetime
from typing import Iterable

import dessuite.comm.modbus as modbus
import dessuite.model.des as des
import dessuite.model.dfa as dfa
import dessuite.model.petri as petri


def control_loop(modbus_device_file: pathlib.Path, model_files: Iterable[pathlib.Path]):
    """Load a Modbus device file and a sequence of model files, and execute a control loop."""

    modbus_device = modbus.ModbusDevice.import_device_file(modbus_device_file)
    show(f"Modbus device ({modbus_device_file.name}):")
    pprint.pprint(modbus_device)

    max_controllable_events = modbus_device.controllable_events()
    show(f"Maximum controllable events: {max_controllable_events}")

    models = [parse_model_file(model_file, max_controllable_events) for model_file in model_files]
    for model in models:
        show(f"Model ({model.name}):")
        pprint.pprint(model)
    show(f"Loaded ({len(models)}) models:")

    controllable_events = functools.reduce(set.union, (model.get_controllable_events() for model in models))
    if not controllable_events.issubset(max_controllable_events):
        raise ValueError("incompatible device file and model files")
    show(f"Controllable events: {controllable_events}")

    slave_address = modbus_device.slave_address
    modbus_client = modbus.DesModbusTcpClient(modbus_device=modbus_device, slave_address=slave_address)

    try:
        show(f"Connecting to: {slave_address.host}:{slave_address.port}")
        modbus_client.connect()
        show("Connected!")

        while True:
            # Receive events from server.
            new_events = modbus_client.receive_events()
            if new_events:
                show(f"Received events: {new_events}")

            # Update models.
            for model, event in itertools.product(models, new_events):
                if model.update(event):
                    show(f"Updated model ({model.name}) with event ({event})")

            # Get enabled controllable events.
            enabled_controllable_events = controllable_events.copy()
            for model in models:
                enabled_controllable_events -= model.get_disabled_controllable_events()

            # Send controller event, if applicable.
            if len(enabled_controllable_events) > 0:
                control_event = enabled_controllable_events.pop()
                modbus_client.send_event(control_event)
                show(f"Sent event: {control_event}")
                for model in models:
                    if model.update(control_event):
                        show(f"Updated model ({model.name}) with event ({control_event})")

    except ConnectionAbortedError:
        show("Connection closed by server; restart controller.")

    except KeyboardInterrupt:
        show("Connection closed by user.")
        modbus_client.disconnect()


def parse_model_file(model_file: pathlib.Path, max_controllable_events: set[des.Event]) -> des.Controller:
    match model_file.suffix:
        case ".gen":
            return dfa.DFA.import_faudes_file(model_file)
        case ".net":
            return petri.Petri.import_tina_file(model_file, max_controllable_events=max_controllable_events)
    raise ValueError(f"invalid model file: {model_file}")


def show(message):
    print(datetime.now(), message, sep="\t")
