from dataclasses import dataclass

from csnake import CodeWriter

from dessuite.generator_tools.modules import common


@dataclass
class ModuleItmTrace(common.GeneratorModule):
    def write_output_interface_functions(self, writer: CodeWriter):
        writer.add_line(r"int __io_putchar(int ch) {")
        writer.add_line(r"  ITM_SendChar(ch);")
        writer.add_line(r"  return ch;")
        writer.add_line(r"}")
