from __future__ import annotations

import pytest

from willy.animation import AssetLibrary, ManifestError
from willy.assets_runtime import PixmapCache
from willy.contracts import Facing


def make_cache(root, *, strict=False) -> PixmapCache:
    library = AssetLibrary(root, strict=strict)
    library.load()
    return PixmapCache(library)


def test_frames_load_from_manifest(asset_root):
    cache = make_cache(asset_root)
    frames = cache.frames("willy_idle", Facing.RIGHT)
    assert len(frames) == 2
    assert all(not frame.isNull() for frame in frames)
    assert (frames[0].width(), frames[0].height()) == (8, 8)


def test_second_load_hits_cache(asset_root):
    cache = make_cache(asset_root)
    first = cache.frames("willy_idle", Facing.RIGHT)
    loads_after_first = cache.image_loads
    second = cache.frames("willy_idle", Facing.RIGHT)
    assert second is first  # same tuple object, not a re-load
    assert cache.image_loads == loads_after_first == 2


def test_left_facing_serves_canon_without_reloading(asset_root):
    # A-04 behaviour: mirroring arrives with A-05 behind this same API.
    cache = make_cache(asset_root)
    right = cache.frames("willy_idle", Facing.RIGHT)
    loads = cache.image_loads
    left = cache.frames("willy_idle", Facing.LEFT)
    assert left is right
    assert cache.image_loads == loads


def test_unknown_asset_release_shares_fallback_cache_entry(asset_root):
    cache = make_cache(asset_root, strict=False)
    frames = cache.frames("willy_nonexistent", Facing.RIGHT)
    assert frames is cache.frames("willy_idle", Facing.RIGHT)  # no duplicate load
    assert cache.image_loads == 2


def test_corrupt_clip_release_falls_back_strict_refuses_to_load(
    asset_root, clip_writer, manifest_factory
):
    path = clip_writer(asset_root, manifest_factory(asset_id="willy_walk"))
    (path.parent / "frame_01.png").write_bytes(b"rotten")

    # Release: the invalid clip is skipped at load, requests serve fallback.
    release = make_cache(asset_root, strict=False)
    assert release.frames("willy_walk", Facing.RIGHT) is release.frames("willy_idle", Facing.RIGHT)

    # Strict: validation reads images and refuses at load() already.
    strict_library = AssetLibrary(asset_root, strict=True)
    with pytest.raises(ManifestError):
        strict_library.load()


def test_frames_unreadable_after_load_raise_for_fallback_itself(
    asset_root, clip_writer, manifest_factory
):
    # Corrupt the fallback's own frames *after* library.load() validated
    # them: nothing safe is left to serve, so this must raise loudly.
    cache = make_cache(asset_root, strict=False)
    (asset_root / "willy_idle" / "frame_00.png").write_bytes(b"rotten")
    with pytest.raises(ManifestError, match="fallback"):
        cache.frames("willy_idle", Facing.RIGHT)
