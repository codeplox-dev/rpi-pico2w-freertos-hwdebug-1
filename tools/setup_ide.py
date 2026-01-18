#!/usr/bin/env python3
"""Setup VSCode for Pico SDK + FreeRTOS development with OpenOCD debugging."""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


def get_project_dir() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.resolve()


def get_local_dir() -> Path:
    """Get the .local directory."""
    return get_project_dir() / ".local"


class SetupStatus:
    """Track setup errors and warnings."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def ok(self, msg: str) -> None:
        print(f"  [OK] {msg}")

    def warn(self, msg: str) -> None:
        print(f"  [WARN] {msg}")
        self.warnings.append(msg)

    def err(self, msg: str) -> None:
        print(f"  [ERROR] {msg}")
        self.errors.append(msg)

    def skip(self, msg: str) -> None:
        print(f"  [SKIP] {msg}")


def which(cmd: str) -> str:
    """Find command in PATH, return path or empty string."""
    return shutil.which(cmd) or ""


def run_cmd(cmd: list, capture: bool = True, check: bool = False) -> Tuple[int, str, str]:
    """Run a command and return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True, check=check)
        return result.returncode, result.stdout or "", result.stderr or ""
    except Exception as e:
        return 1, "", str(e)


def check_prerequisites(status: SetupStatus) -> Tuple[bool, str]:
    """Check for required tools. Returns (has_code_cli, gdb_path)."""
    print("Checking prerequisites...")

    # VSCode CLI
    has_code_cli = bool(which("code"))
    if has_code_cli:
        status.ok("VSCode CLI found")
    else:
        status.warn("VSCode CLI not found (extension auto-install unavailable)")

    # direnv
    if which("direnv"):
        status.ok("direnv found")
    else:
        status.warn("direnv not found (manual environment setup required)")

    # GDB
    gdb_path = ""
    if which("arm-none-eabi-gdb"):
        gdb_path = which("arm-none-eabi-gdb")
        status.ok(f"GDB found: {gdb_path}")
    elif which("gdb-multiarch"):
        gdb_path = which("gdb-multiarch")
        status.ok(f"GDB found: {gdb_path}")
    else:
        status.err("No ARM GDB found (install arm-none-eabi-gdb or gdb-multiarch)")

    # Pico SDK
    sdk_path = get_project_dir() / "deps" / "pico-sdk"
    if sdk_path.exists():
        status.ok("Pico SDK found")
    else:
        status.err("Pico SDK not found (run: just setup-sdk)")

    return has_code_cli, gdb_path


def setup_openocd(status: SetupStatus) -> None:
    """Setup OpenOCD."""
    print("\nSetting up OpenOCD...")

    local_dir = get_local_dir()
    openocd_bin = local_dir / "bin" / "openocd"

    if openocd_bin.exists():
        rc, stdout, stderr = run_cmd([str(openocd_bin), "--version"])
        version = (stderr or stdout).split("\n")[0] if rc == 0 else "unknown"
        status.ok(f"OpenOCD already installed: {version}")
    else:
        print("  Building OpenOCD from source...")
        setup_script = Path(__file__).parent / "setup_openocd.py"
        rc, _, _ = run_cmd([sys.executable, str(setup_script)], capture=False)
        if rc == 0:
            status.ok("OpenOCD built successfully")
        else:
            status.err("OpenOCD build failed")

    # Check RP2350 config
    rp2350_cfg = local_dir / "share" / "openocd" / "scripts" / "target" / "rp2350.cfg"
    if rp2350_cfg.exists():
        status.ok("RP2350 target configuration found")
    else:
        status.err("RP2350 target config missing (OpenOCD may be outdated)")


def install_extensions(status: SetupStatus, has_code_cli: bool) -> None:
    """Install VSCode extensions."""
    print("\nChecking VSCode extensions...")

    extensions = [
        "mkhl.direnv",
        "ms-vscode.cpptools",
        "ms-vscode.cmake-tools",
        "marus25.cortex-debug",
    ]

    if has_code_cli:
        rc, stdout, _ = run_cmd(["code", "--list-extensions"])
        installed = stdout.lower().split("\n") if rc == 0 else []

        for ext in extensions:
            if ext.lower() in installed:
                status.ok(ext)
            else:
                print(f"  Installing {ext}...")
                rc, _, _ = run_cmd(["code", "--install-extension", ext, "--force"])
                if rc == 0:
                    status.ok(f"{ext} (installed)")
                else:
                    status.warn(f"Failed to install {ext}")
    else:
        status.skip("Extension installation (no VSCode CLI)")
        print("  Required extensions:")
        for ext in extensions:
            print(f"    - {ext}")


