# VSCode Debugging Guide

Complete guide to setting up and using VSCode for debugging on the Pico 2 W.

## Initial Setup

### 1. Install Extensions

Run the setup script to install required extensions and verify your configuration:

```bash
just setup-vscode
```

This installs:
- **Cortex-Debug** (`marus25.cortex-debug`) - ARM debugger integration
- **C/C++** (`ms-vscode.cpptools`) - IntelliSense and debugging
- **CMake Tools** (`ms-vscode.cmake-tools`) - Build system integration
- **direnv** (`mkhl.direnv`) - Environment management

### 2. Configure CMake

When you open the project, CMake Tools will prompt you to configure. Select the **default** preset (Pico 2 W ARM). This:

- Configures the build with the ARM cross-compiler
- Generates `compile_commands.json` for IntelliSense
- Sets the build target to `wifi_scanner`

If CMake doesn't configure automatically, run `CMake: Configure` from the Command Palette (`Ctrl+Shift+P`).

### 3. Build the Project

Press `Ctrl+Shift+B` or run:

```bash
just build
```

### 4. Select Build Target

In the CMake Tools status bar (bottom of VSCode), click the build target and select **wifi_scanner**. This ensures F7 builds the correct target.

### 5. Reload VSCode

After initial setup, reload the window (`Ctrl+Shift+P` → `Developer: Reload Window`) to ensure IntelliSense picks up all include paths.

## Debug Configurations

### Debug (F5)

The primary debugging workflow:

1. Builds the project
2. Starts OpenOCD (or reuses existing instance)
3. Flashes firmware to the device
4. Halts at `main()`

Use this when you've made code changes and want to test them.

### Attach

Connects to an already-running target:

1. Starts OpenOCD (or reuses existing instance)
2. Halts the target
3. Does **not** flash new firmware

Use this to inspect a running device without disrupting its state or when you want to debug without reflashing.

## Debug Controls

| Key | Action |
|-----|--------|
| `F5` | Start debugging / Continue |
| `F9` | Toggle breakpoint |
| `F10` | Step over |
| `F11` | Step into |
| `Shift+F11` | Step out |
| `Shift+F5` | Stop debugging |
| `Ctrl+Shift+F5` | Restart debugging |

## Debug Views

When debugging, the Run and Debug sidebar (`Ctrl+Shift+D`) provides several views:

### Variables

Shows local variables, function arguments, and global state. Expand structures to inspect individual fields.

### Watch

Add expressions to monitor. Right-click a variable and select "Add to Watch" or type expressions directly (e.g., `scan_results.count`, `*buffer`).

### Call Stack

Shows the current execution path. Click any frame to view its local variables and source location. With FreeRTOS, you may see multiple threads.

### Breakpoints

Lists all breakpoints. Enable/disable individual breakpoints, add conditions, or set hit counts.

### Registers

Cortex-Debug shows CPU registers (R0-R15, xPSR, etc.) and FPU registers. Expand register groups to see individual values.

### Peripherals

The SVD file (`rp2350.svd`) provides register-level views of all RP2350 peripherals. Expand peripherals like `GPIO`, `UART0`, `SPI0` to see and modify hardware registers directly.

## RTOS Views (FreeRTOS)

