import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"


def _child_environment() -> dict[str, str]:
    """Return an environment in which the src-layout package is importable."""
    environment = os.environ.copy()
    current = environment.get("PYTHONPATH", "")
    src = os.path.normcase(os.path.abspath(SRC_DIR))
    inherited = [item for item in current.split(os.pathsep) if item]
    entries = [str(SRC_DIR), *(item for item in inherited if os.path.normcase(os.path.abspath(item)) != src)]
    environment["PYTHONPATH"] = os.pathsep.join(entries)
    return environment


def _git(*args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
    )


def check_for_updates() -> None:
    print("Checking for updates...")
    try:
        subprocess.run(
            ["git", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        print("Update check skipped: Git is not installed.")
        return

    repository = _git("rev-parse", "--is-inside-work-tree")
    if repository.returncode != 0 or repository.stdout.strip() != "true":
        print("Update check skipped: this copy has no Git repository metadata.")
        return
    upstream = _git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if upstream.returncode != 0:
        print("Update check skipped: the current branch has no upstream remote.")
        return

    try:
        _git("fetch", "--quiet", check=True)
        behind = _git("rev-list", "--count", "HEAD..@{upstream}", check=True)
        commits = int(behind.stdout.strip() or "0")
        if commits <= 0:
            print("You are up to date.")
            return
        print("\n" + "=" * 40)
        print(f"An update is available for Laitoxx ({commits} commit(s)).")
        print("=" * 40)
        answer = input("Do you want to download and install the update now? (y/n): ")
        if answer.casefold() == "y":
            pull = subprocess.run(["git", "pull", "--ff-only"], cwd=PROJECT_ROOT, check=False)
            if pull.returncode == 0:
                print("\nUpdate successful. Re-run the installer if dependencies changed.")
                input("Press Enter to continue starting the application...")
            else:
                print("Update was not applied; local changes or branch history require manual review.")
        else:
            print("Skipping update.")
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Update check skipped: {exc}")


def _venv_python() -> Path:
    relative = Path("venv") / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    return PROJECT_ROOT / relative


def main() -> None:
    print("Starting Laitoxx-Multi-Tool...")
    check_for_updates()

    python_executable = _venv_python()
    if not python_executable.is_file():
        print(f"\nVirtual environment not found at {python_executable}.")
        print("Run install.bat (Windows) or install.sh (Linux/macOS) first.")
        raise SystemExit(1)

    environment = _child_environment()
    print("\nChecking connectivity...")
    subprocess.run(
        [str(python_executable), "-m", "laitoxx.core.netcheck"],
        cwd=PROJECT_ROOT,
        env=environment,
        check=False,
    )

    print(f"\nLaunching using virtual environment: {python_executable}\n")
    try:
        result = subprocess.run(
            [str(python_executable), str(PROJECT_ROOT / "gui.py"), *sys.argv[1:]],
            cwd=PROJECT_ROOT,
            env=environment,
            check=False,
        )
        raise SystemExit(result.returncode)
    except KeyboardInterrupt:
        print("\nExiting...")
        raise SystemExit(0) from None


if __name__ == "__main__":
    main()