def check_vscode_config(status: SetupStatus) -> None:
    """Check VSCode configuration files."""
    print("\nChecking VSCode configuration...")

    config_files = [
        ".vscode/launch.json",
        ".vscode/tasks.json",
        ".vscode/settings.json",
        ".vscode/extensions.json",
    ]

    project_dir = get_project_dir()
    for config in config_files:
        if (project_dir / config).exists():
            status.ok(config)
        else:
            status.err(f"{config} missing")


def check_debug_probe(status: SetupStatus) -> None:
    """Check debug probe connectivity."""
    print("\nChecking debug probe...")

    found_device = False
    for dev in ["/dev/ttyACM0", "/dev/ttyACM1"]:
        if os.path.exists(dev):
            if os.access(dev, os.R_OK):
                status.ok(f"{dev} accessible")
            else:
                status.warn(f"{dev} exists but not readable (check permissions)")
            found_device = True

    if not found_device:
        status.warn("No debug probe detected (connect Pico Debug Probe)")

    # Quick OpenOCD test
    local_dir = get_local_dir()
    openocd_bin = local_dir / "bin" / "openocd"
    if openocd_bin.exists() and os.path.exists("/dev/ttyACM0"):
        print("  Testing OpenOCD connection (2s timeout)...")
        rc, _, _ = run_cmd([
            "timeout", "2",
            str(openocd_bin),
            "-s", str(local_dir / "share" / "openocd" / "scripts"),
            "-f", "interface/cmsis-dap.cfg",
            "-f", "target/rp2350.cfg",
            "-c", "init",
            "-c", "shutdown"
        ])
        if rc == 0:
            status.ok("OpenOCD connected to target")
        else:
            status.warn("OpenOCD could not connect (target may not be powered)")


def setup_direnv(status: SetupStatus) -> None:
    """Allow direnv for the project."""
    project_dir = get_project_dir()
    envrc = project_dir / ".envrc"

    if which("direnv") and envrc.exists():
        print("\nConfiguring direnv...")
        rc, _, _ = run_cmd(["direnv", "allow", str(project_dir)])
        if rc == 0:
            status.ok("direnv allowed for project")
        else:
            status.warn("Could not allow direnv")


def print_summary(status: SetupStatus) -> int:
    """Print setup summary and return exit code."""
    print("\n=== Setup Summary ===\n")

    if status.errors:
        print("Errors (must fix):")
        for err in status.errors:
            print(f"  - {err}")
        print()

    if status.warnings:
        print("Warnings (optional):")
        for warn in status.warnings:
            print(f"  - {warn}")
        print()

    if not status.errors:
        project_dir = get_project_dir()
        print("Ready for debugging!")
        print()
        print("Next steps:")
        print(f"  1. Open project in VSCode: code {project_dir}")
        print("  2. If prompted, reload window for direnv")
        print("  3. Run 'just build' or use Ctrl+Shift+B")
        print("  4. Press F5 to start debugging")
        print()
        print("Debug configurations available:")
        print("  - Debug (OpenOCD): Launches OpenOCD automatically")
        print("  - Debug (External OpenOCD): Connects to running OpenOCD")
        print("  - Attach (External OpenOCD): Attach without reset")
        return 0
    else:
        print("Setup incomplete. Please fix errors above.")
        return 1


def main() -> int:
    """Main entry point."""
    print("=== VSCode IDE Setup for Pico 2 W Debugging ===\n")

    status = SetupStatus()

    has_code_cli, gdb_path = check_prerequisites(status)
    setup_openocd(status)
    install_extensions(status, has_code_cli)
    check_vscode_config(status)
    check_debug_probe(status)
    setup_direnv(status)

    return print_summary(status)


if __name__ == "__main__":
    sys.exit(main())
