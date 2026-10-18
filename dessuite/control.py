import datetime
import functools
import itertools
import pathlib
import pprint
import threading
from collections.abc import Iterable
from queue import Queue

from dessuite.comm import modbus
from dessuite.model import des, dfa, petri


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


def time_control_loop(modbus_device_file: pathlib.Path, model_file: pathlib.Path):
    """Load a Modbus device file and a Tina Toolbox net file, and execute a control loop."""

    modbus_device = modbus.ModbusDevice.import_device_file(modbus_device_file)
    show(f"Modbus device ({modbus_device_file.name}):")
    pprint.pprint(modbus_device)

    max_controllable_events = modbus_device.controllable_events()
    show(f"Maximum controllable events: {max_controllable_events}")

    free_net = petri.Petri.import_tina_file(model_file, max_controllable_events=max_controllable_events)
    show(f"Net ({free_net.name}):")
    pprint.pprint(free_net)

    controllable_events = free_net.get_controllable_events()
    show(f"Controllable events: {controllable_events}")

    slave_address = modbus_device.slave_address
    modbus_client = modbus.DesModbusTcpClient(modbus_device=modbus_device, slave_address=slave_address)

    # Thread setup.
    locked_net = Locked(free_net)
    event_notifier = threading.Event()
    incoming_event_queue: Queue[tuple[des.Event, datetime.datetime]] = Queue()
    outgoing_event_queue: Queue[des.Event] = Queue()

    process_incoming_events_thread = threading.Thread(
        target=process_incoming_events,
        args=(locked_net, incoming_event_queue, event_notifier),
        daemon=True,
    )
    modbus_client_read_loop_thread = threading.Thread(
        target=modbus_client_read_loop, args=(modbus_client, incoming_event_queue), daemon=True
    )
    modbus_client_write_loop_thread = threading.Thread(
        target=modbus_client_write_loop, args=(modbus_client, outgoing_event_queue), daemon=True
    )

    try:
        # Startup.
        show(f"Connecting to: {slave_address.host}:{slave_address.port}")
        modbus_client.connect()
        show("Connected!")

        process_incoming_events_thread.start()
        modbus_client_read_loop_thread.start()
        modbus_client_write_loop_thread.start()

        timestamp = datetime.datetime.now()

        with locked_net as net:
            net.start(timestamp)

        # Main event loop.
        while True:
            with locked_net as net:
                event_notifier.clear()
                next_controllable_event = net.get_next_enabled_controllable_event(timestamp)

            event_executor = None
            if next_controllable_event is not None:
                event, new_timestamp = next_controllable_event
                event_executor = threading.Timer(
                    (new_timestamp - datetime.datetime.now()).total_seconds(),
                    function=send_outgoing_event,
                    args=(locked_net, event, outgoing_event_queue, event_notifier),
                )
                event_executor.start()
                show(f"Scheduled event: {event} ({new_timestamp})")

            # Event was received, cancel impending command if applicable restart loop.
            event_notifier.wait()

            if event_executor is not None:
                event_executor.cancel()
                show("Cancelled scheduled event")

            timestamp = datetime.datetime.now()

    except KeyboardInterrupt:
        show("Connection closed by user.")
        modbus_client.disconnect()


def process_incoming_events(
    locked_net: Locked[petri.Petri],
    incoming_event_queue: Queue[tuple[des.Event, datetime.datetime]],
    event_notifier: threading.Event,
):
    """Updates net according to received events."""
    while True:
        event, timestamp = incoming_event_queue.get()
        with locked_net as net:
            updated = net.update(event, timestamp=timestamp)
        if updated:
            event_notifier.set()
            show(f"Received event (2): {event} ({timestamp})")
        else:
            show(f"Dropped incoming event: {event} ({timestamp})")


def send_outgoing_event(
    locked_net: Locked[petri.Petri],
    event: des.Event,
    outgoing_event_queue: Queue[des.Event],
    event_notifier: threading.Event,
):
    """Tries to send a command that was scheduled."""
    timestamp = datetime.datetime.now()
    with locked_net as net:
        updated = net.update(event, timestamp=timestamp)
    if updated:
        outgoing_event_queue.put(event)
        event_notifier.set()
        show(f"Sent event (1): {event} ({timestamp})")
    else:
        show(f"Dropped outgoing event: {event} ({timestamp})")


def modbus_client_read_loop(
    modbus_client: modbus.DesModbusTcpClient, incoming_event_queue: Queue[tuple[des.Event, datetime.datetime]]
):
    """Continuously receive Modbus messages and adds them to event queue."""
    while True:
        new_events = modbus_client.receive_events()
        timestamp = datetime.datetime.now()
        if new_events:
            for event in new_events:
                incoming_event_queue.put((event, timestamp))
            show(f"Received events (1): {new_events} ({timestamp})")


def modbus_client_write_loop(modbus_client: modbus.DesModbusTcpClient, outgoing_event_queue: Queue[des.Event]):
    """Continuously receives outgoing events and writes to to Modbus client."""
    while True:
        event = outgoing_event_queue.get()
        modbus_client.send_event(event)
        show(f"Sent event (2): {event}")


def parse_model_file(model_file: pathlib.Path, max_controllable_events: set[des.Event]) -> des.Controller:
    match model_file.suffix:
        case ".gen":
            return dfa.DFA.import_faudes_file(model_file)
        case ".net":
            return petri.Petri.import_tina_file(model_file, max_controllable_events=max_controllable_events)
    raise ValueError(f"invalid model file: {model_file}")


def show(message):
    print(datetime.datetime.now(), message, sep="\t")


class Locked[T]:
    # Based on: https://stackoverflow.com/a/37606669
    def __init__(self, obj: T):
        super().__init__()
        self.__obj = obj
        self.lock = threading.Lock()

    def __enter__(self) -> T:
        self.lock.acquire()
        return self.__obj

    def __exit__(self, *_, **__):
        self.lock.release()
