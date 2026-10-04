"""Detached installer: wait for app exit, replace verified files, restart or roll back."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from update_package import HIDDEN, MANIFEST_NAME, apply_payload


def wait_for_exit(pid):
    if os.name == 'nt':
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.OpenProcess(0x100000, False, pid)
        if not handle and ctypes.get_last_error() != 87:
            raise RuntimeError('Nie można sprawdzić, czy poprzednia aplikacja została zamknięta.')
        if handle:
            try:
                if kernel.WaitForSingleObject(handle, 120000) != 0:
                    raise RuntimeError('Aplikacja nie zamknęła się przed instalacją aktualizacji.')
            finally:
                kernel.CloseHandle(handle)
    else:
        deadline = time.monotonic() + 120
        while True:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            if time.monotonic() > deadline:
                raise RuntimeError('Aplikacja nie zamknęła się przed instalacją aktualizacji.')
            time.sleep(.2)


def restart(root, python, recovery=''):
    args = [str(python), str(root / 'app.py')]
    if recovery:
        args += ['--restore-project', recovery]
    subprocess.Popen(args, cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, creationflags=HIDDEN)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--stage', required=True)
    parser.add_argument('--pid', required=True, type=int)
    parser.add_argument('--recovery', default='')
    args = parser.parse_args()
    root, stage = Path(args.root).resolve(), Path(args.stage).resolve()
    with (stage / 'install.log').open('a', encoding='utf-8') as log:
        try:
            manifest = json.loads((stage / MANIFEST_NAME).read_text(encoding='utf-8'))
            wait_for_exit(args.pid)
            apply_payload(root, stage, manifest, sys.executable, log)
        except Exception as exc:
            print(f'Błąd aktualizacji: {exc}', file=log, flush=True)
            (root / '.local').mkdir(exist_ok=True)
            (root / '.local/update-error.json').write_text(json.dumps({'error': str(exc), 'log': str(stage / 'install.log')}), encoding='utf-8')
        restart(root, sys.executable, args.recovery)


if __name__ == '__main__':
    main()
