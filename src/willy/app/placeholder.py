"""Built-in placeholder sprite so A-03 never blocks on art (D-12).

A deliberately crude right-facing pixel boar with real alpha edges —
enough to verify transparency, sizing, and focus behaviour. Real art
arrives through the A-04 asset runtime.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPixmap

_W, _H = 32, 24
_SCALE = 4

_FUR = QColor(139, 90, 43)
_MANE = QColor(61, 38, 19)
_SNOUT = QColor(214, 138, 138)
_TUSK = QColor(240, 234, 214)
_EYE = QColor(30, 22, 15)

# (x, y, w, h, colour) — right-facing canon, like every Willy asset.
_RECTS = [
    (5, 9, 19, 9, _FUR),  # barrel body
    (20, 7, 8, 9, _FUR),  # head
    (6, 7, 15, 3, _MANE),  # spiky mane strip
    (8, 5, 2, 3, _MANE),
    (13, 5, 2, 3, _MANE),
    (18, 5, 2, 3, _MANE),
    (27, 11, 4, 4, _SNOUT),  # snout, right edge
    (26, 14, 2, 2, _TUSK),  # tusk
    (24, 9, 2, 2, _EYE),  # half-lidded suspicious eye
    (7, 18, 3, 5, _FUR),  # legs
    (12, 18, 3, 5, _FUR),
    (17, 18, 3, 5, _FUR),
    (21, 16, 3, 7, _FUR),
    (3, 10, 3, 2, _MANE),  # tail stub
]


def build_placeholder_sprite() -> QPixmap:
    image = QImage(_W, _H, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    for x, y, w, h, colour in _RECTS:
        for px in range(x, x + w):
            for py in range(y, y + h):
                image.setPixelColor(px, py, colour)
    pixmap = QPixmap.fromImage(image)
    return pixmap.scaled(
        _W * _SCALE,
        _H * _SCALE,
        Qt.AspectRatioMode.IgnoreAspectRatio,
        Qt.TransformationMode.FastTransformation,  # nearest-neighbour, integer factor
    )
