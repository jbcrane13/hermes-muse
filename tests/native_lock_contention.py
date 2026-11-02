"""Real plugin-loader contention/recovery in disposable, credential-free homes.

No gateway, model request, live profile, notification delivery or live lock.
"""
import fcntl
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PROBE = r'''
import json, os, socket, sys, threading
from pathlib import Path
home = Path(os.environ['HERMES_HOME']).resolve()
assert home.name.startswith('muse-loader-fixture-')
sys.path.insert(0, sys.argv[1])
if os.environ.get('HERMES_SOURCE'):
    sys.path.insert(0, os.environ['HERMES_SOURCE'])

def audit(event, args):
    if event in {'socket.connect', 'os.system'}:
        raise RuntimeError('Unexpected network or shell in isolated loader probe')
    if event == 'subprocess.Popen':
        command = args[1]
        readonly = {'rev-parse', 'branch', 'log', 'tag', 'rev-list', '--no-optional-locks'}
        if not (isinstance(command, (list, tuple)) and Path(command[0]).name == 'git'
                and len(command) > 1 and command[1] in readonly):
            raise RuntimeError('Unexpected subprocess in isolated loader probe')
    if event == 'open' and isinstance(args[0], (str, bytes)):
        mode, flags = args[1], args[2]
        writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC))
        if writing and not Path(os.fsdecode(args[0])).resolve().is_relative_to(home):
            raise RuntimeError('Write outside disposable loader home')
sys.addaudithook(audit)
from hermes_cli.plugins import discover_plugins, get_plugin_manager
from tools.registry import registry
discover_plugins(force=True)
loaded = get_plugin_manager()._plugins.get('hermes-muse')
entry = registry.get_entry('muse_manage')
result = {'enabled': bool(loaded and loaded.enabled),
          'error': str(getattr(loaded, 'error', '')),
          'tool_registered': entry is not None,
          'remaining_loader_threads': sum(t.name == 'plugin-load:hermes-muse' for t in threading.enumerate())}
if sys.argv[2] == 'available':
    from tools.skills_tool import skill_view
    from cron.jobs import list_jobs
    skill = json.loads(skill_view('hermes-muse:companion'))
    result['companion_loaded'] = bool(skill.get('success') and skill.get('content'))
    result['fixture_jobs'] = len(list_jobs(include_disabled=True))
    entry.handler.__self__.close()
print(json.dumps(result), flush=True)
'''


def main():
    with tempfile.TemporaryDirectory(prefix='muse-loader-fixture-') as temporary:
        home = Path(temporary).resolve()
        (home / 'muse').mkdir(mode=0o700)
        (home / 'config.yaml').write_text('plugins:\n  enabled: [hermes-muse]\ntimezone: UTC\n')
        shutil.copytree(ROOT, home / 'plugins/hermes-muse',
                        ignore=shutil.ignore_patterns('.git', '__pycache__', '.venv'))
        env = {'PATH': os.environ.get('PATH', ''), 'HOME': str(home),
               'HERMES_HOME': str(home), 'TMPDIR': str(home),
               'PYTHONDONTWRITEBYTECODE': '1'}
        if os.environ.get('HERMES_SOURCE'):
            env['HERMES_SOURCE'] = os.environ['HERMES_SOURCE']
        # Only this synthetic file is locked. No original state is copied.
        with (home / 'muse/mutations.lock').open('w+b') as holder:
            fcntl.flock(holder, fcntl.LOCK_EX)
            blocked = subprocess.run([sys.executable, '-c', PROBE, str(ROOT), 'contended'],
                                     cwd=home / 'muse', env=env,
                                     capture_output=True, text=True, timeout=8)
            assert blocked.returncode == 0, blocked.stderr
            evidence = json.loads(blocked.stdout)
            assert not evidence['enabled'] and not evidence['tool_registered'], evidence
            assert 'lock wait expired' in evidence['error'], evidence
            assert evidence['remaining_loader_threads'] == 0, evidence
            before = sorted(str(p.relative_to(home / 'muse')) for p in (home / 'muse').rglob('*'))
            assert before == ['mutations.lock'], before
        recovered = subprocess.run([sys.executable, '-c', PROBE, str(ROOT), 'available'],
                                   cwd=home / 'muse', env=env,
                                   capture_output=True, text=True, timeout=15, check=True)
        result = json.loads(recovered.stdout)
        assert result['enabled'] and result['tool_registered'] and result['companion_loaded'], result
        assert result['fixture_jobs'] == 6 and result['remaining_loader_threads'] == 0, result
        print(json.dumps({'held_lock': evidence, 'after_fixture_release': result,
                          'network_and_subprocess_guard': 'enabled',
                          'credentials_cleared': True, 'live_profile_used': False}))


if __name__ == '__main__':
    main()
