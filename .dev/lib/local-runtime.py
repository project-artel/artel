#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
import signal
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

PORTS = {'server': (8090, '/v3/api-docs'), 'agent': (8000, '/health'), 'home': (5176, '/'), 'support': (9201, '/minio/health/live')}
CURRENT_STEP = ''

def step(label):
    global CURRENT_STEP
    CURRENT_STEP = label
    print('==> '+label, flush=True)

def runtime_path(explicit):
    if explicit:
        path = Path(explicit).expanduser().resolve()
    elif os.environ.get('ARTEL_LOCAL_RUNTIME'):
        path = Path(os.environ['ARTEL_LOCAL_RUNTIME']).expanduser().resolve()
    else:
        candidates = list((Path.home()/'dev/artel/.work').glob('latest-pr-local-*'))
        candidates += list((Path(__file__).resolve().parents[2]/'.work').glob('latest-pr-local-*'))
        candidates = [p for p in candidates if (p/'pids.json').is_file() and (p/'server.env.json').is_file()]
        if not candidates:
            raise RuntimeError('준비된 환경이 없습니다. --runtime으로 기존 실행 폴더를 지정해 주세요.')
        path = max(candidates, key=lambda p: p.name).resolve()
    if not (path/'pids.json').is_file():
        raise RuntimeError(f'pids.json이 없습니다: {path}')
    return path

def owned(root, name, pid):
    proc = Path('/proc')/str(pid)
    try:
        args = (proc/'cmdline').read_bytes().decode().split('\0')
        if ') Z' in (proc/'stat').read_text():
            return False
        cwd = (proc/'cwd').resolve()
        if name == 'support':
            script = Path(__file__).resolve().parents[2]/'.work/latest-pr-local-support.py'
            return str(script) in args and cwd == root
        expected = {'server': 'artel-orchestration-server', 'agent': 'artel-agent-server', 'home': 'artel-home'}[name]
        if cwd != root/expected:
            return False
        if name == 'server':
            metadata=json.loads((root/'pids.json').read_text())
            jar=Path(metadata.get('serverJar',str(root/expected/'target/artel-orchestration-server-0.0.1-SNAPSHOT.jar'))).resolve()
            if not jar.is_relative_to(root):
                return False
            return '-jar' in args and str(jar) in args
        if name == 'agent':
            return 'uvicorn' in args and 'app.main:app' in args
        return 'node_modules/.bin/vite' in args
    except (OSError, KeyError, UnicodeError):
        return False

def http_ready(name):
    port, path = PORTS[name]
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=3) as response:
            return response.status == 200
    except OSError:
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['status', 'revisions', 'logs', 'up', 'down'])
    parser.add_argument('service', nargs='?', choices=list(PORTS))
    parser.add_argument('--runtime')
    parser.add_argument('--lines', type=int, default=40)
    parser.add_argument('--follow', action='store_true')
    args = parser.parse_args()
    if args.lines < 1 or args.lines > 10000:
        parser.error('--lines는 1~10000이어야 합니다')
    if args.action != 'logs' and (args.service or args.follow):
        parser.error('service와 --follow는 logs에서만 사용합니다')
    root = runtime_path(args.runtime)
    pids = json.loads((root/'pids.json').read_text())
    alive = {name: owned(root, name, pids.get(name, -1)) for name in PORTS}
    if args.action == 'status':
        print('환경:', root)
        for name in PORTS:
            print(f'{name:8} PID={pids.get(name, "-")} owned={alive[name]} HTTP={http_ready(name)}')
        print('웹: http://127.0.0.1:5176/projects/1/qa')
        print('로컬 로그인: http://127.0.0.1:5177/login')
        print('로그:', root)
    elif args.action == 'revisions':
        for name, sha in json.loads((root/'revisions.json').read_text()).items():
            print(name, sha)
    elif args.action == 'logs':
        if not args.service:
            parser.error('logs에는 서비스 이름이 필요합니다')
        command = ['tail', '-n', str(args.lines)]
        if args.follow:
            command.append('-f')
        logfile=root/(args.service+'.log')
        if args.service == 'server' and pids.get('serverLog'):
            logfile=(root/pids['serverLog']).resolve()
            if not logfile.is_relative_to(root):
                raise RuntimeError('로그 경로가 실행 환경 밖에 있습니다')
        subprocess.run(command+[str(logfile)], check=True)
    elif args.action == 'up':
        if all(alive.values()):
            if not all(http_ready(name) for name in PORTS):
                raise RuntimeError('기존 PID는 실행 중이지만 일부 HTTP 응답이 없습니다. logs를 확인해 주세요. 재시작하지 않았습니다.')
            print('이미 실행 중입니다. 기존 PID를 유지합니다.')
            return
        if any(alive.values()):
            raise RuntimeError('일부 서비스가 실행 중입니다. 자동으로 재시작하지 않습니다. status와 logs를 확인해 주세요.')
        for name in PORTS:
            try:
                with socket.create_connection(('127.0.0.1', PORTS[name][0]), timeout=1):
                    pass
            except OSError:
                continue
            raise RuntimeError(f'{name}의 {PORTS[name][0]} 포트를 다른 서비스가 사용 중입니다. 기존 프로세스를 유지합니다.')
        script = Path(__file__).resolve().parents[2]/'.work/latest-pr-local-start.py'
        if not script.is_file():
            raise RuntimeError(f'기존 시작 스크립트가 없습니다: {script}')
        if not shutil.which('docker'):
            raise RuntimeError('docker 실행 파일이 필요합니다')
        for required in ['server.env.json', 'agent.env.json', 'artel-orchestration-server/target/artel-orchestration-server-0.0.1-SNAPSHOT.jar', 'artel-agent-server/.venv/bin/python', 'artel-home/node_modules/.bin/vite']:
            if not (root/required).is_file():
                raise RuntimeError(f'시작에 필요한 파일이 없습니다: {root/required}')
        step('기존 의존 container 시작')
        for container in ['artel-local-postgres', 'artel-local-redis', 'artel-eval-20261022-minio']:
            subprocess.run(['docker', 'start', container], check=True)
        step('PostgreSQL 연결 대기')
        deadline = time.monotonic()+30
        while subprocess.run(['docker', 'exec', 'artel-local-postgres', 'pg_isready', '-U', 'postgres'], capture_output=True).returncode:
            if time.monotonic() >= deadline:
                raise RuntimeError('PostgreSQL이 30초 안에 준비되지 않았습니다')
            time.sleep(1)
        step('기존 서비스 시작 스크립트 실행')
        start_env = dict(os.environ, ARTEL_LOCAL_RUNTIME=str(root))
        subprocess.run([sys.executable, str(script)], env=start_env, check=True)
        step('서비스 HTTP 응답 대기')
        deadline = time.monotonic()+60
        while not all(http_ready(name) for name in PORTS):
            if time.monotonic() >= deadline:
                raise RuntimeError('60초 안에 준비되지 않았습니다. local logs로 실패한 서비스를 확인해 주세요.')
            time.sleep(1)
        print('웹: http://127.0.0.1:5176/ · 로그:', root)
    elif args.action == 'down':
        for name in ['home', 'agent', 'server', 'support']:
            if alive[name]:
                os.kill(pids[name], signal.SIGTERM)
                print(name, '중지 요청', pids[name])
        print('게임과 DB container는 유지했습니다.')

if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print('error:', exc, file=sys.stderr)
        if CURRENT_STEP:
            print('실패한 단계:', CURRENT_STEP, file=sys.stderr)
        sys.exit(1)
