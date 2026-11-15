import collections
import dataclasses
import datetime
import enum
import statistics
import string
from pathlib import Path
from typing import Final

from dessuite import generator
from dessuite.model import des, petri


class TaskNumber(enum.IntEnum):
    OTHER = 0
    EVENT_LOOP = 1
    TIMER = 2
    TRACE_LOOP = 3


class TraceType(enum.IntEnum):
    TICK_RATE = enum.auto()
    NET_START_TICK = enum.auto()
    INCOMING_EVENT_RECEIVED = enum.auto()
    INCOMING_EVENT_ACCEPTED = enum.auto()
    INCOMING_EVENT_DROPPED_STRUCTURALLY = enum.auto()
    INCOMING_EVENT_DROPPED_TOO_SOON = enum.auto()
    INCOMING_EVENT_DROPPED_TOO_LATE = enum.auto()
    OUTGOING_COMMAND_ACCEPTED = enum.auto()
    OUTGOING_COMMAND_DROPPED_STRUCTURALLY = enum.auto()
    OUTGOING_COMMAND_DROPPED_TOO_SOON = enum.auto()
    OUTGOING_COMMAND_DROPPED_TOO_LATE = enum.auto()
    OUTGOING_COMMAND_DROPPED = enum.auto()
    OUTGOING_COMMAND_QUEUED = enum.auto()
    OUTGOING_COMMAND_STARTED = enum.auto()
    OUTGOING_COMMAND_FINISHED = enum.auto()
    COMMAND_NOT_CHOSEN_TOO_LATE = enum.auto()
    TASK_SWITCHED_IN = enum.auto()
    TASK_SWITCHED_OUT = enum.auto()
    INTERRUPT_START = enum.auto()
    INTERRUPT_END = enum.auto()


@dataclasses.dataclass(frozen=True)
class TraceMessageRaw:
    index: int
    tick: int
    type: TraceType
    data: tuple[int, ...]


@dataclasses.dataclass(frozen=True)
class TraceMessage:
    index: int
    timestamp: datetime.timedelta
    type: TraceType


@dataclasses.dataclass(frozen=True)
class TraceMessageTickRate(TraceMessage):
    event_tick_scale: datetime.timedelta
    trace_tick_scale: datetime.timedelta


@dataclasses.dataclass(frozen=True)
class TraceMessageNetStart(TraceMessage):
    net_start_timestamp: datetime.timedelta


@dataclasses.dataclass(frozen=True)
class TraceMessageEvent(TraceMessage):
    event: des.Event
    event_timestamp: datetime.timedelta


@dataclasses.dataclass(frozen=True)
class TraceMessageTaskScheduler(TraceMessage):
    task_number: TaskNumber


@dataclasses.dataclass(frozen=True)
class TraceMessageInterrupt(TraceMessage):
    pass


