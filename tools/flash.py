#!/usr/bin/env python3
"""Flash firmware to target via debug probe using OpenOCD."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def get_project_dir() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.resolve()


def get_openocd_path() -> Path:
    """Get the path to the local OpenOCD binary."""
    return get_project_dir() / ".local" / "bin" / "openocd"


def get_openocd_scripts() -> Path:
    """Get the path to OpenOCD scripts directory."""
    return get_project_dir() / ".local" / "share" / "openocd" / "scripts"


def flash(elf_file: Path, adapter_speed: int = 5000) -> int:
    """Flash firmware to target.

    Args:
        elf_file: Path to the ELF file to flash
        adapter_speed: OpenOCD adapter speed in kHz

    Returns:
        Exit code from OpenOCD
    """
    openocd = get_openocd_path()
    scripts = get_openocd_scripts()

    if not openocd.exists():
        print(f"Error: OpenOCD not found at {openocd}", file=sys.stderr)
        print("Run: just setup-openocd", file=sys.stderr)
        return 1

    if not elf_file.exists():
        print(f"Error: ELF file not found: {elf_file}", file=sys.stderr)
        return 1

    cmd = [
        str(openocd),
        "-s", str(scripts),
        "-f", "interface/cmsis-dap.cfg",
        "-f", "target/rp2350.cfg",
        "-c", f"adapter speed {adapter_speed}",
        "-c", f"program {elf_file} verify reset exit"
    ]

    return subprocess.run(cmd).returncode


def reset() -> int:
    """Reset the target without flashing."""
    openocd = get_openocd_path()
    scripts = get_openocd_scripts()

    if not openocd.exists():
        print(f"Error: OpenOCD not found at {openocd}", file=sys.stderr)
        return 1

    cmd = [
        str(openocd),
        "-s", str(scripts),
        "-f", "interface/cmsis-dap.cfg",
        "-f", "target/rp2350.cfg",
        "-c", "init",
        "-c", "reset run",
        "-c", "shutdown"
    ]

    return subprocess.run(cmd).returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Flash firmware to Pico 2 W via debug probe"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # flash command (default)
    flash_parser = subparsers.add_parser("flash", help="Flash firmware to target")
    flash_parser.add_argument("elf_file", nargs="?",
                              default=str(get_project_dir() / "build" / "src" / "wifi_scanner.elf"),
                              help="Path to ELF file")
    flash_parser.add_argument("--speed", type=int, default=5000,
                              help="Adapter speed in kHz (default: 5000)")

    # reset command
    subparsers.add_parser("reset", help="Reset target without flashing")

    args = parser.parse_args()

    # Default to flash if no command given but args present
    if not args.command:
        if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
            # Treat first arg as ELF file
            sys.exit(flash(Path(sys.argv[1])))
        else:
            # Default flash with default ELF
            sys.exit(flash(Path(get_project_dir() / "build" / "src" / "wifi_scanner.elf")))

    if args.command == "flash":
        sys.exit(flash(Path(args.elf_file), args.speed))
    elif args.command == "reset":
        sys.exit(reset())


if __name__ == "__main__":
    main()
