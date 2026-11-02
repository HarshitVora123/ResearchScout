#!/usr/bin/env python3
"""
ResearchScout Project Manager — Single Script to Start, Stop, and Monitor the Project.

Usage:
    python run.py                — Start Backend & Frontend, open browser, press Ctrl+C to stop
    python run.py start          — Start in foreground (interactive dev mode)
    python run.py start -d       — Start in background (detached daemon mode)
    python run.py stop           — Stop all running project processes
    python run.py restart        — Restart all services
    python run.py status         — Check if Backend & Frontend are running
    python run.py seed           — Seed sample opportunities and demo user
"""

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
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

def is_port_open(port: int, host: str = "127.0.0.1") -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def save_pids(**kwargs) -> None:
    data = load_pids()
    data.update({k: v for k, v in kwargs.items() if v is not None})
    try:
        PID_FILE.write_text(json.dumps(data), encoding="utf-8")
    except Exception:
        pass


def load_pids() -> dict:
    try:
        return json.loads(PID_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def kill_pid(pid: int) -> None:
    try:
        if IS_WIN:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.run(
                ["kill", "-9", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass


def kill_port(port: int) -> None:
    """Kill any process listening on the given port."""
    if not IS_WIN:
        try:
            out = subprocess.check_output(f"lsof -ti:{port}", shell=True, text=True, stderr=subprocess.DEVNULL)
            for pid in out.strip().split():
                kill_pid(int(pid))
        except Exception:
            pass
        return

    try:
        out = subprocess.check_output("netstat -ano -p tcp", shell=True, text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            p = line.strip().split()
            if len(p) >= 5 and f":{port}" in p[1] and p[3] == "LISTENING":
                try:
                    kill_pid(int(p[4]))
                except (ValueError, IndexError):
                    pass
    except Exception:
        pass


def wait_for_port(port: int, timeout: int = 35, label: str = "") -> bool:
    deadline = time.time() + timeout
    dots = 0
    while time.time() < deadline:
        if is_port_open(port):
            return True
        time.sleep(0.5)
        dots += 1
        if dots % 4 == 0:
            elapsed = int(timeout - (deadline - time.time()))
            print(f"  ... waiting for {label or str(port)} ({elapsed}s)", end="\r")
    return False


def ensure_database_seeded() -> None:
    """Auto-seed sample opportunities if the DB has none."""
    db_file = BACKEND_DIR / "researchscout.db"
    needs_seed = False
    if not db_file.exists():
        needs_seed = True
    else:
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_file))
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM opportunities")
            count = c.fetchone()[0]
            conn.close()
            if count == 0:
                needs_seed = True
        except Exception:
            needs_seed = True

    if needs_seed:
        print("  [*] Initializing database with sample research opportunities...")
        try:
            subprocess.run(
                [str(VENV_PYTHON), "-m", "app.seed"],
                cwd=str(BACKEND_DIR),
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("  [✓] Database seeded successfully!")
        except Exception as e:
            print(f"  [!] Note: Seeding had a minor issue ({e}), continuing...")


# ── Launch Logic ──────────────────────────────────────────────────────────────

def launch_safe(cmd: list[str], cwd: str, log_path: str, background: bool = False) -> subprocess.Popen:
    """
    Launch a child process safely on Windows and Unix.
    In background mode on Windows, runs via cmd /c with shell redirection so
    file handles belong to the OS and survive after this script exits.
    In foreground mode, pipes output to log file with shared write permissions.
    """
    log_file = Path(log_path)
    log_file.parent.mkdir(exist_ok=True)

    if background and IS_WIN:
        # Windows-safe detached execution with OS-level redirection
        cmd_str = " ".join(f'"{c}"' if " " in c else c for c in cmd)
        full_shell_cmd = f'cmd.exe /c "{cmd_str} > "{log_path}" 2>&1"'
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        return subprocess.Popen(
            full_shell_cmd,
            cwd=cwd,
            creationflags=flags,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )
    elif background:
        # Unix background
        log_fh = open(log_path, "a", encoding="utf-8")
        return subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    else:
        # Foreground mode
        log_fh = open(log_path, "w", encoding="utf-8")
        flags = subprocess.CREATE_NEW_PROCESS_GROUP if IS_WIN else 0
        return subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=flags,
        )


# ── Services ──────────────────────────────────────────────────────────────────

def start_backend(background: bool = False) -> subprocess.Popen | None:
    if is_port_open(8000):
        print("  [✓] Backend already listening on http://localhost:8000")
        return None

    log_path = str(LOG_DIR / "backend.log")
    print("  [+] Starting Backend (FastAPI) on http://localhost:8000 ...")

    cmd = [
        str(VENV_PYTHON),
        "-m", "uvicorn", "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
    ]

    proc = launch_safe(cmd, str(BACKEND_DIR), log_path, background=background)

    if wait_for_port(8000, timeout=30, label="Backend"):
        print(f"  [✓] Backend started! (PID {proc.pid})")
        return proc
    else:
        print("  [!] Backend taking longer than usual to bind. Check .logs/backend.log")
        return proc


def start_frontend(background: bool = False) -> subprocess.Popen | None:
    if is_port_open(3000):
        print("  [✓] Frontend already listening on http://localhost:3000")
        return None

    log_path = str(LOG_DIR / "frontend.log")
    print("  [+] Starting Frontend (Next.js) on http://localhost:3000 ...")

    npm = "npm.cmd" if IS_WIN else "npm"
    cmd = [npm, "run", "dev"]

    proc = launch_safe(cmd, str(FRONTEND_DIR), log_path, background=background)

    if wait_for_port(3000, timeout=40, label="Frontend"):
        print(f"  [✓] Frontend started! (PID {proc.pid})")
        return proc
    else:
        print("  [!] Frontend taking longer than usual to bind. Check .logs/frontend.log")
        return proc


def run_foreground():
    """Run both services interactively in the foreground with clean Ctrl+C handling."""
    print("\n" + "=" * 50)
    print("🔬 ResearchScout — Starting Autonomous Research Platform")
    print("=" * 50)

    # 1. Ensure DB has data
    ensure_database_seeded()

    # 2. Kill any stale processes on our ports
    if not is_port_open(8000):
        kill_port(8000)
    if not is_port_open(3000):
        kill_port(3000)

    # 3. Launch both
    b_proc = start_backend(background=False)
    f_proc = start_frontend(background=False)

    save_pids(
        backend=b_proc.pid if b_proc else None,
        frontend=f_proc.pid if f_proc else None,
    )

    print("\n" + "=" * 50)
    print("🎉 ResearchScout is running successfully!")
    print("   🌐 Web App:   http://localhost:3000")
    print("   ⚡ API:       http://localhost:8000")
    print("   📚 API Docs:  http://localhost:8000/docs")
    print("   📄 Logs:      .logs/backend.log & .logs/frontend.log")
    print("=" * 50)
    print("💡 Press Ctrl+C at any time to cleanly stop all services.\n")

    # 4. Automatically open browser
    try:
        time.sleep(1)
        webbrowser.open("http://localhost:3000")
    except Exception:
        pass

    # 5. Monitor processes until Ctrl+C
    try:
        while True:
            time.sleep(1)
            # Check if backend unexpectedly died
            if b_proc and b_proc.poll() is not None:
                print("\n[!] Backend process exited unexpectedly! Last lines of .logs/backend.log:")
                try:
                    lines = Path(LOG_DIR / "backend.log").read_text(encoding="utf-8", errors="replace").splitlines()
                    for ln in lines[-10:]:
                        print(f"    {ln}")
                except Exception:
                    pass
                break

            # Check if frontend unexpectedly died
            if f_proc and f_proc.poll() is not None:
                print("\n[!] Frontend process exited unexpectedly! Last lines of .logs/frontend.log:")
                try:
                    lines = Path(LOG_DIR / "frontend.log").read_text(encoding="utf-8", errors="replace").splitlines()
                    for ln in lines[-10:]:
                        print(f"    {ln}")
                except Exception:
                    pass
                break
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping ResearchScout...")
    finally:
        stop_all(quiet=True)
        print("✅ ResearchScout has been cleanly stopped.\n")


def run_background():
    """Start both services as persistent background processes."""
    print("\n🚀 Starting ResearchScout in background mode...")
    ensure_database_seeded()
    b_proc = start_backend(background=True)
    f_proc = start_frontend(background=True)
    save_pids(
        backend=b_proc.pid if b_proc else None,
        frontend=f_proc.pid if f_proc else None,
    )
    print("\n" + "=" * 50)
    print("🎉 ResearchScout is running in the background!")
    print("   🌐 Frontend:  http://localhost:3000")
    print("   ⚡ Backend:   http://localhost:8000")
    print("   📚 API Docs:  http://localhost:8000/docs")
    print("=" * 50)
    print("💡 Run 'python run.py stop' to stop all services.\n")


def stop_all(quiet: bool = False):
    if not quiet:
        print("\n🛑 Stopping ResearchScout...")
    pids = load_pids()
    for name, pid in pids.items():
        if not quiet:
            print(f"  [-] Stopping {name} (PID {pid})...")
        kill_pid(pid)
    kill_port(8000)
    kill_port(3000)
    if PID_FILE.exists():
        try:
            PID_FILE.unlink()
        except Exception:
            pass
    if not quiet:
        print("✅ All services stopped.\n")


def status():
    print("\n🔍 ResearchScout Status:")
    be = is_port_open(8000)
    fe = is_port_open(3000)
    print(f"  ⚡ Backend  (8000): {'🟢 RUNNING' if be else '🔴 STOPPED'}")
    print(f"  🌐 Frontend (3000): {'🟢 RUNNING' if fe else '🔴 STOPPED'}")
    if be:
        try:
            r = urllib.request.urlopen("http://localhost:8000/health", timeout=2)
            d = json.loads(r.read())
            print(f"     API Health: {d.get('status')} (v{d.get('version', '?')})")
        except Exception:
            pass
    p = load_pids()
    if p:
        print(f"  📌 Recorded PIDs: {p}")
    print()


def seed():
    print("\n🌱 Seeding database...")
    ensure_database_seeded()
    print("✅ Done.\n")


def main():
    args = [a.lower() for a in sys.argv[1:]]
    if not args or args[0] in ("start", "dev", "run"):
        if "-d" in args or "--background" in args or "--daemon" in args:
            run_background()
        else:
            run_foreground()
    elif args[0] == "stop":
        stop_all()
    elif args[0] == "restart":
        stop_all()
        time.sleep(2)
        run_foreground()
    elif args[0] == "status":
        status()
    elif args[0] == "seed":
        seed()
    else:
        print("\n🔬 ResearchScout Project Controller")
        print("  python run.py             — Start Backend + Frontend (auto-opens browser, Ctrl+C to stop)")
        print("  python run.py start -d    — Start in background")
        print("  python run.py stop        — Stop all running services")
        print("  python run.py restart     — Restart all services")
        print("  python run.py status      — Check services health")
        print("  python run.py seed        — Seed database\n")


if __name__ == "__main__":
    main()
