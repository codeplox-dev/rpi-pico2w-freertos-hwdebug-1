# Raspberry Pi Pico 2 W FreeRTOS w/ Debug Probe

This project demonstrates project setup and tooling for the Pico 2 W running FreeRTOS. It uses the [Official Debug Probe](https://www.raspberrypi.com/documentation/microcontrollers/debug-probe.html) for flashing and hardware debugging. Note that you can use this build system without the dedicated debugger by building a `.uf2` file and copying it to the Pico's storage, but the specifics of this are left to the interested reader.

The project can be used from the CLI entirely, but there is also support for setting up VSCode for debugging.

The business logic of this simple system scans WiFi in a continuous loop every 20 seconds, blinking the LED during scans. The results are written as text to USB serial. RTT is used through the debug probe to send debug messages to the developer. 

## Pico Hardware Setup

![Hardware setup showing Pico 2 W and Debug Probe](doc/hardware-setup.jpg)

Connect both devices to your workstation via USB:

- **Pico 2 W** (right): USB provides power and serial output for scan results
- **Debug Probe** (left): USB provides debug interface for flashing and debugging

The 3-wire debug cable connects the Debug Probe's **D** (debug) port to the Pico's **Debug** port. The Debug Probe's **U** (UART) port is left unconnected—we use the Pico's native USB for serial output, which simplifies field deployment since only one cable is needed for normal operation.

## Workstation Software Setup

The portable Nix environment and toolchain setup scripts in `tools/` provide a consistent native runtime environment across platforms. The system is tested on macOS with Apple Silicon, Linux amd64, and Raspberry Pi 64-bit running Ubuntu 24.04.

Storage requirements: the dedicated Pico tooling and sources total about 600MB. The reusable Nix environment adds about 300MB.

### Requirements

- Raspberry Pi Pico 2 W + Debug Probe (or any CMSIS-DAP debugger)
- Nix (flakes enabled) and direnv — see **[Nix Environment Guide](doc/nix-environment.md)** for setup and portability

On Linux, `just setup` automatically installs udev rules and adds your user to the `dialout` and `plugdev` groups for USB device access. You'll need to log out and back in after the first setup for group changes to take effect.

## Quick Start

```bash
# Clone and enter directory
git clone https://github.com/codeplox-dev/rpi-pico2w-freertos-hwdebug-1.git
cd rpi-pico2w-freertos-hwdebug-1

# Load nix environment
direnv allow

# First-time setup
just setup

# Build and flash
just run

# Read serial output (Ctrl+C to stop)
just serial-read
```

### Example Output

```
========================================
  Pico 2 W WiFi Scanner
  FreeRTOS + CYW43
========================================

Scanning every 20 seconds...
--- Starting scan ---

  SSID                              BSSID               CH     RSSI  AUTH
  --------------------------------------------------------------------------------
  MyNetwork                         24:C9:A1:5C:27:98  ch 6   -45dBm  WPA2
  Neighbor_WiFi                     80:69:1A:B9:C0:F1  ch11   -72dBm  WPA2

  Found 2 networks
```

## Commands

| Command | Description |
|---------|-------------|
| `just setup` | First-time setup (SDK, FreeRTOS, OpenOCD, udev) |
| `just build` | Build the application |
| `just flash` | Flash to device via debug probe |
| `just run` | Build and flash |
| `just serial-read` | Read serial output (Ctrl+C to stop) |
| `just serial-read N` | Read for N seconds |
| `just rtt-read` | Read RTT debug output via debug probe |
| `just rtt-read N` | Read RTT for N seconds |
| `just test` | Run host tests |
| `just stop` | Stop running debug sessions (openocd, gdb) |
| `just clean` | Stop debug sessions and remove build artifacts |

## VSCode Debugging

```bash
just setup-vscode   # Install extensions and verify configuration
just build          # Required for IntelliSense
```

Open the project in VSCode, then press **F5** to start debugging. The **Debug** configuration builds, flashes, and halts at `main()`. Use **Attach** to connect to an already-running target without flashing.

For serial output while debugging, run `just serial-read` in the integrated terminal—it automatically resumes the target if halted.

See **[VSCode Debugging Guide](doc/vscode-debugging.md)** for detailed setup, RTOS task inspection, peripheral register views, and troubleshooting.

## Architecture

Two FreeRTOS tasks coordinate scanning:

- **Main task**: Requests scans every 20 seconds, prints results to serial
- **Scanner task**: Performs WiFi scans, blinks LED during scan

## RTT Debugging

RTT (Real-Time Transfer) provides fast debug output through the debug probe without requiring a USB serial connection. While serial output (`just serial-read`) shows application messages like scan results, RTT output (`just rtt-read`) shows timestamped debug logs useful during development.

**Message path:** Application code calls `DBG_INFO()`, `DBG_WARN()`, or `DBG_ERROR()` macros from `debug_log.hpp`. These expand to `printf()` calls, which the Pico SDK routes to all enabled stdio drivers—USB, UART, and RTT. The RTT driver writes to a circular buffer in target RAM. OpenOCD polls this buffer through the debug probe's SWD connection and streams the data to a TCP port, which `just rtt-read` connects to and displays.

**Why use RTT:**

- **Debug probe only:** Works when only the debug probe is connected—no need for a second USB cable to the Pico
- **Continues when halted:** Output keeps flowing even when execution is stopped at a breakpoint
- **Low overhead:** Writes to RAM are fast and non-blocking, minimizing timing impact on real-time code

To view RTT output, run `just rtt-read` in a terminal while the target is running or being debugged. Both serial and RTT can run simultaneously since they use independent channels.

## Troubleshooting

**Build fails:** After setting up Nix and direnv, you must execute `just setup` to set up the build environment.

**No serial output:** Ensure Pico USB is connected (not just debug probe). Wait a few seconds after flash for USB enumeration.

**Flash fails with "unable to find CMSIS-DAP device":** On Linux, this is usually a USB permissions issue. Re-run `just setup` to install udev rules, then log out and back in for group changes to take effect. If the problem persists, verify the debug probe is connected with `lsusb | grep 2e8a`.

**IntelliSense errors:** Run `just build` to generate `compile_commands.json`, then reload VSCode.

## Technical Details

- **MCU:** RP2350 dual Cortex-M33 at 150 MHz (Core 0 only; Core 1 and RISC-V cores idle)
- **Threading:** FreeRTOS preemptive scheduler; two tasks coordinate via task notifications
- **WiFi:** CYW43439 via FreeRTOS lwIP integration
- **SDK:** Pico SDK 2.2.0, FreeRTOS with tickless idle

See **[Hardware Overview](doc/hardware.md)** for details on the RP2350's dual-architecture cores, PIO capabilities, and power characteristics.

## Tools Used

[Claude Code](https://claude.ai/claude-code) was used interactively throughout this project to:

- Explore FreeRTOS project setup and configuration options
- Build and troubleshoot the Nix-based toolchain and justfile commands
- Write and refine documentation

## See Also

**[Rust/Embassy Port Plan](rust-port.md)** — A speculative plan for porting this project to Rust using Embassy, generated with Claude Code. The port has not been implemented.
