"""Implementation of a Petri Net extended with the concept of inhibitor and read arcs and
with the concept of controllable events for use in Discrete Event Systems (DES)."""

import functools
import pathlib
from collections import Counter
from collections.abc import Hashable
from dataclasses import dataclass, field
from itertools import chain
from typing import Any, Callable, Final

import more_itertools

import des_controller.model.des as des
import des_controller.model.petri.net_parser as net_parser


"""Functions for extracting an event name from a transition's name and label."""


type Extractor = Callable[[str, str | None], str]


def __always_name(name: str, _: Any) -> str:
    return name


def __label_if_present_else_name(name: str, label: str | None) -> str:
    return name


AlwaysName: Final[Extractor] = __always_name
LabelIfPresentElseName: Final[Extractor] = __label_if_present_else_name


"""Helper types for Petri net."""


@dataclass(frozen=True)
class Place:
    id: Hashable


type State = Counter[Place]
type Weights = Counter[Place]


@dataclass(frozen=True)
class Transition:
    input_weights: Weights = field(kw_only=True)
    output_weights: Weights = field(kw_only=True)
    read_weights: Weights = field(kw_only=True)
    inhibitor_weights: Weights = field(kw_only=True)


@dataclass
class Petri(des.Controller):
    """Petri Net with inhibitor/read arcs and controllable events for DES."""

    # Base Petri Net + inhibitor/read arcs.
    places: Final[set[Place]] = field(kw_only=True)
    events: Final[set[des.Event]] = field(kw_only=True)
    transitions: Final[dict[des.Event, Transition]] = field(kw_only=True)
    initial_state: Final[State] = field(kw_only=True)
    current_state: State = field(init=False)

    # Controller extension.
    controllable_events: Final[set[des.Event]] = field(kw_only=True)

    @functools.cached_property
    def uncontrollable_events(self) -> set[des.Event]:
        return self.events - self.controllable_events

    def __post_init__(self):
        # TODO: validate transitions, initial_state and controllable_events.
        self.current_state = self.initial_state

    def update(self, event: des.Event) -> bool:
        """Update current state according to event. Return True if state changed, False otherwised."""
        if not self.event_is_enabled(event):
            return False
        self.current_state += self.transitions[event].output_weights
        self.current_state -= self.transitions[event].input_weights
        return True

    def event_is_enabled(self, event: des.Event) -> bool:
        """Return True if event is enabled, False otherwise."""
        transition = self.transitions[event]
        if (
            self.current_state >= transition.input_weights
            and self.current_state >= transition.read_weights
            and all(self.current_state[p] < transition.inhibitor_weights[p] for p in transition.inhibitor_weights)
        ):
            return True
        return False

    def enabled_events(self) -> set[des.Event]:
        """Return set of events which may cause a transition in the current state."""
        return set(event for event in self.events if self.event_is_enabled(event))

    def enabled_controllable_events(self) -> set[des.Event]:
        """Return set of controllable events enabled in the current state."""
        return self.controllable_events.intersection(self.enabled_events())

    def disabled_controllable_events(self) -> set[des.Event]:
        """Return set of controllable events disabled in the current state."""
        return self.controllable_events - self.enabled_controllable_events()

    @staticmethod
    def import_tina_file(
        path: pathlib.Path,
        *,
        controllable_events: set[des.Event] = set(),
        event_name_extractor: Extractor = LabelIfPresentElseName,
    ) -> Petri:
        """Construct an instance of a Petri Net from a Tina Toolbox textual format file (.net).
        Optionally, allows specifying a set of events as controllable."""

        # Properties of the parsed Petri Net.
        transitions: dict[des.Event, Transition] = {}
        initial_state_partial: State = Counter()

        with pathlib.Path(path).open(mode="r", encoding="cp1252") as net:
            for line in net:
                if trdesc := net_parser.try_parse_trdesc(line):
                    # TODO: parse and use intervals.
                    # TODO: parse and use stopwatch arcs.
                    event_name = event_name_extractor(trdesc.transition, trdesc.label)

                    inputs = more_itertools.bucket(trdesc.inputs, key=lambda t: t.arc_type)
                    input_weights = Counter({Place(t.place): t.weight for t in inputs[net_parser.ArcType.NORMAL_ARC]})
                    read_weights = Counter({Place(t.place): t.weight for t in inputs[net_parser.ArcType.TEST_ARC]})
                    inhibitor_weights = Counter(
                        {Place(t.place): t.weight for t in trdesc.inputs if inputs[net_parser.ArcType.INHIBITOR_ARC]}
                    )

                    output_weights = Counter({Place(t.place): t.weight for t in trdesc.outputs})

                    transitions[des.Event(event_name)] = Transition(
                        input_weights=input_weights,
                        output_weights=output_weights,
                        read_weights=read_weights,
                        inhibitor_weights=inhibitor_weights,
                    )

                elif pldesc := net_parser.try_parse_pldesc(line):
                    initial_state_partial[Place(pldesc.place)] = pldesc.markings

        events = set(transitions.keys())
        places = set(
            place
            for place in chain(
                initial_state_partial.keys(),
                chain.from_iterable(transition.input_weights.keys() for transition in transitions.values()),
                chain.from_iterable(transition.output_weights.keys() for transition in transitions.values()),
                chain.from_iterable(transition.read_weights.keys() for transition in transitions.values()),
                chain.from_iterable(transition.inhibitor_weights.keys() for transition in transitions.values()),
            )
        )
        initial_state = Counter({place: initial_state_partial.get(place, 0) for place in places})

        return Petri(
            places=places,
            events=events,
            transitions=transitions,
            initial_state=initial_state,
            controllable_events=controllable_events,
        )
