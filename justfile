# Pico 2 W WiFi Scanner - Pico SDK + FreeRTOS

default:
    @just --list

# =============================================================================
# Environment Setup
# =============================================================================

# Setup development environment (SDK, FreeRTOS, OpenOCD)
envsetup: setup-sdk setup-openocd

# Setup Pico SDK and FreeRTOS Kernel
setup-sdk:
    python3 ./tools/setup_sdk.py

# Build OpenOCD from source (required for RP2350 support)
setup-openocd:
    python3 ./tools/setup_openocd.py

# Setup VSCode IDE (extensions and configuration)
idesetup:
    python3 ./tools/setup_ide.py

# =============================================================================
# Build & Flash
# =============================================================================

# Configure CMake build
configure:
    cmake -B build -G Ninja

# Build the application
build: configure
    cmake --build build

# Build and flash
run: build flash

# Flash to target via debug probe
flash:
    python3 ./tools/flash.py

# Reset the target
reset:
    python3 ./tools/flash.py reset

# =============================================================================
# Serial Console
# =============================================================================

# List available serial devices
serial-list:
    python3 ./tools/serial_util.py list

# Open interactive console (Ctrl+A Ctrl+X to exit)
console:
    python3 ./tools/serial_util.py console

# Capture serial output for specified duration (default 5s)
capture duration="5":
    python3 ./tools/serial_util.py capture /dev/ttyACM1 {{duration}}

# =============================================================================
# Testing
# =============================================================================

# Build and run unit tests (host-side, no hardware)
unit-test:
    cmake -B build/test -S test -G Ninja
    cmake --build build/test
    ./build/test/test_unit

# Build and run integration tests (with mocks)
integration-test:
    cmake -B build/test -S test -G Ninja
    cmake --build build/test
    ./build/test/test_integration

# Run all tests
test: unit-test integration-test

# =============================================================================
# Code Quality
# =============================================================================

# Run C++ linters (cppcheck, clang-tidy)
lint:
    @echo "Running cppcheck..."
    cppcheck --enable=warning,style,performance --error-exitcode=1 \
        --suppress=missingIncludeSystem \
        -I src src/*.cpp src/*.hpp 2>&1 || true
    @echo ""
    @echo "Running clang-tidy..."
    clang-tidy src/*.cpp src/*.hpp \
        --checks='-*,readability-*,bugprone-*,modernize-*,performance-*' \
        --warnings-as-errors='' \
        -- -std=c++17 -I src 2>&1 || true

# Run all checks (lint + tests)
check: lint test

# =============================================================================
# Cleanup
# =============================================================================

# Clean build artifacts
clean:
    rm -rf build

# Remove all generated content (SDK, FreeRTOS, OpenOCD, build)
distclean: clean
    rm -rf deps .local pico_sdk_import.cmake FreeRTOS_Kernel_import.cmake
