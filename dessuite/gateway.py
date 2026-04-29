import threading
from datetime import datetime
from pathlib import Path

import dessuite.comm.serial as serial
import dessuite.comm.modbus as modbus
import dessuite.model.petri as petri
import dessuite.generator as generator


def gateway(model_file: Path, modbus_device_file: Path, spec_file: Path, port: str, baud_rate: int):
    # Load generator configs.
    net = petri.Petri.import_tina_file(model_file)
    generator_spec = generator.GeneratorSpec.initialize_from_net(net)
    generator_spec.import_dessuite_file(spec_file)

    # Start serial.
    show(f"(Serial) Connecting to port: {port}")
    serial_client = serial.DesSerialClient(generator_spec=generator_spec, port=port, baud_rate=baud_rate)
    show("(Serial) Connected!")

    # Start Modbus.
    modbus_device = modbus.ModbusDevice.import_device_file(modbus_device_file)
    slave_address = modbus_device.slave_address
    modbus_client = modbus.DesModbusTcpClient(modbus_device=modbus_device, slave_address=slave_address)

    try:
        show(f"(Modbus) Connecting to slave address: {slave_address.host}:{slave_address.port}")
        modbus_client.connect()
        show("(Modbus) Connected!")

        threading.Thread(target=gateway_modbus_to_serial, args=(modbus_client, serial_client)).start()
        gateway_serial_to_modbus(modbus_client, serial_client)

    except ConnectionAbortedError:
        show("Connection closed by server; restart controller.")

    except KeyboardInterrupt:
        show("Connection closed by user.")
        modbus_client.disconnect()


def gateway_modbus_to_serial(modbus_client: modbus.DesModbusTcpClient, serial_client: serial.DesSerialClient):
    new_events = modbus_client.receive_events()
    if new_events:
        show(f"(Modbus) Received events: {new_events}")
    for event in new_events:
        serial_client.send_event(event)
        show(f"(Serial) Sent event: {event}")


def gateway_serial_to_modbus(modbus_client: modbus.DesModbusTcpClient, serial_client: serial.DesSerialClient):
    new_events = serial_client.receive_events()
    if new_events:
        show(f"(Serial) Received events: {new_events}")
    for event in new_events:
        modbus_client.send_event(event)
        show(f"(Modbus) Sent event: {event}")


def show(message):
    print(datetime.now(), message, sep="\t")
