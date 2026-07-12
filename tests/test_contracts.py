from __future__ import annotations

import ast
import dataclasses
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from willy.contracts import (
    AnimationManifest,
    AnimationPriority,
    Facing,
    FrameSpec,
    PlayAnimation,
    ScreenPoint,
    WillyClicked,
    WillyStateSnapshot,
)
from willy.contracts.enums import MouseButton

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)

SAMPLES = [
    ScreenPoint(1, 2),
    WillyClicked(timestamp=NOW, button=MouseButton.LEFT, clicks_in_last_10s=1),
    PlayAnimation(animation_id="willy_idle", facing=Facing.RIGHT, priority=AnimationPriority.IDLE),
    FrameSpec(image="willy_idle_00.png", duration_ms=83),
    WillyStateSnapshot(
        position=ScreenPoint(0, 0), screen_name="s", facing=Facing.LEFT, updated_at=NOW
    ),
]


@pytest.mark.parametrize("dto", SAMPLES, ids=lambda d: type(d).__name__)
def test_dtos_are_frozen(dto):
    field = dataclasses.fields(dto)[0].name
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(dto, field, None)


def test_manifest_defaults():
    m = AnimationManifest(
        asset_id="willy_idle",
        source_direction=Facing.RIGHT,
        mirror_allowed=True,
        loop=True,
        priority=AnimationPriority.IDLE,
        frames=(FrameSpec("willy_idle_00.png", 83),),
    )
    assert m.anchors == {}


def test_priority_ordering():
    assert (
        AnimationPriority.REACTION.value
        > AnimationPriority.INTERACTION.value
        > AnimationPriority.AMBIENT.value
        > AnimationPriority.IDLE.value
    )


def test_contracts_import_stdlib_only():
    """contracts/ may import only the stdlib and itself (INTERFACES.md)."""
    pkg_dir = Path(__file__).parent.parent / "src" / "willy" / "contracts"
    allowed_prefix = ("willy.contracts",)
    for py in pkg_dir.glob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                top = name.split(".")[0]
                ok = top in sys.stdlib_module_names or name.startswith(allowed_prefix)
                assert ok, f"{py.name} imports non-stdlib module {name!r}"
