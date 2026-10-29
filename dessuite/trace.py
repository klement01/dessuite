import enum


class TraceType(enum.IntEnum):
    TICK_RATE = enum.auto()
    NET_START_TICK = enum.auto()
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
