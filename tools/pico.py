#!/usr/bin/env python3
"""Pico 2 W development tool - flash, debug, and serial operations.

Consolidates all Pico development operations into a single tool.
"""

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from common import get_project_dir, get_local_dir

# =============================================================================
# Configuration
# =============================================================================

DEFAULT_BAUD = 115200
GDB_PORT = 3333
TELNET_PORT = 4444


def get_openocd_path() -> Path:
    """Get the path to the local OpenOCD binary."""
    return get_local_dir() / "bin" / "openocd"


def get_openocd_scripts() -> Path:
    """Get the path to OpenOCD scripts directory."""
    return get_local_dir() / "share" / "openocd" / "scripts"


def get_default_elf() -> Path:
    """Get the default ELF file path."""
    return get_project_dir() / "build" / "src" / "wifi_scanner.elf"


# =============================================================================
# Serial Device Detection
# =============================================================================

def find_pico_device() -> Optional[str]:
    """Find the Pico's USB CDC device (not the debug probe UART)."""
    try:
        from serial.tools import list_ports
    except ImportError:
        return None

    for port in list_ports.comports():
        if port.vid == 0x2e8a and port.pid in (0x0009, 0x000a, 0x0005):
            return port.device
        if port.product and "Pico" in port.product and "Debug" not in port.product:
            return port.device
    return None


def wait_for_pico(timeout: float = 5.0) -> Optional[str]:
    """Wait for Pico USB CDC to appear and be stable."""
    import serial as _serial
    start = time.time()
    device = None
    stable_since = None

    while time.time() - start < timeout:
        found = find_pico_device()
        if found and os.path.exists(found) and os.access(found, os.R_OK | os.W_OK):
            if found == device and stable_since:
                # Device has been stable for a while, try to open it
                if time.time() - stable_since >= 0.5:
                    try:
                        port = _serial.Serial(found, 115200, timeout=0.1)
                        port.close()
                        return found
                    except (OSError, _serial.SerialException):
                        # Not ready yet, keep waiting
                        stable_since = None
            else:
                # New device found, start stability timer
                device = found
                stable_since = time.time()
        else:
            # Device disappeared, reset
            device = None
            stable_since = None
        time.sleep(0.1)
    return device  # Return last found device even if not fully stable


def get_serial_device(wait: bool = True) -> Optional[str]:
    """Get serial device, with optional wait for Pico.

    Returns None if no Pico CDC device found (e.g., when debugging).
    """
    if wait:
        print("Waiting for Pico USB CDC...", file=sys.stderr)
        device = wait_for_pico(5.0)
        if device:
            return device
    else:
        device = find_pico_device()
        if device and os.path.exists(device) and os.access(device, os.R_OK | os.W_OK):
            return device
    return None


# =============================================================================
# PID File Management
# =============================================================================

def get_pid_dir() -> Path:
    """Get the directory for PID files."""
    return get_local_dir() / "run"


def get_pid_file(name: str) -> Path:
    """Get the path to a PID file."""
    return get_pid_dir() / f"{name}.pid"


def read_pid_file(name: str) -> Optional[int]:
    """Read PID from file, return None if file doesn't exist or is invalid."""
    pid_file = get_pid_file(name)
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text().strip())
        return pid if pid > 0 else None
    except (ValueError, OSError):
        return None


def write_pid_file(name: str, pid: int) -> None:
    """Write PID to file."""
    pid_dir = get_pid_dir()
    pid_dir.mkdir(parents=True, exist_ok=True)
    get_pid_file(name).write_text(str(pid))


def remove_pid_file(name: str) -> None:
    """Remove PID file if it exists."""
    pid_file = get_pid_file(name)
    if pid_file.exists():
        pid_file.unlink()


