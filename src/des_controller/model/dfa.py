"""Implementation of a Deterministic Finite Automaton (DFA) extended with the concept of controllable events
for use in Discrete Event Systems (DES)."""

import collections
import itertools
import pathlib
import xml.etree.ElementTree as ElementTree
from collections.abc import Hashable
from dataclasses import dataclass, field
from typing import Final

import des_controller.model.des as des


@dataclass(frozen=True)
class State:
    id: Hashable


@dataclass
class DFA(des.Controller):
    """Deterministic Finite Automaton (DFA) for Discrete Event Systems (DES)."""

    # Base DFA.
    states: Final[set[State]] = field(kw_only=True)
    events: Final[set[des.Event]] = field(kw_only=True)
    transitions: Final[dict[State, dict[des.Event, State]]] = field(kw_only=True)
    initial_state: Final[State] = field(kw_only=True)
    marked_states: Final[set[State]] = field(kw_only=True)
    current_state: State = field(init=False)

    # Controller extension.
    controllable_events: Final[set[des.Event]] = field(kw_only=True)

    def __post_init__(self):
        # TODO: validate transitions, initial_state, marked_states and controllable_events.
        self.current_state = self.initial_state

    # Virtual method implementations.

    def update(self, event: des.Event) -> bool:
        """Update current state according to event. Return True if state changed, False otherwised."""
        if event not in self.transitions[self.current_state]:
            return False
        self.current_state = self.transitions[self.current_state][event]
        return True

    def get_controllable_events(self) -> set[des.Event]:
        """Return set of controllable events."""
        return self.controllable_events

    def get_disabled_controllable_events(self) -> set[des.Event]:
        """Return set of controllable events disabled in the current state."""
        return self.get_controllable_events() - set(self.transitions[self.current_state])

    # Helper methods.

    @staticmethod
    def import_faudes_file(path: pathlib.Path) -> DFA:
        """Construct an instance of a DFA from a FAUDES Generator file (.gen)."""
        # Extract raw strings from file.
        # TODO: proper error handling.
        tree = ElementTree.parse(str(path))
        alphabet_raw = tree.find("Alphabet").text.strip()  # pyright: ignore[reportOptionalMemberAccess]
        states_raw = tree.find("States").text.strip()  # pyright: ignore[reportOptionalMemberAccess]
        transitions_raw = tree.find("TransRel").text.strip()  # pyright: ignore[reportOptionalMemberAccess]
        initial_state_raw = tree.find("InitStates").text.strip()  # pyright: ignore[reportOptionalMemberAccess]
        marked_states_raw = tree.find("MarkedStates").text.strip()  # pyright: ignore[reportOptionalMemberAccess]

        # Parse strings into appropriate formats.
        states = set(State(s) for s in states_raw.split())
        events = set(des.Event(e) for e in alphabet_raw.split() if e != "+C+")

        transitions = collections.defaultdict(dict)
        for s0, e, s1 in (t.split() for t in transitions_raw.split("\n")):
            transitions[State(s0)][des.Event(e)] = State(s1)
        transitions = dict(transitions)

        initial_state = State(initial_state_raw)
        marked_states = set(State(s) for s in marked_states_raw.split())
        controllable_events = set(des.Event(e) for e, n in itertools.pairwise(alphabet_raw.split()) if n == "+C+")

        # Assemble DFA.
        return DFA(
            name=path.name,
            states=states,
            events=events,
            transitions=transitions,
            initial_state=initial_state,
            marked_states=marked_states,
            controllable_events=controllable_events,
        )
