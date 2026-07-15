"""Static forbidden-API scan (ARCHITECTURE.md §8, CLAUDE.md product
restrictions): no input automation, no screen/keystroke capture, no file
writes outside the modules already vetted to write under
`%APPDATA%/WillyDesktop` (`persistence/`, and `platform/single_instance.py`
for its lock file).

Grep-level by design, per ARCHITECTURE.md §8's own description — this is a
tripwire against accidental reintroduction, not a general taint tracker.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

FORBIDDEN_IMPORT_PATTERN = re.compile(r"^\s*(import|from)\s+(pyautogui|keyboard)\b")
FORBIDDEN_CALL_PATTERN = re.compile(r"\bSendInput\b")
WRITE_CALL_PATTERN = re.compile(
    r'open\([^)]*["\']w[b]?["\']|\.write_text\(|\.write_bytes\(|\.mkdir\('
)

ALLOWED_WRITE_PREFIXES = (
    "willy/persistence/",
    "willy/platform/single_instance.py",
)


@dataclass(frozen=True, slots=True)
class Violation:
    path: str
    line_number: int
    line: str
    reason: str


def scan_source_tree(src_root: Path) -> list[Violation]:
    """Scan every `*.py` under `src_root` (pass the repo's `src/` dir)."""
    violations: list[Violation] = []
    for path in sorted(src_root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(src_root).as_posix()
        text = path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            if FORBIDDEN_IMPORT_PATTERN.search(line) or FORBIDDEN_CALL_PATTERN.search(line):
                violations.append(
                    Violation(rel, line_number, line.strip(), "forbidden input-automation API")
                )
            elif WRITE_CALL_PATTERN.search(line) and not any(
                rel.startswith(prefix) for prefix in ALLOWED_WRITE_PREFIXES
            ):
                violations.append(
                    Violation(rel, line_number, line.strip(), "file write outside persistence/")
                )
    return violations
