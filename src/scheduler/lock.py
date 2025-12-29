"""
Scheduler Lock Utilities (Phase 8B).

Implements a simple single-runner guarantee using an atomic lock file.
The lock file contains:
  - PID (first line)
  - ISO timestamp in UTC (second line)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Optional


def _is_process_alive(pid: int) -> bool:
    try:
        if pid <= 0:
            return False
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _parse_pid(lock_path: str) -> Optional[int]:
    try:
        with open(lock_path, "r", encoding="utf-8") as f:
            first_line = (f.readline() or "").strip()
        return int(first_line) if first_line.isdigit() else None
    except Exception:
        return None


def _parse_timestamp(lock_path: str) -> Optional[datetime]:
    try:
        with open(lock_path, "r", encoding="utf-8") as f:
            _ = f.readline()
            raw_ts = (f.readline() or "").strip()
        if not raw_ts:
            return None
        raw_ts = raw_ts.removesuffix("Z")
        ts = datetime.fromisoformat(raw_ts)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)
    except Exception:
        return None


@dataclass
class SchedulerLock:
    """
    File-based scheduler lock.

    Use `try_acquire()` to become the scheduler leader. If the lock is held by an
    active process (based on PID), acquisition fails. Stale locks are removed.
    """

    lock_path: str
    stale_after_seconds: Optional[int] = None
    is_process_alive: Callable[[int], bool] = _is_process_alive
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)

    _held: bool = False

    def try_acquire(self) -> bool:
        os.makedirs(os.path.dirname(self.lock_path) or ".", exist_ok=True)

        if os.path.exists(self.lock_path):
            existing_pid = _parse_pid(self.lock_path)
            ts = _parse_timestamp(self.lock_path)

            is_stale = False
            if self.stale_after_seconds is not None and ts is not None:
                age = (self.now() - ts).total_seconds()
                is_stale = age > float(self.stale_after_seconds)

            if existing_pid and self.is_process_alive(existing_pid) and not is_stale:
                return False

            try:
                os.remove(self.lock_path)
            except Exception:
                return False

        try:
            fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            return False
        except Exception:
            return False

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(f"{os.getpid()}\n{self.now().isoformat()}Z\n")
            self._held = True
            return True
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            return False

    def release(self) -> None:
        if not self._held:
            return
        self._held = False
        try:
            if os.path.exists(self.lock_path):
                os.remove(self.lock_path)
        except Exception:
            pass

