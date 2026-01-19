/**
 * @file debug_log.hpp
 * @brief Debug logging macros for RTT/stdio output.
 *
 * Output goes to all enabled stdio drivers (USB, UART, RTT).
 * RTT provides real-time output through the debug probe without
 * requiring a serial connection.
 *
 * Usage:
 *   DBG_INFO("WiFi", "Starting scan");
 *   DBG_INFO("WiFi", "Found %u networks", count);
 *   DBG_ERROR("Main", "Init failed: %d", err);
 */

#ifndef DEBUG_LOG_HPP
#define DEBUG_LOG_HPP

#include <cstdio>
#include "FreeRTOS.h"
#include "task.h"

// Enable debug logging (set to 0 to disable all debug output)
#ifndef DEBUG_LOG_ENABLED
#define DEBUG_LOG_ENABLED 1
#endif

#if DEBUG_LOG_ENABLED

/**
 * @brief Log an informational message.
 * @param tag Module/component name (e.g., "WiFi", "Main")
 * @param fmt printf-style format string
 */
#define DBG_INFO(tag, fmt, ...) \
    printf("[%8lu] [" tag "] " fmt "\n", \
           static_cast<unsigned long>(xTaskGetTickCount()), ##__VA_ARGS__)

/**
 * @brief Log an error message.
 * @param tag Module/component name
 * @param fmt printf-style format string
 */
#define DBG_ERROR(tag, fmt, ...) \
    printf("[%8lu] [" tag "] ERROR: " fmt "\n", \
           static_cast<unsigned long>(xTaskGetTickCount()), ##__VA_ARGS__)

/**
 * @brief Log a warning message.
 * @param tag Module/component name
 * @param fmt printf-style format string
 */
#define DBG_WARN(tag, fmt, ...) \
    printf("[%8lu] [" tag "] WARN: " fmt "\n", \
           static_cast<unsigned long>(xTaskGetTickCount()), ##__VA_ARGS__)

#else

#define DBG_INFO(tag, fmt, ...)  ((void)0)
#define DBG_ERROR(tag, fmt, ...) ((void)0)
#define DBG_WARN(tag, fmt, ...)  ((void)0)

#endif // DEBUG_LOG_ENABLED

#endif // DEBUG_LOG_HPP
