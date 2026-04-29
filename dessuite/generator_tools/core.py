import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field

import dessuite.model.des as des
from dessuite.generator_tools.util import key_is_truthy


@dataclass(frozen=True)
class CoreEvent:
    event: des.Event
    event_name: str
    event_idx: int


@dataclass
class CoreTaskSettings:
    internal_name: str
    priority: str | int
    stack_depth: str | int = "configMINIMAL_STACK_SIZE"
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
class CoreTaskExecuteCommandSettings(CoreTaskSettings):
    internal_name: str = "ExecuteCommand"
    priority: str | int = 12


@dataclass
class CoreTaskUpdateStateSettings(CoreTaskSettings):
    internal_name: str = "UpdateState"
    priority: str | int = 11


@dataclass
class CoreTaskSetCommandSettings(CoreTaskSettings):
    internal_name: str = "SetCommand"
    priority: str | int = 10


@dataclass
class CoreSettings:
    auto_enumerate_events: bool = True
    event_queue_size: int | str = 32
    task_execute_command: CoreTaskExecuteCommandSettings = field(default_factory=CoreTaskExecuteCommandSettings)
    task_update_state: CoreTaskUpdateStateSettings = field(default_factory=CoreTaskUpdateStateSettings)
    task_set_command: CoreTaskSetCommandSettings = field(default_factory=CoreTaskSetCommandSettings)

    def update_from_element_tree(self, core_settings: ElementTree.Element[str]):
        if (m := core_settings.find("AutoEnumerate")) is not None:
            self.auto_enumerate_events = key_is_truthy(m.text)
        if (m := core_settings.find("EventQueueSize")) is not None:
            self.event_queue_size = m.text  # pyright: ignore[reportAttributeAccessIssue]
        if (m := core_settings.find("Tasks/ExecuteCommand")) is not None:
            self.task_execute_command.update_from_element_tree(m)
        if (m := core_settings.find("Tasks/UpdateState")) is not None:
            self.task_update_state.update_from_element_tree(m)
        if (m := core_settings.find("Tasks/SetCommand")) is not None:
            self.task_set_command.update_from_element_tree(m)

        if not self.auto_enumerate_events:
            raise ValueError("core: AutoEnumerate=False is not supported yet")
