#!/usr/bin/env python3
"""Setup VSCode for Pico SDK + FreeRTOS development with OpenOCD debugging."""

import json
import os
import shutil
import sys
from pathlib import Path
from typing import List

from common import get_project_dir, get_local_dir, run_cmd_status


def get_vscode_configs() -> dict:
    """Return default VSCode configuration files content."""
    return {
        "launch.json": {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "Debug",
                    "type": "cortex-debug",
                    "request": "launch",
                    "cwd": "${workspaceFolder}",
                    "executable": "${workspaceFolder}/build/src/wifi_scanner.elf",
                    "servertype": "openocd",
                    "serverpath": "${workspaceFolder}/.local/bin/openocd",
                    "searchDir": ["${workspaceFolder}/.local/share/openocd/scripts"],
                    "configFiles": [
                        "interface/cmsis-dap.cfg",
                        "target/rp2350.cfg"
                    ],
                    "openOCDLaunchCommands": ["adapter speed 4000"],
                    "svdFile": "${workspaceFolder}/deps/pico-sdk/src/rp2350/hardware_regs/rp2350.svd",
                    "runToEntryPoint": "main",
                    "preLaunchTask": "Build"
                },
                {
                    "name": "Attach",
                    "type": "cortex-debug",
                    "request": "attach",
                    "cwd": "${workspaceFolder}",
                    "executable": "${workspaceFolder}/build/src/wifi_scanner.elf",
                    "servertype": "openocd",
                    "serverpath": "${workspaceFolder}/.local/bin/openocd",
                    "searchDir": ["${workspaceFolder}/.local/share/openocd/scripts"],
                    "configFiles": [
                        "interface/cmsis-dap.cfg",
                        "target/rp2350.cfg"
                    ],
                    "openOCDLaunchCommands": ["adapter speed 4000"],
                    "svdFile": "${workspaceFolder}/deps/pico-sdk/src/rp2350/hardware_regs/rp2350.svd"
                }
            ]
        },
        "tasks.json": {
            "version": "2.0.0",
            "tasks": [
                {
                    "label": "Build",
                    "type": "shell",
                    "command": "just",
                    "args": ["build"],
                    "group": {
                        "kind": "build",
                        "isDefault": True
                    },
                    "problemMatcher": ["$gcc"]
                },
                {
                    "label": "Clean",
                    "type": "shell",
                    "command": "just",
                    "args": ["clean"],
                    "problemMatcher": []
                },
                {
                    "label": "Serial Read",
                    "type": "shell",
                    "command": "just",
                    "args": ["serial-read"],
                    "problemMatcher": [],
                    "isBackground": True
                }
            ]
        },
        "settings.json": {
            "cmake.configureOnOpen": True,
            "cmake.generator": "Ninja",
            "cmake.buildDirectory": "${workspaceFolder}/build",
            "C_Cpp.default.configurationProvider": "ms-vscode.cmake-tools",
            "cortex-debug.openocdPath": "${workspaceFolder}/.local/bin/openocd",
            "files.associations": {
                "*.h": "c",
                "FreeRTOSConfig.h": "c"
            }
        },
        "extensions.json": {
            "recommendations": [
                "mkhl.direnv",
                "ms-vscode.cpptools",
                "ms-vscode.cmake-tools",
                "marus25.cortex-debug",
                "mcu-debug.rtos-views"
            ]
        },
        "c_cpp_properties.json": {
            "version": 4,
            "configurations": [
                {
                    "name": "Pico 2 W (ARM)",
                    "compileCommands": "${workspaceFolder}/build/compile_commands.json",
                    "includePath": [
                        "${workspaceFolder}/src/**",
                        "${workspaceFolder}/deps/pico-sdk/**",
                        "${workspaceFolder}/deps/FreeRTOS-Kernel/include"
                    ],
                    "defines": [
                        "PICO_BOARD=pico2_w",
                        "PICO_RP2350=1"
                    ],
                    "intelliSenseMode": "gcc-arm",
                    "cStandard": "c11",
                    "cppStandard": "c++23"
                },
                {
                    "name": "Host Tests",
                    "compileCommands": "${workspaceFolder}/build/compile_commands.json",
                    "includePath": [
                        "${workspaceFolder}/test/**",
                        "${workspaceFolder}/src/**"
                    ],
                    "intelliSenseMode": "linux-gcc-x64",
                    "cStandard": "c11",
                    "cppStandard": "c++23"
                }
            ]
        }
    }


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


