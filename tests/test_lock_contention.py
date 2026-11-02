"""Bounded contention at the Store initialization boundary; synthetic homes only."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from hermes_muse.store import Store


class LockContentionTests(unittest.TestCase):
    def test_contended_initialization_returns_without_deferred_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary).resolve()
            store = Store(home)
            store.write('fixture', 'sentinel', {'value': 'keep'})
            database = home / 'muse/state.db'
            before = hashlib.sha256(database.read_bytes()).hexdigest()
            script = '''import json, sys
from hermes_muse.store import Store
from hermes_muse.content_io import DomainError
try:
    store = Store(sys.argv[1])
    store.write('fixture', 'sentinel', {'value': 'unexpected'})
    print(json.dumps({'unexpected_write': True}))
except DomainError as error:
    print(json.dumps({'code': error.code}))
'''
            with (home / 'muse/mutations.lock').open('r+b') as holder:
                fcntl.flock(holder, fcntl.LOCK_EX)
                started = time.monotonic()
                result = subprocess.run(
                    [sys.executable, '-c', script, str(home)],
                    cwd=Path(__file__).resolve().parents[1],
                    env={**os.environ, 'HERMES_HOME': str(home)},
                    text=True, capture_output=True, timeout=5,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), {'code': 'resource_busy'})
                self.assertLess(time.monotonic() - started, 5)
                self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(), before)
            self.assertEqual(store.read('fixture', 'sentinel'), {'value': 'keep'})
            store.write('fixture', 'after-release', {'value': 'works'})
            self.assertEqual(store.read('fixture', 'after-release'), {'value': 'works'})


    def test_thread_contention_expires_before_holder_releases(self):
        import threading
        from hermes_muse.locks import file_lock
        from hermes_muse.content_io import DomainError

        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary).resolve()
            store = Store(home)
            outcomes = []
            started = threading.Event()

            def contender():
                started.set()
                try:
                    Store(home)
                    outcomes.append('unexpected_acquisition')
                except DomainError as error:
                    outcomes.append(error.code)

            with file_lock(home / 'muse/mutations.lock'):
                thread = threading.Thread(target=contender)
                thread.start()
                self.assertTrue(started.wait(2))
                thread.join(3)
                finished_while_held = not thread.is_alive()
            thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertTrue(finished_while_held)
            self.assertEqual(outcomes, ['resource_busy'])
            store.write('fixture', 'after-release', {'value': 'works'})

    def test_reentrant_transactions_preserve_outer_exclusion(self):
        from hermes_muse.locks import file_lock

        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary).resolve()
            store = Store(home)
            path = home / 'muse/mutations.lock'
            script = '''import fcntl, sys
with open(sys.argv[1], 'r+b') as candidate:
    try:
        fcntl.flock(candidate, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print('blocked')
    else:
        print('acquired')
'''
            with file_lock(path):
                with file_lock(path):
                    store.write('fixture', 'nested', {'value': 'kept'})
                held = subprocess.run([sys.executable, '-c', script, str(path)],
                                      capture_output=True, text=True, timeout=5, check=True)
                self.assertEqual(held.stdout.strip(), 'blocked')
            released = subprocess.run([sys.executable, '-c', script, str(path)],
                                      capture_output=True, text=True, timeout=5, check=True)
            self.assertEqual(released.stdout.strip(), 'acquired')
            self.assertEqual(store.read('fixture', 'nested'), {'value': 'kept'})


if __name__ == '__main__':
    unittest.main()
