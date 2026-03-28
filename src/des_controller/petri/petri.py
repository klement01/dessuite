"""Implementation of a Petri Net extended with the concept of inhibitor and read arcs and
with the concept of controllable events for use in Discrete Event Systems (DES)."""

import functools
import pathlib
import re
from collections import Counter
from collections.abc import Hashable
from dataclasses import dataclass, field
from itertools import chain
from typing import cast, Final


import des_controller.des as des
import des_controller.petri.extractors as extractors


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
        self.current_state -= self.transitions[event].output_weights
        return True

    def event_is_enabled(self, event: des.Event) -> bool:
        """Return True if event is enabled, False otherwise."""
        transition = self.transitions[event]
        if (
            self.current_state > transition.input_weights
            and self.current_state > transition.read_weights
            and self.current_state < transition.inhibitor_weights
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
        event_name_extractor: extractors.Extractor = extractors.LabelIfPresentElseName,
    ) -> Petri:
        """Construct an instance of a Petri Net from a Tina Toolbox textual format file (.net).
        Optionally, allows specifying a set of events as controllable."""

        # TODO: implement properly, using pyparsing (https://pypi.org/project/pyparsing/) and grammar spec (https://projects.laas.fr/tina/manuals/formats.html#2)

        # Properties of the parsed Petri Net.
        transitions: dict[des.Event, Transition] = {}
        initial_state: State = Counter()

        # Regular patterns for transitions.
        tr_ptrn: Final = re.compile(
            r"^tr \{?(?P<name>.+?)\}?(?: : \{?(?P<label>.+?)\}?)? (?P<interval>[^ ]+) (?P<transitions>.+)$"
        )
        interval_ptrn: Final = re.compile(
            r"^(?P<left_bracket>\[|\])(?P<lower_limit>\d+|w),(?P<upper_limit>\d+|w)(?P<right_bracket>\[|\])"
        )
        transition_pattern: Final = re.compile(
            r"(?:^| )(?P<name>([^{}]+)|(?:\{.+\}))(?:(?P<modifier>\*|\?|\!|(?:\?-)|(?:\!-))(?P<weight>\d+))?(?: |$)"
        )

        # Regular pattern for places' initial markings.
        pl_ptrn: Final = re.compile(r"^pl \{?(?P<name>.+?)\}?(?: : \{?(?P<label>.+?)\}?)? \((?P<markings>\d+)\)$")

        # Funcion for unescaping names and labels.
        unescape_ptrn: Final = re.compile(r"\\(.)")

        def unescape(s: str | None) -> str | None:
            return None if s is None else unescape_ptrn.sub(r"\1", s)

        with pathlib.Path(path).open(mode="r", encoding="cp1252") as net:
            for line in net:
                if m := tr_ptrn.match(line):
                    # Parse name and label.
                    transition_name = unescape(m["name"])
                    transition_label = unescape(m["label"])
                    event_name = event_name_extractor(cast(str, transition_name), transition_label)

                    # TODO: parse and use intervals.

                    # Parse transition weights.
                    # TODO: parse and use stopwatch arcs.
                    input_weights: Weights = Counter()
                    output_weights: Weights = Counter()
                    read_weights: Weights = Counter()
                    inhibitor_weights: Weights = Counter()

                    # Create transition.
                    transition = Transition(
                        input_weights=input_weights,
                        output_weights=output_weights,
                        read_weights=read_weights,
                        inhibitor_weights=inhibitor_weights,
                    )
                    transitions[des.Event(event_name)] = transition

                elif m := pl_ptrn.match(line):
                    place_name = unescape(m["name"])
                    place_markings = int(m["markings"])
                    initial_state[Place(place_name)] = place_markings

        events = set(transitions.keys())
        places = set(
            place
            for place in chain(
                initial_state.keys(),
                chain.from_iterable(transition.input_weights.keys() for transition in transitions.values()),
                chain.from_iterable(transition.output_weights.keys() for transition in transitions.values()),
                chain.from_iterable(transition.read_weights.keys() for transition in transitions.values()),
                chain.from_iterable(transition.inhibitor_weights.keys() for transition in transitions.values()),
            )
        )

        return Petri(
            places=places,
            events=events,
            transitions=transitions,
            initial_state=initial_state,
            controllable_events=controllable_events,
        )
