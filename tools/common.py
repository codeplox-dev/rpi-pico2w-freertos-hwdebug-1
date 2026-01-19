"""Common utilities for Pico development tools."""

import subprocess
from pathlib import Path
from typing import Optional, Tuple


def get_project_dir() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.resolve()


def get_local_dir() -> Path:
    """Get the .local directory for local installations."""
    return get_project_dir() / ".local"


def get_deps_dir() -> Path:
    """Get the dependencies directory."""
    return get_project_dir() / "deps"


def run_cmd(
    cmd: list,
    cwd: Optional[Path] = None,
    check: bool = True,
    capture: bool = False
) -> subprocess.CompletedProcess:
    """Run a command and return the result.

    Args:
        cmd: Command and arguments as a list
        cwd: Working directory for the command
        check: If True, raise CalledProcessError on non-zero exit
        capture: If True, capture stdout/stderr as text

    Returns:
        CompletedProcess instance
    """
    kwargs = {"cwd": cwd, "check": check}
    if capture:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    return subprocess.run(cmd, **kwargs)


def run_cmd_status(
    cmd: list,
    capture: bool = True,
    check: bool = False
) -> Tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr).

    Convenience wrapper that never raises, always returns status tuple.
    """
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True, check=check)
        return result.returncode, result.stdout or "", result.stderr or ""
    except Exception as e:
        return 1, "", str(e)
