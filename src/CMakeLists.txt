# Pico 2 W WiFi Scanner - FreeRTOS Application

add_executable(wifi_scanner
    main.cpp
    wifi_scanner.cpp
    led.cpp
)

target_include_directories(wifi_scanner PRIVATE
    ${CMAKE_CURRENT_LIST_DIR}
)

# Link required libraries
target_link_libraries(wifi_scanner
    pico_stdlib
    pico_cyw43_arch_lwip_sys_freertos
    FreeRTOS-Kernel-Heap4
)

# Enable USB CDC, UART, and RTT for stdio
pico_enable_stdio_usb(wifi_scanner 1)
pico_enable_stdio_uart(wifi_scanner 1)
pico_enable_stdio_rtt(wifi_scanner 1)

# Increase RTT buffer size from 1KB to 4KB for better debug output
target_compile_definitions(wifi_scanner PRIVATE BUFFER_SIZE_UP=4096)

# Generate UF2 and other outputs
pico_add_extra_outputs(wifi_scanner)
