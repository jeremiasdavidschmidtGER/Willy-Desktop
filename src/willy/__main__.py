"""Entry point. `python -m willy` shows Willy (A-03); --version stays Qt-free."""

from __future__ import annotations

import argparse
import sys

from willy import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="willy")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    parser.add_argument(
        "--sprite",
        default=None,
        help="path to a static Willy PNG (defaults to the built-in placeholder)",
    )
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0

    from willy.app.wiring import run_app  # deferred: keep --version free of Qt

    return run_app(sprite_path=args.sprite)


if __name__ == "__main__":
    sys.exit(main())
