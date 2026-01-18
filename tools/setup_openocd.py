#!/usr/bin/env python3
"""Build OpenOCD from source (required for RP2350 support)."""

import os
import subprocess
import sys
from pathlib import Path


def get_project_dir() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.resolve()


def get_local_dir() -> Path:
    """Get the .local directory for local installations."""
    return get_project_dir() / ".local"


def run_cmd(cmd: list, cwd: Path = None, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    kwargs = {"cwd": cwd, "check": check}
    if capture:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    return subprocess.run(cmd, **kwargs)


def get_nproc() -> int:
    """Get the number of CPU cores for parallel builds."""
    try:
        return os.cpu_count() or 4
    except Exception:
        return 4


def main() -> int:
    """Main entry point."""
    local_dir = get_local_dir()
    openocd_bin = local_dir / "bin" / "openocd"
    src_dir = local_dir / "src"

    # Check if already installed
    if openocd_bin.exists():
        print("OpenOCD already installed.")
        try:
            result = run_cmd([str(openocd_bin), "--version"], capture=True, check=False)
            version_line = (result.stderr or result.stdout or "").split("\n")[0]
            print(version_line)
        except Exception:
            pass
        return 0

    print("Building OpenOCD from source...")

    # Create directories
    src_dir.mkdir(parents=True, exist_ok=True)

    openocd_src = src_dir / "openocd"

    # Clone if needed
    if not openocd_src.exists():
        print("Cloning OpenOCD repository...")
        run_cmd([
            "git", "clone", "--depth", "1",
            "https://github.com/openocd-org/openocd.git"
        ], cwd=src_dir)

    # Bootstrap
    print("Running bootstrap...")
    try:
        run_cmd(["./bootstrap"], cwd=openocd_src, check=False)
    except Exception:
        pass

    # Configure
    print("Configuring...")
    run_cmd([
        "./configure",
        f"--prefix={local_dir}",
        "--enable-cmsis-dap",
        "--enable-picoprobe",
        "--disable-werror"
    ], cwd=openocd_src)

    # Build
    print(f"Building with {get_nproc()} parallel jobs...")
    run_cmd(["make", f"-j{get_nproc()}"], cwd=openocd_src)

    # Install
    print("Installing...")
    run_cmd(["make", "install"], cwd=openocd_src)

    # Verify
    print()
    print("OpenOCD installed.")
    if openocd_bin.exists():
        result = run_cmd([str(openocd_bin), "--version"], capture=True, check=False)
        version_line = (result.stderr or result.stdout or "").split("\n")[0]
        print(version_line)
        return 0
    else:
        print("Error: OpenOCD binary not found after install", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
