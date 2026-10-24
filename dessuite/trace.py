import enum


class TraceType(enum.IntEnum):
    NET_START_TICK = enum.auto()
    TICK_RATE = enum.auto()
    INCOMING_EVENT_ACCEPTED = enum.auto()
    INCOMING_EVENT_DROPPED = enum.auto()
    OUTGOING_COMMAND_QUEUED = enum.auto()
    OUTGOING_COMMAND_DROPPED = enum.auto()
    OUTGOING_COMMAND_STARTED = enum.auto()
    OUTGOING_COMMAND_FINISHED = enum.auto()
