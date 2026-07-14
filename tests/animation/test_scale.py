"""D-14: integer nearest-neighbour scaling in the pixmap cache."""

from __future__ import annotations

import pytest

from willy.animation.controller import WillyAnimationController
from willy.animation.library import AssetLibrary
from willy.app.bus import SyncEventBus
from willy.assets_runtime.pixmap_cache import PixmapCache
from willy.contracts import Facing


def make_cache(root) -> PixmapCache:
    library = AssetLibrary(root, strict=True)
    library.load()
    return PixmapCache(library)


def test_scale_doubles_dimensions(asset_root):
    cache = make_cache(asset_root)
    native = cache.frames("willy_idle", Facing.RIGHT, 1)
    scaled = cache.frames("willy_idle", Facing.RIGHT, 2)
    assert (scaled[0].width(), scaled[0].height()) == (
        native[0].width() * 2,
        native[0].height() * 2,
    )
    assert len(scaled) == len(native)


def test_scaled_frames_are_cached(asset_root):
    cache = make_cache(asset_root)
    first = cache.frames("willy_idle", Facing.RIGHT, 2)
    ops = cache.scale_ops
    loads = cache.image_loads
    second = cache.frames("willy_idle", Facing.RIGHT, 2)
    assert second is first
    assert cache.scale_ops == ops  # scaled once, then cache hits
    assert cache.image_loads == loads  # no file re-reads either


def test_scaled_left_facing_builds_on_mirrored_native(asset_root):
    cache = make_cache(asset_root)
    left_native = cache.frames("willy_idle", Facing.LEFT, 1)
    left_scaled = cache.frames("willy_idle", Facing.LEFT, 2)
    assert left_scaled[0].width() == left_native[0].width() * 2
    # one mirror pass total: scaling reuses the mirrored natives
    assert cache.mirror_ops == len(left_native)


@pytest.mark.parametrize("bad", [0, -1, 1.5, "2"])
def test_invalid_scale_rejected(asset_root, bad):
    cache = make_cache(asset_root)
    with pytest.raises(ValueError):
        cache.frames("willy_idle", Facing.RIGHT, bad)


def test_controller_serves_scaled_frames(asset_root, fake_clock):
    library = AssetLibrary(asset_root, strict=True)
    library.load()
    cache = PixmapCache(library)
    controller = WillyAnimationController(
        cache=cache, library=library, bus=SyncEventBus(), clock=fake_clock, scale=2
    )
    assert (controller.tick().width(), controller.tick().height()) == (16, 16)  # 8x8 art at 2x