@dataclasses.dataclass(frozen=True)
class TraceCollection:
    trace_message_tick_rate: TraceMessageTickRate
    trace_message_net_start: TraceMessageNetStart
    trace_messages_event: list[TraceMessageEvent]
    trace_messages_task_scheduler: list[TraceMessageTaskScheduler]
    trace_messages_interrupt: list[TraceMessageInterrupt]

    @staticmethod
    def import_trace_file(trace_file: Path, *, generator_spec: generator.GeneratorSpec) -> TraceCollection:
        # Parse all trace messages.
        trace_messages_raw: list[TraceMessageRaw] = []
        with trace_file.open(mode="r", encoding="utf-8") as f:
            for line_index, line in enumerate(f):
                try:
                    columns = (int(i) for i in line.split())
                    trace_index, trace_tick, trace_type_raw, *trace_data = columns
                    trace_type = TraceType(trace_type_raw)
                except ValueError:
                    raise ValueError(f"invalid line: {line}") from None

                if trace_index != line_index:
                    raise ValueError(f"wrong trace index; expected ({line_index}), got: {trace_index}")

                trace_messages_raw.append(
                    TraceMessageRaw(index=trace_index, tick=trace_tick, type=trace_type, data=tuple(trace_data))
                )

        # Process tick rate message.
        tick_rate_message_candidates_raw = [m for m in trace_messages_raw if m.type == TraceType.TICK_RATE]
        if len(tick_rate_message_candidates_raw) == 0:
            raise ValueError("no tick rate trace found")
        elif len(tick_rate_message_candidates_raw) > 1:
            raise ValueError("multiple tick rate traces found")
        try:
            tick_rate_message_raw = tick_rate_message_candidates_raw[0]
            event_tick_rate, trace_tick_rate = tick_rate_message_raw.data
            event_tick_scale = datetime.timedelta(seconds=1) / event_tick_rate
            trace_tick_scale = datetime.timedelta(seconds=1) / trace_tick_rate

            trace_message_tick_rate = TraceMessageTickRate(
                index=tick_rate_message_raw.index,
                timestamp=tick_rate_message_raw.tick * trace_tick_scale,
                type=tick_rate_message_raw.type,
                event_tick_scale=event_tick_scale,
                trace_tick_scale=trace_tick_scale,
            )
        except IndexError, ValueError, ZeroDivisionError:
            raise ValueError("invalid tick rate message") from None

        # Process remaining messages.
        trace_message_net_start: TraceMessageNetStart | None = None
        trace_messages_event: list[TraceMessageEvent] = []
        trace_messages_task_scheduler: list[TraceMessageTaskScheduler] = []
        trace_messages_interrupt: list[TraceMessageInterrupt] = []

        for message_raw in trace_messages_raw:
            message_timestamp = message_raw.tick * trace_message_tick_rate.trace_tick_scale

            match message_raw.type:
                case TraceType.TICK_RATE:
                    pass
                case TraceType.NET_START_TICK:
                    if trace_message_net_start is not None:
                        raise ValueError("multiple net start tick traces found")

                    try:
                        net_start_tick = message_raw.data[0]
                        trace_message_net_start = TraceMessageNetStart(
                            index=message_raw.index,
                            timestamp=message_timestamp,
                            type=message_raw.type,
                            net_start_timestamp=net_start_tick * trace_message_tick_rate.event_tick_scale,
                        )
                    except IndexError, ValueError:
                        raise ValueError(f"invalid net start message at line {message_raw.index}") from None
                case (
                    TraceType.INCOMING_EVENT_RECEIVED
                    | TraceType.INCOMING_EVENT_ACCEPTED
                    | TraceType.INCOMING_EVENT_DROPPED_STRUCTURALLY
                    | TraceType.INCOMING_EVENT_DROPPED_TOO_SOON
                    | TraceType.INCOMING_EVENT_DROPPED_TOO_LATE
                    | TraceType.OUTGOING_COMMAND_ACCEPTED
                    | TraceType.OUTGOING_COMMAND_DROPPED_STRUCTURALLY
                    | TraceType.OUTGOING_COMMAND_DROPPED_TOO_SOON
                    | TraceType.OUTGOING_COMMAND_DROPPED_TOO_LATE
                    | TraceType.OUTGOING_COMMAND_DROPPED
                    | TraceType.OUTGOING_COMMAND_QUEUED
                    | TraceType.OUTGOING_COMMAND_STARTED
                    | TraceType.OUTGOING_COMMAND_FINISHED
                    | TraceType.COMMAND_NOT_CHOSEN_TOO_LATE
                ):
                    try:
                        event_tick, event_idx = message_raw.data
                        trace_messages_event.append(
                            TraceMessageEvent(
                                index=message_raw.index,
                                timestamp=message_timestamp,
                                type=message_raw.type,
                                event=generator_spec.ordered_events[event_idx].event,
                                event_timestamp=event_tick * trace_message_tick_rate.event_tick_scale,
                            )
                        )
                    except IndexError, ValueError:
                        raise ValueError(f"invalid event message at line {message_raw.index}")
                case TraceType.TASK_SWITCHED_IN | TraceType.TASK_SWITCHED_OUT:
                    try:
                        task_number_raw = message_raw.data[0]
                        if task_number_raw in TaskNumber:
                            task_number = TaskNumber(task_number_raw)
                        else:
                            task_number = TaskNumber.OTHER
                        trace_messages_task_scheduler.append(
                            TraceMessageTaskScheduler(
                                index=message_raw.index,
                                timestamp=message_timestamp,
                                type=message_raw.type,
                                task_number=task_number,
                            )
                        )
                    except IndexError, ValueError:
                        raise ValueError(f"invalid task scheduler message at line {message_raw.index}")
                case TraceType.INTERRUPT_START | TraceType.INTERRUPT_END:
                    trace_messages_interrupt.append(
                        TraceMessageInterrupt(
                            index=message_raw.index,
                            timestamp=message_timestamp,
                            type=message_raw.type,
                        )
                    )
                case _:
                    raise ValueError(f"unexpected trace type: {message_raw.type}")

        if trace_message_net_start is None:
            raise ValueError("no net start tick trace found")

        return TraceCollection(
            trace_message_tick_rate=trace_message_tick_rate,
            trace_message_net_start=trace_message_net_start,
            trace_messages_event=trace_messages_event,
            trace_messages_task_scheduler=trace_messages_task_scheduler,
            trace_messages_interrupt=trace_messages_interrupt,
        )


