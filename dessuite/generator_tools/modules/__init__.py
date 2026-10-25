import dessuite.generator_tools.modules.common
import dessuite.generator_tools.modules.custom_include
import dessuite.generator_tools.modules.hal_gpio
import dessuite.generator_tools.modules.hal_uart
import dessuite.generator_tools.modules.itm_trace

from . import common

type GeneratorModule = common.GeneratorModule


def get_module_from_name(name: str) -> type[dessuite.generator_tools.modules.common.GeneratorModule]:
    MODULE_DB = {
        "HalGpio": dessuite.generator_tools.modules.hal_gpio.ModuleHalGpio,
        "HalUart": dessuite.generator_tools.modules.hal_uart.ModuleHalUart,
        "CustomInclude": dessuite.generator_tools.modules.custom_include.ModuleCustomInclude,
        "ItmTrace": dessuite.generator_tools.modules.itm_trace.ModuleItmTrace,
    }
    try:
        m = MODULE_DB[name]
    except KeyError:
        raise ValueError(f"unknown module: {name}")
    return m
