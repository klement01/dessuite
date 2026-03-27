"""Implementation of a Petri Net extended with the concept of inhibitor and read arcs and
with the concept of controllable events for use in Discrete Event Systems (DES)."""

import functools
from collections import Counter
from collections.abc import Hashable
from dataclasses import dataclass, field
from typing import Final

import des_controller.des as des


@dataclass(frozen=True)
class Place:
    id: Hashable


type State = Counter[Place]
type Weights = Counter[Place]


@dataclass(frozen=True)
class Transition:
    input_weights: Weights
    output_weights: Weights
    read_weights: Weights
    inhibitor_weights: Weights


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
