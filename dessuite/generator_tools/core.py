from dataclasses import dataclass, field
from xml.etree import ElementTree

from dessuite.generator_tools.util import key_is_truthy
from dessuite.model import des


@dataclass(frozen=True)
class CoreEvent:
    event: des.Event
    event_name: str
    event_idx: int


@dataclass
class CoreTaskSettings:
    internal_name: str
    priority: str | int
    stack_depth: str | int | None = "configMINIMAL_STACK_SIZE"
    _name: str | None = None

    @property
    def name(self):
        return self._name or self.internal_name

    def update_from_element_tree(self, et: ElementTree.Element[str]):
        if (m := et.find("Name")) is not None:
            self._name = m.text
        if (m := et.find("StackDepth")) is not None:
            self.stack_depth = m.text  # pyright: ignore[reportAttributeAccessIssue]
        if (m := et.find("Priority")) is not None:
            self.priority = m.text  # pyright: ignore[reportAttributeAccessIssue]


@dataclass
class CoreTaskWakeOnIncomingEventSettings(CoreTaskSettings):
    internal_name: str = "DessuiteWakeOnIncomingEvent"
    priority: str | int = "configMAX_PRIORITIES - 2"


@dataclass
class CoreTaskWakeOnScheduledCommandSettings(CoreTaskSettings):
    internal_name: str = "DessuiteWakeOnScheduledCommand"
    priority: str | int = "configMAX_PRIORITIES - 1"
    stack_depth: str | int | None = None


@dataclass
class CoreSettings:
    auto_enumerate_events: bool = True
    incoming_event_queue_size: int | str = 32
    task_wake_on_incoming_event: CoreTaskWakeOnIncomingEventSettings = field(
        default_factory=CoreTaskWakeOnIncomingEventSettings
    )
    task_wake_on_scheduled_command: CoreTaskWakeOnScheduledCommandSettings = field(
        default_factory=CoreTaskWakeOnScheduledCommandSettings
    )

    def update_from_element_tree(self, core_settings: ElementTree.Element[str]):
        if (m := core_settings.find("AutoEnumerate")) is not None:
            self.auto_enumerate_events = key_is_truthy(m.text)
        if (m := core_settings.find("IncomingEventQueueSize")) is not None:
            self.incoming_event_queue_size = m.text  # pyright: ignore[reportAttributeAccessIssue]
        if (m := core_settings.find("Tasks/HandleIncomingEvents")) is not None:
            self.task_wake_on_incoming_event.update_from_element_tree(m)
        if (m := core_settings.find("Tasks/WakeOnScheduledCommand")) is not None:
            self.task_wake_on_scheduled_command.update_from_element_tree(m)

        if not self.auto_enumerate_events:
            raise ValueError("core: AutoEnumerate=False is not supported yet")
