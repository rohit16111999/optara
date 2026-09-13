"""Run the existing FastAPI worker and production Next.js server in one container."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen

root=Path(__file__).resolve().parents[1]
os.chdir(root)
domain=os.getenv('RAILWAY_PUBLIC_DOMAIN')
if domain and not os.getenv('ALLOWED_ORIGINS'):
    os.environ['ALLOWED_ORIGINS']='https://'+domain
children=[]
stopping=False

def stop(*_):
    global stopping
    stopping=True

signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)
try:
    children.append(subprocess.Popen([sys.executable,'-m','uvicorn','backend.app.main:app','--host','127.0.0.1','--port','8000','--no-access-log'],start_new_session=True))
    ready=False
    deadline=time.monotonic()+60
    while not stopping and children[0].poll() is None and time.monotonic()<deadline:
        try:
            with urlopen('http://127.0.0.1:8000/api/health',timeout=2) as response:
                ready=response.status==200
            if ready:break
        except (URLError,TimeoutError):pass
        time.sleep(.25)
    if not ready:raise SystemExit('Backend did not become healthy; frontend was not exposed.')
    children.append(subprocess.Popen(['node','node_modules/next/dist/bin/next','start','--hostname','0.0.0.0','--port',os.getenv('PORT','3000')],cwd=root/'frontend',start_new_session=True))
    while not stopping and all(p.poll() is None for p in children):time.sleep(.5)
finally:
    for process in children:
        if process.poll() is None:os.killpg(process.pid,signal.SIGTERM)
    for process in children:
        try:process.wait(timeout=8)
        except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL)
