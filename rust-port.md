# Rust Port Plan: Embassy WiFi Scanner for Pico 2 W

This document provides a complete plan for porting the FreeRTOS-based WiFi scanner to Rust using Embassy, targeting the Raspberry Pi Pico 2 W (RP2350 + CYW43439).

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Mapping](#architecture-mapping)
3. [Project Structure](#project-structure)
4. [Dependencies](#dependencies)
5. [Configuration Files](#configuration-files)
6. [Source Code Implementation](#source-code-implementation)
7. [Multicore Design](#multicore-design)
8. [RTT Debug Logging](#rtt-debug-logging)
9. [Build System Updates](#build-system-updates)
10. [Testing Strategy](#testing-strategy)
11. [Implementation Steps](#implementation-steps)
12. [Verification Checklist](#verification-checklist)

---

## Executive Summary

### Goals
- Full feature parity with the C++/FreeRTOS implementation
- **Multicore execution**: Core 0 (CYW43 + USB), Core 1 (main loop)
- **USB Serial output**: Primary user-facing output, matching C++ behavior
- **RTT debug logging**: Additional debug output via hardware debugger
- Tickless idle / low-power wait using Embassy's WFI-based executor
- Retain existing tooling (Nix flake, justfile, Python tools)

### Key Technology Choices
| Component | C++/FreeRTOS | Rust/Embassy |
|-----------|--------------|--------------|
| Runtime | FreeRTOS tasks | Embassy async executor |
| Concurrency | Semaphores | async/await + channels |
| WiFi | Pico SDK cyw43_arch | `cyw43` + `cyw43-pio` crates |
| Timing | FreeRTOS timers | `embassy-time` Timer |
| Low Power | configUSE_TICKLESS_IDLE | Embassy executor WFI |
| Multicore | FreeRTOS SMP (unused) | `embassy_rp::multicore` |
| Primary Output | USB Serial (printf) | USB Serial (embassy-usb) |
| Debug Output | N/A | RTT + defmt (via debug probe) |

---

## Architecture Mapping

### Current C++ Architecture
```
┌─────────────────────────────────────────────────────┐
│                    FreeRTOS                         │
├─────────────────────┬───────────────────────────────┤
│   Main Task (Core 0)│   Scanner Task (Core 0)       │
│   - Print banner    │   - Wait on request_sem       │
│   - Init WiFi       │   - do_scan()                 │
│   - Loop:           │     - LED blink start         │
│     - request_scan()│     - cyw43_wifi_scan()       │
│     - print_results │     - Poll until complete     │
│     - vTaskDelay    │     - LED blink stop          │
│                     │   - Signal complete_sem       │
└─────────────────────┴───────────────────────────────┘
```

### New Rust Architecture (Multicore with Channels)
```
┌─────────────────────────────────────────────────────┐
│                  Embassy Runtime                    │
├─────────────────────┬───────────────────────────────┤
│ Core 0 Executor     │ Core 1 Executor               │
├─────────────────────┼───────────────────────────────┤
│ cyw43_driver_task   │ main_task                     │
│ - CYW43 event loop  │ - Print banner (USB Serial)   │
│                     │ - Loop:                       │
│ wifi_worker_task    │   - send WifiCmd::Scan        │
│ - Receive WifiCmd   │   - await ScanResult          │
│ - control.scan()    │   - print results (USB)       │
│ - LED blink during  │   - log to RTT (debug)        │
│ - Send ScanResult   │   - Timer::after(20s)         │
│                     │                               │
│ usb_task            │                               │
│ - USB CDC serial    │                               │
└─────────────────────┴───────────────────────────────┘

Communication: embassy_sync::channel::Channel<WifiCmd, ScanResult>
Output: USB Serial (user-facing) + RTT/defmt (debug probe)
```

---

## Project Structure

```
rpi-pico2w-freertos-hwdebug-1/
├── rust/                          # Rust project root
│   ├── Cargo.toml                 # Dependencies and features
│   ├── Cargo.lock                 # Locked dependencies
│   ├── build.rs                   # Linker script setup
│   ├── memory.x                   # RP2350 memory layout
│   ├── Embed.toml                 # probe-rs/cargo-embed RTT config
│   ├── .cargo/
│   │   └── config.toml            # Target, runner, and defmt config
│   ├── firmware/                  # CYW43 firmware blobs (download required)
│   │   ├── 43439A0.bin            # Main WiFi firmware (~230KB)
│   │   └── 43439A0_clm.bin        # Regulatory data (~5KB)
│   └── src/
│       ├── main.rs                # Entry point, Core 0 + Core 1 setup
│       ├── scan_types.rs          # APInfo, ScanResult, AuthMode, WifiCmd
│       └── fmt.rs                 # defmt timestamp configuration
├── src/                           # Existing C++ code (reference)
├── tools/                         # Existing Python tools
│   ├── flash.py                   # Update for Rust binary path
│   └── ...
├── flake.nix                      # Update with Rust toolchain
├── justfile                       # Add Rust build/run targets
└── rust-port.md                   # This plan document
```

### Key Files

| File | Purpose |
|------|---------|
| `main.rs` | Multicore setup, USB serial, CYW43 init, Core 0/1 tasks |
| `scan_types.rs` | Data structures matching C++ version |
| `fmt.rs` | defmt timestamp for RTT output |
| `Embed.toml` | RTT channel configuration for `cargo embed` |
| `.cargo/config.toml` | Build target, runner, DEFMT_LOG setting |

### Critical Pre-Implementation Step

**Before writing any code**, verify the actual API by checking the Embassy examples:

```bash
# Clone Embassy repo to check current API
git clone --depth 1 https://github.com/embassy-rs/embassy.git /tmp/embassy

# Check the wifi_scan example for current API
cat /tmp/embassy/examples/rp/src/bin/wifi_scan.rs

# Check Cargo.toml for current versions
cat /tmp/embassy/examples/rp/Cargo.toml
```

The code in this plan is based on Embassy documentation as of January 2026. APIs may have changed. Always verify against the actual examples before implementing.

---

## Dependencies

### Cargo.toml

```toml
[package]
name = "wifi-scanner"
version = "0.1.0"
edition = "2021"
license = "MIT OR Apache-2.0"

[dependencies]
# Embassy core (check https://crates.io/crates/embassy-executor for latest)
embassy-executor = { version = "0.7", features = ["arch-cortex-m", "executor-thread", "defmt", "integrated-timers"] }
embassy-time = { version = "0.4", features = ["defmt", "defmt-timestamp-uptime"] }
embassy-sync = { version = "0.6", features = ["defmt"] }
embassy-futures = "0.1"

# Embassy RP2350 HAL (check https://crates.io/crates/embassy-rp for latest)
# As of Jan 2026, use version 0.9.x or git dependency for RP2350 support
embassy-rp = { version = "0.9", features = [
    "defmt",
    "unstable-pac",
    "time-driver",
    "critical-section-impl",
    "rp235xb",              # Pico 2 W uses RP2350B variant
    "binary-info",
] }

# USB support for serial output
embassy-usb = { version = "0.4", features = ["defmt"] }
embassy-usb-logger = { version = "0.3" }

# CYW43 WiFi driver (check https://crates.io/crates/cyw43 for latest)
cyw43 = { version = "0.6", features = ["defmt", "firmware-logs"] }
cyw43-pio = { version = "0.9", features = ["defmt"] }

# Cortex-M support
cortex-m = { version = "0.7", features = ["inline-asm"] }
cortex-m-rt = "0.7"

# RTT debug logging (in addition to USB serial)
defmt = "1.0"
defmt-rtt = "1.0"
panic-probe = { version = "1.0", features = ["print-defmt"] }

# Formatting for USB serial output
core-fmt-macros = "0.1"   # Or use core::fmt directly
ufmt = "0.2"              # Lightweight formatting alternative

# Utilities
static_cell = "2"
portable-atomic = { version = "1", features = ["critical-section"] }
heapless = { version = "0.8", features = ["defmt-03"] }

[build-dependencies]
# None needed - linker scripts handled in build.rs

[profile.release]
debug = 2           # Keep debug info for probe-rs
lto = "thin"
opt-level = "s"

[profile.dev]
debug = 2
opt-level = 1       # Some optimization even in dev for code size
```

### Dependency Version Notes

**IMPORTANT**: Embassy releases frequently. Before implementing, check for the latest compatible versions:
- [embassy-rp on crates.io](https://crates.io/crates/embassy-rp)
- [cyw43 on crates.io](https://crates.io/crates/cyw43)
- [Embassy GitHub releases](https://github.com/embassy-rs/embassy/releases)

If crates.io versions are too old for RP2350, use git dependencies:
```toml
embassy-rp = { git = "https://github.com/embassy-rs/embassy", features = [...] }
cyw43 = { git = "https://github.com/embassy-rs/embassy", features = [...] }
cyw43-pio = { git = "https://github.com/embassy-rs/embassy", features = [...] }
```

Key feature requirements:
- `rp235xb` - Pico 2 W uses the RP2350B variant (not RP2350A)
- `critical-section-impl` - Required for multicore safety
- `time-driver` - Required for `embassy-time` functionality

---

## Configuration Files

### .cargo/config.toml

```toml
[build]
target = "thumbv8m.main-none-eabihf"

[target.thumbv8m.main-none-eabihf]
runner = "probe-rs run --chip RP2350"
rustflags = [
    "-C", "link-arg=--nmagic",
    "-C", "link-arg=-Tlink.x",
    "-C", "link-arg=-Tdefmt.x",
]

[env]
DEFMT_LOG = "debug"
```

### Embed.toml

```toml
[default.general]
chip = "RP2350"

[default.rtt]
enabled = true
up_mode = "NoBlockSkip"
channels = [
    { up = 0, name = "defmt", format = "Defmt" },
]

[default.flashing]
enabled = true

[default.reset]
enabled = true
halt_afterwards = false

[default.gdb]
enabled = false
```

### memory.x

```ld
MEMORY {
    BOOT2 : ORIGIN = 0x10000000, LENGTH = 0x100
    FLASH : ORIGIN = 0x10000100, LENGTH = 4096K - 0x100
    RAM   : ORIGIN = 0x20000000, LENGTH = 512K
    SRAM4 : ORIGIN = 0x20080000, LENGTH = 4K
    SRAM5 : ORIGIN = 0x20081000, LENGTH = 4K
}

/* Firmware storage in flash (after application) */
_cyw43_firmware_start = ORIGIN(FLASH) + 256K;
_cyw43_firmware_end = _cyw43_firmware_start + 256K;

SECTIONS {
    .start_block : {
        __start_block_addr = .;
        KEEP(*(.start_block));
    } > FLASH
}

INSERT BEFORE .text;

SECTIONS {
    .bi_entries : {
        __bi_entries_start = .;
        KEEP(*(.bi_entries));
        __bi_entries_end = .;
    } > FLASH
}

INSERT AFTER .text;

SECTIONS {
    .end_block : {
        __end_block_addr = .;
        KEEP(*(.end_block));
    } > FLASH
}

INSERT AFTER .uninit;

PROVIDE(start_to_end = __end_block_addr - __start_block_addr);
PROVIDE(end_to_start = __start_block_addr - __end_block_addr);
```

### build.rs

```rust
use std::env;
use std::fs::File;
use std::io::Write;
use std::path::PathBuf;

fn main() {
    let out = PathBuf::from(env::var_os("OUT_DIR").unwrap());

    // Put memory.x in the linker search path
    File::create(out.join("memory.x"))
        .unwrap()
        .write_all(include_bytes!("memory.x"))
        .unwrap();

    println!("cargo:rustc-link-search={}", out.display());
    println!("cargo:rerun-if-changed=memory.x");
    println!("cargo:rerun-if-changed=build.rs");
}
```

---

## Source Code Implementation

### src/main.rs (Multicore with USB Serial + RTT)

```rust
//! Pico 2 W WiFi Scanner - Embassy async implementation
//!
//! Multicore design:
//! - Core 0: CYW43 driver, WiFi worker, USB serial output
//! - Core 1: Main loop, scan requests, output formatting
//!
//! Output:
//! - USB Serial: Primary user-facing output (like C++ version)
//! - RTT/defmt: Additional debug logging via hardware debug probe

#![no_std]
#![no_main]

mod fmt;
mod scan_types;

use core::fmt::Write as FmtWrite;

use defmt::*;
use embassy_executor::{Executor, Spawner};
use embassy_rp::bind_interrupts;
use embassy_rp::gpio::{Level, Output};
use embassy_rp::multicore::{spawn_core1, Stack};
use embassy_rp::peripherals::{DMA_CH0, PIO0, USB};
use embassy_rp::pio::{InterruptHandler as PioInterruptHandler, Pio};
use embassy_rp::usb::{Driver, InterruptHandler as UsbInterruptHandler};
use embassy_sync::blocking_mutex::raw::CriticalSectionRawMutex;
use embassy_sync::channel::Channel;
use embassy_time::{Duration, Timer};
use embassy_usb::class::cdc_acm::{CdcAcmClass, State};
use embassy_usb::{Builder, Config};
use heapless::String;
use static_cell::StaticCell;
use {defmt_rtt as _, panic_probe as _};

use crate::scan_types::{APInfo, AuthMode, ScanResult, MAX_SCAN_RESULTS, SCAN_INTERVAL_SECS};

bind_interrupts!(struct Irqs {
    PIO0_IRQ_0 => PioInterruptHandler<PIO0>;
    USBCTRL_IRQ => UsbInterruptHandler<USB>;
});

/// Commands sent from Core 1 to Core 0
#[derive(Clone, Copy)]
pub enum WifiCmd {
    Scan,
}

/// Channel for WiFi commands (Core 1 -> Core 0)
static CMD_CHANNEL: Channel<CriticalSectionRawMutex, WifiCmd, 1> = Channel::new();

/// Channel for scan results (Core 0 -> Core 1)
static RESULT_CHANNEL: Channel<CriticalSectionRawMutex, ScanResult, 1> = Channel::new();

/// Channel for USB serial output (Core 1 -> Core 0)
/// Uses heapless::String to avoid heap allocation
static USB_TX_CHANNEL: Channel<CriticalSectionRawMutex, String<256>, 8> = Channel::new();

/// Stack for Core 1
static mut CORE1_STACK: Stack<8192> = Stack::new();

/// CYW43 firmware (included in binary)
static FW: &[u8] = include_bytes!("../firmware/43439A0.bin");
static CLM: &[u8] = include_bytes!("../firmware/43439A0_clm.bin");

/// Core 0 entry point - handles CYW43 and USB
#[embassy_executor::main]
async fn main(spawner: Spawner) {
    debug!("Core 0: Starting initialization...");

    let p = embassy_rp::init(Default::default());

    // =========================================================================
    // USB Serial Setup
    // =========================================================================
    let driver = Driver::new(p.USB, Irqs);

    let mut config = Config::new(0x2E8A, 0x000A); // Raspberry Pi vendor ID
    config.manufacturer = Some("Raspberry Pi");
    config.product = Some("Pico 2 W WiFi Scanner");
    config.serial_number = Some("RUST-001");
    config.max_power = 100;
    config.max_packet_size_0 = 64;

    // USB buffers
    static CONFIG_DESCRIPTOR: StaticCell<[u8; 256]> = StaticCell::new();
    static BOS_DESCRIPTOR: StaticCell<[u8; 256]> = StaticCell::new();
    static CONTROL_BUF: StaticCell<[u8; 64]> = StaticCell::new();
    static STATE: StaticCell<State> = StaticCell::new();

    let config_desc = CONFIG_DESCRIPTOR.init([0; 256]);
    let bos_desc = BOS_DESCRIPTOR.init([0; 256]);
    let control_buf = CONTROL_BUF.init([0; 64]);
    let state = STATE.init(State::new());

    let mut builder = Builder::new(
        driver,
        config,
        config_desc,
        bos_desc,
        &mut [], // No MSOS descriptors
        control_buf,
    );

    let class = CdcAcmClass::new(&mut builder, state, 64);
    let usb = builder.build();

    // Spawn USB tasks
    unwrap!(spawner.spawn(usb_task(usb)));
    unwrap!(spawner.spawn(usb_write_task(class)));

    debug!("Core 0: USB initialized");

    // =========================================================================
    // CYW43 WiFi Setup
    // =========================================================================
    let pwr = Output::new(p.PIN_23, Level::Low);
    let cs = Output::new(p.PIN_25, Level::High);
    let mut pio = Pio::new(p.PIO0, Irqs);
    let spi = cyw43_pio::PioSpi::new(
        &mut pio.common,
        pio.sm0,
        cyw43_pio::DEFAULT_CLOCK_DIVIDER,
        pio.irq0,
        cs,
        p.PIN_24,
        p.PIN_29,
        p.DMA_CH0,
    );

    static CYW43_STATE: StaticCell<cyw43::State> = StaticCell::new();
    let cyw43_state = CYW43_STATE.init(cyw43::State::new());
    let (_net_device, mut control, runner) = cyw43::new(cyw43_state, pwr, spi, FW).await;

    unwrap!(spawner.spawn(cyw43_driver_task(runner)));

    control.init(CLM).await;
    control.gpio_set(0, true).await; // LED on

    debug!("Core 0: CYW43 initialized");

    // =========================================================================
    // Start Core 1
    // =========================================================================
    debug!("Core 0: Starting Core 1...");
    spawn_core1(
        p.CORE1,
        unsafe { &mut *core::ptr::addr_of_mut!(CORE1_STACK) },
        || {
            static EXECUTOR1: StaticCell<Executor> = StaticCell::new();
            let executor = EXECUTOR1.init(Executor::new());
            executor.run(|spawner| {
                unwrap!(spawner.spawn(core1_main_task()));
            });
        },
    );

    debug!("Core 0: Entering WiFi command loop");

    // =========================================================================
    // WiFi Command Processor Loop (Core 0)
    // =========================================================================
    loop {
        let cmd = CMD_CHANNEL.receive().await;
        match cmd {
            WifiCmd::Scan => {
                debug!("Core 0: Processing scan request");
                let result = do_scan_with_blink(&mut control).await;
                RESULT_CHANNEL.send(result).await;
            }
        }
    }
}

/// Perform WiFi scan with LED blinking
async fn do_scan_with_blink(control: &mut cyw43::Control<'_>) -> ScanResult {
    let mut result = ScanResult::new();
    let mut led_state = true;
    let blink_interval = Duration::from_millis(50);

    let scan_opts = cyw43::ScanOptions::default();
    let mut scanner = control.scan(scan_opts).await;

    loop {
        // Toggle LED
        control.gpio_set(0, led_state).await;
        led_state = !led_state;

        // Check for scan results with timeout
        match embassy_time::with_timeout(blink_interval, scanner.next()).await {
            Ok(Some(bss)) => {
                if result.count < MAX_SCAN_RESULTS as u16
                   && !bss.ssid.is_empty()
                   && bss.ssid[0] != 0
                {
                    let mut ap = APInfo::new();
                    let ssid_len = bss.ssid.len().min(32);
                    ap.ssid[..ssid_len].copy_from_slice(&bss.ssid[..ssid_len]);
                    ap.ssid_len = ssid_len as u8;
                    ap.bssid.copy_from_slice(&bss.bssid);
                    ap.rssi = bss.rssi;
                    ap.channel = bss.channel as u8;
                    ap.auth = AuthMode::from_cyw43(bss.security);
                    result.networks[result.count as usize] = ap;
                    result.count += 1;
                }
            }
            Ok(None) => break, // Scan complete
            Err(_) => continue, // Timeout, continue blinking
        }
    }

    control.gpio_set(0, true).await; // LED solid on
    result.success = true;
    result
}

/// CYW43 driver background task (Core 0)
#[embassy_executor::task]
async fn cyw43_driver_task(
    runner: cyw43::Runner<'static, Output<'static>, cyw43_pio::PioSpi<'static, PIO0, 0, DMA_CH0>>,
) -> ! {
    runner.run().await
}

/// USB device task (Core 0)
#[embassy_executor::task]
async fn usb_task(mut usb: embassy_usb::UsbDevice<'static, Driver<'static, USB>>) -> ! {
    usb.run().await
}

/// USB serial write task - sends queued messages (Core 0)
#[embassy_executor::task]
async fn usb_write_task(mut class: CdcAcmClass<'static, Driver<'static, USB>>) {
    loop {
        class.wait_connection().await;
        debug!("USB serial connected");

        loop {
            let msg = USB_TX_CHANNEL.receive().await;

            // Write to USB, ignore errors (disconnection handled by wait_connection)
            if class.write_packet(msg.as_bytes()).await.is_err() {
                break;
            }
        }

        debug!("USB serial disconnected");
    }
}

/// Main task running on Core 1 - handles user interface
#[embassy_executor::task]
async fn core1_main_task() {
    // Wait a moment for USB to initialize
    Timer::after(Duration::from_millis(500)).await;

    // Print banner to USB serial
    usb_println("");
    usb_println("========================================");
    usb_println("  Pico 2 W WiFi Scanner");
    usb_println("  Embassy + CYW43 (Rust)");
    usb_println("========================================");
    usb_println("");

    // Also log to RTT for debugging
    info!("Core 1: Main task started");

    usb_println("Initializing WiFi...");
    Timer::after(Duration::from_millis(100)).await; // Let Core 0 init
    usb_println("WiFi initialized.");
    usb_println("");

    let mut msg: String<64> = String::new();
    let _ = core::write!(&mut msg, "Scanning every {} seconds...", SCAN_INTERVAL_SECS);
    usb_println(msg.as_str());
    usb_println("");

    loop {
        usb_println("--- Starting scan ---");
        debug!("Core 1: Requesting scan");

        // Request scan from Core 0
        CMD_CHANNEL.send(WifiCmd::Scan).await;

        // Wait for result
        let result = RESULT_CHANNEL.receive().await;
        debug!("Core 1: Received result, {} networks", result.count);

        if result.success {
            print_results_usb(&result);
        } else {
            let mut msg: String<64> = String::new();
            let _ = core::write!(&mut msg, "Scan failed (error: {})", result.error_code);
            usb_println(msg.as_str());
            error!("Scan failed: {}", result.error_code);
        }

        // Wait before next scan (Embassy uses WFI for low power)
        Timer::after_secs(SCAN_INTERVAL_SECS).await;
    }
}

/// Send a line to USB serial (queued, non-blocking)
fn usb_println(s: &str) {
    let mut msg: String<256> = String::new();
    let _ = msg.push_str(s);
    let _ = msg.push_str("\r\n");

    // Try to send, drop if channel is full (non-blocking)
    let _ = USB_TX_CHANNEL.try_send(msg);
}

/// Print scan results to USB serial
fn print_results_usb(result: &ScanResult) {
    usb_println("");
    usb_println("  SSID                              BSSID               CH     RSSI  AUTH");
    usb_println("  --------------------------------------------------------------------------------");

    for i in 0..result.count as usize {
        let ap = &result.networks[i];

        let mut line: String<256> = String::new();
        let _ = core::write!(
            &mut line,
            "  {:32}  {:02X}:{:02X}:{:02X}:{:02X}:{:02X}:{:02X}  ch{:2}  {:4}dBm  {}",
            ap.ssid_str(),
            ap.bssid[0], ap.bssid[1], ap.bssid[2],
            ap.bssid[3], ap.bssid[4], ap.bssid[5],
            ap.channel,
            ap.rssi,
            ap.auth.as_str()
        );
        usb_println(line.as_str());

        // Also log to RTT for debugging
        debug!("  {} ch{} {}dBm", ap.ssid_str(), ap.channel, ap.rssi);
    }

    usb_println("");
    let mut msg: String<64> = String::new();
    let _ = core::write!(&mut msg, "  Found {} networks", result.count);
    usb_println(msg.as_str());
    usb_println("");

    // Summary to RTT
    info!("Scan complete: {} networks found", result.count);
}
```

### Output Behavior

**USB Serial** (primary, user-facing):
- Matches the C++ version output format exactly
- Connect with `just console` or `picocom /dev/ttyACM0`
- Works independently of debug probe

**RTT/defmt** (debug, via hardware debugger):
- Additional debug logging
- View with `cargo embed` or `probe-rs attach`
- Uses `debug!()` for verbose info, `info!()` for summaries, `error!()` for failures

### Log Level Control

RTT log levels are set at build time:
```bash
DEFMT_LOG=debug cargo build --release  # Verbose
DEFMT_LOG=info cargo build --release   # Summary only
DEFMT_LOG=error cargo build --release  # Errors only
```

### src/scan_types.rs

```rust
//! Data types for WiFi scan results

use defmt::Format;
use heapless::String;

/// Maximum SSID length per 802.11 spec
pub const MAX_SSID_LEN: usize = 32;

/// BSSID (MAC address) length
pub const BSSID_LEN: usize = 6;

/// Maximum APs to store per scan
pub const MAX_SCAN_RESULTS: usize = 32;

/// Scan interval in seconds
pub const SCAN_INTERVAL_SECS: u64 = 20;

/// Marker type for scan requests
#[derive(Clone, Copy)]
pub struct ScanRequest;

/// Authentication mode of discovered AP
#[derive(Clone, Copy, Debug, Format, PartialEq, Eq, Default)]
#[repr(u8)]
pub enum AuthMode {
    Open = 0,
    Wep,
    WpaPsk,
    Wpa2Psk,
    WpaWpa2Psk,
    Wpa3Psk,
    #[default]
    Unknown,
}

impl AuthMode {
    /// Convert CYW43 security flags to AuthMode
    pub fn from_cyw43(security: u32) -> Self {
        // CYW43 security flags
        const OPEN: u32 = 0;
        const WEP: u32 = 1 << 0;
        const WPA: u32 = 1 << 1;
        const WPA2: u32 = 1 << 2;
        const WPA3: u32 = 1 << 3;

        if security == OPEN {
            Self::Open
        } else if security & WEP != 0 {
            Self::Wep
        } else if security & WPA3 != 0 {
            Self::Wpa3Psk
        } else if (security & WPA2 != 0) && (security & WPA != 0) {
            Self::WpaWpa2Psk
        } else if security & WPA2 != 0 {
            Self::Wpa2Psk
        } else if security & WPA != 0 {
            Self::WpaPsk
        } else {
            Self::Unknown
        }
    }

    /// Get display string for auth mode
    pub const fn as_str(&self) -> &'static str {
        match self {
            Self::Open => "OPEN",
            Self::Wep => "WEP",
            Self::WpaPsk => "WPA",
            Self::Wpa2Psk => "WPA2",
            Self::WpaWpa2Psk => "WPA/WPA2",
            Self::Wpa3Psk => "WPA3",
            Self::Unknown => "???",
        }
    }
}

/// Data for a single AP scan result
#[derive(Clone, Copy, Default)]
pub struct APInfo {
    /// SSID bytes (not null-terminated)
    pub ssid: [u8; MAX_SSID_LEN],
    /// Actual SSID length
    pub ssid_len: u8,
    /// MAC address
    pub bssid: [u8; BSSID_LEN],
    /// Signal strength in dBm
    pub rssi: i16,
    /// WiFi channel
    pub channel: u8,
    /// Authentication mode
    pub auth: AuthMode,
}

impl APInfo {
    pub const fn new() -> Self {
        Self {
            ssid: [0; MAX_SSID_LEN],
            ssid_len: 0,
            bssid: [0; BSSID_LEN],
            rssi: 0,
            channel: 0,
            auth: AuthMode::Unknown,
        }
    }

    /// Get SSID as a string slice
    pub fn ssid_str(&self) -> &str {
        core::str::from_utf8(&self.ssid[..self.ssid_len as usize])
            .unwrap_or("<invalid>")
    }
}

/// Result of a WiFi scan operation
#[derive(Clone, Copy)]
pub struct ScanResult {
    /// true if scan completed without error
    pub success: bool,
    /// Error code if !success
    pub error_code: i32,
    /// Number of APs found
    pub count: u16,
    /// Discovered networks
    pub networks: [APInfo; MAX_SCAN_RESULTS],
}

impl ScanResult {
    pub const fn new() -> Self {
        Self {
            success: false,
            error_code: 0,
            count: 0,
            networks: [APInfo::new(); MAX_SCAN_RESULTS],
        }
    }

    pub fn reset(&mut self) {
        self.success = false;
        self.error_code = 0;
        self.count = 0;
    }

    pub fn is_full(&self) -> bool {
        self.count as usize >= MAX_SCAN_RESULTS
    }
}

impl Default for ScanResult {
    fn default() -> Self {
        Self::new()
    }
}
```

### src/led.rs

```rust
//! LED control utilities
//!
//! On Pico W/Pico 2 W, the LED is controlled through the CYW43 chip's GPIO,
//! not a direct RP2350 GPIO pin.

// LED control is integrated into core1.rs via the cyw43 Control struct
// This module can contain LED-related constants and helpers if needed

/// LED GPIO pin on CYW43 (internal, always 0)
pub const LED_PIN: u8 = 0;

/// Default blink interval in milliseconds
pub const DEFAULT_BLINK_MS: u64 = 50;
```

### src/fmt.rs

```rust
//! defmt formatting configuration

use defmt_rtt as _;
use panic_probe as _;

/// Configure defmt timestamp (optional - embassy-time provides this)
#[defmt::timestamp]
fn timestamp() -> u64 {
    // embassy-time provides timestamps when defmt-timestamp-uptime feature is enabled
    embassy_time::Instant::now().as_micros()
}
```

### src/wifi.rs

```rust
//! WiFi-related utilities and constants

/// Default scan timeout in milliseconds
pub const SCAN_TIMEOUT_MS: u64 = 30_000;

/// CYW43 power management mode for scanning
pub use cyw43::PowerManagementMode;

/// WiFi initialization helper (if needed for more complex setups)
pub struct WifiConfig {
    pub power_mode: PowerManagementMode,
}

impl Default for WifiConfig {
    fn default() -> Self {
        Self {
            power_mode: PowerManagementMode::PowerSave,
        }
    }
}
```

---

## Multicore Design

### Architecture Overview

The design uses true multicore execution with channel-based communication:

| Core | Tasks | Rationale |
|------|-------|-----------|
| Core 0 | cyw43_driver_task, wifi_worker_task, usb_task | Hardware drivers + WiFi operations |
| Core 1 | main_task | User interface, scan requests, output formatting |

**Key Constraint**: The `cyw43::Control` struct requires `&mut self` for all operations. All CYW43 operations (scanning, LED control) must happen on Core 0.

### Communication Pattern

```
Core 1                          Core 0
───────                         ───────
main_task                       wifi_worker_task
    │                               │
    ├── send(WifiCmd::Scan) ───────▶│
    │                               ├── LED blink start
    │   (waiting on channel)        ├── control.scan().await
    │                               ├── collect results
    │                               ├── LED solid on
    │◀────── send(ScanResult) ──────┤
    │                               │
    ├── format output               │
    ├── write to USB_TX_CHANNEL ───▶│ usb_task
    │                               │   └── USB CDC write
    ├── defmt::info!() ─────────────┼──▶ RTT (debug probe)
    └── Timer::after(20s).await     │
```

### Output Channels

1. **USB Serial (Primary)** - User-facing output via USB CDC, matches C++ behavior
2. **RTT/defmt (Debug)** - Additional debug logging via hardware debug probe

### Channel Definitions

```rust
/// Commands from Core 1 to Core 0
enum WifiCmd {
    Scan,
}

/// Channels for inter-core communication
static CMD_CHANNEL: Channel<CriticalSectionRawMutex, WifiCmd, 1>;
static RESULT_CHANNEL: Channel<CriticalSectionRawMutex, ScanResult, 1>;

/// Channel for USB serial output (formatted strings)
static USB_TX_CHANNEL: Channel<CriticalSectionRawMutex, heapless::String<256>, 4>;
```

### Critical Section Safety
- Enable `critical-section-impl` feature in `embassy-rp`
- Use `CriticalSectionRawMutex` for all cross-core channels
- All shared state goes through Embassy sync primitives
- The `Control` struct stays on Core 0 only

---

## Dual Output: USB Serial + RTT

### Output Strategy

| Channel | Purpose | When to Use |
|---------|---------|-------------|
| USB Serial | Primary user output | Normal operation, matches C++ behavior |
| RTT/defmt | Debug logging | Development, troubleshooting via debug probe |

### USB Serial (Primary)

User-facing output via USB CDC ACM. Matches the C++ version exactly:
- Connect via: `just console` or `picocom /dev/ttyACM0 -b 115200`
- Works without debug probe connected
- Formatted output with SSID, BSSID, channel, RSSI, auth mode

### RTT Debug Logging (Secondary)

Additional debug output via hardware debug probe:

**Features Enabled**:
- `defmt` - Efficient binary logging framework
- `defmt-rtt` - RTT transport layer
- `panic-probe` - Panic handler outputs via defmt

**Log Levels** (set at build time):
```bash
DEFMT_LOG=trace cargo build --release  # Everything
DEFMT_LOG=debug cargo build --release  # Debug + Info + Warn + Error
DEFMT_LOG=info cargo build --release   # Info + Warn + Error
DEFMT_LOG=warn cargo build --release   # Warn + Error only
DEFMT_LOG=error cargo build --release  # Errors only
```

**Viewing RTT Output**:
```bash
# Flash and view RTT (recommended for development)
cargo embed --release

# Run and view RTT
probe-rs run --chip RP2350 target/thumbv8m.main-none-eabihf/release/wifi-scanner

# Attach to already-running firmware
probe-rs attach --chip RP2350 target/thumbv8m.main-none-eabihf/release/wifi-scanner
```

### Usage in Code

```rust
// USB Serial (user output) - goes to USB_TX_CHANNEL
usb_println("Found 5 networks");

// RTT/defmt (debug output) - goes to debug probe
debug!("Processing AP: {}", ssid);  // Verbose, development only
info!("Scan complete: {} networks", count);  // Summary
error!("WiFi init failed: {}", err);  // Errors
```

### Simultaneous Viewing

You can view both outputs simultaneously:
```bash
# Terminal 1: USB Serial
just console

# Terminal 2: RTT (requires debug probe)
probe-rs attach --chip RP2350 target/thumbv8m.main-none-eabihf/release/wifi-scanner
```

---

## Build System Updates

### flake.nix Updates

```nix
{
  description = "RP2350 WiFi Scanner - Embassy (Rust)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    rust-overlay.url = "github:oxalica/rust-overlay";
  };

  outputs = { self, nixpkgs, flake-utils, rust-overlay }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        overlays = [ (import rust-overlay) ];
        pkgs = import nixpkgs { inherit system overlays; };

        rustToolchain = pkgs.rust-bin.stable.latest.default.override {
          extensions = [ "rust-src" "rust-analyzer" "llvm-tools-preview" ];
          targets = [
            "thumbv8m.main-none-eabihf"  # ARM Cortex-M33
            "riscv32imac-unknown-none-elf"  # RISC-V (optional)
          ];
        };
      in {
        devShells.default = pkgs.mkShell {
          nativeBuildInputs = with pkgs; [
            # Rust toolchain
            rustToolchain

            # Embedded tools
            probe-rs-tools
            flip-link
            cargo-binutils

            # Existing tools (retain for C++ reference)
            cmake
            ninja
            python3
            python3Packages.pyserial

            # OpenOCD (for non-probe-rs debugging)
            openocd

            # Debug/console tools
            picocom
            gdb

            # Build essentials
            just
            git
          ];

          buildInputs = with pkgs; [
            libusb1
            hidapi
          ];

          shellHook = ''
            export PATH="$PWD/.local/bin:$PATH"

            # Rust project
            export DEFMT_LOG=debug

            # Existing C++ paths (if still used)
            export PICO_SDK_PATH="$PWD/deps/pico-sdk"
            export FREERTOS_KERNEL_PATH="$PWD/deps/FreeRTOS-Kernel"

            echo "Rust WiFi Scanner Development Environment"
            echo "  cargo build --release   # Build"
            echo "  cargo embed --release   # Flash + RTT"
            echo "  just rust-run           # Build + flash"
          '';
        };
      }
    );
}
```

### justfile Additions

```makefile
# Rust/Embassy targets
# =============================================================================

# Build Rust application
rust-build:
    cd rust && cargo build --release

# Flash Rust application via probe-rs
rust-flash:
    cd rust && cargo flash --release --chip RP2350

# Build, flash, and open RTT console (for debugging)
rust-run:
    cd rust && cargo embed --release

# Flash only, then open USB serial console (normal usage)
rust-run-serial: rust-flash
    @echo "Waiting for USB enumeration..."
    sleep 2
    just console

# View RTT debug output (attach to running firmware)
rust-rtt:
    cd rust && probe-rs attach --chip RP2350 target/thumbv8m.main-none-eabihf/release/wifi-scanner

# Build with verbose debug logging
rust-debug:
    cd rust && DEFMT_LOG=debug cargo build --release

# Build with trace-level logging (very verbose)
rust-trace:
    cd rust && DEFMT_LOG=trace cargo build --release

# Check Rust code (fast compile check)
rust-check:
    cd rust && cargo check

# Run clippy lints
rust-lint:
    cd rust && cargo clippy -- -D warnings

# Format Rust code
rust-fmt:
    cd rust && cargo fmt

# Run Rust tests (host-based unit tests)
rust-test:
    cd rust && cargo test --lib --target x86_64-unknown-linux-gnu

# Clean Rust build artifacts
rust-clean:
    cd rust && cargo clean

# Full Rust check (format + lint + build)
rust-all: rust-fmt rust-lint rust-build

# Show Rust binary size
rust-size:
    cd rust && cargo size --release -- -A
```

### tools/flash.py Update

```python
# Add at the top of get_firmware_path()
def get_firmware_path() -> Path:
    """Get the path to the firmware binary."""
    project_dir = get_project_dir()

    # Check for Rust binary first
    rust_elf = project_dir / "rust" / "target" / "thumbv8m.main-none-eabihf" / "release" / "wifi-scanner"
    if rust_elf.exists():
        return rust_elf

    # Fall back to C++ binary
    cpp_elf = project_dir / "build" / "src" / "wifi_scanner.elf"
    if cpp_elf.exists():
        return cpp_elf

    raise FileNotFoundError("No firmware binary found. Run 'just rust-build' or 'just build'")
```

---

## Testing Strategy

### Unit Tests (Host-based)

Create `rust/tests/scan_types_test.rs`:

```rust
//! Unit tests for scan types (run on host)

use wifi_scanner::scan_types::*;

#[test]
fn test_auth_mode_from_cyw43_open() {
    assert_eq!(AuthMode::from_cyw43(0), AuthMode::Open);
}

#[test]
fn test_auth_mode_from_cyw43_wep() {
    assert_eq!(AuthMode::from_cyw43(1), AuthMode::Wep);
}

#[test]
fn test_auth_mode_from_cyw43_wpa2() {
    assert_eq!(AuthMode::from_cyw43(4), AuthMode::Wpa2Psk);
}

#[test]
fn test_auth_mode_from_cyw43_wpa_wpa2() {
    assert_eq!(AuthMode::from_cyw43(6), AuthMode::WpaWpa2Psk);
}

#[test]
fn test_scan_result_default() {
    let result = ScanResult::new();
    assert!(!result.success);
    assert_eq!(result.count, 0);
    assert!(!result.is_full());
}

#[test]
fn test_ap_info_ssid_str() {
    let mut ap = APInfo::new();
    ap.ssid[..4].copy_from_slice(b"Test");
    ap.ssid_len = 4;
    assert_eq!(ap.ssid_str(), "Test");
}
```

### Integration Tests (On-device)

Integration testing requires the actual hardware. Use RTT output to verify:

1. WiFi initializes successfully
2. Scan returns results
3. LED blinks during scan
4. Results contain expected fields

```rust
// In main.rs, add test-only assertions
#[cfg(feature = "integration-test")]
fn validate_result(result: &ScanResult) {
    if result.success {
        // Should find at least one network (unless in RF-shielded room)
        defmt::assert!(result.count > 0, "No networks found");

        for i in 0..result.count as usize {
            let ap = &result.networks[i];
            // SSID should not be empty
            defmt::assert!(ap.ssid_len > 0, "Empty SSID");
            // RSSI should be negative
            defmt::assert!(ap.rssi < 0, "Invalid RSSI");
            // Channel should be valid (1-14 for 2.4GHz)
            defmt::assert!(ap.channel >= 1 && ap.channel <= 14, "Invalid channel");
        }
    }
}
```

---

## Implementation Steps

### Phase 1: Project Setup (Estimated: 1-2 hours)

1. [ ] Create `rust/` directory structure
2. [ ] Copy CYW43 firmware files to `rust/firmware/`
   - Download from: https://github.com/embassy-rs/embassy/tree/main/cyw43-firmware
   - Files: `43439A0.bin`, `43439A0_clm.bin`
3. [ ] Create `Cargo.toml` with dependencies
4. [ ] Create `.cargo/config.toml`
5. [ ] Create `Embed.toml`
6. [ ] Create `memory.x` and `build.rs`
7. [ ] Update `flake.nix` with Rust tooling
8. [ ] Update `justfile` with Rust targets

### Phase 2: Basic Bringup (Estimated: 2-3 hours)

1. [ ] Implement minimal `main.rs` with Embassy init
2. [ ] Verify RTT output works (`info!("Hello")`)
3. [ ] Add USB CDC serial and verify output (`usb_println("Hello")`)
4. [ ] Initialize CYW43 and control LED
5. [ ] Flash and verify LED blinks

### Phase 3: WiFi Scanning (Estimated: 2-3 hours)

1. [ ] Implement `scan_types.rs`
2. [ ] Implement single-core WiFi scanning
3. [ ] Verify scan results appear in RTT output
4. [ ] Match output format to C++ version

### Phase 4: Multicore (Estimated: 2-3 hours)

1. [ ] Implement `core1.rs` with Core 1 executor
2. [ ] Move scanner_task to Core 1
3. [ ] Implement channel-based communication
4. [ ] Verify both cores operational

### Phase 5: LED Blinking During Scan (Estimated: 1-2 hours)

1. [ ] Implement `led_blink_task`
2. [ ] Add Signal-based start/stop control
3. [ ] Verify LED blinks during scan, solid otherwise

### Phase 6: Polish and Testing (Estimated: 2-3 hours)

1. [ ] Add host-based unit tests
2. [ ] Run clippy and fix warnings
3. [ ] Verify all features match C++ version
4. [ ] Update README with Rust build instructions

---

## Verification Checklist

### Functional Requirements

- [ ] Banner prints on startup via USB serial
- [ ] WiFi initializes successfully
- [ ] Scan executes every 20 seconds
- [ ] Scan results show SSID, BSSID, channel, RSSI, auth mode on USB serial
- [ ] USB serial output format matches C++ version
- [ ] LED solid ON when idle
- [ ] LED blinks rapidly (50ms) during active scan
- [ ] LED returns to solid ON after scan
- [ ] Application runs without USB serial connected (output buffered/dropped)
- [ ] No crashes or panics during extended operation (1+ hour)

### Technical Requirements

- [ ] Multicore: WiFi worker runs on Core 0
- [ ] Multicore: Main task runs on Core 1
- [ ] USB Serial: CDC ACM device enumerates correctly
- [ ] USB Serial: Output visible via `just console`
- [ ] RTT: Debug output visible via `cargo embed`
- [ ] RTT: Log level respects DEFMT_LOG setting
- [ ] Low Power: CPU uses WFI during Timer::after() waits
- [ ] Release build fits in flash (<512KB excluding firmware)
- [ ] probe-rs can flash via debug probe

### Code Quality

- [ ] `cargo clippy` passes with no warnings
- [ ] `cargo fmt --check` passes
- [ ] Unit tests pass on host
- [ ] No `unsafe` blocks except where required (multicore stack)
- [ ] All public items documented

---

## Appendix: CYW43 Firmware

The CYW43439 chip requires binary firmware blobs. These are licensed separately.

### Download
```bash
mkdir -p rust/firmware
cd rust/firmware
curl -LO https://github.com/embassy-rs/embassy/raw/main/cyw43-firmware/43439A0.bin
curl -LO https://github.com/embassy-rs/embassy/raw/main/cyw43-firmware/43439A0_clm.bin
```

### Size
- `43439A0.bin`: ~230KB (main firmware)
- `43439A0_clm.bin`: ~5KB (regulatory data)

### License
These firmware files are subject to the Cypress/Infineon license. See the Embassy repository for details.

---

## Appendix: Troubleshooting

### probe-rs doesn't detect the device
```bash
# Check USB permissions
lsusb | grep -i "debug probe"

# On Linux, add udev rules
sudo curl -o /etc/udev/rules.d/69-probe-rs.rules \
  https://probe.rs/files/69-probe-rs.rules
sudo udevadm control --reload
sudo udevadm trigger
```

### RTT output is garbled
- Ensure DEFMT_LOG is set at build time, not runtime
- Rebuild with `cargo build --release` after changing log level

### Scan returns no networks
- Check WiFi is enabled on test networks (not 5GHz only)
- CYW43439 only supports 2.4GHz
- Try scanning in location with known networks

### Multicore crashes
- Increase CORE1_STACK size (default 8192)
- Ensure `critical-section-impl` feature is enabled
- Check for shared mutable state without proper synchronization

---

## References

- [Embassy Documentation](https://embassy.dev/book/)
- [embassy-rp HAL](https://docs.embassy.dev/embassy-rp/git/rp235x/)
- [cyw43 Driver](https://docs.embassy.dev/cyw43/git/default/)
- [defmt Logging](https://defmt.ferrous-systems.com/)
- [probe-rs](https://probe.rs/)
- [pico-pico Book](https://pico.implrust.com/)
- [RP2350 Datasheet](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf)