The [RTOS Views extension](https://marketplace.visualstudio.com/items?itemName=mcu-debug.rtos-views) provides visibility into FreeRTOS internals during debugging.

### What You Can See

When the debugger is paused, the xRTOS panel shows:

- **Tasks** - All FreeRTOS tasks with their current state (Running, Ready, Blocked, Suspended)
- **Task details** - Stack usage, priority, and runtime statistics (if enabled)
- **Queues** - Queue status and contents (experimental)
- **Semaphores** - Semaphore state (experimental)
- **Timers** - Software timer status (experimental)

### Enabling RTOS Views

RTOS views are automatically detected when the debugger stops. The extension searches for FreeRTOS global variables to identify the RTOS.

**Note:** RTOS detection only works when the debugger is paused—the extension cannot query state while the target is running.

### Enabling Runtime Statistics (Optional)

To see per-task CPU usage in the RTOS view, enable these in `src/FreeRTOSConfig.h`:

```c
#define configGENERATE_RUN_TIME_STATS           1
#define configUSE_TRACE_FACILITY                1
#define configUSE_STATS_FORMATTING_FUNCTIONS    1
```

This requires a high-frequency timer for accurate measurements and adds some overhead.

### Learn More

- [Cortex-Debug GitHub](https://github.com/Marus/cortex-debug) - Extension source and documentation
- [RTOS Views Extension](https://marketplace.visualstudio.com/items?itemName=mcu-debug.rtos-views) - Detailed RTOS visualization
- [MCU on Eclipse: FreeRTOS Debugging](https://mcuoneclipse.com/2021/06/02/visual-studio-code-for-c-c-with-arm-cortex-m-part-7-freertos/) - In-depth tutorial
- [FreeRTOS VSCode Development](https://www.freertos.org/Community/Blogs/2021/using-visual-studio-code-for-freertos-development) - Official FreeRTOS guide

## Serial Output While Debugging

The Pico outputs scan results via USB CDC serial. To view serial output during a debug session:

### Method 1: Integrated Terminal

1. Open terminal (`` Ctrl+` ``)
2. Run `just serial-read`
3. Start debugging with `F5`

The serial reader automatically resumes the target if the debugger left it halted.

### Method 2: Split View

1. Start serial reader in one terminal pane
2. Split the terminal (click ⊞ icon)
3. Use the second pane for other commands while monitoring serial output

### Method 3: VSCode Task

Run the `Serial Read` task via Command Palette (`Ctrl+Shift+P` → `Tasks: Run Task` → `Serial Read`).

**Tip:** Serial output requires the firmware to be running. If you don't see output after hitting a breakpoint, press `F5` to continue execution.

## Running Tests

### From Terminal

```bash
just test
```

### From VSCode

The C++ TestMate extension discovers tests automatically:

1. Open Testing sidebar (`Ctrl+Shift+T` or flask icon)
2. Tests appear under `test_unit` and `test_integration`
3. Click play to run, or debug icon to debug with breakpoints

Tests run on the host machine using the doctest framework, not on the Pico.

## IntelliSense Configuration

The project provides two IntelliSense configurations (select from the C++ status bar):

- **Pico 2 W (ARM)** - For firmware source files (`src/`)
- **Host Tests** - For test files (`test/`)

If IntelliSense shows false errors:

1. Ensure you've run `just build` (generates `compile_commands.json`)
2. Reload VSCode window
3. Check the correct configuration is selected for your file type

## Troubleshooting

### "Cannot find source file"

The ELF file references source paths from build time. Ensure you're debugging from the same directory where you built.

### Breakpoints not hitting

- Verify firmware was flashed (use **Debug** config, not **Attach**)
- Check optimization level—`-O2` or `-Os` may optimize away some code
- Ensure breakpoint is on executable code, not declarations

### "Target not halted" errors

The debug probe may have lost connection. Try:
1. Stop debugging (`Shift+F5`)
2. Run `./tools/pico.py openocd stop`
3. Restart debugging (`F5`)

### RTOS view shows no tasks

- RTOS detection only works when paused—set a breakpoint after `vTaskStartScheduler()`
- Ensure FreeRTOS symbols are not stripped from the ELF

### Variables show "optimized out"

Compiler optimization removed the variable. To inspect it:
- Add it to a `volatile` declaration
- Reduce optimization level (`-O0`) for debug builds
- Use the Watch panel with the raw memory address

### OpenOCD connection refused

Another process may be using the debug probe:

```bash
# Check if OpenOCD is running
ss -tlnp | grep 3333

# Stop any existing OpenOCD
./tools/pico.py openocd stop
pkill openocd  # if needed
```

## Advanced: GDB Commands

Access the GDB console via the Debug Console (`Ctrl+Shift+Y`) during a debug session. Prefix commands with `-exec`:

```
-exec info threads          # List all threads
-exec thread 2              # Switch to thread 2
-exec x/10x 0x20000000      # Examine memory
-exec set var x = 5         # Modify variable
-exec monitor reset halt    # OpenOCD: reset and halt
-exec monitor reg           # OpenOCD: show registers
```
