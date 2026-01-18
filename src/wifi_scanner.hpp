/**
 * @file wifi_scanner.hpp
 * @brief WiFi scanning with synchronous request-response pattern.
 *
 * The scanner task waits for scan requests and returns results
 * via a shared pointer. Uses FreeRTOS semaphores for synchronization.
 */

#ifndef WIFI_SCANNER_HPP
#define WIFI_SCANNER_HPP

#include "scan_msg.hpp"

namespace wifi {

/**
 * @brief Initialize WiFi hardware (CYW43).
 * @return true on success, false on failure
 *
 * Must be called before starting the scanner task.
 */
bool init();

/**
 * @brief Start the WiFi scanner task.
 * @return true if task created successfully
 *
 * The task waits for scan requests triggered by request_scan().
 */
bool start_scanner_task();

/**
 * @brief Request a synchronous WiFi scan.
 * @param result Pointer to ScanResult to populate
 * @param timeout_ms Maximum time to wait for scan completion
 * @return true if scan completed within timeout
 *
 * Blocks until scan completes or timeout expires.
 * LED blinks during scan, stops when complete.
 */
bool request_scan(ScanResult* result, uint32_t timeout_ms = 30000);

} // namespace wifi

#endif // WIFI_SCANNER_HPP
