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
class CoreTaskHandleNetUpdatesSettings(CoreTaskSettings):
    internal_name: str = "HandleNetUpdates"
    priority: str | int = "configMAX_PRIORITIES - 3"


@dataclass
class CoreTaskHandleIncomingEventsSettings(CoreTaskSettings):
    internal_name: str = "HandleIncomingEvents"
    priority: str | int = "configMAX_PRIORITIES - 2"


@dataclass
class CoreTaskExecuteOutgoingCommandSettings(CoreTaskSettings):
    internal_name: str = "ExecuteOutgoingCommand"
    priority: str | int = "configMAX_PRIORITIES - 1"
    stack_depth: str | int | None = None


@dataclass
class CoreSettings:
    auto_enumerate_events: bool = True
    event_queue_size: int | str = 32
    task_handle_net_updates: CoreTaskHandleNetUpdatesSettings = field(default_factory=CoreTaskHandleNetUpdatesSettings)
    task_handle_incoming_events: CoreTaskHandleIncomingEventsSettings = field(
        default_factory=CoreTaskHandleIncomingEventsSettings
    )
    task_execute_outgoing_commands: CoreTaskExecuteOutgoingCommandSettings = field(
        default_factory=CoreTaskExecuteOutgoingCommandSettings
    )

    def update_from_element_tree(self, core_settings: ElementTree.Element[str]):
        if (m := core_settings.find("AutoEnumerate")) is not None:
            self.auto_enumerate_events = key_is_truthy(m.text)
        if (m := core_settings.find("EventQueueSize")) is not None:
            self.event_queue_size = m.text  # pyright: ignore[reportAttributeAccessIssue]
        if (m := core_settings.find("Tasks/HandleNetUpdates")) is not None:
            self.task_handle_net_updates.update_from_element_tree(m)
        if (m := core_settings.find("Tasks/HandleIncomingEvents")) is not None:
            self.task_handle_incoming_events.update_from_element_tree(m)
        if (m := core_settings.find("Tasks/ExecuteOutgoingCommands")) is not None:
            self.task_execute_outgoing_commands.update_from_element_tree(m)

        if not self.auto_enumerate_events:
            raise ValueError("core: AutoEnumerate=False is not supported yet")
