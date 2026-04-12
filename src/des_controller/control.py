import itertools
import pathlib
from typing import Iterable

import des_controller.comm.modbus as modbus
import des_controller.model.des as des
import des_controller.model.dfa as dfa
import des_controller.model.petri as petri


def control_loop(modbus_device_file: pathlib.Path, model_files: Iterable[pathlib.Path]):

    modbus_device = modbus.ModbusDevice.import_device_file(modbus_device_file)
    controllable_events = modbus_device.controllable_events()
    models = [parse_model_file(model_file, controllable_events) for model_file in model_files]
    modbus_client = modbus.DesModbusTcpClient(modbus_device=modbus_device)

    try:
        while True:
            new_events = modbus_client.receive_events()
            for model, event in itertools.product(models, new_events):
                model.update(event)
            enabled_controllable_events = controllable_events.copy()
            for model in models:
                enabled_controllable_events -= model.disabled_controllable_events()
            if len(enabled_controllable_events) > 0:
                control_event = enabled_controllable_events.pop()
                modbus_client.send_event(control_event)
                for model in models:
                    model.update(control_event)
    except KeyboardInterrupt:
        return


def parse_model_file(model_file: pathlib.Path, controllable_events: set[des.Event]) -> des.Controller:
    match model_file.suffix:
        case ".gen":
            return dfa.DFA.import_faudes_file(model_file)
        case ".net":
            return petri.Petri.import_tina_file(model_file, controllable_events=controllable_events)
    raise ValueError(f"invalid model file: {model_file}")
