"""One-date local research runs; never invoke agents in --check mode."""
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
from zoneinfo import ZoneInfo

folder = Path(__file__).resolve().parent
config = json.loads((folder / 'runner-config.json').read_text())
role = sys.argv[1]
if role not in ('codex', 'claude'):
    raise SystemExit('Unknown role')
if '--check' in sys.argv:
    assert Path(config[role]).is_file()
    assert (folder / f'{role.upper()}_TASK.md').is_file()
    assert (folder / 'HANDOFF.md').is_file()
    print(f'{role}: executable and task present; no agent started')
    raise SystemExit(0)
now = datetime.datetime.now(ZoneInfo('Asia/Ho_Chi_Minh'))
if now.date().isoformat() != '2026-10-07':
    raise SystemExit(0)
lock = (folder / f'{role}.lock').open('a')
try:
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    raise SystemExit(0)
marker = folder / f'{role}.started'
try:
    fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
except FileExistsError:
    raise SystemExit(0)
with os.fdopen(fd, 'w') as stream:
    stream.write(now.isoformat())

def status(state, **details):
    # Serializes read/modify/write in case the two launches overlap unexpectedly.
    with (folder / 'status.lock').open('a') as guard:
        fcntl.flock(guard, fcntl.LOCK_EX)
        target = folder / 'execution-status.json'
        data = json.loads(target.read_text()) if target.exists() else {}
        data[role] = {'state': state, 'time': datetime.datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).isoformat(), **details}
        temporary = folder / 'execution-status.tmp'
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        temporary.replace(target)

prompt = (folder / f'{role.upper()}_TASK.md').read_text()
if role == 'codex':
    command = [config[role], 'exec', '-C', config['root'], '-s', 'workspace-write', '-c', 'approval_policy="never"', '--color', 'never', '-o', str(folder / 'CODEX_FINAL.md'), '-']
    duration = 19 * 60
else:
    command = [config[role], '-p', '--model', 'opus', '--effort', 'medium', '--permission-mode', 'acceptEdits', '--permission-prompts', 'none', '--allowedTools', 'Read,Glob,Grep,WebSearch,WebFetch,Write(doc/security-research/**),Edit(doc/security-research/**)', '--output-format', 'json']
    duration = 45 * 60
status('running')
environment = os.environ.copy()
environment['PATH'] = '/home/abel/.local/bin:/usr/local/bin:/usr/bin:/bin:' + environment.get('PATH', '')
try:
    with (folder / 'logs' / f'{role}.log').open('w') as log:
        result = subprocess.run(command, input=prompt, text=True, cwd=config['root'], env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=duration)
    status('finished' if result.returncode == 0 else 'failed', exit_code=result.returncode)
except subprocess.TimeoutExpired:
    status('timeout', seconds=duration)
except Exception as error:
    status('failed', error=str(error))
    raise
