# Dependency Version Management

This project pins specific versions of external dependencies to ensure reproducible builds. All version specifications are centralized in the `justfile` and can be overridden when upgrading.

## Pinned Dependencies

| Dependency | Variable | Current Version | Source |
|------------|----------|-----------------|--------|
| Pico SDK | `pico_sdk_version` | 2.2.0 | [Tags](https://github.com/raspberrypi/pico-sdk/tags) |
| FreeRTOS Kernel | `freertos_kernel_version` | 4f7299d... | [Commits](https://github.com/raspberrypi/FreeRTOS-Kernel/commits/main) |
| OpenOCD | `openocd_version` | v0.9.0 | [Tags](https://github.com/openocd-org/openocd/tags) |
| picotool | `picotool_version` | 2.2.0 | [Tags](https://github.com/raspberrypi/picotool/tags) |

### Version Formats

- **Pico SDK, picotool**: Use release tags (e.g., `2.2.0`, `2.3.0`)
- **OpenOCD**: Use release tags with `v` prefix (e.g., `v0.9.0`, `v0.10.0`)
- **FreeRTOS Kernel**: The Raspberry Pi fork has no tags; use full commit hashes

## Upgrading Dependencies

### Step 1: Clean Existing Dependencies

Remove all downloaded dependencies and built artifacts:

```bash
just distclean
```

This removes:
- `deps/` — SDK, FreeRTOS Kernel, picotool source
- `.local/` — Built OpenOCD and picotool binaries
- `build/` — Build artifacts
- `pico_sdk_import.cmake`, `FreeRTOS_Kernel_import.cmake`

### Step 2: Override Version and Setup

Use `just --set` to override one or more versions:

```bash
# Upgrade Pico SDK (also updates picotool by default)
just --set pico_sdk_version "2.3.0" --set picotool_version "2.3.0" setup

# Upgrade OpenOCD
just --set openocd_version "v0.10.0" setup

# Upgrade FreeRTOS Kernel
just --set freertos_kernel_version "abc123def456..." setup

# Upgrade everything at once
just --set pico_sdk_version "2.3.0" \
     --set picotool_version "2.3.0" \
     --set freertos_kernel_version "abc123..." \
     --set openocd_version "v0.10.0" \
     setup
```

### Step 3: Test the Build

Verify everything works with the new versions:

```bash
just build
just test
just flash
```

### Step 4: Update the justfile

Once verified, update the default versions in the `justfile`:

```just
pico_sdk_version := "2.3.0"
freertos_kernel_version := "new-commit-hash"
openocd_version := "v0.10.0"
picotool_version := "2.3.0"
```

## Finding New Versions

### Pico SDK

Check the [releases page](https://github.com/raspberrypi/pico-sdk/releases) or list tags:

```bash
git ls-remote --tags https://github.com/raspberrypi/pico-sdk.git | tail -5
```

### FreeRTOS Kernel

The Raspberry Pi fork doesn't use tags. Get the latest commit:

```bash
git ls-remote https://github.com/raspberrypi/FreeRTOS-Kernel.git HEAD
```

Or browse [recent commits](https://github.com/raspberrypi/FreeRTOS-Kernel/commits/main) and select a known-good state.

### OpenOCD

Check the [releases page](https://github.com/openocd-org/openocd/releases) or list tags:

```bash
git ls-remote --tags https://github.com/openocd-org/openocd.git | grep -v '\^{}' | tail -5
```

### picotool

Usually matches the SDK version. Check [releases](https://github.com/raspberrypi/picotool/releases):

```bash
git ls-remote --tags https://github.com/raspberrypi/picotool.git | tail -5
```

## Version Compatibility

### SDK and picotool

These are tightly coupled—always use matching versions. The SDK provides headers that picotool needs at build time.

### FreeRTOS Kernel

The Raspberry Pi fork tracks upstream FreeRTOS but includes RP2350-specific port files. Major SDK updates may require a FreeRTOS update for compatibility.

### OpenOCD

RP2350 support requires OpenOCD v0.12+ or a recent build from source. Newer versions may include bug fixes for debug probe communication.

## Troubleshooting

### Build fails after upgrade

1. Ensure `just distclean` was run before changing versions
2. Check for breaking API changes in release notes
3. Try reverting to known-good versions

### FreeRTOS import file not found

The path to `FreeRTOS_Kernel_import.cmake` changed between kernel versions. Check that it exists at:

```
deps/FreeRTOS-Kernel/portable/ThirdParty/GCC/RP2350_ARM_NTZ/FreeRTOS_Kernel_import.cmake
```

### picotool version mismatch

If picotool shows an unexpected version or fails to build, remove it and rebuild:

```bash
rm -rf deps/picotool .local/bin/picotool
just setup
```
