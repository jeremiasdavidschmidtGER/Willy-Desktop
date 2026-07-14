from __future__ import annotations

import pytest

from willy.animation import ManifestError, load_manifest
from willy.contracts import AnimationPriority, Facing


def test_valid_manifest_round_trip(tmp_path, clip_writer, manifest_factory):
    manifest = load_manifest(clip_writer(tmp_path, manifest_factory()))
    assert manifest.asset_id == "willy_idle"
    assert manifest.source_direction is Facing.RIGHT
    assert manifest.mirror_allowed is True
    assert manifest.loop is True
    assert manifest.priority is AnimationPriority.IDLE
    assert [f.image for f in manifest.frames] == ["frame_00.png", "frame_01.png"]
    assert [f.duration_ms for f in manifest.frames] == [100, 120]
    assert manifest.anchors == {"body_pivot": (4, 3), "ground": (4, 7)}


@pytest.mark.parametrize(
    ("broken", "expected_in_message"),
    [
        ({"frames": []}, "frames"),
        ({"asset_id": 7}, "asset_id"),
        ({"source_direction": "LEFT"}, "source_direction"),
        ({"source_direction": "SIDEWAYS"}, "SIDEWAYS"),
        ({"priority": "URGENT"}, "URGENT"),
        ({"mirror_allowed": "yes"}, "mirror_allowed"),
        ({"loop": 1}, "loop"),
        ({"frames": [{"image": "frame_00.png", "duration_ms": 0}]}, "duration_ms"),
        ({"frames": [{"image": "frame_00.png", "duration_ms": -5}]}, "duration_ms"),
        ({"frames": [{"image": "", "duration_ms": 100}]}, "image"),
        ({"frames": [{"duration_ms": 100}]}, "image"),
        ({"anchors": {"ground": [1]}}, "ground"),
        ({"anchors": {"ground": [1, "2"]}}, "ground"),
        ({"anchors": "none"}, "anchors"),
    ],
)
def test_invalid_manifest_names_file_and_field(
    tmp_path, clip_writer, manifest_factory, broken, expected_in_message
):
    with pytest.raises(ManifestError) as excinfo:
        load_manifest(clip_writer(tmp_path, manifest_factory(**broken)))
    assert "manifest.json" in str(excinfo.value)  # names the file
    assert expected_in_message in str(excinfo.value)  # names the field


def test_missing_required_field(tmp_path, clip_writer, manifest_factory):
    manifest_dict = manifest_factory()
    del manifest_dict["priority"]
    with pytest.raises(ManifestError, match="priority"):
        load_manifest(clip_writer(tmp_path, manifest_dict))


def test_missing_image_file(tmp_path, clip_writer, manifest_factory):
    path = clip_writer(tmp_path, manifest_factory(), skip_images=("frame_01.png",))
    with pytest.raises(ManifestError, match="frame_01.png"):
        load_manifest(path)


def test_unreadable_image_file(tmp_path, clip_writer, manifest_factory):
    path = clip_writer(tmp_path, manifest_factory(), skip_images=("frame_01.png",))
    (path.parent / "frame_01.png").write_bytes(b"not a png")
    with pytest.raises(ManifestError, match="unreadable"):
        load_manifest(path)


def test_mixed_frame_sizes_rejected(tmp_path, clip_writer, manifest_factory):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QPixmap

    path = clip_writer(tmp_path, manifest_factory())
    odd = QPixmap(16, 16)
    odd.fill(Qt.GlobalColor.transparent)
    odd.save(str(path.parent / "frame_01.png"), "PNG")
    with pytest.raises(ManifestError, match="differs from frame 0"):
        load_manifest(path)


def test_anchor_out_of_bounds(tmp_path, clip_writer, manifest_factory):
    path = clip_writer(tmp_path, manifest_factory(anchors={"ground": [8, 3]}))  # x == width
    with pytest.raises(ManifestError, match="outside frame bounds"):
        load_manifest(path)


def test_anchor_on_edge_is_valid(tmp_path, clip_writer, manifest_factory):
    manifest = load_manifest(clip_writer(tmp_path, manifest_factory(anchors={"ground": [7, 7]})))
    assert manifest.anchors["ground"] == (7, 7)


def test_malformed_json(tmp_path, qapp):
    clip = tmp_path / "willy_idle"
    clip.mkdir()
    path = clip / "manifest.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(ManifestError, match="unreadable manifest"):
        load_manifest(path)
