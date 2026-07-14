from __future__ import annotations

from willy.platform.single_instance import SingleInstanceGuard, default_lock_path


def test_first_acquire_succeeds(tmp_path):
    guard = SingleInstanceGuard(tmp_path / "willy.lock")
    assert guard.acquire() is True
    assert guard.held
    guard.release()


def test_second_instance_is_refused(tmp_path):
    path = tmp_path / "willy.lock"
    first = SingleInstanceGuard(path)
    second = SingleInstanceGuard(path)
    assert first.acquire() is True
    assert second.acquire() is False
    assert not second.held
    first.release()


def test_release_allows_reacquire(tmp_path):
    path = tmp_path / "willy.lock"
    first = SingleInstanceGuard(path)
    first.acquire()
    first.release()
    second = SingleInstanceGuard(path)
    assert second.acquire() is True
    second.release()


def test_stale_unlocked_file_does_not_block(tmp_path):
    # A leftover file without a live lock (e.g. after power loss) must not
    # stop the app from launching.
    path = tmp_path / "willy.lock"
    path.write_text("stale")
    guard = SingleInstanceGuard(path)
    assert guard.acquire() is True
    guard.release()


def test_acquire_is_idempotent_while_held(tmp_path):
    guard = SingleInstanceGuard(tmp_path / "willy.lock")
    assert guard.acquire() is True
    assert guard.acquire() is True
    guard.release()


def test_default_path_under_appdata():
    path = default_lock_path({"APPDATA": "C:/Users/x/AppData/Roaming"})
    assert path.as_posix().endswith("WillyDesktop/willy.lock")
