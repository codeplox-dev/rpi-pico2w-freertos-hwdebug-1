#!/usr/bin/env python3
"""Setup Pico SDK, FreeRTOS Kernel, and picotool."""

import argparse
import os
import shutil
import subprocess
import sys

from common import get_project_dir, get_deps_dir, get_local_dir, run_cmd


def clone_pico_sdk(version: str) -> bool:
    """Clone the Pico SDK if not already present."""
    deps_dir = get_deps_dir()
    sdk_dir = deps_dir / "pico-sdk"

    if sdk_dir.exists():
        print(f"Pico SDK already exists at {sdk_dir}")
        return True

    print(f"Cloning Pico SDK v{version}...")
    run_cmd([
        "git", "clone", "--depth", "1",
        "--branch", version,
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


def build_picotool(version: str) -> bool:
    """Build and install picotool to .local/bin."""
    local_dir = get_local_dir()
    deps_dir = get_deps_dir()
    picotool_dir = deps_dir / "picotool"
    picotool_bin = local_dir / "bin" / "picotool"

    # Check if already installed with correct version
    if picotool_bin.exists():
        result = subprocess.run(
            [str(picotool_bin), "version"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and version in result.stdout:
            print(f"picotool {version} already installed at {picotool_bin}")
            return True
        print(f"Updating picotool to version {version}...")
        shutil.rmtree(picotool_dir, ignore_errors=True)

    # Clone picotool
    if not picotool_dir.exists():
        print(f"Cloning picotool v{version}...")
        run_cmd([
            "git", "clone", "--depth", "1",
            "--branch", version,
            "https://github.com/raspberrypi/picotool.git"
        ], cwd=deps_dir)

    # Build picotool
    print("Building picotool...")
    build_dir = picotool_dir / "build"
    build_dir.mkdir(exist_ok=True)

    sdk_path = deps_dir / "pico-sdk"

    # Pass SDK path directly to cmake to avoid environment variable conflicts
    subprocess.run([
        "cmake", "-B", str(build_dir), "-G", "Ninja",
        f"-DCMAKE_INSTALL_PREFIX={local_dir}",
        f"-DPICO_SDK_PATH={sdk_path}",
        "-DPICOTOOL_NO_LIBUSB=1",  # Don't require libusb for basic functionality
    ], cwd=picotool_dir, check=True)

    subprocess.run(["cmake", "--build", str(build_dir)], cwd=picotool_dir, check=True)

    # Install picotool
    print("Installing picotool...")
    run_cmd(["cmake", "--install", str(build_dir)], cwd=picotool_dir, check=True)

    print(f"  Installed picotool to {picotool_bin}")
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
    parser = argparse.ArgumentParser(description="Setup Pico SDK, FreeRTOS Kernel, and picotool")
    parser.add_argument("--sdk-version", required=True, help="Pico SDK version (e.g., 2.2.0)")
    parser.add_argument("--picotool-version", default=None, help="picotool version (defaults to SDK version)")
    args = parser.parse_args()

    # Default picotool version to SDK version
    picotool_version = args.picotool_version or args.sdk_version

    deps_dir = get_deps_dir()
    deps_dir.mkdir(parents=True, exist_ok=True)

    local_dir = get_local_dir()
    (local_dir / "bin").mkdir(parents=True, exist_ok=True)

    try:
        clone_pico_sdk(args.sdk_version)
        clone_freertos_kernel()
        build_picotool(picotool_version)
        copy_cmake_imports()

        print()
        print("SDK setup complete!")
        print(f"  Pico SDK:        {deps_dir / 'pico-sdk'}")
        print(f"  FreeRTOS Kernel: {deps_dir / 'FreeRTOS-Kernel'}")
        print(f"  picotool:        {local_dir / 'bin' / 'picotool'}")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"Error: Command failed with exit code {e.returncode}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
