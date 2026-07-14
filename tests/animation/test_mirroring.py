from __future__ import annotations

import pytest
from PySide6.QtGui import QColor, QImage, QPixmap

from willy.animation import AssetLibrary, mirror_anchor, mirror_anchors, mirror_pixmap
from willy.assets_runtime import PixmapCache
from willy.contracts import Facing

WIDTH, HEIGHT = 5, 4


def patterned_pixmap(qapp) -> QPixmap:
    """Every pixel unique, with varying alpha — mirror errors cannot hide."""
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            image.setPixelColor(x, y, QColor(x * 40, y * 50, (x + y) * 20, 255 - x * 30))
    return QPixmap.fromImage(image)


class TestMirrorPixmap:
    def test_pixel_exact_against_reference_loop(self, qapp):
        source = patterned_pixmap(qapp)
        mirrored = mirror_pixmap(source).toImage()
        reference = source.toImage()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                assert mirrored.pixelColor(x, y) == reference.pixelColor(WIDTH - 1 - x, y), (
                    f"pixel ({x},{y}) wrong"
                )

    def test_alpha_preserved(self, qapp):
        mirrored = mirror_pixmap(patterned_pixmap(qapp))
        assert mirrored.hasAlphaChannel()

    def test_double_mirror_is_identity(self, qapp):
        source = patterned_pixmap(qapp)
        twice = mirror_pixmap(mirror_pixmap(source)).toImage()
        # Normalise format: QPixmap storage is premultiplied ARGB and
        # QImage equality compares formats as well as pixels.
        fmt = QImage.Format.Format_ARGB32
        assert twice.convertToFormat(fmt) == source.toImage().convertToFormat(fmt)

    def test_size_unchanged(self, qapp):
        mirrored = mirror_pixmap(patterned_pixmap(qapp))
        assert (mirrored.width(), mirrored.height()) == (WIDTH, HEIGHT)


class TestAnchorTransform:
    @pytest.mark.parametrize(
        ("anchor", "width", "expected"),
        [
            ((0, 5), 10, (9, 5)),  # left edge → right edge
            ((9, 5), 10, (0, 5)),  # right edge → left edge
            ((4, 0), 10, (5, 0)),
            ((50, 86), 102, (51, 86)),  # willy_walk ground anchor
        ],
    )
    def test_formula_x_transformed_y_unchanged(self, anchor, width, expected):
        assert mirror_anchor(anchor, width) == expected

    def test_mirror_anchors_maps_all_keys(self):
        anchors = {"ground": (50, 86), "mouth": (90, 40), "rear_effect": (5, 60)}
        mirrored = mirror_anchors(anchors, 102)
        assert mirrored == {"ground": (51, 86), "mouth": (11, 40), "rear_effect": (96, 60)}

    def test_double_transform_is_identity(self):
        anchors = {"ground": (50, 86), "eyes": (56, 49)}
        assert mirror_anchors(mirror_anchors(anchors, 102), 102) == anchors


class TestCacheIntegration:
    def make_cache(self, root) -> PixmapCache:
        library = AssetLibrary(root, strict=True)
        library.load()
        return PixmapCache(library)

    def test_left_frames_are_pixel_exact_mirrors(self, repo_assets, qapp):
        cache = self.make_cache(repo_assets)
        rights = cache.frames("willy_walk", Facing.RIGHT)
        lefts = cache.frames("willy_walk", Facing.LEFT)
        assert len(lefts) == len(rights)
        right0 = rights[0].toImage().convertToFormat(QImage.Format.Format_ARGB32)
        left0 = lefts[0].toImage().convertToFormat(QImage.Format.Format_ARGB32)
        width = right0.width()
        for y in range(0, right0.height(), 7):  # sampled rows: full grid is slow
            for x in range(width):
                assert left0.pixelColor(x, y) == right0.pixelColor(width - 1 - x, y)

    def test_mirror_happens_once_then_cache_hits(self, repo_assets, qapp):
        cache = self.make_cache(repo_assets)
        first = cache.frames("willy_walk", Facing.LEFT)
        ops_after_first = cache.mirror_ops
        loads_after_first = cache.image_loads
        second = cache.frames("willy_walk", Facing.LEFT)
        assert second is first
        assert cache.mirror_ops == ops_after_first  # zero image operations
        assert cache.image_loads == loads_after_first

    def test_neutral_asset_served_as_is_for_either_facing(
        self, asset_root, clip_writer, manifest_factory
    ):
        clip_writer(asset_root, manifest_factory(asset_id="willy_neutral", mirror_allowed=False))
        cache = self.make_cache(asset_root)
        rights = cache.frames("willy_neutral", Facing.RIGHT)
        lefts = cache.frames("willy_neutral", Facing.LEFT)
        assert lefts is rights  # same tuple, no mirror, no re-load
        assert cache.mirror_ops == 0
        assert cache.anchors("willy_neutral", Facing.LEFT) == dict(
            cache.anchors("willy_neutral", Facing.RIGHT)
        )

    def test_anchors_transformed_for_left_facing(self, repo_assets, qapp):
        cache = self.make_cache(repo_assets)
        right = cache.anchors("willy_walk", Facing.RIGHT)
        left = cache.anchors("willy_walk", Facing.LEFT)
        width = cache.frames("willy_walk", Facing.RIGHT)[0].width()
        assert right == {"body_pivot": (50, 56), "ground": (50, 86)}
        assert left == {"body_pivot": (width - 51, 56), "ground": (width - 51, 86)}
        assert left["ground"][1] == right["ground"][1]  # y never changes

    def test_anchor_lookup_is_cached(self, repo_assets, qapp):
        cache = self.make_cache(repo_assets)
        assert cache.anchors("willy_walk", Facing.LEFT) is cache.anchors("willy_walk", Facing.LEFT)
