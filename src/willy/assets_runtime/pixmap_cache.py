"""Pixmap cache keyed (asset_id, facing) — A-04.

Loads each clip's frames from disk exactly once. No scaling, no
smoothing here: pixmaps are served at native pixel resolution and any
scaling downstream must be nearest-neighbour at integer factors.

A-04 serves the right-facing canon for either facing; A-05 replaces the
LEFT path with a real mirrored variant behind this same API, which is
why callers already pass a facing.
"""

from __future__ import annotations

import logging

from PySide6.QtGui import QPixmap

from willy.animation.library import AssetLibrary
from willy.animation.manifests import ManifestError
from willy.contracts import Facing

LOGGER = logging.getLogger(__name__)


class PixmapCache:
    def __init__(self, library: AssetLibrary, *, logger: logging.Logger | None = None) -> None:
        self._library = library
        self._logger = logger or LOGGER
        self._cache: dict[tuple[str, Facing], tuple[QPixmap, ...]] = {}
        self._image_loads = 0  # test-observable: cache hits add nothing

    @property
    def image_loads(self) -> int:
        return self._image_loads

    def frames(self, asset_id: str, facing: Facing) -> tuple[QPixmap, ...]:
        key = (asset_id, facing)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        if facing is not Facing.RIGHT:
            # Until A-05 lands, either facing serves the canon pixmaps —
            # shared, not re-loaded.
            frames = self.frames(asset_id, Facing.RIGHT)
            self._cache[key] = frames
            return frames

        frames = self._load(asset_id)
        self._cache[key] = frames
        return frames

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
