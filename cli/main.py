"""Entry point del CLI d-arxiv — registrado en pyproject.toml como `d-arxiv`.

Ticket: CLI-01
"""

from __future__ import annotations

import argparse
import sys

from lib.setup import run_wizard


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada del CLI d-arxiv. Registrado en pyproject.toml como
    project.scripts: d-arxiv = "cli.main:main".

    Args:
        argv: argumentos de línea de comandos, sin el nombre del programa.
            Si es None, usa sys.argv[1:].

    Returns:
        Código de salida del proceso: 0 en éxito, 1 si el subcomando lanza
        una excepción (el mensaje de la excepción se imprime a stderr, sin
        traceback crudo), 2 si argv no matchea ningún subcomando conocido
        (comportamiento estándar de argparse).
    """
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0

    if not hasattr(args, "func"):
        parser.print_usage(sys.stderr)
        return 2

    try:
        return args.func(args)
    except Exception as exc:
        print(f"{exc}", file=sys.stderr)
        return 1


def _cmd_wizard(args: argparse.Namespace) -> int:
    """Subcomando 'wizard' — invoca lib.setup.run_wizard() interactivo.

    Args:
        args: namespace de argparse (sin argumentos propios en esta versión;
            existe por consistencia con el resto de subcomandos futuros).

    Returns:
        0 si run_wizard() completa sin excepción, 1 si lanza RuntimeError
        o ValueError (mensaje impreso a stderr).
    """
    run_wizard()
    return 0


# --- helpers internos ---


def _build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argparse con el subcomando 'wizard'."""
    parser = argparse.ArgumentParser(prog="d-arxiv")
    subparsers = parser.add_subparsers(dest="command")

    wizard_parser = subparsers.add_parser(
        "wizard", help="ejecuta el wizard interactivo de instalación"
    )
    wizard_parser.set_defaults(func=_cmd_wizard)

    return parser


if __name__ == "__main__":
    sys.exit(main())
