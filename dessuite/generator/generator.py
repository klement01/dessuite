import pathlib
from typing import Final

DES_CONTROLLER_C_TEMPLATE: Final = pathlib.Path(__file__) / "c" / "des_controller.c.template"
DES_CONTROLLER_H: Final = pathlib.Path(__file__) / "c" / "des_controller.h"