def check_prerequisites(status: SetupStatus) -> bool:
    """Check for required tools. Returns True if VSCode CLI is available."""
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
    gdb_path = which("arm-none-eabi-gdb") or which("gdb-multiarch")
    if gdb_path:
        status.ok(f"GDB found: {gdb_path}")
    else:
        status.err("No ARM GDB found (install arm-none-eabi-gdb or gdb-multiarch)")

    # Pico SDK
    sdk_path = get_project_dir() / "deps" / "pico-sdk"
    if sdk_path.exists():
        status.ok("Pico SDK found")
    else:
        status.err("Pico SDK not found (run: just setup)")

    return has_code_cli


def setup_openocd(status: SetupStatus) -> None:
    """Setup OpenOCD."""
    print("\nSetting up OpenOCD...")

    local_dir = get_local_dir()
    openocd_bin = local_dir / "bin" / "openocd"

    if openocd_bin.exists():
        rc, stdout, stderr = run_cmd_status([str(openocd_bin), "--version"])
        version = (stderr or stdout).split("\n")[0] if rc == 0 else "unknown"
        status.ok(f"OpenOCD already installed: {version}")
    else:
        print("  Building OpenOCD from source...")
        setup_script = Path(__file__).parent / "setup_openocd.py"
        rc, _, _ = run_cmd_status([sys.executable, str(setup_script)], capture=False)
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
        rc, stdout, _ = run_cmd_status(["code", "--list-extensions"])
        installed = stdout.lower().split("\n") if rc == 0 else []

        for ext in extensions:
            if ext.lower() in installed:
                status.ok(ext)
            else:
                print(f"  Installing {ext}...")
                rc, _, _ = run_cmd_status(["code", "--install-extension", ext, "--force"])
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
    """Check and create VSCode configuration files."""
    print("\nChecking VSCode configuration...")

    project_dir = get_project_dir()
    vscode_dir = project_dir / ".vscode"
    configs = get_vscode_configs()

    # Create .vscode directory if needed
    if not vscode_dir.exists():
        vscode_dir.mkdir(parents=True)
        status.ok(".vscode directory created")

    for filename, content in configs.items():
        config_path = vscode_dir / filename
        if config_path.exists():
            status.ok(f".vscode/{filename}")
        else:
            # Create the missing config file
            with open(config_path, "w") as f:
                json.dump(content, f, indent=4)
            status.ok(f".vscode/{filename} (created)")

    # Check compile_commands.json exists (generated by CMake)
    compile_commands = project_dir / "build" / "compile_commands.json"
    if compile_commands.exists():
        status.ok("build/compile_commands.json (IntelliSense)")
    else:
        status.warn("build/compile_commands.json missing (run 'just build' first)")


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
        rc, _, _ = run_cmd_status([
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


def check_direnv(status: SetupStatus) -> None:
    """Check direnv status."""
    project_dir = get_project_dir()
    envrc = project_dir / ".envrc"

    if envrc.exists():
        if which("direnv"):
            status.ok(".envrc exists (run 'direnv allow' if not yet allowed)")
        else:
            status.warn(".envrc exists but direnv not installed")
    else:
        status.warn(".envrc missing")


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
        print("  - Debug: Build, start OpenOCD, flash, and debug")
        print("  - Attach: Connect to running OpenOCD without flashing")
        return 0
    else:
        print("Setup incomplete. Please fix errors above.")
        return 1


def main() -> int:
    """Main entry point."""
    print("=== VSCode IDE Setup for Pico 2 W Debugging ===\n")

    status = SetupStatus()

    has_code_cli = check_prerequisites(status)
    setup_openocd(status)
    install_extensions(status, has_code_cli)
    check_vscode_config(status)
    check_debug_probe(status)
    check_direnv(status)

    return print_summary(status)


if __name__ == "__main__":
    sys.exit(main())
