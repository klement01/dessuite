"""Implementation of a Petri Net extended with the concept of inhibitor and read arcs and
with the concept of controllable events for use in Discrete Event Systems (DES)."""

import datetime
import pathlib
from collections import Counter
from collections.abc import Callable, Hashable
from dataclasses import InitVar, dataclass, field
from itertools import chain
from typing import Any, Final

import more_itertools

from dessuite.model import des
from dessuite.model.detail import net_file_parser

"""Functions for extracting an event name from a transition's name and label."""


type Extractor = Callable[[str, str | None], str]


def __always_name(name: str, _: Any) -> str:
    return name


def __label_if_present_else_name(name: str, label: str | None) -> str:
    return label if label else name


AlwaysName: Final[Extractor] = __always_name
LabelIfPresentElseName: Final[Extractor] = __label_if_present_else_name


"""Helper types for Petri net."""


@dataclass(frozen=True)
class Place:
    id: Hashable


@dataclass(frozen=True)
class Interval:
    lower_limit: datetime.timedelta
    upper_limit: datetime.timedelta | None


type State = Counter[Place]
type Weights = Counter[Place]


@dataclass(frozen=True)
class Transition:
    input_weights: Weights = field(kw_only=True)
    output_weights: Weights = field(kw_only=True)
    read_weights: Weights = field(kw_only=True)
    inhibitor_weights: Weights = field(kw_only=True)
    interval: Interval = field(kw_only=True)


