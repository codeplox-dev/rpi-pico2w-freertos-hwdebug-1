/**
 * @file main.cpp
 * @brief Pico 2 W WiFi Scanner - FreeRTOS application.
 *
 * Architecture:
 *   - Main task: Periodically requests scans and displays results
 *   - Scanner task: Waits for requests, performs scans, returns results
 *   - LED blinks during active scans
 */

#include <cstdio>
#include "pico/stdlib.h"
#include "FreeRTOS.h"
#include "task.h"

#include "scan_msg.hpp"
#include "wifi_scanner.hpp"
#include "led.hpp"
#include "debug_log.hpp"

namespace {

constexpr uint32_t MAIN_STACK_SIZE = 2048;
constexpr UBaseType_t MAIN_PRIORITY = tskIDLE_PRIORITY + 1;
constexpr uint32_t SCAN_INTERVAL_MS = 20000;

/**
 * @brief Print a single AP to console.
 */
void print_ap(const APInfo& ap) {
    char bssid_str[18];
    ap.format_bssid(bssid_str, sizeof(bssid_str));

    printf("  %-32s  %s  ch%2u  %4ddBm  %s\n",
           ap.ssid.data(),
           bssid_str,
           ap.channel,
           ap.rssi,
           auth_mode_to_string(ap.auth));
}

/**
 * @brief Print scan results to console.
 */
void print_results(const ScanResult& result) {
    if (!result.success) {
        printf("Scan failed (error: %d)\n\n", static_cast<int>(result.error_code));
        return;
    }

    printf("\n");
    printf("  %-32s  %-17s  %3s  %7s  %s\n", "SSID", "BSSID", "CH", "RSSI", "AUTH");
    printf("  %s\n", "--------------------------------------------------------------------------------");

    for (uint16_t i = 0; i < result.count; i++) {
        print_ap(result.networks[i]);
    }

    printf("\n  Found %u networks\n\n", result.count);
}

/**
 * @brief Print startup banner.
 */
void print_banner() {
    printf("\n");
    printf("========================================\n");
    printf("  Pico 2 W WiFi Scanner\n");
    printf("  FreeRTOS + CYW43\n");
    printf("========================================\n\n");
}

/**
 * @brief Initialize WiFi subsystem.
 * @return true on success
 */
bool init_wifi() {
    DBG_INFO("Main", "WiFi init starting");
    printf("Initializing WiFi...\n");
    if (!wifi::init()) {
        DBG_ERROR("Main", "WiFi init failed");
        printf("ERROR: WiFi init failed!\n");
        return false;
    }
    DBG_INFO("Main", "WiFi init complete");
    printf("WiFi initialized.\n\n");

    // LED solid on when idle
    led::on();
    return true;
}

/**
 * @brief Main console task.
 */
void main_task(void* params) {
    static_cast<void>(params);

    DBG_INFO("Main", "main_task started");
    print_banner();

    if (!init_wifi()) {
        DBG_ERROR("Main", "Halting due to WiFi init failure");
        while (true) { vTaskDelay(pdMS_TO_TICKS(1000)); }
    }

    DBG_INFO("Main", "Starting scanner task");
    if (!wifi::start_scanner_task()) {
        DBG_ERROR("Main", "Failed to start scanner task");
        printf("ERROR: Failed to start scanner task!\n");
        while (true) { vTaskDelay(pdMS_TO_TICKS(1000)); }
    }
    DBG_INFO("Main", "Scanner task started");

    printf("Scanning every %u seconds...\n", SCAN_INTERVAL_MS / 1000);

    ScanResult result;
    while (true) {
        DBG_INFO("Main", "Requesting scan");
        printf("--- Starting scan ---\n");

        if (wifi::request_scan(&result)) {
            DBG_INFO("Main", "Scan complete: %u networks found", result.count);
            print_results(result);
        } else {
            DBG_WARN("Main", "Scan timeout");
            printf("Scan timeout!\n\n");
        }

        vTaskDelay(pdMS_TO_TICKS(SCAN_INTERVAL_MS));
    }
}

} // anonymous namespace

extern "C" void vApplicationStackOverflowHook(TaskHandle_t xTask, char* pcTaskName) {
    (void)xTask;
    DBG_ERROR("RTOS", "Stack overflow in task: %s", pcTaskName);
    printf("STACK OVERFLOW: %s\n", pcTaskName);
    while (true) { tight_loop_contents(); }
}

int main() {
    stdio_init_all();

    DBG_INFO("Main", "Firmware starting");
    DBG_INFO("Main", "Creating main_task");
    xTaskCreate(main_task, "main", MAIN_STACK_SIZE, nullptr, MAIN_PRIORITY, nullptr);

    DBG_INFO("Main", "Starting FreeRTOS scheduler");
    vTaskStartScheduler();

    // Should never reach here
    DBG_ERROR("Main", "Scheduler exited unexpectedly");
    while (true) { tight_loop_contents(); }
    return 0;
}
