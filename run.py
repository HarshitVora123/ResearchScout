#!/usr/bin/env python3
"""
ResearchScout Project Manager — Single Script to Start, Stop, and Monitor the Project.

Usage:
    python run.py start     — Start both Backend (port 8000) and Frontend (port 3000)
    python run.py stop      — Stop all running project processes
    python run.py restart   — Restart both Backend and Frontend
    python run.py status    — Check if Backend & Frontend are running
"""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

# Force UTF-8 stdout/stderr encoding for Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

# Find the venv python
VENV_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
if not VENV_PYTHON.exists():
    VENV_PYTHON = BACKEND_DIR / ".venv" / "bin" / "python"
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)

LOG_DIR = ROOT_DIR / ".logs"
LOG_DIR.mkdir(exist_ok=True)

PID_FILE = LOG_DIR / "pids.json"

IS_WIN = sys.platform == "win32"


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            return True
    except OSError:
        return False


def save_pids(**kwargs) -> None:
    data = load_pids()
    data.update({k: v for k, v in kwargs.items() if v is not None})
    PID_FILE.write_text(json.dumps(data))


def load_pids() -> dict:
    try:
        return json.loads(PID_FILE.read_text())
    except Exception:
        return {}


def kill_pid(pid: int) -> None:
    try:
        if IS_WIN:
            subprocess.run(["taskkill", "/F", "/PID", str(pid), "/T"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(["kill", "-9", str(pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def kill_port(port: int) -> None:
    """Kill any process listening on port (Windows only)."""
    if not IS_WIN:
        return
    try:
        out = subprocess.check_output("netstat -ano -p tcp", shell=True, text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            p = line.strip().split()
            if len(p) >= 5 and f":{port}" in p[1] and p[3] == "LISTENING":
                try:
                    kill_pid(int(p[4]))
                except ValueError:
                    pass
    except Exception:
        pass


# ── Launch logic ──────────────────────────────────────────────────────────────

def launch_detached(cmd: list[str], cwd: str, log_path: str) -> "subprocess.Popen | None":
    """
    Launch a process that survives after this script exits.
    On Windows: uses DETACHED_PROCESS + CREATE_NEW_PROCESS_GROUP.
    On Unix:    uses start_new_session=True.
    """
    log_fh = open(log_path, "w", encoding="utf-8", buffering=1)

    common = dict(
        cwd=cwd,
        stdout=log_fh,
        stderr=subprocess.STDOUT,
    )

    if IS_WIN:
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            return subprocess.Popen(cmd, creationflags=flags, close_fds=True, **common)
        except OSError:
            # Fallback: no DETACHED_PROCESS (some restricted envs)
            return subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP, **common)
    else:
        return subprocess.Popen(cmd, start_new_session=True, **common)


def wait_for_port(port: int, timeout: int = 30, label: str = "") -> bool:
    deadline = time.time() + timeout
    dots = 0
    while time.time() < deadline:
        if is_port_open(port):
            return True
        time.sleep(0.5)
        dots += 1
        if dots % 4 == 0:
            elapsed = timeout - (deadline - time.time())
            print(f"  ... waiting ({elapsed:.0f}s)", end="\r")
    return False


# ── Commands ──────────────────────────────────────────────────────────────────

def start_backend() -> int | None:
    if is_port_open(8000):
        print("  [✓] Backend already running on http://localhost:8000")
        return None

    log_path = str(LOG_DIR / "backend.log")
    print("  [+] Starting Backend on http://localhost:8000 ...")

    cmd = [str(VENV_PYTHON), "-m", "uvicorn", "app.main:app",
           "--host", "0.0.0.0", "--port", "8000"]

    proc = launch_detached(cmd, str(BACKEND_DIR), log_path)
    if proc is None:
        print("  [!] Failed to spawn backend process.")
        return None

    if wait_for_port(8000, timeout=25, label="Backend"):
        print(f"  [✓] Backend started! (PID {proc.pid})")
        return proc.pid
    else:
        # Show tail of log to diagnose
        try:
            lines = Path(log_path).read_text(encoding="utf-8", errors="replace").splitlines()
            if lines:
                print("  [!] Backend log (last 5 lines):")
                for ln in lines[-5:]:
                    print(f"      {ln}")
        except Exception:
            pass
        print("  [!] Backend did not bind to port 8000 within 25s.")
        return proc.pid


def start_frontend() -> int | None:
    if is_port_open(3000):
        print("  [✓] Frontend already running on http://localhost:3000")
        return None

    log_path = str(LOG_DIR / "frontend.log")
    print("  [+] Starting Frontend on http://localhost:3000 ...")

    npm = "npm.cmd" if IS_WIN else "npm"
    cmd = [npm, "run", "dev"]

    proc = launch_detached(cmd, str(FRONTEND_DIR), log_path)
    if proc is None:
        print("  [!] Failed to spawn frontend process.")
        return None

    if wait_for_port(3000, timeout=40, label="Frontend"):
        print(f"  [✓] Frontend started! (PID {proc.pid})")
        return proc.pid
    else:
        print("  [!] Frontend did not bind to port 3000 within 40s. Check .logs/frontend.log")
        return proc.pid


def start_all() -> None:
    print("\n🚀 Starting ResearchScout...")
    print("-" * 45)
    b_pid = start_backend()
    f_pid = start_frontend()
    save_pids(backend=b_pid, frontend=f_pid)
    print("\n" + "=" * 45)
    print("🎉 ResearchScout is running!")
    print("   🌐 Frontend:  http://localhost:3000")
    print("   ⚡ Backend:   http://localhost:8000")
    print("   📚 API Docs:  http://localhost:8000/docs")
    print("   📄 Logs:      .logs/backend.log & .logs/frontend.log")
    print("=" * 45)
    print("💡 Run  python run.py stop  to stop all services.\n")


def stop_all() -> None:
    print("\n🛑 Stopping ResearchScout...")
    pids = load_pids()
    for name, pid in pids.items():
        print(f"  [-] Stopping {name} (PID {pid})...")
        kill_pid(pid)
    # Force-kill by port (catches any strays)
    kill_port(8000)
    kill_port(3000)
    if PID_FILE.exists():
        PID_FILE.unlink()
    time.sleep(1)
    print("✅ Done.\n")


def status() -> None:
    import urllib.request
    print("\n🔍 ResearchScout Status:")
    be = is_port_open(8000)
    fe = is_port_open(3000)
    print(f"  ⚡ Backend  (8000): {'🟢 RUNNING' if be else '🔴 STOPPED'}")
    print(f"  🌐 Frontend (3000): {'🟢 RUNNING' if fe else '🔴 STOPPED'}")
    if be:
        try:
            r = urllib.request.urlopen("http://localhost:8000/health", timeout=2)
            d = json.loads(r.read())
            print(f"     API: {d.get('status')} v{d.get('version','?')}")
        except Exception:
            pass
    p = load_pids()
    if p:
        print(f"  📌 PIDs: {p}")
    print()


def main():
    action = sys.argv[1].lower() if len(sys.argv) > 1 else "help"
    if action == "start":
        start_all()
    elif action == "stop":
        stop_all()
    elif action == "restart":
        stop_all()
        time.sleep(2)
        start_all()
    elif action == "status":
        status()
    else:
        print("\n🔬 ResearchScout Project Controller")
        print("  python run.py start    — Start Backend + Frontend")
        print("  python run.py stop     — Stop all services")
        print("  python run.py restart  — Restart all services")
        print("  python run.py status   — Check status\n")


if __name__ == "__main__":
    main()
