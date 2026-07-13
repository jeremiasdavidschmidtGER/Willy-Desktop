"""Entry point. Gate A scaffold: --version only; the window arrives with A-03."""

from __future__ import annotations

import argparse
import sys

from willy import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="willy")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    print("Willy Desktop scaffold (Gate A) — nothing to run yet; see docs/GATE_A_BACKLOG.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
