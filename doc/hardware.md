# RP2350 Hardware Overview

This document summarizes the RP2350 hardware capabilities and how this project uses them.

## Processor Cores

The RP2350 is a dual-architecture microcontroller with **four CPU cores total**, though only two can be active at any time:

| Core Type | Architecture | Clock | FPU | Notes |
|-----------|--------------|-------|-----|-------|
| 2x ARM Cortex-M33 | ARMv8-M | 150 MHz | Yes (SP + simplified DP) | DSP instructions, TrustZone capable |
| 2x Hazard3 RISC-V | RV32IMAC | 150 MHz | No (soft-float only) | Open-source core by Raspberry Pi |

At boot, the RP2350 can enable:
- Two Cortex-M33 cores (ARM mode)
- Two Hazard3 cores (RISC-V mode)
- One of each (mixed mode)

**This project uses ARM mode** with the `pico_arm_cortex_m33_gcc.cmake` toolchain.

### Why ARM for This Project

The Cortex-M33 cores offer:
- **Hardware floating-point**: Single-precision FPU plus simplified double-precision (add, subtract, multiply, divide, square root)
- **DSP instructions**: Useful for signal processing
- **Better performance**: 4.09 vs 3.81 CoreMark/MHz compared to Hazard3
- **Mature tooling**: GCC, GDB, and debugger support is well-established

The Hazard3 RISC-V cores are suitable for:
- Projects prioritizing open-source ISA
- Integer-only workloads
- Educational/experimental RISC-V development

### Current Core Usage

This project runs **single-core on Core 0 only**:

```c
// src/FreeRTOSConfig.h
#define configNUMBER_OF_CORES  1
#define configTICK_CORE        0
```

Core 1 remains idle. FreeRTOS SMP mode (`configNUMBER_OF_CORES = 2`) could enable dual-core execution, but adds complexity for inter-core synchronization.

## Memory

| Type | Size | Notes |
|------|------|-------|
| SRAM | 520 KB | Includes 8 KB of ECC-protected memory |
| Flash | 4 MB | External QSPI (on Pico 2 W) |
| ROM | 32 KB | Bootloader and utility functions |

## Programmable I/O (PIO)

The RP2350 has **3 PIO blocks** (up from 2 on RP2040), each containing:
- 4 state machines
- 32 instruction slots
- 8 IRQ flags

**Total: 12 state machines** for implementing custom protocols in hardware.

### PIO Capabilities

- Executes custom digital protocols with cycle-accurate timing
- 9 instructions: JMP, WAIT, IN, OUT, PUSH, PULL, MOV, IRQ, SET
- Each instruction takes exactly 1 clock cycle
- DMA integration for zero-CPU-overhead data transfer
- New in RP2350: FIFOs usable as random-access memory, cross-PIO interrupts

### PIO Use Cases

This project does not currently use PIO, but it would be well-suited for:

| Use Case | Description |
|----------|-------------|
| **WS2812/NeoPixel LEDs** | RGB status indicators instead of single LED blink; ~10 lines of PIO assembly for the 800 kHz protocol |
| **Display output** | SPI display for showing scan results, or VGA output via PIO-generated sync signals |
| **Quadrature encoders** | Hardware edge detection without missing pulses |
| **Custom protocols** | SDIO slave, MDIO, proprietary sensor interfaces |
| **High-speed I/O** | Demonstrated 900 Mb/s sensor data transfer without CPU load |

### Getting Started with PIO

The SDK includes a PIO assembler. Create a `.pio` file and add to CMakeLists.txt:

```cmake
pico_generate_pio_header(your_target ${CMAKE_CURRENT_LIST_DIR}/your_program.pio)
```

See [raspberrypi/pico-examples/pio/](https://github.com/raspberrypi/pico-examples/tree/master/pio) for examples including WS2812 and UART implementations.

## Wireless (Pico 2 W)

The Pico 2 W includes an Infineon CYW43439:
- **WiFi**: 802.11n (2.4 GHz)
- **Bluetooth**: 5.2 (BLE + Classic)

This project uses WiFi for scanning; Bluetooth is available but unused.

## Other Peripherals

| Peripheral | Count | Notes |
|------------|-------|-------|
| GPIO | 30 | 26 user-accessible on Pico 2 W |
| ADC | 4 channels | 12-bit, 500 ksps |
| UART | 2 | |
| SPI | 2 | |
| I2C | 2 | |
| PWM | 12 channels | 8 slices, 2 channels each |
| USB | 1 | 1.1 Host/Device |
| Timer | 1 | 64-bit with 4 alarms |

## Power Consumption

The RP2350 on 40nm process uses less power than the RP2040:
- **Active**: ~80 mW (vs ~100 mW on RP2040)
- **Sleep**: ~27 uA
- **Dormant**: Lower still with RTC wakeup

This project uses FreeRTOS tickless idle (`configUSE_TICKLESS_IDLE = 1`) to reduce power during idle periods.

## References

- [RP2350 Datasheet](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf)
- [Pico 2 W Datasheet](https://datasheets.raspberrypi.com/picow/pico-2-w-datasheet.pdf)
- [Hazard3 GitHub](https://github.com/Wren6991/Hazard3)
- [Pico SDK PIO Examples](https://github.com/raspberrypi/pico-examples/tree/master/pio)
