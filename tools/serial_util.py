#!/usr/bin/env python3
"""
Serial port utilities for Pico 2 development.

Key features:
- CTRL-C exits cleanly at any point
- All operations have hard timeouts
- Handles USB enumeration delays gracefully
"""

import argparse
import os
import signal
import sys
import time
import subprocess
from pathlib import Path

DEFAULT_BAUD = 115200
DEFAULT_TIMEOUT = 5
DEFAULT_WAIT_TIMEOUT = 10
DEFAULT_DEVICE = "/dev/ttyACM1"

# Global for clean shutdown
_serial_port = None


def _signal_handler(signum, frame):
    """Handle CTRL-C gracefully."""
    global _serial_port
    if _serial_port:
        try:
            _serial_port.close()
        except Exception:
            pass
    print("\nInterrupted.", file=sys.stderr)
    sys.exit(130)  # Standard exit code for SIGINT


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def cmd_list() -> None:
    """List available serial devices with detailed info."""
    try:
        from serial.tools import list_ports
    except ImportError:
        print("Error: pyserial not installed. Run: pip install pyserial", file=sys.stderr)
        sys.exit(1)

    ports = list(list_ports.comports())
    ports = [p for p in ports if p.vid is not None or not p.device.startswith("/dev/ttyS")]

    if not ports:
        print("No serial devices found")
        return

    print("Serial devices:")
    for port in sorted(ports, key=lambda p: p.device):
        print(f"  {port.device}")
        if port.description and port.description != "n/a":
            print(f"      Description: {port.description}")
        if port.manufacturer:
            print(f"      Manufacturer: {port.manufacturer}")
        if port.product:
            print(f"      Product: {port.product}")
        if port.serial_number:
            print(f"      Serial: {port.serial_number}")
        if port.vid is not None and port.pid is not None:
            print(f"      VID:PID: {port.vid:04x}:{port.pid:04x}")


def cmd_wait(device: str = DEFAULT_DEVICE, timeout: int = DEFAULT_WAIT_TIMEOUT) -> bool:
    """Wait for a device to appear."""
    timeout = min(timeout, 60)
    print(f"Waiting for {device} (timeout: {timeout}s)...", file=sys.stderr)

    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(device) and os.access(device, os.R_OK):
            print(f"Device {device} is ready", file=sys.stderr)
            return True
        time.sleep(0.5)
        elapsed = int(time.time() - start)
        if elapsed > 0 and elapsed % 4 == 0:
            print(f"  ... waiting ({elapsed}s elapsed)", file=sys.stderr)

    print(f"Error: Device {device} did not appear within {timeout}s", file=sys.stderr)
    cmd_list()
    return False


def cmd_read(device: str = DEFAULT_DEVICE, duration: int = DEFAULT_TIMEOUT, baud: int = DEFAULT_BAUD) -> bytes:
    """Read from serial with guaranteed termination."""
    global _serial_port
    duration = min(duration, 600)

    if not os.path.exists(device):
        print(f"Error: Device {device} not found", file=sys.stderr)
        cmd_list()
        sys.exit(1)

    if not os.access(device, os.R_OK):
        print(f"Error: Cannot read {device} (permission denied)", file=sys.stderr)
        sys.exit(1)

    try:
        import serial
    except ImportError:
        print("Error: pyserial not installed. Run: pip install pyserial", file=sys.stderr)
        sys.exit(1)

    print(f"Reading from {device} for {duration}s (Ctrl+C to stop)...", file=sys.stderr)

    captured = b""
    try:
        _serial_port = serial.Serial(port=device, baudrate=baud, timeout=0.1)
        _serial_port.dtr = True
        _serial_port.rts = True

        end_time = time.time() + duration
        while time.time() < end_time:
            data = _serial_port.read(1024)
            if data:
                captured += data
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()

        _serial_port.close()
        _serial_port = None
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\nDone. Captured {len(captured)} bytes.", file=sys.stderr)
    return captured


def cmd_capture(device: str = DEFAULT_DEVICE, duration: int = DEFAULT_TIMEOUT,
                wait_timeout: int = DEFAULT_WAIT_TIMEOUT, baud: int = DEFAULT_BAUD) -> bytes:
    """Combined wait + read for post-flash capture."""
    if not cmd_wait(device, wait_timeout):
        sys.exit(1)

    time.sleep(0.5)
    return cmd_read(device, duration, baud)


def cmd_console(device: str = DEFAULT_DEVICE, baud: int = DEFAULT_BAUD) -> None:
    """Open interactive console."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("Error: console command requires an interactive terminal", file=sys.stderr)
        print("Use 'read' command for non-interactive use", file=sys.stderr)
        sys.exit(1)

    for tool in ["picocom", "minicom"]:
        if subprocess.run(["which", tool], capture_output=True).returncode == 0:
            if not os.path.exists(device):
                print(f"Error: Device {device} not found", file=sys.stderr)
                cmd_list()
                sys.exit(1)

            print(f"Connecting to {device} at {baud} baud...")
            if tool == "picocom":
                print("Exit with Ctrl+A Ctrl+X")
                os.execvp("picocom", ["picocom", device, "-b", str(baud)])
            else:
                os.execvp("minicom", ["minicom", "-D", device, "-b", str(baud)])

    print("Error: No terminal emulator found (install picocom or minicom)", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Serial port utilities for Pico 2 W development.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s list                         # List serial devices
    %(prog)s read /dev/ttyACM1 10         # Read for 10 seconds
    %(prog)s capture /dev/ttyACM1 10      # Wait for device, read for 10s
    %(prog)s console                      # Interactive console
"""
    )

    parser.add_argument("-b", "--baud", type=int, default=DEFAULT_BAUD,
                        help=f"Baud rate (default: {DEFAULT_BAUD})")

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("list", help="List available serial devices")

    wait_parser = subparsers.add_parser("wait", help="Wait for device to appear")
    wait_parser.add_argument("device", nargs="?", default=DEFAULT_DEVICE, help="Device path")
    wait_parser.add_argument("timeout", nargs="?", type=int, default=DEFAULT_WAIT_TIMEOUT, help="Timeout in seconds")

    read_parser = subparsers.add_parser("read", help="Read serial output")
    read_parser.add_argument("device", nargs="?", default=DEFAULT_DEVICE, help="Device path")
    read_parser.add_argument("duration", nargs="?", type=int, default=DEFAULT_TIMEOUT, help="Duration in seconds")

    capture_parser = subparsers.add_parser("capture", help="Wait for device, then capture output")
    capture_parser.add_argument("device", nargs="?", default=DEFAULT_DEVICE, help="Device path")
    capture_parser.add_argument("duration", nargs="?", type=int, default=DEFAULT_TIMEOUT, help="Duration in seconds")
    capture_parser.add_argument("wait_timeout", nargs="?", type=int, default=DEFAULT_WAIT_TIMEOUT, help="Wait timeout")

    console_parser = subparsers.add_parser("console", help="Open interactive console")
    console_parser.add_argument("device", nargs="?", default=DEFAULT_DEVICE, help="Device path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "list":
        cmd_list()
    elif args.command == "wait":
        if not cmd_wait(args.device, args.timeout):
            sys.exit(1)
    elif args.command == "read":
        cmd_read(args.device, args.duration, args.baud)
    elif args.command == "capture":
        cmd_capture(args.device, args.duration, args.wait_timeout, args.baud)
    elif args.command == "console":
        cmd_console(args.device, args.baud)


if __name__ == "__main__":
    main()