def is_pid_running(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def cleanup_stale_pid(name: str) -> None:
    """Remove PID file if the process is no longer running."""
    pid = read_pid_file(name)
    if pid and not is_pid_running(pid):
        remove_pid_file(name)


# =============================================================================
# OpenOCD Helpers
# =============================================================================

def is_port_open(port: int, host: str = "localhost") -> bool:
    """Check if a port is open."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((host, port)) == 0
    except (socket.error, OSError):
        return False


def get_openocd_pid() -> Optional[int]:
    """Get PID of this project's OpenOCD process, cleaning up stale records."""
    # First check our PID file
    pid = read_pid_file("openocd")
    if pid:
        if is_pid_running(pid):
            return pid
        # Stale PID file, clean up
        remove_pid_file("openocd")
    return None


def is_openocd_running() -> bool:
    """Check if this project's OpenOCD is running."""
    pid = get_openocd_pid()
    if pid:
        return True
    # Also check if port is in use (might be another project's OpenOCD)
    return is_port_open(GDB_PORT)


def openocd_command(cmd: str, timeout: float = 2.0) -> bool:
    """Send a command to OpenOCD via telnet. Returns True on success."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(("localhost", TELNET_PORT))
            # Read banner
            s.recv(1024)
            # Send command
            s.sendall(f"{cmd}\n".encode())
            # Read response
            s.recv(1024)
            return True
    except (socket.error, OSError):
        return False


def flash_via_telnet(elf_path: Path, timeout: float = 30.0) -> tuple[bool, str]:
    """Flash firmware via running OpenOCD's telnet interface.

    Returns (success, output) tuple.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect(("localhost", TELNET_PORT))

            # Read banner (includes escape codes)
            time.sleep(0.1)
            s.recv(1024)

            all_output = []

            def send_and_read(cmd: str, read_timeout: float = 10.0, success_marker: str = "") -> str:
                """Send command and read response until prompt or success marker."""
                s.sendall(f"{cmd}\n".encode())
                response = b""
                s.settimeout(1.0)  # Short timeout for individual reads
                deadline = time.time() + read_timeout
                while time.time() < deadline:
                    try:
                        chunk = s.recv(4096)
                        if not chunk:
                            break
                        response += chunk
                        decoded = response.decode("utf-8", errors="replace")
                        # Check for success marker if provided
                        if success_marker and success_marker in decoded:
                            # Read a bit more to get the prompt
                            time.sleep(0.1)
                            try:
                                s.settimeout(0.5)
                                extra = s.recv(1024)
                                response += extra
                            except socket.timeout:
                                pass
                            break
                        # Check for prompt (command completed) - > at end of line
                        if b"\n> " in response or response.rstrip().endswith(b">"):
                            break
                    except socket.timeout:
                        # Keep trying until deadline
                        continue
                return response.decode("utf-8", errors="replace")

            # Halt target
            out = send_and_read("reset halt", 5.0)
            all_output.append(out)

            # Program and verify - look for "Verified OK" as success marker
            out = send_and_read(f"program {elf_path} verify", 60.0, "** Verified OK **")
            all_output.append(out)

            full_output = "\n".join(all_output)

            if "** Verified OK **" not in out:
                if "** Programming Finished **" in out:
                    # Programming done but verify might have failed or not completed
                    pass
                return False, full_output

            # Reset and run
            out = send_and_read("reset run", 5.0)
            all_output.append(out)

            return True, "\n".join(all_output)

    except socket.timeout:
        return False, "Timeout waiting for OpenOCD response"
    except (socket.error, OSError) as e:
        return False, f"Failed to communicate with OpenOCD: {e}"


def resume_target() -> bool:
    """Resume target execution via OpenOCD. Returns True if successful."""
    if not is_port_open(TELNET_PORT):
        return False
    return openocd_command("resume")


def is_debugger_available() -> tuple[bool, str]:
    """Check if the CMSIS-DAP debugger interface is available for a new OpenOCD instance.

    This should only be called when no existing OpenOCD is running (caller should
    check telnet port first and reuse if available).

    Returns (available, message) where message explains why if not available.
    """
    # Probe the USB interface by running a quick OpenOCD init/shutdown
    openocd = get_openocd_path()
    scripts = get_openocd_scripts()

    if not openocd.exists():
        return False, f"OpenOCD not found at {openocd}"

    cmd = [str(openocd), "-s", str(scripts),
           "-f", "interface/cmsis-dap.cfg", "-f", "target/rp2350.cfg",
           "-c", "adapter speed 5000", "-c", "init", "-c", "shutdown"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        stderr = result.stderr

        if "could not claim interface" in stderr.lower() or "resource busy" in stderr.lower():
            return False, "Debug probe USB interface is busy (another process has claimed it)"

        if "error submitting usb" in stderr.lower():
            return False, "Debug probe USB communication error (interface may be in use)"

        if result.returncode != 0:
            # Check for other common errors
            if "no cmsis-dap device found" in stderr.lower():
                return False, "No CMSIS-DAP debug probe found (is it connected?)"
            # Unknown error, but still failed
            return False, f"Debug probe initialization failed: {stderr.strip()[-200:]}"

        return True, "Debug probe available"

    except subprocess.TimeoutExpired:
        return False, "Debug probe timed out (interface may be hung)"
    except Exception as e:
        return False, f"Failed to probe debug interface: {e}"


def run_openocd(commands: list[str]) -> int:
    """Run OpenOCD with given commands."""
    openocd = get_openocd_path()
    scripts = get_openocd_scripts()

    if not openocd.exists():
        print(f"Error: OpenOCD not found at {openocd}", file=sys.stderr)
        print("Run: just setup", file=sys.stderr)
        return 1

    cmd = [str(openocd), "-s", str(scripts),
           "-f", "interface/cmsis-dap.cfg", "-f", "target/rp2350.cfg"]
    for c in commands:
        cmd.extend(["-c", c])

    return subprocess.run(cmd).returncode


# =============================================================================
# Flash Command
# =============================================================================

def cmd_flash(elf_file: Optional[Path] = None, reset_only: bool = False) -> int:
    """Flash firmware or reset target."""
    elf = elf_file or get_default_elf()

    # Check if OpenOCD is already running - if so, reuse it via telnet
    if is_port_open(TELNET_PORT):
        print("Using running OpenOCD instance...", file=sys.stderr)

        if reset_only:
            if openocd_command("reset run"):
                print("Target reset.", file=sys.stderr)
                return 0
            print("Error: Failed to reset target", file=sys.stderr)
            return 1

        if not elf.exists():
            print(f"Error: ELF file not found: {elf}", file=sys.stderr)
            return 1

        success, output = flash_via_telnet(elf)
        if success:
            print("Flash complete.", file=sys.stderr)
            return 0
        else:
            print(f"Error: Flash failed", file=sys.stderr)
            print(output, file=sys.stderr)
            return 1

    # No running OpenOCD - check if debugger is available and start fresh
    available, message = is_debugger_available()
    if not available:
        print(f"Error: {message}", file=sys.stderr)
        return 1

    if reset_only:
        return run_openocd(["init", "reset run", "shutdown"])

    if not elf.exists():
        print(f"Error: ELF file not found: {elf}", file=sys.stderr)
        return 1

    return run_openocd([
        "adapter speed 5000",
        f"program {elf} verify reset exit"
    ])


# =============================================================================
# Debug Commands (for VSCode integration)
# =============================================================================

def cmd_openocd_start(foreground: bool = False) -> int:
    """Start OpenOCD server (reuses existing from this project)."""
    # Clean up any stale PID records first
    cleanup_stale_pid("openocd")

    # Check if our OpenOCD is running
    our_pid = get_openocd_pid()
    if our_pid:
        print(f"OpenOCD already running (PID: {our_pid}) on port {GDB_PORT}")
        return 0

    # Check if port is in use by another project's OpenOCD
    if is_port_open(GDB_PORT):
        print(f"Warning: Port {GDB_PORT} in use by another process", file=sys.stderr)
        print("Stop the other OpenOCD or use a different port", file=sys.stderr)
        return 1

    openocd = get_openocd_path()
    scripts = get_openocd_scripts()

    if not openocd.exists():
        print(f"Error: OpenOCD not found", file=sys.stderr)
        return 1

    cmd = [str(openocd), "-s", str(scripts),
           "-f", "interface/cmsis-dap.cfg", "-f", "target/rp2350.cfg",
           "-c", "adapter speed 5000", "-c", "init", "-c", "reset halt"]

    if foreground:
        return subprocess.run(cmd).returncode

    # Background mode
    log_file = get_project_dir() / "build" / "openocd.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    print("Starting OpenOCD...")
    with open(log_file, "w") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                               start_new_session=True)

    # Wait for ready
    start = time.time()
    while time.time() - start < 10.0:
        if is_port_open(GDB_PORT):
            # Save PID for this project
            write_pid_file("openocd", proc.pid)
            print(f"OpenOCD started (PID: {proc.pid})")
            print(f"  GDB: localhost:{GDB_PORT}")
            return 0
        # Check if process died
        if proc.poll() is not None:
            break
        time.sleep(0.1)

    # OpenOCD failed to start - check log for specific errors
    print("Error: OpenOCD failed to start", file=sys.stderr)
    try:
        log_content = log_file.read_text()
        if "could not claim interface" in log_content.lower() or "resource busy" in log_content.lower():
            print("Debug probe USB interface is busy (another process has claimed it)", file=sys.stderr)
        elif "no cmsis-dap device found" in log_content.lower():
            print("No CMSIS-DAP debug probe found (is it connected?)", file=sys.stderr)
        elif "error submitting usb" in log_content.lower():
            print("Debug probe USB communication error", file=sys.stderr)
        print(f"See {log_file} for details", file=sys.stderr)
    except Exception:
        pass
    return 1


def cmd_openocd_stop() -> int:
    """Stop this project's OpenOCD server."""
    # Clean up stale records first
    cleanup_stale_pid("openocd")

    pid = get_openocd_pid()
    if not pid:
        # Check if port is in use (might be another project's)
        if is_port_open(GDB_PORT):
            print(f"Port {GDB_PORT} in use but not by this project's OpenOCD")
            print("Use 'pkill openocd' to stop all OpenOCD instances")
        else:
            print("OpenOCD not running")
        return 0

    print(f"Stopping OpenOCD (PID: {pid})...")
    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(50):
            time.sleep(0.1)
            try:
                os.kill(pid, 0)
            except OSError:
                break
        else:
            os.kill(pid, signal.SIGKILL)
    except OSError as e:
        print(f"Error: {e}", file=sys.stderr)
        # Still remove PID file even if kill failed
        remove_pid_file("openocd")
        return 1

    # Clean up PID file
    remove_pid_file("openocd")
    print("OpenOCD stopped")
    return 0


# =============================================================================
# Serial Commands
# =============================================================================

def cmd_serial_read(duration: Optional[int] = None, device: Optional[str] = None,
                    baud: int = DEFAULT_BAUD) -> int:
    """Read serial output. If duration specified, exit after that time. Otherwise read forever."""
    # If OpenOCD is running, resume target first (it may be halted from debugging)
    if not device and is_openocd_running():
        print("Debugger active, resuming target...", file=sys.stderr)
        resume_target()
        time.sleep(0.5)  # Brief wait for firmware to start

    if device:
        if not os.path.exists(device):
            print(f"Error: Device {device} not found", file=sys.stderr)
            return 1
    else:
        device = get_serial_device(wait=True)
        if not device:
            print("Error: Pico USB CDC not found", file=sys.stderr)
            print("", file=sys.stderr)
            print("Ensure:", file=sys.stderr)
            print("  1. Pico is connected via USB (not just debug probe)", file=sys.stderr)
            print("  2. Firmware has been flashed: just run", file=sys.stderr)
            print("  3. Wait a few seconds after flash for USB enumeration", file=sys.stderr)
            return 1

    try:
        import serial
    except ImportError:
        print("Error: pyserial not installed", file=sys.stderr)
        return 1

    if duration:
        print(f"Reading from {device} for {duration}s (Ctrl+C to stop)...", file=sys.stderr)
    else:
        print(f"Reading from {device} (Ctrl+C to stop)...", file=sys.stderr)

    captured = 0
    port = None
    try:
        port = serial.Serial(port=device, baudrate=baud, timeout=0.1)

        end_time = time.time() + duration if duration else None
        while True:
            if end_time and time.time() >= end_time:
                break
            data = port.read(1024)
            if data:
                captured += len(data)
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1
    finally:
        if port:
            try:
                # Graceful close: flush buffers and lower control signals
                port.reset_input_buffer()
                port.reset_output_buffer()
                port.dtr = False
                port.rts = False
            except (OSError, serial.SerialException):
                pass  # Device may have disconnected
            port.close()

    print(f"\nRead {captured} bytes.", file=sys.stderr)
    return 0


# =============================================================================
# Main
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pico 2 W development tool",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # flash
    flash_p = subparsers.add_parser("flash", help="Flash firmware to target")
    flash_p.add_argument("elf", nargs="?", help="ELF file (default: build output)")
    flash_p.add_argument("--reset", action="store_true", help="Reset only, don't flash")

    # openocd (for VSCode/debug integration)
    ocd_p = subparsers.add_parser("openocd", help="OpenOCD server control")
    ocd_p.add_argument("action", choices=["start", "stop"],
                       help="Action to perform")
    ocd_p.add_argument("--foreground", "-f", action="store_true",
                       help="Run in foreground")

    # serial-read (reads forever or for specified duration)
    sr_p = subparsers.add_parser("serial-read", help="Read serial output")
    sr_p.add_argument("duration", nargs="?", type=int, default=None,
                      help="Duration in seconds (omit to read forever)")
    sr_p.add_argument("-d", "--device", help="Serial device")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "flash":
        elf = Path(args.elf) if args.elf else None
        sys.exit(cmd_flash(elf, reset_only=args.reset))

    elif args.command == "openocd":
        if args.action == "start":
            sys.exit(cmd_openocd_start(foreground=args.foreground))
        elif args.action == "stop":
            sys.exit(cmd_openocd_stop())

    elif args.command == "serial-read":
        sys.exit(cmd_serial_read(args.duration, args.device))


if __name__ == "__main__":
    main()