@dataclass
class Petri(des.Controller):
    """Petri Net with inhibitor/read arcs and controllable events for DES."""

    # Base Petri Net + inhibitor/read arcs.
    places: Final[set[Place]] = field(kw_only=True)
    events: Final[set[des.Event]] = field(kw_only=True)
    transitions: Final[dict[des.Event, Transition]] = field(kw_only=True)
    initial_state: Final[State] = field(kw_only=True)
    current_state: State = field(init=False, repr=False)

    # Time Petri Net extension.
    start_time: InitVar[datetime.datetime | None] = field(kw_only=True, default=None)
    structurally_enabled_event_timestamps: dict[des.Event, datetime.datetime] = field(
        init=False, default_factory=dict, repr=False
    )

    # Controller extension.
    controllable_events: Final[set[des.Event]] = field(kw_only=True)

    def __post_init__(self, start_time: datetime.datetime | None):
        # TODO: validate transitions, initial_state and controllable_events.
        self.start(datetime.datetime.now() if start_time is None else start_time)

    def start(self, start_time: datetime.datetime):
        self.current_state = self.initial_state.copy()
        self.structurally_enabled_event_timestamps.clear()
        self.update_structurally_enabled_transitions(start_time)

    # Virtual method implementations and concrete method overrides.

    def update(self, event: des.Event, *, timestamp: datetime.datetime | None = None) -> bool:
        """Update current state according to event. Return True if state changed, False otherwise."""
        if timestamp is None:
            timestamp = datetime.datetime.now()

        if not self.get_event_is_enabled(event, timestamp=timestamp):
            return False

        self.current_state += self.transitions[event].output_weights
        self.current_state -= self.transitions[event].input_weights

        self.update_structurally_enabled_transitions(timestamp=timestamp)

        return True

    def get_controllable_events(self) -> set[des.Event]:
        """Return set of controllable events."""
        return self.controllable_events

    def get_disabled_controllable_events(self, *, timestamp: datetime.datetime | None = None) -> set[des.Event]:
        """Return set of controllable events disabled in the current state."""
        if timestamp is None:
            timestamp = datetime.datetime.now()

        return {
            event
            for event in self.get_controllable_events()
            if not self.get_event_is_enabled(event, timestamp=timestamp)
        }

    # Time Petri Net extension.

    def get_next_enabled_controllable_event(
        self, timestamp: datetime.datetime | None
    ) -> tuple[des.Event, datetime.datetime] | None:
        """Return (Event, timestamp) pair for next controllable event that will become available."""
        if timestamp is None:
            timestamp = datetime.datetime.now()

        structurally_enabled_controllable_transitions = [
            (event, self.transitions[event])
            for event in self.controllable_events
            if event in self.structurally_enabled_event_timestamps
        ]

        return min(
            (
                (event, transition.interval.lower_limit + self.structurally_enabled_event_timestamps[event])
                for event, transition in structurally_enabled_controllable_transitions
                if transition.interval.upper_limit is None
                or transition.interval.upper_limit + self.structurally_enabled_event_timestamps[event] <= timestamp
            ),
            key=lambda t: t[-1],
            default=None,
        )

    # Helper methods.

    def update_structurally_enabled_transitions(self, timestamp: datetime.datetime):
        """Updates dictionary of structurally enabled transitions and the moments when they *first* became enabled."""
        self.structurally_enabled_event_timestamps = {
            event: self.structurally_enabled_event_timestamps.get(event, None) or timestamp
            for event in self.events
            if self.get_event_is_structurally_enabled(event)
        }

    def get_event_is_enabled(self, event: des.Event, *, timestamp: datetime.datetime) -> bool:
        """Return True if event is enabled, False otherwise."""
        if not self.get_event_is_structurally_enabled(event):
            return False
        transition = self.transitions[event]
        transition_enabled_timestamp = self.structurally_enabled_event_timestamps[event]
        return transition_enabled_timestamp + transition.interval.lower_limit <= timestamp and (
            transition.interval.upper_limit is None
            or timestamp <= transition_enabled_timestamp + transition.interval.upper_limit
        )

    def get_event_is_structurally_enabled(self, event: des.Event) -> bool:
        """Return True if event is enabled (based on markings, ignoring timing), False otherwise."""
        if event not in self.transitions:
            return False
        transition = self.transitions[event]
        return (
            self.current_state >= transition.input_weights
            and self.current_state >= transition.read_weights
            and all(self.current_state[p] < w for p, w in transition.inhibitor_weights.items())
        )

    @staticmethod
    def import_tina_file(
        path: pathlib.Path,
        *,
        max_controllable_events: set[des.Event] | None = None,
        event_name_extractor: Extractor = LabelIfPresentElseName,
        interval_scale: datetime.timedelta = datetime.timedelta(milliseconds=1),
    ) -> Petri:
        """Construct an instance of a Petri Net from a Tina Toolbox textual format file (.net).
        Optionally, allows specifying a set of events as controllable."""
        # Properties of the parsed Petri Net.
        transitions: dict[des.Event, Transition] = {}
        initial_state_partial: State = Counter()

        with pathlib.Path(path).open(mode="r", encoding="cp1252") as net:
            for line in net:
                if trdesc := net_file_parser.try_parse_trdesc(line):
                    # TODO: properly handle multiple transitions assigned to the same event.
                    # TODO: parse and use stopwatch arcs.
                    event_name = event_name_extractor(trdesc.transition, trdesc.label)

                    inputs = more_itertools.bucket(trdesc.inputs, key=lambda t: t.arc_type)
                    input_weights = Counter(
                        {Place(t.place): t.weight for t in inputs[net_file_parser.ArcType.NORMAL_ARC]}
                    )
                    read_weights = Counter({Place(t.place): t.weight for t in inputs[net_file_parser.ArcType.TEST_ARC]})
                    inhibitor_weights = Counter(
                        {Place(t.place): t.weight for t in inputs[net_file_parser.ArcType.INHIBITOR_ARC]}
                    )

                    output_weights = Counter({Place(t.place): t.weight for t in trdesc.outputs})

                    # TODO: don't ignore "inclusive" fields of interval.
                    interval = Interval(
                        trdesc.interval.lower_limit.value * interval_scale,
                        trdesc.interval.upper_limit.value * interval_scale if trdesc.interval.upper_limit else None,
                    )

                    transitions[des.Event(event_name)] = Transition(
                        input_weights=input_weights,
                        output_weights=output_weights,
                        read_weights=read_weights,
                        inhibitor_weights=inhibitor_weights,
                        interval=interval,
                    )

                elif pldesc := net_file_parser.try_parse_pldesc(line):
                    initial_state_partial[Place(pldesc.place)] = pldesc.markings

        events = set(transitions.keys())
        places = {
            place
            for place in chain(
                initial_state_partial.keys(),
                chain.from_iterable(transition.input_weights.keys() for transition in transitions.values()),
                chain.from_iterable(transition.output_weights.keys() for transition in transitions.values()),
                chain.from_iterable(transition.read_weights.keys() for transition in transitions.values()),
                chain.from_iterable(transition.inhibitor_weights.keys() for transition in transitions.values()),
            )
        }
        initial_state = Counter({place: initial_state_partial.get(place, 0) for place in places})

        return Petri(
            name=path.name,
            places=places,
            events=events,
            transitions=transitions,
            initial_state=initial_state,
            controllable_events=events.intersection(max_controllable_events or set()),
        )
