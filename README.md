# Pico 2 W WiFi Scanner

WiFi scanner for Raspberry Pi Pico 2 W using Pico SDK and FreeRTOS.

**Behavior:**
- Starts scanning immediately on power-up (no console connection required)
- Scans for nearby WiFi networks every 20 seconds
- LED solid ON when idle, blinks rapidly during active scans
- Results output to USB serial if connected; otherwise discarded (no buffering)

## Requirements

**Hardware:**
- Raspberry Pi Pico 2 W
- Raspberry Pi Debug Probe (or CMSIS-DAP debugger)
- USB cables for both debug probe and Pico

**Software:**
- Linux host with Nix (flakes enabled)
- direnv (recommended)

## Quick Start

```bash
# Clone and enter directory
git clone <repo-url>
cd rpi-pico2w-freertos-hwdebug-1

# Allow direnv (loads nix environment automatically)
direnv allow

# First-time setup: clone SDK, FreeRTOS, build OpenOCD
just envsetup

# Build and flash
just run

# View output (Ctrl+A Ctrl+X to exit)
just console

# End-to-end test: build, flash, capture 25s of output (default is 5 if not overridden)
just run capture 25
```

## Commands

| Command | Description |
|---------|-------------|
| `just envsetup` | First-time setup (SDK, FreeRTOS, OpenOCD) |
| `just build` | Build the application |
| `just flash` | Flash to device via debug probe |
| `just run` | Build and flash |
| `just console` | Interactive serial console |
| `just capture` | Capture serial output (default 5s) |
| `just capture 30` | Capture for 30 seconds |
| `just serial-list` | List serial devices with details |
| `just test` | Run all tests (unit + integration) |
| `just lint` | Run C++ linters (cppcheck, clang-tidy) |
| `just check` | Run lint + tests |
| `just idesetup` | Setup VS Code (extensions, config) |
| `just clean` | Remove build artifacts |
| `just distclean` | Remove all generated content |

## Serial Output

```
========================================
  Pico 2 W WiFi Scanner
  FreeRTOS + CYW43
========================================

Initializing WiFi...
WiFi initialized.

Scanning every 20 seconds...
--- Starting scan ---

  SSID                              BSSID               CH     RSSI  AUTH
  --------------------------------------------------------------------------------
  MyNetwork                         24:C9:A1:5C:27:98  ch 6   -45dBm  WPA2
  Neighbor_WiFi                     80:69:1A:B9:C0:F1  ch11   -72dBm  WPA2

  Found 2 networks
```

## Architecture

The application uses FreeRTOS with two tasks:

- **Main task**: Requests scans every 20 seconds (using tickless idle), prints results
- **Scanner task**: Performs WiFi scans when requested, blinks LED during scan

```
Main Task                          Scanner Task
    │                                   │
    ├── request_scan() ────────────────▶│
    │   (semaphore)                     ├── LED blink (fast)
    │                                   ├── cyw43_wifi_scan()
    │                                   ├── collect results
    │◀──────────────────────────────────┤
    │   (semaphore + result)            └── LED solid on
    ├── print results
    └── vTaskDelay (20s, tickless)
```

## Project Structure

```
.
├── src/
│   ├── main.cpp           # Main task, console output
│   ├── wifi_scanner.cpp   # Scanner task, CYW43 interface
│   ├── wifi_scanner.hpp   # Scanner API
│   ├── scan_msg.hpp       # Result structures (APInfo, ScanResult)
│   ├── led.cpp            # LED control via FreeRTOS timer
│   ├── led.hpp            # LED API
│   ├── FreeRTOSConfig.h   # FreeRTOS configuration
│   ├── lwipopts.h         # lwIP configuration
│   └── CMakeLists.txt     # Application build config
├── tools/
│   ├── setup_sdk.py       # Clone Pico SDK and FreeRTOS
│   ├── setup_openocd.py   # Build OpenOCD from source
│   ├── flash.py           # Flash via debug probe
│   └── serial_util.py     # Serial console utilities
├── CMakeLists.txt         # Top-level CMake config
├── justfile               # Build commands
└── flake.nix              # Nix development environment
```

## Troubleshooting

**No serial output:**
1. Check device exists: `just serial-list`
2. Ensure Pico USB is connected (not just debug probe)
3. Wait a few seconds after flash for USB enumeration

**Flash fails:**
1. Check debug probe: `lsusb | grep -i "debug probe"`
2. Verify OpenOCD: `.local/bin/openocd --version`
3. Rebuild OpenOCD: `just setup-openocd`

**Build errors:**
1. Ensure nix environment is active: `echo $PICO_SDK_PATH`
2. Re-run setup: `just envsetup`
3. Clean rebuild: `just clean && just build`

## Technical Details

- **MCU:** RP2350 (dual Cortex-M33, 150 MHz)
- **WiFi:** CYW43439 (via `pico_cyw43_arch_lwip_sys_freertos`)
- **RTOS:** FreeRTOS with tickless idle
- **SDK:** Pico SDK 2.1.0+
- **OpenOCD:** Built from source (RP2350 support)
