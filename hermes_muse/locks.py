"""Reentrant process/thread locks for the profile's shared mutation boundary."""

from contextlib import contextmanager
import os
import threading
import fcntl
import time

# Bound each acquisition below the default native loader's 10-second deadline.
# This does not bound a critical section or the whole initialization sequence.
LOCK_WAIT_SECONDS = 2.0
LOCK_POLL_SECONDS = 0.05

_guard = threading.Lock()
_locks = {}
_local = threading.local()


@contextmanager
def file_lock(path):
    # One lock order for install/audit/content and record transactions.
    if path.name != "mutations.lock":
        with file_lock(path.parent / "mutations.lock"):
            with _file_lock(path):
                yield
    else:
        with _file_lock(path):
            yield


@contextmanager
def _file_lock(path):
    key = str(path.absolute())
    with _guard:
        lock = _locks.setdefault(key, threading.RLock())
    from .content_io import DomainError, check_cancelled

    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    check_cancelled()
    if not lock.acquire(timeout=LOCK_WAIT_SECONDS):
        raise DomainError('resource_busy', 'Muse lock wait expired; inspect the original request before retrying')
    try:
        held = getattr(_local, "held", {})
        _local.held = held
        if key in held:
            yield
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        from .content_io import Files

        if path.parent.name != "muse":
            raise ValueError("Lock must belong to the profile Muse root")
        with Files(path.parent.parent).directory() as parent:
            fd = os.open(
                path.name, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600, dir_fd=parent
            )
        acquired = False
        try:
            while True:
                check_cancelled()
                if time.monotonic() >= deadline:
                    raise DomainError('resource_busy', 'Muse lock wait expired; inspect the original request before retrying')
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    acquired = True
                    break
                except BlockingIOError:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise DomainError('resource_busy', 'Muse lock wait expired; inspect the original request before retrying')
                    time.sleep(min(LOCK_POLL_SECONDS, remaining))
            held[key] = fd
            try:
                yield
            finally:
                held.pop(key, None)
        finally:
            try:
                if acquired:
                    fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)
    finally:
        lock.release()
