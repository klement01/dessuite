"""Common components of a Discrete Event Systems (DES)."""

import abc
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Event:
    id: Any


class Controller(abc.ABC):
    """Abstract Base Class (ABC) for a Discrete Event Systems (DES) controller."""

    @abc.abstractmethod
    def update(self, event: Event) -> bool:
        """Update current state according to event. Return True if state changed, False otherwised."""
        ...

    @abc.abstractmethod
    def disabled_controllable_events(self) -> set[Event]:
        """Return set of controllable events disabled in the current state."""
        ...
