"""AnimationManifest JSON loading and validation (A-04, loading half).

Errors are loud and precise: every ManifestError names the file and the
offending field, so a broken export is diagnosable from the message alone.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QImageReader

from willy.contracts import AnimationManifest, AnimationPriority, Facing, FrameSpec


class ManifestError(Exception):
    """Invalid manifest; the message names file and field."""


def load_manifest(manifest_path: Path) -> AnimationManifest:
    """Parse and fully validate one manifest, including its image files."""
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ManifestError(f"{manifest_path}: unreadable manifest ({error})") from error
    if not isinstance(raw, dict):
        raise ManifestError(f"{manifest_path}: manifest root must be an object")

    manifest = _parse(raw, manifest_path)
    _validate_images(manifest, manifest_path)
    return manifest


def _parse(raw: dict, path: Path) -> AnimationManifest:
    asset_id = _require(raw, "asset_id", str, path)
    source_direction = _parse_enum(Facing, _require(raw, "source_direction", str, path), path)
    if source_direction is not Facing.RIGHT:
        raise ManifestError(
            f"{path}: source_direction must be RIGHT for canon assets, got {source_direction.name}"
        )
    priority = _parse_enum(AnimationPriority, _require(raw, "priority", str, path), path)

    frames_raw = _require(raw, "frames", list, path)
    if not frames_raw:
        raise ManifestError(f"{path}: frames must contain at least one entry")
    frames = tuple(_parse_frame(entry, index, path) for index, entry in enumerate(frames_raw))

    anchors_raw = raw.get("anchors", {})
    if not isinstance(anchors_raw, dict):
        raise ManifestError(f"{path}: anchors must be an object")
    anchors = {name: _parse_anchor(name, value, path) for name, value in anchors_raw.items()}

    return AnimationManifest(
        asset_id=asset_id,
        source_direction=source_direction,
        mirror_allowed=_require(raw, "mirror_allowed", bool, path),
        loop=_require(raw, "loop", bool, path),
        priority=priority,
        frames=frames,
        anchors=anchors,
    )


def _parse_frame(entry: object, index: int, path: Path) -> FrameSpec:
    if not isinstance(entry, dict):
        raise ManifestError(f"{path}: frames[{index}] must be an object")
    image = entry.get("image")
    if not isinstance(image, str) or not image:
        raise ManifestError(f"{path}: frames[{index}].image must be a non-empty string")
    duration = entry.get("duration_ms")
    if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
        raise ManifestError(f"{path}: frames[{index}].duration_ms must be an int > 0")
    return FrameSpec(image=image, duration_ms=duration)


def _parse_anchor(name: str, value: object, path: Path) -> tuple[int, int]:
    ok = (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and all(isinstance(v, int) and not isinstance(v, bool) for v in value)
    )
    if not ok:
        raise ManifestError(f"{path}: anchors.{name} must be [x, y] with integer coordinates")
    return (value[0], value[1])


def _validate_images(manifest: AnimationManifest, path: Path) -> None:
    """Frames must exist, be readable, and share one size; anchors in-bounds."""
    base_dir = path.parent
    size = None
    for index, frame in enumerate(manifest.frames):
        image_path = base_dir / frame.image
        if not image_path.is_file():
            raise ManifestError(f"{path}: frames[{index}].image not found: {frame.image}")
        frame_size = QImageReader(str(image_path)).size()
        if not frame_size.isValid():
            raise ManifestError(f"{path}: frames[{index}].image unreadable: {frame.image}")
        if size is None:
            size = frame_size
        elif frame_size != size:
            raise ManifestError(
                f"{path}: frames[{index}].image size {frame_size.width()}x{frame_size.height()}"
                f" differs from frame 0 ({size.width()}x{size.height()})"
            )
    assert size is not None  # frames is non-empty
    for name, (x, y) in manifest.anchors.items():
        if not (0 <= x < size.width() and 0 <= y < size.height()):
            raise ManifestError(
                f"{path}: anchors.{name} ({x}, {y}) outside frame bounds"
                f" {size.width()}x{size.height()}"
            )


def _require(raw: dict, key: str, expected: type, path: Path):
    value = raw.get(key)
    if not isinstance(value, expected) or (expected is not bool and isinstance(value, bool)):
        raise ManifestError(f"{path}: field '{key}' must be {expected.__name__}")
    return value


def _parse_enum(enum_type, value: str, path: Path):
    try:
        return enum_type[value]
    except KeyError:
        valid = ", ".join(member.name for member in enum_type)
        raise ManifestError(
            f"{path}: '{value}' is not a valid {enum_type.__name__} (expected one of: {valid})"
        ) from None
