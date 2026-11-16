"""Own only this lab's localhost MongoDB process. Never remove saved data."""
import argparse
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import time
from pymongo import MongoClient
from pymongo.errors import PyMongoError

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get('MONGO16_DATA', ROOT / 'data')).resolve()
PORT = int(os.environ.get('MONGO16_PORT', '27117'))


def owned_pid():
    pidfile = DATA / 'mongod.pid'
    if not pidfile.exists():
        return None
    pid = int(pidfile.read_text())
    try:
        if Path(f'/proc/{pid}/stat').read_text().split()[2] == 'Z':
            return None
        args = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
    except FileNotFoundError:
        return None
    # Linux/Codespaces: guard against PID reuse and unrelated MongoDB servers.
    if b'--dbpath' not in args or str(DATA / 'db').encode() not in args:
        raise RuntimeError('PID file points to another process. Inspect it before proceeding.')
    return pid


def start():
    if owned_pid():
        print('This lab server is already running.')
        return
    binary = shutil.which('mongod')
    if not binary:
        raise RuntimeError('mongod is missing. Run bash install.sh first.')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', PORT))  # Refuse to reuse an occupied port.
    (DATA / 'db').mkdir(parents=True, exist_ok=True, mode=0o700)
    DATA.chmod(0o700)
    args = [binary, '--dbpath', str(DATA / 'db'), '--port', str(PORT),
            '--bind_ip', '127.0.0.1', '--auth', '--logpath', str(DATA / 'mongod.log'),
            '--logappend', '--wiredTigerCacheSizeGB', '0.25']
    process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, start_new_session=True)
    (DATA / 'mongod.pid').write_text(str(process.pid))
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'mongod exited. Read {DATA / "mongod.log"}')
        try:
            with MongoClient('127.0.0.1', PORT, directConnection=True,
                             serverSelectionTimeoutMS=500) as client:
                client.admin.command('ping')
            print(f'Listening on 127.0.0.1:{PORT} with authorization enabled.')
            return
        except PyMongoError:
            time.sleep(0.2)
    raise RuntimeError('Startup timeout. Inspect the log; use stop before retrying.')


def stop():
    pid = owned_pid()
    if not pid:
        print('This lab server is stopped.')
        return
    os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            state = Path(f'/proc/{pid}/stat').read_text().split()[2]
            if state == 'Z':
                break
        except FileNotFoundError:
            break
        time.sleep(0.2)
    else:
        raise RuntimeError('Shutdown is still pending. Inspect the log; do not remove data files.')
    (DATA / 'mongod.pid').unlink(missing_ok=True)
    print('Stopped this lab server; data kept.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['start', 'stop', 'status'])
    action = parser.parse_args().action
    if action == 'start': start()
    elif action == 'stop': stop()
    else: print('Running' if owned_pid() else 'Stopped')
