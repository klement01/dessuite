from dataclasses import dataclass, field
from xml.etree import ElementTree

from csnake import CodeWriter

from dessuite.generator_tools.modules import common


@dataclass
class ModuleCustomIncludeSettings:
    includes: list[str] = field(default_factory=list)

    def update_from_element_tree(self, et: ElementTree.Element[str]):
        for include in et.iterfind("Include"):
            self.includes.append(include.text)  # pyright: ignore[reportArgumentType]


@dataclass
class ModuleCustomInclude(common.GeneratorModule):
    settings: ModuleCustomIncludeSettings = field(default_factory=ModuleCustomIncludeSettings)

    def update_settings_from_element_tree(self, et: ElementTree.Element[str]):
        self.settings.update_from_element_tree(et)

    def write_includes(self, writer: CodeWriter):
        for include in self.settings.includes:
            writer.add_line(f"#include {include}")
