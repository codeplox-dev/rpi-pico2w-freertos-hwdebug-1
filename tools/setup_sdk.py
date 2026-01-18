#!/usr/bin/env python3
"""Setup Pico SDK and FreeRTOS Kernel (Raspberry Pi fork)."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

PICO_SDK_VERSION = "2.2.0"


def get_project_dir() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.resolve()


def get_deps_dir() -> Path:
    """Get the dependencies directory."""
    return get_project_dir() / "deps"


def run_cmd(cmd: list, cwd: Path = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command and return the result."""
    return subprocess.run(cmd, cwd=cwd, check=check)


def clone_pico_sdk() -> bool:
    """Clone the Pico SDK if not already present."""
    deps_dir = get_deps_dir()
    sdk_dir = deps_dir / "pico-sdk"

    if sdk_dir.exists():
        print(f"Pico SDK already exists at {sdk_dir}")
        return True

    print(f"Cloning Pico SDK v{PICO_SDK_VERSION}...")
    run_cmd([
        "git", "clone", "--depth", "1",
        "--branch", PICO_SDK_VERSION,
        "https://github.com/raspberrypi/pico-sdk.git"
    ], cwd=deps_dir)

    print("Initializing SDK submodules...")
    run_cmd(["git", "submodule", "update", "--init", "--depth", "1"], cwd=sdk_dir)

    return True


def clone_freertos_kernel() -> bool:
    """Clone the FreeRTOS Kernel (Raspberry Pi fork) if not already present."""
    deps_dir = get_deps_dir()
    freertos_dir = deps_dir / "FreeRTOS-Kernel"

    if freertos_dir.exists():
        print(f"FreeRTOS Kernel already exists at {freertos_dir}")
        return True

    print("Cloning FreeRTOS Kernel (Raspberry Pi fork)...")
    run_cmd([
        "git", "clone", "--depth", "1",
        "https://github.com/raspberrypi/FreeRTOS-Kernel.git"
    ], cwd=deps_dir)

    return True


def copy_cmake_imports() -> bool:
    """Copy CMake import files to project root."""
    project_dir = get_project_dir()
    deps_dir = get_deps_dir()

    print("Copying CMake import files to project root...")

    # pico_sdk_import.cmake
    sdk_import_src = deps_dir / "pico-sdk" / "external" / "pico_sdk_import.cmake"
    sdk_import_dst = project_dir / "pico_sdk_import.cmake"
    if sdk_import_src.exists():
        shutil.copy(sdk_import_src, sdk_import_dst)
        print(f"  Copied {sdk_import_dst.name}")
    else:
        print(f"  Warning: {sdk_import_src} not found", file=sys.stderr)

    # FreeRTOS_Kernel_import.cmake
    freertos_import_src = deps_dir / "FreeRTOS-Kernel" / "portable" / "ThirdParty" / "GCC" / "RP2350_ARM_NTZ" / "FreeRTOS_Kernel_import.cmake"
    freertos_import_dst = project_dir / "FreeRTOS_Kernel_import.cmake"
    if freertos_import_src.exists():
        shutil.copy(freertos_import_src, freertos_import_dst)
        print(f"  Copied {freertos_import_dst.name}")
    else:
        print(f"  Warning: {freertos_import_src} not found", file=sys.stderr)

    return True


def main() -> int:
    """Main entry point."""
    deps_dir = get_deps_dir()
    deps_dir.mkdir(parents=True, exist_ok=True)

    try:
        clone_pico_sdk()
        clone_freertos_kernel()
        copy_cmake_imports()

        print()
        print("SDK setup complete!")
        print(f"  Pico SDK:        {deps_dir / 'pico-sdk'}")
        print(f"  FreeRTOS Kernel: {deps_dir / 'FreeRTOS-Kernel'}")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with exit code {e.returncode}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
