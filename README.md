# Pico 2 W WiFi Scanner

WiFi scanner for Raspberry Pi Pico 2 W using Pico SDK and FreeRTOS. Scans for nearby networks every 20 seconds, blinking the LED during scans. Results output to USB serial.

## Hardware Setup

![Hardware setup showing Pico 2 W and Debug Probe](doc/hardware-setup.jpg)

Connect both devices to your workstation via USB:

- **Pico 2 W** (right): USB provides power and serial output for scan results
- **Debug Probe** (left): USB provides debug interface for flashing and debugging

The 3-wire debug cable connects the Debug Probe's **D** (debug) port to the Pico's **Debug** port. The Debug Probe's **U** (UART) port is left unconnected—we use the Pico's native USB for serial output, which simplifies field deployment since only one cable is needed for normal operation.

## Software Setup

The portable Nix environment and toolchain setup scripts in `tools/` provide a consistent native runtime environment across platforms. The system is tested on macOS with Apple Silicon, Linux amd64, and Raspberry Pi 64-bit running Raspbian Bookworm or Ubuntu 24.10.

Storage requirements: the dedicated Pico tooling and sources total about 600MB. The reusable Nix environment adds about 300MB.

### Requirements

- Raspberry Pi Pico 2 W + Debug Probe (or any CMSIS-DAP debugger)
- Nix (flakes enabled) and direnv — see **[Nix Environment Guide](doc/nix-environment.md)** for setup and portability

## Quick Start

```bash
# Clone and enter directory
git clone https://github.com/codeplox-dev/rpi-pico2w-freertos-hwdebug-1.git
cd rpi-pico2w-freertos-hwdebug-1

# Load nix environment
direnv allow

# First-time setup (SDK, FreeRTOS, OpenOCD)
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
| `just setup` | First-time setup (SDK, FreeRTOS, OpenOCD) |
| `just build` | Build the application |
| `just flash` | Flash to device via debug probe |
| `just run` | Build and flash |
| `just serial-read` | Read serial output (Ctrl+C to stop) |
| `just serial-read N` | Read for N seconds |
| `just test` | Run host tests |
| `just clean` | Remove build artifacts |

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

## Project Structure

```
src/                  # Application source
test/                 # Host-side unit and integration tests
tools/                # Build and flash utilities
.vscode/              # Debug configurations and tasks
flake.nix             # Nix development environment
justfile              # Command runner
```

## Troubleshooting

**No serial output:** Ensure Pico USB is connected (not just debug probe). Wait a few seconds after flash for USB enumeration.

**Flash fails:** Check debug probe connection. Rebuild OpenOCD with `just setup` if needed.

**IntelliSense errors:** Run `just build` to generate `compile_commands.json`, then reload VSCode.

## Technical Details

- **MCU:** RP2350 (dual Cortex-M33, 150 MHz)
- **WiFi:** CYW43439 via FreeRTOS lwIP integration
- **SDK:** Pico SDK 2.2.0, FreeRTOS with tickless idle
- **Debug:** OpenOCD (built from source for RP2350 support)
