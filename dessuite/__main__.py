import argparse
import sys
from pathlib import Path

import dessuite.control as control
import dessuite.generator as generator
import dessuite.gateway as gateway


def __main__() -> int:
    parser = argparse.ArgumentParser(prog="dessuite", description="suite of tools for Discrete Event Systems (DES)")
    subparsers = parser.add_subparsers(help="available tools", required=True)

    # Controller tool.
    parser_controller = subparsers.add_parser(name="controller", help="act as a controller for FlexFact")
    parser_controller.add_argument(
        "modbus_device_file", type=Path, help="Modbus Device file (.dev) exported from FlexFact"
    )
    parser_controller.add_argument(
        "model_files",
        nargs="+",
        type=Path,
        help="list of controller files; accepted formats: .gen (FAUDES), .net (Tina Toolbox)",
    )
    parser_controller.set_defaults(func=parser_controller_handler)

    # Generator tool.
    parser_generator = subparsers.add_parser(
        name="generator", help="generate a Petri Net implementation for a microcontroller"
    )
    parser_generator.add_argument(
        "model_file", type=Path, help="Tina Toolbox textual format file (.net) representing a Petri Net"
    )
    parser_generator.add_argument("spec_file", type=Path, help="dessuite specification file (.des.xml)")
    parser_generator.add_argument("out_c", type=Path, help="generated C source file (.c) output")
    parser_generator.add_argument("out_h", type=Path, help="generated C header file (.h) output")
    parser_generator.set_defaults(func=parser_generator_handler)

    # Gateway tool.
    parser_gateway = subparsers.add_parser(
        name="gateway", help="act as gateway between FlexFact and a controller generated with generator"
    )
    parser_gateway.add_argument(
        "model_file", type=Path, help="Tina Toolbox textual format file (.net) representing a Petri Net"
    )
    parser_gateway.add_argument(
        "modbus_device_file", type=Path, help="Modbus Device file (.dev) exported from FlexFact"
    )
    parser_gateway.add_argument("spec_file", type=Path, help="dessuite specification file (.des.xml)")
    parser_gateway.add_argument("port", help="port")
    parser_gateway.add_argument("--baud", default=115200, type=int, help="baud rate")
    parser_gateway.set_defaults(func=parser_gateway_handler)

    args = parser.parse_args()
    return args.func(args)


def parser_controller_handler(args: argparse.Namespace) -> int:
    modbus_device_file: Path = args.modbus_device_file
    model_files: list[Path] = args.model_files
    control.control_loop(modbus_device_file, model_files)
    return 0


def parser_generator_handler(args: argparse.Namespace) -> int:
    model_file: Path = args.model_file
    spec_file: Path = args.spec_file
    out_c: Path = args.out_c
    out_h: Path = args.out_h
    generator.generate(model_file, spec_file, out_c, out_h)
    return 0


def parser_gateway_handler(args: argparse.Namespace) -> int:
    model_file: Path = args.model_file
    modbus_device_file: Path = args.modbus_device_file
    spec_file: Path = args.spec_file
    port: str = args.port
    baud: int = args.baud
    gateway.gateway(model_file, modbus_device_file, spec_file, port, baud)
    return 0


if __name__ == "__main__":
    sys.exit(__main__())
