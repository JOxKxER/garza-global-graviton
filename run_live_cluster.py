import subprocess
import time
import sys
import os
from pathlib import Path

processes = {}

def find_ngrok():
    # Search common Windows install locations for ngrok.exe
    search_dirs = [
        os.environ.get('LOCALAPPDATA', ''),
        os.path.join(os.environ.get('USERPROFILE', ''), 'Downloads'),
        os.environ.get('ProgramFiles', ''),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ngrok'),
        'C:\\tools\\ngrok',
        'V:\\03_Source_Code'
    ]
    for d in search_dirs:
        if d:
            for p in Path(d).rglob('ngrok.exe'):
                return str(p)
    return 'ngrok'

NGROK_BIN = find_ngrok()

def start_process(name, cmd):
    print(f'[*] Spawning service: {name} -> {cmd}')
    p = subprocess.Popen(cmd, shell=True)
    processes[name] = {'process': p, 'cmd': cmd}

def monitor_cluster():
    # 1. Start primary services
    ngrok_cmd = f'"{NGROK_BIN}" http 8000 --url=stamp-dangling-dugout.ngrok-free.dev'
    start_process('NGROK_TUNNEL', ngrok_cmd)
    time.sleep(2)
    start_process('WORKER_NODE_1', f'"{sys.executable}" shard_worker.py')
    start_process('WORKER_NODE_2', f'"{sys.executable}" shard_worker.py')
    time.sleep(1)
    start_process('TRAFFIC_DAEMON', f'"{sys.executable}" traffic_daemon.py')
    
    print('=' * 60)
    print('>>> GARZA GLOBAL GRAVITON: LIVE SUPERVISOR ACTIVE <<<')
    print('Coordinator, Workers, Traffic, and Public TLS are Online.')
    print('=' * 60)

    try:
        while True:
            for name, meta in list(processes.items()):
                p = meta['process']
                if p.poll() is not None:
                    print(f'[WARN] Service {name} exited with code {p.returncode}. Reviving...')
                    new_p = subprocess.Popen(meta['cmd'], shell=True)
                    processes[name]['process'] = new_p
            time.sleep(3)
    except KeyboardInterrupt:
        print('\n[!] Shutting down live cluster...')
        for name, meta in processes.items():
            meta['process'].terminate()
        sys.exit(0)

if __name__ == '__main__':
    monitor_cluster()
