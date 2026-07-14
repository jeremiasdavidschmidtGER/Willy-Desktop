"""Asset library: discovers and validates every clip under an assets root.

Strict mode (tests/dev) raises on any problem; release mode logs and
serves the registered fallback so a missing asset can never crash the
app (ARCHITECTURE.md §5).
"""

from __future__ import annotations

import logging
from pathlib import Path

from willy.animation.manifests import ManifestError, load_manifest
from willy.contracts import AnimationManifest

LOGGER = logging.getLogger(__name__)

FALLBACK_ASSET_ID = "willy_idle"


class AssetLibrary:
    def __init__(
        self,
        root: Path | str,
        *,
        strict: bool = False,
        fallback_asset_id: str = FALLBACK_ASSET_ID,
        logger: logging.Logger | None = None,
    ) -> None:
        self._root = Path(root)
        self._strict = strict
        self._fallback_asset_id = fallback_asset_id
        self._logger = logger or LOGGER
        self._manifests: dict[str, AnimationManifest] = {}
        self._directories: dict[str, Path] = {}

    @property
    def asset_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._manifests))

    @property
    def strict(self) -> bool:
        return self._strict

    @property
    def fallback_asset_id(self) -> str:
        return self._fallback_asset_id

    def load(self) -> None:
        """Discover `<root>/<asset_id>/manifest.json` clips and validate them.

        The fallback asset must load — without a static idle there is
        nothing safe to serve, so that failure raises even in release.
        """
        if not self._root.is_dir():
            raise ManifestError(f"asset root does not exist: {self._root}")
        for manifest_path in sorted(self._root.glob("*/manifest.json")):
            try:
                manifest = load_manifest(manifest_path)
            except ManifestError:
                if self._strict or manifest_path.parent.name == self._fallback_asset_id:
                    raise
                self._logger.exception("Skipping invalid manifest %s", manifest_path)
                continue
            if manifest.asset_id != manifest_path.parent.name:
                message = (
                    f"{manifest_path}: asset_id '{manifest.asset_id}'"
                    f" does not match directory '{manifest_path.parent.name}'"
                )
                if self._strict:
                    raise ManifestError(message)
                self._logger.error("%s — skipped", message)
                continue
            self._manifests[manifest.asset_id] = manifest
            self._directories[manifest.asset_id] = manifest_path.parent
        if self._fallback_asset_id not in self._manifests:
            raise ManifestError(
                f"fallback asset '{self._fallback_asset_id}' missing from {self._root}"
            )

    def manifest(self, asset_id: str) -> AnimationManifest:
        found = self._manifests.get(asset_id)
        if found is not None:
            return found
        if self._strict:
            raise ManifestError(f"unknown asset_id '{asset_id}'")
        self._logger.error("Unknown asset_id '%s'; serving fallback", asset_id)
        return self._manifests[self._fallback_asset_id]

    def directory_for(self, asset_id: str) -> Path:
        # Resolve through manifest() so release-mode fallback applies here too.
        return self._directories[self.manifest(asset_id).asset_id]
