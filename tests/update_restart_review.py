"""The real detached helper waits for the parent, installs and restarts a test app."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from release_tools import build_release
from update_package import ARCHIVE_NAME, HIDDEN, MANIFEST_NAME, file_hash, unpack_update

ROOT = Path(__file__).resolve().parents[1]
(ROOT / 'checks').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=ROOT / 'checks') as temp:
    work = Path(temp)
    manifest = build_release(ROOT, work / 'dist', 'build-restart-test', '3' * 40, 1)
    stage = work / 'stage'
    payload = unpack_update(work / 'dist' / ARCHIVE_NAME, stage, manifest)
    # A deterministic test application records the restart instead of opening another UI.
    (payload / 'app.py').write_text("import json, sys\nfrom pathlib import Path\nPath(__file__).with_name('restarted.json').write_text(json.dumps(sys.argv))\n", encoding='utf-8')
    manifest['files']['app.py'] = file_hash(payload / 'app.py')
    (stage / MANIFEST_NAME).write_text(json.dumps(manifest), encoding='utf-8')
    root = work / 'app'
    root.mkdir()
    (root / 'app.py').write_text('# still running previous app')
    (root / 'requirements.txt').write_bytes((ROOT / 'requirements.txt').read_bytes())
    recovery = work / 'recovery-project.json'
    recovery.write_text('{"source": "saved current project"}')
    parent = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(1)'], creationflags=HIDDEN)
    helper = subprocess.Popen([sys.executable, str(ROOT / 'update_helper.py'), '--root', str(root),
                               '--stage', str(stage), '--pid', str(parent.pid), '--recovery', str(recovery)], creationflags=HIDDEN)
    try:
        time.sleep(.2)
        assert (root / 'app.py').read_text() == '# still running previous app'
        parent.wait(timeout=5)
        helper.wait(timeout=15)
        assert helper.returncode == 0, (stage / 'install.log').read_text()
        deadline = time.monotonic() + 10
        while not (root / 'restarted.json').exists():
            assert time.monotonic() < deadline, (stage / 'install.log').read_text()
            time.sleep(.05)
        restarted = json.loads((root / 'restarted.json').read_text())
        assert restarted[-2:] == ['--restore-project', str(recovery)]
        assert json.loads((root / 'version.json').read_text())['version'] == 'build-restart-test'
        assert (stage / 'installed.json').exists()
    finally:
        for process in (parent, helper):
            if process.poll() is None:
                process.kill()
                process.wait()
print('PASS: detached installer waits for parent exit, replaces verified files and restarts with the saved project.')
