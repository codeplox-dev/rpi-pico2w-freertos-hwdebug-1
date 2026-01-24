# Pico 2 W WiFi Scanner - Build and Development

# =============================================================================
# Dependency Versions (override with: just --set pico_sdk_version "2.3.0" setup)
# =============================================================================

# Pico SDK - https://github.com/raspberrypi/pico-sdk/tags
pico_sdk_version := "2.2.0"

# FreeRTOS Kernel (Raspberry Pi fork) - https://github.com/raspberrypi/FreeRTOS-Kernel
# No tags available; using commit hash from main branch
freertos_kernel_version := "4f7299d6ea746b27a9dd19e87af568e34bd65b15"

# OpenOCD - https://github.com/raspberrypi/openocd/tags (Raspberry Pi fork with RP2350 support)
openocd_version := "sdk-2.2.0"

# picotool - https://github.com/raspberrypi/picotool/tags
# Usually matches SDK version
picotool_version := "2.2.0"

# =============================================================================
# Project paths
# =============================================================================

project_dir := justfile_directory()

# SDK paths (override any conflicting environment variables)
export PICO_SDK_PATH := project_dir / "deps/pico-sdk"
export FREERTOS_KERNEL_PATH := project_dir / "deps/FreeRTOS-Kernel"

default:
    @just --list

# =============================================================================
# Setup
# =============================================================================

# Setup development environment (SDK, FreeRTOS, OpenOCD, udev rules)
setup:
    ./tools/setup_sdk.py --sdk-version {{pico_sdk_version}} --freertos-version {{freertos_kernel_version}} --picotool-version {{picotool_version}}
    ./tools/setup_openocd.py --version {{openocd_version}}
    ./tools/setup_udev.py

# Setup VSCode IDE
setup-vscode:
    ./tools/setup_vscode.py

# =============================================================================
# Build & Flash
# =============================================================================

# Build the application
build:
    cmake --preset default
    cmake --build build

# Flash firmware to target
flash:
    ./tools/pico.py flash

# Build and flash (main development workflow)
run: build flash

# =============================================================================
# Serial & RTT
# =============================================================================

# Read serial output (forever if no duration, or for N seconds)
serial-read duration="":
    ./tools/pico.py serial-read {{duration}}

# Read RTT output via debug probe (forever if no duration, or for N seconds)
rtt-read duration="":
    ./tools/pico.py rtt-read {{duration}}

# =============================================================================
# Testing
# =============================================================================

# Run all tests
test:
    cmake --preset default -S test
    cmake --build build/test
    ctest --test-dir build/test --output-on-failure

# =============================================================================
# Cleanup
# =============================================================================

# Stop any running debug sessions (openocd, gdb)
stop:
    -pkill -f openocd 2>/dev/null || true
    -pkill -f arm-none-eabi-gdb 2>/dev/null || true

# Clean build artifacts and caches
clean: stop
    rm -rf build .pytest_cache .cache tools/__pycache__ .local/run

# Clean everything (SDK, OpenOCD, build)
distclean: clean
    rm -rf deps .local pico_sdk_import.cmake FreeRTOS_Kernel_import.cmake
