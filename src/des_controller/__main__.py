import argparse
import pathlib
import sys

import des_controller.control as control


def __main__() -> int:
    parser = argparse.ArgumentParser(
        prog="DES Controller", description="Implements a controller for a Discrete Event System (DES)"
    )
    parser.add_argument(
        "modbus_device_file", type=pathlib.Path, help="Modbus Device file (.dev) exported from FlexFact"
    )
    parser.add_argument(
        "model_files",
        nargs="+",
        type=pathlib.Path,
        help="list of FAUDES Generator files (.gen) or Tina Toolbox textual format files (.net)",
    )

    args = parser.parse_args()
    modbus_device_file: pathlib.Path = args.modbus_device_file
    model_files: list[pathlib.Path] = args.model_files

    control.control_loop(modbus_device_file, model_files)

    return 0


if __name__ == "__main__":
    sys.exit(__main__())
