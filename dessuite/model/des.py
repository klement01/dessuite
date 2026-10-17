"""Common components of a Discrete Event Systems (DES)."""

import abc
import datetime
from collections.abc import Hashable
from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    id: Hashable


@dataclass
class Controller(abc.ABC):
    """Abstract Base Class (ABC) for a Discrete Event Systems (DES) controller."""

    name: str

    @abc.abstractmethod
    def update(self, event: Event) -> bool:
        """Update current state according to event. Return True if state changed, False otherwise."""
        ...

    @abc.abstractmethod
    def get_controllable_events(self) -> set[Event]:
        """Return set of controllable events."""
        ...

    @abc.abstractmethod
    def get_disabled_controllable_events(self) -> set[Event]:
        """Return set of controllable events disabled in the current state."""
        ...

    def get_next_enabled_controllable_event_timestamp(
        self, timestamp: datetime.datetime | None
    ) -> datetime.datetime | None:
        """Return timestamp when a controllable event that is structurally enabled but disabled due to timing
        becomes enabled, or None if there are no events in this state."""
        return None
