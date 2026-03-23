"""Implementation of a Deterministic Finite Automaton (DFA) extended with the concept of controllable events
for use in Discrete Event Systems (DES)."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class State:
    id: Any


@dataclass
class Event:
    id: Any


@dataclass
class DFA:
    """Deterministic Finite Automaton (DFA) for Discrete Event Systems (DES)."""

    states: set[State] = field(kw_only=True)
    events: set[Event] = field(kw_only=True)
    transitions: dict[State, dict[Event, State]] = field(kw_only=True)
    initial_state: State = field(kw_only=True)
    marked_states: set[State] = field(kw_only=True)
    controllable_events: set[Event] = field(kw_only=True)
    uncontrollable_events: set[Event] = field(init=False, repr=False)
    current_state: State = field(init=False)

    def __post_init__(self):
        # TODO: validate transitions, initial_state, marked_states and controllable_events.
        self.uncontrollable_events = self.events - self.controllable_events
        self.current_state = self.initial_state

    def update(self, event: Event) -> State:
        """Update current state according to event. Return new state."""
        enabled_transitions = self.transitions[self.current_state]
        if event in enabled_transitions:
            self.current_state = enabled_transitions[event]
        return self.current_state

    def enabled_events(self) -> set[Event]:
        """Return set of events which may cause a transition in the current state."""
        return set(self.transitions[self.current_state])

    def enabled_controllable_events(self) -> set[Event]:
        """Return set of controllable events enabled in the current state."""
        return self.controllable_events.intersection(self.enabled_events())

    def disabled_controllable_events(self) -> set[Event]:
        """Return set of controllable events disabled in the current state."""
        return self.controllable_events - self.enabled_controllable_events()
