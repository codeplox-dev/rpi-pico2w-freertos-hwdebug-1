# Test suite for WiFi Scanner
# Builds and runs on host (not target) for unit and integration testing

cmake_minimum_required(VERSION 3.13)
project(wifi_scanner_tests CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Unit tests - pure logic, no dependencies
add_executable(test_unit
    test_unit.cpp
)
target_include_directories(test_unit PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/../src
)

# Integration tests - with mocks
add_executable(test_integration
    test_integration.cpp
)
target_include_directories(test_integration PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_CURRENT_SOURCE_DIR}/../src
)

# Enable warnings
foreach(target test_unit test_integration)
    target_compile_options(${target} PRIVATE
        -Wall -Wextra -Wpedantic
    )
endforeach()
