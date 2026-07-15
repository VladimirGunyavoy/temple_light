"""
Auto-restart wrapper for main.py.

Normal exit (Escape, which calls application.quit() -> exit code 0)
restarts the scene so the latest saved edits are picked up automatically;
an error exit (non-zero, i.e. an exception) stops the watcher so the
traceback stays visible.
"""
import os
import subprocess
import sys
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
TARGET_SCRIPT = os.path.join(PROJECT_ROOT, 'main.py')

# Interpreter used to relaunch main.py — must have ursina/numpy installed.
# Defaults to whichever interpreter is running watcher.py itself, so
# `python watcher.py` "just works" as long as that's an ursina-enabled
# install; override with the URSINA_PYTHON env var if you run watcher.py
# with a different interpreter than the one main.py needs (e.g. on a
# machine with more than one Python install, see ../README.md).
PYTHON_EXE = os.environ.get('URSINA_PYTHON', sys.executable)


def main():
    print("=" * 60)
    print("MAIN.PY AUTO-RESTART")
    print("=" * 60)
    print(f"Target script: {TARGET_SCRIPT}")
    print(f"Interpreter:   {PYTHON_EXE}")
    print("Behavior:")
    print("  - Normal exit (Escape / code 0) -> auto-restart")
    print("  - Error exit (code != 0)        -> stop, traceback stays on screen")
    print("=" * 60)

    if not os.path.exists(TARGET_SCRIPT):
        print(f"ERROR: script not found at {TARGET_SCRIPT}")
        sys.exit(1)

    restart_count = 0
    try:
        while True:
            restart_count += 1
            print(f"\n[START #{restart_count}] Running main.py")

            process = subprocess.Popen([PYTHON_EXE, "-u", TARGET_SCRIPT], cwd=PROJECT_ROOT)
            exit_code = process.wait()

            if exit_code == 0:
                print(f"[EXIT] Normal exit (code {exit_code}) -> restarting in 1s")
                time.sleep(1)
            else:
                print(f"[ERROR] Exit code {exit_code} -> stopping watcher")
                break
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Ctrl+C -> watcher stopped")


if __name__ == '__main__':
    main()