EVENT_NAME_ALLOWED: Final = set(string.ascii_letters + string.digits + "_\u2019")
EVENT_NAME_TRANS_TABLE: Final = str.maketrans({"{": r"\{", "}": r"\}", "\\": r"\\"})


def escape_event_name(event_name: str) -> str:
    if all(c in EVENT_NAME_ALLOWED for c in event_name):
        return event_name

    return f"{{{event_name.translate(EVENT_NAME_TRANS_TABLE)}}}"


def get_task_timings(task_traces: list[TraceMessageTaskScheduler], task_number: TaskNumber) -> list[datetime.timedelta]:
    task_timings: list[datetime.timedelta] = []
    start: datetime.timedelta | None = None
    for task_trace in task_traces:
        if task_trace.task_number != task_number:
            continue
        if task_trace.type == TraceType.TASK_SWITCHED_IN:
            start = task_trace.timestamp
        elif task_trace.type == TraceType.TASK_SWITCHED_OUT and start:
            task_timings.append(task_trace.timestamp - start)
            start = None
    return task_timings


def get_stat_strings(timings: list[datetime.timedelta]) -> list[str]:
    timings_float = [t.total_seconds() * 1000 for t in timings]
    return [
        f"count: {len(timings_float)}\n",
        f"avg [ms]: {statistics.mean(timings_float):.02f}\n",
        f"stddev [ms]: {statistics.stdev(timings_float):.02f}\n",
        f"median [ms]: {statistics.median(timings_float):.02f}\n",
        f"max [ms]: {max(timings_float):.02f}\n",
    ]


