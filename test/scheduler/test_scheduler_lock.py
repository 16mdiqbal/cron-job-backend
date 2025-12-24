from datetime import datetime, timedelta, timezone

from src.scheduler.lock import SchedulerLock


def test_scheduler_lock_acquire_and_release(tmp_path):
    lock_path = str(tmp_path / "scheduler.lock")
    lock = SchedulerLock(lock_path)

    assert lock.try_acquire() is True
    assert lock.try_acquire() is False

    lock.release()
    assert lock.try_acquire() is True


def test_scheduler_lock_stale_pid_is_replaced(tmp_path):
    lock_path = tmp_path / "scheduler.lock"
    lock_path.write_text("999999\n2000-01-01T00:00:00Z\n", encoding="utf-8")

    lock = SchedulerLock(str(lock_path))
    assert lock.try_acquire() is True


def test_scheduler_lock_respects_active_pid_when_provided(tmp_path):
    lock_path = tmp_path / "scheduler.lock"
    lock_path.write_text("123\n2000-01-01T00:00:00Z\n", encoding="utf-8")

    lock = SchedulerLock(str(lock_path), is_process_alive=lambda pid: pid == 123)
    assert lock.try_acquire() is False


def test_scheduler_lock_can_break_stale_after_seconds(tmp_path):
    lock_path = tmp_path / "scheduler.lock"
    lock_path.write_text("123\n2000-01-01T00:00:00Z\n", encoding="utf-8")

    now = datetime(2000, 1, 1, 0, 0, 2, tzinfo=timezone.utc)
    lock = SchedulerLock(
        str(lock_path),
        stale_after_seconds=1,
        is_process_alive=lambda pid: pid == 123,
        now=lambda: now,
    )
    assert lock.try_acquire() is True

