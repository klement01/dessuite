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
class CoreTaskEventLoopSettings(CoreTaskSettings):
    internal_name: str = "DessuiteEventLoop"
    priority: str | int = "configMAX_PRIORITIES - 1"


@dataclass
class CoreTaskScheduleCommandSettings(CoreTaskSettings):
    internal_name: str = "DessuiteScheduleCommand"
    priority: str | int = "configMAX_PRIORITIES - 2"
    stack_depth: str | int | None = None


@dataclass
class CoreTaskTraceLoopSettings(CoreTaskSettings):
    internal_name: str = "DessuiteTraceLoop"
    priority: str | int = 1
    enabled: bool = False
    queue_size: int | str = 32


@dataclass
class CoreSettings:
    auto_enumerate_events: bool = True
    event_queue_size: int | str = 32
    task_event_loop: CoreTaskEventLoopSettings = field(default_factory=CoreTaskEventLoopSettings)
    task_schedule_command: CoreTaskScheduleCommandSettings = field(default_factory=CoreTaskScheduleCommandSettings)
    task_trace_loop: CoreTaskTraceLoopSettings = field(default_factory=CoreTaskTraceLoopSettings)

    def update_from_element_tree(self, core_settings: ElementTree.Element[str]):
        if (m := core_settings.find("AutoEnumerate")) is not None:
            self.auto_enumerate_events = key_is_truthy(m.text)
        if (m := core_settings.find("EventQueueSize")) is not None:
            self.event_queue_size = m.text  # pyright: ignore[reportAttributeAccessIssue]
        if (m := core_settings.find("Tasks/EventLoop")) is not None:
            self.task_event_loop.update_from_element_tree(m)
        if (m := core_settings.find("Tasks/ScheduleCommand")) is not None:
            self.task_schedule_command.update_from_element_tree(m)
        if (m := core_settings.find("Tasks/TraceLoop")) is not None:
            self.task_trace_loop.update_from_element_tree(m)
            if (me := m.find("Enabled")) is not None:
                self.task_trace_loop.enabled = key_is_truthy(me.text)
            if (me := m.find("TraceQueueSize")) is not None:
                self.task_trace_loop.queue_size = me.text  # pyright: ignore[reportAttributeAccessIssue]

        if not self.auto_enumerate_events:
            raise ValueError("core: AutoEnumerate=False is not supported yet")
