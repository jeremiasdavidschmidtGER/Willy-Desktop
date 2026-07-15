from __future__ import annotations

import pytest

from willy.animation import AssetLibrary, ManifestError

GATE_A_CHECKLIST = {
    "willy_idle",
    "willy_idle_blink",
    "willy_walk",
    "willy_sitting",
    "willy_lying_down",
    "willy_sleeping",
    "willy_waking",
    "willy_annoyed",
    "willy_smug",
    "willy_surprised",
    "willy_dragged",
    "willy_drop_landing",
}


def test_all_shipped_gate_a_manifests_validate(qapp, repo_assets):
    # Acceptance: every manifest shipped in the repo validates in strict mode.
    library = AssetLibrary(repo_assets, strict=True)
    library.load()
    assert GATE_A_CHECKLIST <= set(library.asset_ids)
    # checklist + run, sit_down, sit_up, front_enter, front_idle, front_leave,
    # fuming, annoyed_idle
    assert len(library.asset_ids) == 20


def test_unknown_asset_strict_raises(asset_root):
    library = AssetLibrary(asset_root, strict=True)
    library.load()
    with pytest.raises(ManifestError, match="willy_nonexistent"):
        library.manifest("willy_nonexistent")


def test_unknown_asset_release_serves_fallback(asset_root, caplog):
    library = AssetLibrary(asset_root, strict=False)
    library.load()
    manifest = library.manifest("willy_nonexistent")
    assert manifest.asset_id == "willy_idle"
    assert any("willy_nonexistent" in record.message for record in caplog.records)


def test_invalid_clip_release_skipped_strict_raises(asset_root, clip_writer, manifest_factory):
    clip_writer(asset_root, manifest_factory(asset_id="willy_broken", frames=[]))

    release = AssetLibrary(asset_root, strict=False)
    release.load()
    assert "willy_broken" not in release.asset_ids

    strict = AssetLibrary(asset_root, strict=True)
    with pytest.raises(ManifestError, match="willy_broken"):
        strict.load()


def test_asset_id_directory_mismatch_rejected(asset_root, clip_writer, manifest_factory):
    clip_writer(asset_root, manifest_factory(asset_id="willy_walk"))
    (asset_root / "willy_walk").rename(asset_root / "willy_misnamed")

    strict = AssetLibrary(asset_root, strict=True)
    with pytest.raises(ManifestError, match="does not match directory"):
        strict.load()

    release = AssetLibrary(asset_root, strict=False)
    release.load()
    assert "willy_walk" not in release.asset_ids


def test_missing_fallback_raises_even_in_release(tmp_path, clip_writer, manifest_factory):
    clip_writer(tmp_path, manifest_factory(asset_id="willy_walk"))
    library = AssetLibrary(tmp_path, strict=False)
    with pytest.raises(ManifestError, match="fallback"):
        library.load()


def test_missing_root_raises(tmp_path):
    library = AssetLibrary(tmp_path / "nowhere")
    with pytest.raises(ManifestError, match="asset root"):
        library.load()