def generate_runtime_stats(trace_file: Path, model_file: Path, out_scenario_file: Path, out_stats_file: Path):
    net = petri.Petri.import_tina_file(model_file)
    generator_spec = generator.GeneratorSpec.initialize_from_net(net)
    trace_collection = TraceCollection.import_trace_file(trace_file, generator_spec=generator_spec)

    ACCEPTED_EVENTS: Final = [
        event_trace
        for event_trace in trace_collection.trace_messages_event
        if event_trace.type in (TraceType.INCOMING_EVENT_ACCEPTED, TraceType.OUTGOING_COMMAND_ACCEPTED)
    ]

    # Event history.
    with out_scenario_file.open(mode="w", encoding="utf-8") as f:
        timer = trace_collection.trace_message_net_start.net_start_timestamp

        for event_trace in ACCEPTED_EVENTS:
            delay = event_trace.event_timestamp - timer
            timer = event_trace.event_timestamp

            f.write(f"{escape_event_name(str(event_trace.event.id))}@{delay.total_seconds() * 1000:.2f}\n")

    # Runtime statistics.

    with out_stats_file.open(mode="w", encoding="utf-8") as f:
        # Event loop execution stats.
        f.write("event loop stats:\n")
        f.write("=" * 40 + "\n")
        f.writelines(
            get_stat_strings(get_task_timings(trace_collection.trace_messages_task_scheduler, TaskNumber.EVENT_LOOP))
        )

        f.write("\n\n")

        # Timer execution stats.
        f.write("timer stats:\n")
        f.write("=" * 40 + "\n")
        f.writelines(
            get_stat_strings(get_task_timings(trace_collection.trace_messages_task_scheduler, TaskNumber.TIMER))
        )

        f.write("\n\n")

        # Trace loop execution stats.
        f.write("trace loop stats:\n")
        f.write("=" * 40 + "\n")
        f.writelines(
            get_stat_strings(get_task_timings(trace_collection.trace_messages_task_scheduler, TaskNumber.TRACE_LOOP))
        )

        f.write("\n\n")

        # Interrupt execution stats.
        interrupt_timings: list[datetime.timedelta] = []
        interrupt_starts: list[datetime.timedelta] = []
        for interrupt_trace in trace_collection.trace_messages_interrupt:
            if interrupt_trace.type == TraceType.INTERRUPT_START:
                interrupt_starts.append(interrupt_trace.timestamp)
            elif interrupt_trace.type == TraceType.INTERRUPT_END and interrupt_starts:
                interrupt_timings.append(interrupt_trace.timestamp - interrupt_starts.pop())

        f.write("interrupt stats:\n")
        f.write("=" * 40 + "\n")
        f.writelines(get_stat_strings(interrupt_timings))

        f.write("\n\n")

        # Event intervals (beta).
        event_timings_beta = {
            event: transition.interval.upper.value.total_seconds() * 1000 if transition.interval.upper else float("inf")
            for event, transition in net.transitions.items()
        }

        f.write("event intervals (beta) [ms]:\n")
        f.write("=" * 40 + "\n")

        for event, timing in sorted(event_timings_beta.items(), key=lambda i: i[-1]):
            f.write(f"{escape_event_name(str(event.id))}: {timing:.2f}\n")

        f.write("\n\n")

        # Event intervals (beta - alpha).
        event_timings_delta = {
            event: (transition.interval.upper.value - transition.interval.lower.value).total_seconds() * 1000
            if transition.interval.upper
            else float("inf")
            for event, transition in net.transitions.items()
        }

        f.write("event intervals (beta - alpha) [ms]:\n")
        f.write("=" * 40 + "\n")

        for event, timing in sorted(event_timings_delta.items(), key=lambda i: i[-1]):
            f.write(f"{escape_event_name(str(event.id))}: {timing:.2f}\n")

        f.write("\n\n")

        # Incoming event counts.
        accepted_incoming_events_counter = collections.Counter(
            event_trace.event
            for event_trace in ACCEPTED_EVENTS
            if event_trace.type == TraceType.INCOMING_EVENT_ACCEPTED
        )

        f.write("incoming events accepted:\n")
        f.write("=" * 40 + "\n")

        for event, count in sorted(accepted_incoming_events_counter.items(), key=lambda i: i[-1]):
            f.write(f"{escape_event_name(str(event.id))}: {count}\n")

        f.write("-" * 40 + "\n")
        f.write(f"total: {sum(accepted_incoming_events_counter.values())}\n")

        f.write("\n\n")

        # Outgoing command counts.
        accepted_outgoing_commands = collections.Counter(
            event_trace.event
            for event_trace in ACCEPTED_EVENTS
            if event_trace.type == TraceType.OUTGOING_COMMAND_ACCEPTED
        )

        f.write("outgoing commands accepted:\n")
        f.write("=" * 40 + "\n")

        for event, count in sorted(accepted_outgoing_commands.items(), key=lambda i: i[-1]):
            f.write(f"{escape_event_name(str(event.id))}: {count}\n")

        f.write("-" * 40 + "\n")
        f.write(f"total: {sum(accepted_outgoing_commands.values())}\n")
