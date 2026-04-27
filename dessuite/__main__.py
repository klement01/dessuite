import argparse
import pathlib
import sys

import dessuite.control as control


def __main__() -> int:
    parser = argparse.ArgumentParser(
        prog="dessuite", description="suite of tools for Discrete Event Systems (DES)"
    )
    subparsers = parser.add_subparsers(help="available tools", required=True)

    # Controller tool.
    parser_controller = subparsers.add_parser(name="controller", help="act as a controller for FlexFact")
    parser_controller.add_argument(
        "modbus_device_file", type=pathlib.Path, help="Modbus Device file (.dev) exported from FlexFact"
    )
    parser_controller.add_argument(
        "model_files",
        nargs="+",
        type=pathlib.Path,
        help="list of controller files; accepted formats: .gen (FAUDES), .net (Tina Toolbox)",
    )
    parser_controller.set_defaults(func=parser_controller_handler)

    args = parser.parse_args()
    return args.func(args)


def parser_controller_handler(args: argparse.Namespace) -> int:
    modbus_device_file: pathlib.Path = args.modbus_device_file
    model_files: list[pathlib.Path] = args.model_files
    control.control_loop(modbus_device_file, model_files)
    return 0


if __name__ == "__main__":
    sys.exit(__main__())
