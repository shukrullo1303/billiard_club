"""Local launcher used by RUN.command (macOS) and RUN.bat (Windows)."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent
URL = 'http://127.0.0.1:8000/'


def runtime():
    candidates = [ROOT / folder / binary for folder in ('.venv', 'venv')
                  for binary in ('Scripts/python.exe', 'bin/python')]
    candidates.append(Path(sys.executable))
    for executable in candidates:
        if not executable.is_file():
            continue
        env = os.environ.copy()
        # This checkout may contain an environment copied from another Mac.
        if executable == Path(sys.executable):
            version = f'python{sys.version_info.major}.{sys.version_info.minor}'
            packages = ROOT / 'venv' / 'lib' / version / 'site-packages'
            if packages.is_dir():
                env['PYTHONPATH'] = str(packages) + os.pathsep + env.get('PYTHONPATH', '')
        probe = subprocess.run([str(executable), '-c', 'import django, PIL; assert django.VERSION >= (6, 0)'], env=env, capture_output=True)
        if probe.returncode == 0:
            return str(executable), env
    raise RuntimeError('Python 3.12+ va requirements.txt dagi kutubxonalar kerak. Virtual muhitni tayyorlang.')


def open_when_ready(stop):
    while not stop.wait(0.5):
        try:
            with urllib.request.urlopen(URL, timeout=1) as response:
                if response.status == 200:
                    webbrowser.open(URL)
                    return
        except Exception:
            pass


def main():
    os.chdir(ROOT)
    python, env = runtime()
    command = [python, str(ROOT / 'manage.py')]
    if '--check' in sys.argv:
        return subprocess.call(command + ['check'], env=env)
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1', 8000)) == 0:
            print('8000-port band. Avval oldingi server oynasida Ctrl+C bosing, keyin RUN ni qayta oching.')
            return 1
    if subprocess.call(command + ['migrate', '--noinput'], env=env):
        return 1
    print(f'Bilyard ishga tushmoqda: {URL}\nTo‘xtatish uchun Ctrl+C bosing.', flush=True)
    stop = threading.Event()
    threading.Thread(target=open_when_ready, args=(stop,), daemon=True).start()
    try:
        return subprocess.call(command + ['runserver', '127.0.0.1:8000', '--noreload'], env=env)
    except KeyboardInterrupt:
        print('\nServer to‘xtatildi.')
        return 0
    finally:
        stop.set()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (RuntimeError, OSError) as error:
        print(f'Ishga tushmadi: {error}')
        sys.exit(1)
