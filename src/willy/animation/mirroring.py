"""Pixel-exact horizontal mirroring and anchor transforms (A-05).

Contract (INTERFACES.md §5, MVP §28.6): mirrored anchor
``x' = frame_width - 1 - x``, ``y`` unchanged. Alpha is preserved; no
smoothing anywhere. Mirroring happens once per asset load — callers
cache both facings (see assets_runtime.PixmapCache).
"""

from __future__ import annotations

from collections.abc import Mapping

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap


def mirror_pixmap(pixmap: QPixmap) -> QPixmap:
    """Exact horizontal mirror, alpha preserved, no resampling."""
    image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    return QPixmap.fromImage(_hflip(image))


def _hflip(image: QImage) -> QImage:
    if hasattr(image, "flipped"):  # Qt >= 6.9
        return image.flipped(Qt.Orientation.Horizontal)
    return image.mirrored(True, False)  # pragma: no cover (older Qt)


def mirror_anchor(anchor: tuple[int, int], frame_width: int) -> tuple[int, int]:
    x, y = anchor
    return (frame_width - 1 - x, y)


def mirror_anchors(
    anchors: Mapping[str, tuple[int, int]], frame_width: int
) -> dict[str, tuple[int, int]]:
    return {name: mirror_anchor(anchor, frame_width) for name, anchor in anchors.items()}
