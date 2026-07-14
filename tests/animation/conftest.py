from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO_ASSETS = Path(__file__).parent.parent.parent / "assets" / "manifests"


def valid_manifest_dict(**overrides) -> dict:
    manifest = {
        "asset_id": "willy_idle",
        "source_direction": "RIGHT",
        "mirror_allowed": True,
        "loop": True,
        "priority": "IDLE",
        "frames": [
            {"image": "frame_00.png", "duration_ms": 100},
            {"image": "frame_01.png", "duration_ms": 120},
        ],
        "anchors": {"body_pivot": [4, 3], "ground": [4, 7]},
    }
    manifest.update(overrides)
    return manifest


def _write_clip(root: Path, manifest: dict, *, image_size=(8, 8), skip_images=()) -> Path:
    """Write `<root>/<asset_id>/manifest.json` plus its frame PNGs."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap

    clip_dir = root / str(manifest["asset_id"])
    clip_dir.mkdir(parents=True, exist_ok=True)
    (clip_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for frame in manifest.get("frames", []):
        name = frame.get("image")
        if not isinstance(name, str) or not name or name in skip_images:
            continue
        pixmap = QPixmap(*image_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        pixmap.save(str(clip_dir / name), "PNG")
    return clip_dir / "manifest.json"


@pytest.fixture
def manifest_factory():
    return valid_manifest_dict


@pytest.fixture
def clip_writer(qapp):
    # qapp dependency: QPixmap needs a QGuiApplication.
    return _write_clip


@pytest.fixture
def repo_assets() -> Path:
    return REPO_ASSETS


@pytest.fixture
def asset_root(tmp_path, clip_writer) -> Path:
    """A minimal valid asset root containing only the fallback clip."""
    clip_writer(tmp_path, valid_manifest_dict())
    return tmp_path
