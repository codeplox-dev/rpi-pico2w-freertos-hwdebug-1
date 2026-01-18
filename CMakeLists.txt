cmake_minimum_required(VERSION 3.13)

# Set board before importing SDK
set(PICO_BOARD pico2_w)

# Set FreeRTOS kernel path
set(FREERTOS_KERNEL_PATH ${CMAKE_CURRENT_LIST_DIR}/deps/FreeRTOS-Kernel)

# Import Pico SDK and FreeRTOS (must be before pico_sdk_init for SDK <= 1.3.1)
include(pico_sdk_import.cmake)
include(FreeRTOS_Kernel_import.cmake)

project(wifi_scanner C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# Initialize the Pico SDK
pico_sdk_init()

# Add application source directory
add_subdirectory(src)
