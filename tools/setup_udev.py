#!/usr/bin/env python3
"""Setup udev rules for Raspberry Pi Pico devices on Linux.

This script installs udev rules that allow non-root users to access
the Pico and Debug Probe USB devices.
"""

import grp
import os
import platform
import subprocess
import sys
from pathlib import Path


UDEV_RULES_FILE = "/etc/udev/rules.d/99-pico.rules"
PLUGDEV_GROUP = "plugdev"

# Raspberry Pi Pico USB device rules
# VID 0x2e8a = Raspberry Pi
# PID 0x0009 = Pico (CDC)
# PID 0x000a = Pico (CMSIS-DAP)
# PID 0x0005 = Pico (MSD)
# PID 0x000c = Debug Probe (CMSIS-DAP)
UDEV_RULES = """\
# Raspberry Pi Pico and Debug Probe
# Allow non-root users to access USB devices

# Pico (various modes)
SUBSYSTEM=="usb", ATTR{idVendor}=="2e8a", ATTR{idProduct}=="0009", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="2e8a", ATTR{idProduct}=="000a", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="2e8a", ATTR{idProduct}=="0005", MODE="0666", GROUP="plugdev"

# Debug Probe (CMSIS-DAP)
SUBSYSTEM=="usb", ATTR{idVendor}=="2e8a", ATTR{idProduct}=="000c", MODE="0666", GROUP="plugdev"
"""


def is_linux() -> bool:
    """Check if running on Linux."""
    return platform.system() == "Linux"


def check_group_exists(group: str) -> bool:
    """Check if a group exists on the system."""
    try:
        grp.getgrnam(group)
        return True
    except KeyError:
        return False


def is_user_in_group(group: str) -> bool:
    """Check if the current user is in the specified group."""
    try:
        gid = grp.getgrnam(group).gr_gid
        return gid in os.getgroups() or group in [grp.getgrgid(g).gr_name for g in os.getgroups()]
    except (KeyError, PermissionError):
        return False


def rules_installed() -> bool:
    """Check if udev rules are already installed."""
    rules_path = Path(UDEV_RULES_FILE)
    if not rules_path.exists():
        return False
    return "2e8a" in rules_path.read_text()


def install_udev_rules() -> tuple[bool, str]:
    """Install udev rules. Returns (success, message)."""
    if rules_installed():
        return True, "udev rules already installed"

    try:
        # Write rules file via sudo
        result = subprocess.run(
            ["sudo", "tee", UDEV_RULES_FILE],
            input=UDEV_RULES,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False, f"Failed to write udev rules: {result.stderr}"

        # Reload udev rules
        result = subprocess.run(
            ["sudo", "udevadm", "control", "--reload-rules"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False, f"Failed to reload udev rules: {result.stderr}"

        # Trigger udev to apply rules to existing devices
        result = subprocess.run(
            ["sudo", "udevadm", "trigger"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False, f"Failed to trigger udev: {result.stderr}"

        return True, "udev rules installed"

    except Exception as e:
        return False, f"Error installing udev rules: {e}"


def add_user_to_group(group: str) -> tuple[bool, str]:
    """Add current user to a group. Returns (success, message)."""
    user = os.environ.get("USER", os.environ.get("LOGNAME", ""))
    if not user:
        return False, "Could not determine current user"

    if is_user_in_group(group):
        return True, f"User already in {group} group"

    if not check_group_exists(group):
        # Create the group first
        result = subprocess.run(
            ["sudo", "groupadd", group],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False, f"Failed to create {group} group: {result.stderr}"

    try:
        result = subprocess.run(
            ["sudo", "usermod", "-aG", group, user],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False, f"Failed to add user to {group}: {result.stderr}"

        return True, f"Added {user} to {group} group (log out and back in to take effect)"

    except Exception as e:
        return False, f"Error adding user to group: {e}"


def main() -> int:
    """Main entry point."""
    if not is_linux():
        # No-op on non-Linux systems (macOS, Windows, etc.)
        return 0

    print("Setting up udev rules for Raspberry Pi Pico devices...")

    had_errors = False

    # Install udev rules (critical - fail if this doesn't work)
    success, message = install_udev_rules()
    if success:
        print(f"  {message}")
    else:
        print(f"Error: {message}", file=sys.stderr)
        print("", file=sys.stderr)
        print("To install udev rules manually:", file=sys.stderr)
        print(f"  sudo tee {UDEV_RULES_FILE} << 'EOF'", file=sys.stderr)
        print(UDEV_RULES.strip(), file=sys.stderr)
        print("EOF", file=sys.stderr)
        print("  sudo udevadm control --reload-rules && sudo udevadm trigger", file=sys.stderr)
        return 1

    # Add user to dialout group (for serial access)
    success, message = add_user_to_group("dialout")
    if success:
        print(f"  {message}")
    else:
        print(f"  Warning: {message}", file=sys.stderr)
        print(f"    To fix: sudo usermod -aG dialout $USER", file=sys.stderr)
        had_errors = True

    # Add user to plugdev group (for USB device access)
    success, message = add_user_to_group(PLUGDEV_GROUP)
    if success:
        print(f"  {message}")
    else:
        print(f"  Warning: {message}", file=sys.stderr)
        print(f"    To fix: sudo usermod -aG {PLUGDEV_GROUP} $USER", file=sys.stderr)
        had_errors = True

    if had_errors:
        print("", file=sys.stderr)
        print("Some group operations failed. You may need to run the commands above manually.", file=sys.stderr)
        print("After fixing, log out and back in for changes to take effect.", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
