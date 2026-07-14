"""Pixmap cache keyed (asset_id, facing) — A-04 loading, A-05 mirroring.

Loads each clip's files from disk exactly once and mirrors once per
asset (INTERFACES.md §5): both facings live in the cache after first
use. `mirror_allowed=False` assets are served as-is for either facing.
No scaling, no smoothing here: pixmaps are served at native pixel
resolution and any scaling downstream must be nearest-neighbour at
integer factors.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping

from PySide6.QtGui import QPixmap

from willy.animation.library import AssetLibrary
from willy.animation.manifests import ManifestError
from willy.animation.mirroring import mirror_anchors, mirror_pixmap
from willy.contracts import Facing

LOGGER = logging.getLogger(__name__)


class PixmapCache:
    def __init__(self, library: AssetLibrary, *, logger: logging.Logger | None = None) -> None:
        self._library = library
        self._logger = logger or LOGGER
        self._cache: dict[tuple[str, Facing], tuple[QPixmap, ...]] = {}
        self._anchor_cache: dict[tuple[str, Facing], Mapping[str, tuple[int, int]]] = {}
        self._image_loads = 0  # test-observable: cache hits add nothing
        self._mirror_ops = 0  # test-observable: mirroring happens once per asset

    @property
    def image_loads(self) -> int:
        return self._image_loads

    @property
    def mirror_ops(self) -> int:
        return self._mirror_ops

    def frames(self, asset_id: str, facing: Facing) -> tuple[QPixmap, ...]:
        key = (asset_id, facing)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        if facing is not Facing.RIGHT:
            canon = self.frames(asset_id, Facing.RIGHT)
            if self._library.manifest(asset_id).mirror_allowed:
                frames = tuple(mirror_pixmap(pixmap) for pixmap in canon)
                self._mirror_ops += len(frames)
            else:
                frames = canon  # neutral asset: served as-is for either facing
            self._cache[key] = frames
            return frames

        frames = self._load(asset_id)
        self._cache[key] = frames
        return frames

    def anchors(self, asset_id: str, facing: Facing) -> Mapping[str, tuple[int, int]]:
        """Anchor positions valid for the frames served under this facing."""
        key = (asset_id, facing)
        cached = self._anchor_cache.get(key)
        if cached is not None:
            return cached

        manifest = self._library.manifest(asset_id)
        if facing is Facing.RIGHT or not manifest.mirror_allowed:
            anchors: Mapping[str, tuple[int, int]] = dict(manifest.anchors)
        else:
            frame_width = self.frames(asset_id, Facing.RIGHT)[0].width()
            anchors = mirror_anchors(manifest.anchors, frame_width)
        self._anchor_cache[key] = anchors
        return anchors

    def _load(self, asset_id: str) -> tuple[QPixmap, ...]:
        manifest = self._library.manifest(asset_id)
        if manifest.asset_id != asset_id:
            # Library substituted the fallback (release mode): share its
            # cache entry instead of loading the same files twice.
            return self.frames(manifest.asset_id, Facing.RIGHT)
        directory = self._library.directory_for(manifest.asset_id)
        loaded: list[QPixmap] = []
        for frame in manifest.frames:
            pixmap = QPixmap(str(directory / frame.image))
            self._image_loads += 1
            if pixmap.isNull():
                message = f"unreadable frame image {directory / frame.image} for '{asset_id}'"
                if self._library.strict:
                    raise ManifestError(message)
                self._logger.error("%s; serving fallback", message)
                return self._fallback_frames(asset_id)
            loaded.append(pixmap)
        return tuple(loaded)

    def _fallback_frames(self, requested_asset_id: str) -> tuple[QPixmap, ...]:
        fallback_id = self._library.fallback_asset_id
        if fallback_id == requested_asset_id:
            raise ManifestError(f"fallback asset '{fallback_id}' has unreadable frames")
        return self.frames(fallback_id, Facing.RIGHT)
