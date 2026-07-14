"""Forbidden-API static scan (A-11): unit tests of the scanner itself, plus
the actual CI tripwire — a real scan of this repo's `src/willy/` tree,
running as a normal pytest test so it's wired into CI on every PR without a
separate workflow step."""

from __future__ import annotations

from pathlib import Path

import willy
from tools.test_harness.forbidden_api_check import scan_source_tree

SRC_ROOT = Path(willy.__file__).resolve().parents[1]


class TestScanSourceTree:
    def test_clean_tree_has_no_violations(self, tmp_path):
        (tmp_path / "clean.py").write_text("x = 1\n", encoding="utf-8")
        assert scan_source_tree(tmp_path) == []

    def test_detects_pyautogui_import(self, tmp_path):
        (tmp_path / "bad.py").write_text("import pyautogui\n", encoding="utf-8")
        violations = scan_source_tree(tmp_path)
        assert len(violations) == 1
        assert violations[0].reason == "forbidden input-automation API"

    def test_detects_keyboard_from_import(self, tmp_path):
        (tmp_path / "bad.py").write_text("from keyboard import press\n", encoding="utf-8")
        violations = scan_source_tree(tmp_path)
        assert len(violations) == 1

    def test_detects_send_input_call(self, tmp_path):
        (tmp_path / "bad.py").write_text("ctypes.windll.user32.SendInput(1, 2, 3)\n", "utf-8")
        violations = scan_source_tree(tmp_path)
        assert len(violations) == 1

    def test_detects_write_outside_persistence(self, tmp_path):
        (tmp_path / "bad.py").write_text('open("out.txt", "w")\n', encoding="utf-8")
        violations = scan_source_tree(tmp_path)
        assert len(violations) == 1
        assert violations[0].reason == "file write outside persistence/"

    def test_writes_inside_persistence_are_allowed(self, tmp_path):
        persistence_dir = tmp_path / "willy" / "persistence"
        persistence_dir.mkdir(parents=True)
        (persistence_dir / "database.py").write_text(
            "path.mkdir(parents=True, exist_ok=True)\n", encoding="utf-8"
        )
        assert scan_source_tree(tmp_path) == []

    def test_writes_inside_single_instance_are_allowed(self, tmp_path):
        platform_dir = tmp_path / "willy" / "platform"
        platform_dir.mkdir(parents=True)
        (platform_dir / "single_instance.py").write_text(
            "self._path.parent.mkdir(parents=True, exist_ok=True)\n", encoding="utf-8"
        )
        assert scan_source_tree(tmp_path) == []

    def test_comment_mentioning_keyboard_focus_is_not_flagged(self, tmp_path):
        # Regression guard: "keyboard focus" is legitimate prose in this
        # codebase (WillyWindow never steals keyboard focus); only an
        # actual import/from of the `keyboard` package should trip the scan.
        (tmp_path / "ok.py").write_text("# Never steals keyboard focus.\nx = 1\n", encoding="utf-8")
        assert scan_source_tree(tmp_path) == []


class TestRepoSourceTreeIsClean:
    def test_repo_src_tree_has_no_forbidden_api_usage(self):
        violations = scan_source_tree(SRC_ROOT)
        assert violations == [], "\n".join(
            f"{v.path}:{v.line_number}: {v.reason}: {v.line}" for v in violations
        )
