# Nix Development Environment

This project uses [Nix](https://nixos.org/) with flakes to provide a reproducible development environment across different machines.

## Why Nix?

- **Reproducibility**: Every developer gets identical toolchain versions
- **Isolation**: Project dependencies don't conflict with system packages
- **Declarative**: All dependencies defined in `flake.nix`
- **Cross-platform**: Works on Linux and macOS (x86_64 and aarch64)

## Requirements

- Nix with flakes enabled
- [direnv](https://direnv.net/) (recommended)

### Installing Nix

```bash
# Linux/macOS (multi-user installation)
sh <(curl -L https://nixos.org/nix/install) --daemon

# Enable flakes (add to ~/.config/nix/nix.conf)
experimental-features = nix-command flakes
```

### Installing direnv

```bash
# With Nix
nix profile install nixpkgs#direnv

# Or via system package manager
# Debian/Ubuntu: sudo apt install direnv
# macOS: brew install direnv

# Add to shell (bash)
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc

# Add to shell (zsh)
echo 'eval "$(direnv hook zsh)"' >> ~/.zshrc
```

## Usage

### With direnv (Recommended)

```bash
cd rpi-pico2w-freertos-hwdebug-1
direnv allow
# Environment loads automatically when entering directory
```

### Without direnv

```bash
cd rpi-pico2w-freertos-hwdebug-1
nix develop
# Or: nix develop .#default
```

## What's Included

### Build Tools

| Package | Version | Purpose |
|---------|---------|---------|
| cmake | 3.x | Build system generator |
| ninja | 1.x | Fast build executor |
| gcc-arm-embedded | 14.3 | ARM Cortex-M cross-compiler (includes GDB) |

### SDK Setup

| Package | Purpose |
|---------|---------|
| python3 | Setup scripts |
| pyserial | Serial communication |
| git | Clone SDK and FreeRTOS |

### OpenOCD Build Dependencies

OpenOCD is built from source for RP2350 support. These packages are required:

| Package | Purpose |
|---------|---------|
| autoconf, automake, libtool | GNU build system |
| pkg-config | Library detection |
| jimtcl | TCL interpreter |
| capstone | Disassembly engine |
| texinfo | Documentation |
| libusb1, hidapi, libftdi1 | USB communication |

### Development Tools

| Package | Purpose |
|---------|---------|
| gdb | Debug host tests |
| cppcheck | Static analysis |
| clang-tools | clang-tidy linting |
| just | Command runner |

## Environment Variables

The shell hook sets these automatically:

```bash
PATH=".local/bin:$PATH"           # Local OpenOCD
PICO_SDK_PATH="deps/pico-sdk"     # Pico SDK location
FREERTOS_KERNEL_PATH="deps/FreeRTOS-Kernel"
PICO_BOARD="pico2_w"              # Target board
```

## Customization

### Pinned Versions

The `flake.nix` pins nixpkgs to a specific commit for reproducibility:

```nix
nixpkgs.url = "github:NixOS/nixpkgs/5912c1772a44e31bf1c63c0390b90501e5026886";
```

To update to latest nixpkgs:

```bash
nix flake update
```

### Adding Packages

Edit `flake.nix` to add packages:

```nix
nativeBuildInputs = with pkgs; [
  # existing packages...
  your-new-package
];
```

Then reload the environment:

```bash
direnv reload
# Or exit and re-enter: nix develop
```

## Portability

### Supported Platforms

The flake uses `eachDefaultSystem` which includes:

- `x86_64-linux`
- `aarch64-linux`
- `x86_64-darwin` (macOS Intel)
- `aarch64-darwin` (macOS Apple Silicon)

### Known Limitations

- **Windows**: Use WSL2 with a Linux distribution
- **macOS USB**: May need additional permissions for debug probe access
- **ARM Linux**: Works on Raspberry Pi 4/5 with NixOS or Nix

### Without Nix

If you can't use Nix, install these manually:

1. **ARM toolchain**: `gcc-arm-none-eabi` (v12+ recommended)
2. **Build tools**: cmake, ninja, python3, pip (pyserial)
3. **OpenOCD**: Build from source or use v0.12+ with RP2350 support
4. **Development**: just, git, gdb

Set environment variables manually:

```bash
export PICO_SDK_PATH=/path/to/pico-sdk
export FREERTOS_KERNEL_PATH=/path/to/FreeRTOS-Kernel
export PICO_BOARD=pico2_w
```

## Troubleshooting

### "direnv: error .envrc is blocked"

Run `direnv allow` to trust the project's `.envrc`.

### Slow first load

The first `nix develop` or `direnv allow` downloads and builds packages. Subsequent loads use cached packages.

### Checking disk usage

To see how much disk space the Nix environment uses:

```bash
du -sh $(nix flake metadata github:NixOS/nixpkgs --json | jq -r '.path')
```

### "experimental feature 'flakes' is disabled"

Add to `~/.config/nix/nix.conf`:

```
experimental-features = nix-command flakes
```

Then restart the Nix daemon:

```bash
sudo systemctl restart nix-daemon
```

### Debug probe permissions (Linux)

Create udev rules for the debug probe:

```bash
# /etc/udev/rules.d/99-pico.rules
SUBSYSTEM=="usb", ATTR{idVendor}=="2e8a", MODE="0666"
```

Then reload:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```
