import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from pathlib import Path

import dessuite.generator_tools.core as core
import dessuite.generator_tools.modules as modules


@dataclass
class EventAction: ...


@dataclass
class EventTrigger: ...


@dataclass
class EventData:
    name: str
    controllable: bool
    actions: list[EventAction]
    triggers: list[EventTrigger]


@dataclass
class GeneratorSpec:
    core_settings: core.CoreSettings = field(default_factory=core.CoreSettings)
    modules: dict[str, modules.GeneratorModule] = field(default_factory=dict)
    events: list[EventData] = field(default_factory=list)


def generate(spec_file: Path, out_c: Path, out_h: Path):
    settings = GeneratorSpec()

    tree = ElementTree.parse(str(spec_file))

    if (m := tree.find("Core")) is not None:
        settings.core_settings.update_from_element_tree(m)

    if (m := tree.find("Modules")) is not None:
        for mi in m.iter():
            name = mi.tag
            module = modules.get_module_from_name(name)()
            module.update_settings_from_element_tree(mi)
            settings.modules[name] = module

    if (m := tree.find("Events")) is not None:
        for mi in m.iter():
            name = mi.find("Name").text  # pyright: ignore[reportOptionalMemberAccess]
            controllable = mi.find("Controllable|Actions") is not None
