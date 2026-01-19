{
  description = "RP2350 WiFi Scanner - Pico SDK + FreeRTOS for Pico 2 W";

  inputs = {
    # Pinned to specific commits for reproducibility
    nixpkgs.url = "github:NixOS/nixpkgs/5912c1772a44e31bf1c63c0390b90501e5026886";
    flake-utils.url = "github:numtide/flake-utils/11707dc2f618dd54ca8739b309ec4fc024de578b";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in {
        devShells.default = pkgs.mkShell {
          nativeBuildInputs = with pkgs; [
            # Build tools
            cmake
            ninja
            python3
            python3Packages.pyserial

            # ARM toolchain
            gcc-arm-embedded

            # OpenOCD build dependencies
            autoconf
            automake
            libtool
            texinfo
            pkg-config
            jimtcl
            capstone

            # Debug tools
            gdb

            # Code quality
            cppcheck
            clang-tools

            # Build essentials
            just
            git
          ];

          buildInputs = with pkgs; [
            libusb1
            hidapi
            libftdi1
          ];

          shellHook = ''
            export PATH="$PWD/.local/bin:$PATH"
            export PICO_SDK_PATH="$PWD/deps/pico-sdk"
            export FREERTOS_KERNEL_PATH="$PWD/deps/FreeRTOS-Kernel"
            export PICO_BOARD="pico2_w"

            if [ ! -d deps/pico-sdk ]; then
              echo ""
              echo "Run 'just envsetup' to initialize SDK and OpenOCD"
              echo ""
            fi
          '';
        };
      }
    );
}
