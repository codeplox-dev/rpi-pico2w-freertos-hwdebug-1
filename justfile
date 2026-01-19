# Pico 2 W WiFi Scanner - Build and Development

pico_sdk_version := "2.2.0"
project_dir := justfile_directory()

# SDK paths (override any conflicting environment variables)
export PICO_SDK_PATH := project_dir / "deps/pico-sdk"
export FREERTOS_KERNEL_PATH := project_dir / "deps/FreeRTOS-Kernel"

default:
    @just --list

# =============================================================================
# Setup
# =============================================================================

# Setup development environment (SDK, FreeRTOS, OpenOCD)
setup:
    ./tools/setup_sdk.py --sdk-version {{pico_sdk_version}}
    ./tools/setup_openocd.py

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

# Clean build artifacts and caches
clean:
    -./tools/pico.py openocd stop 2>/dev/null
    rm -rf build .pytest_cache .cache tools/__pycache__ .local/run

# Clean everything (SDK, OpenOCD, build)
distclean: clean
    rm -rf deps .local pico_sdk_import.cmake FreeRTOS_Kernel_import.cmake
