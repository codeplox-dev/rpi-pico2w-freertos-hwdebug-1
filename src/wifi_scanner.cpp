/**
 * @file wifi_scanner.cpp
 * @brief WiFi scanning implementation with synchronous request-response.
 */

#include "wifi_scanner.hpp"
#include "led.hpp"

#include "pico/cyw43_arch.h"
#include "FreeRTOS.h"
#include "task.h"
#include "semphr.h"

#include <algorithm>
#include <cstring>

namespace {

constexpr uint32_t SCANNER_STACK_SIZE = 2048;
constexpr UBaseType_t SCANNER_PRIORITY = tskIDLE_PRIORITY + 2;
constexpr uint32_t LED_BLINK_INTERVAL_MS = 50;
constexpr uint32_t SCAN_POLL_INTERVAL_MS = 50;

// Synchronization primitives for request-response pattern.
// Note: For this single-caller example, direct calls to do_scan() would suffice.
// However, semaphores provide the foundation for safely adding concurrent
// scan requesters (e.g., a command task, network trigger) without races.
SemaphoreHandle_t g_request_sem = nullptr;
SemaphoreHandle_t g_complete_sem = nullptr;

// Shared scan result pointer (safe: written before request_sem, read after)
ScanResult* g_result_ptr = nullptr;

/**
 * @brief Callback invoked by CYW43 for each AP found during scan.
 */
int scan_result_callback(void* env, const cyw43_ev_scan_result_t* result) {
    if (!result) return 0;

    auto* scan_result = static_cast<ScanResult*>(env);
    if (!scan_result || scan_result->is_full()) return 0;

    APInfo ap;

    // Copy SSID (with bounds check using std::min)
    const auto ssid_len = std::min(static_cast<std::size_t>(result->ssid_len), MAX_SSID_LEN);
    std::memcpy(ap.ssid.data(), result->ssid, ssid_len);
    ap.ssid[ssid_len] = '\0';

    // Skip hidden networks (empty SSID)
    if (ap.ssid[0] == '\0') return 0;

    // Copy remaining fields
    std::memcpy(ap.bssid.data(), result->bssid, BSSID_LEN);
    ap.rssi = result->rssi;
    ap.channel = result->channel;
    ap.auth = auth_mode_from_cyw43(result->auth_mode);

    [[maybe_unused]] const bool added = scan_result->add(ap);
    return 0;
}

/**
 * @brief Perform a single WiFi scan.
 */
void do_scan(ScanResult* result) {
    result->reset();

    led::start_blink(LED_BLINK_INTERVAL_MS);

    // Use brace initialization instead of memset
    cyw43_wifi_scan_options_t scan_options{};

    int err = cyw43_wifi_scan(&cyw43_state, &scan_options, result, scan_result_callback);
    if (err != 0) {
        led::stop_blink();
        result->error_code = err;
        return;
    }

    while (cyw43_wifi_scan_active(&cyw43_state)) {
        vTaskDelay(pdMS_TO_TICKS(SCAN_POLL_INTERVAL_MS));
    }

    led::stop_blink();
    result->success = true;
}

/**
 * @brief Scanner task - waits for requests and performs scans.
 */
void scanner_task(void* params) {
    static_cast<void>(params);

    while (true) {
        if (xSemaphoreTake(g_request_sem, portMAX_DELAY) == pdTRUE) {
            ScanResult* result = g_result_ptr;
            if (result) {
                do_scan(result);
            }
            xSemaphoreGive(g_complete_sem);
        }
    }
}

} // anonymous namespace

namespace wifi {

[[nodiscard]] bool init() {
    if (cyw43_arch_init()) {
        return false;
    }
    cyw43_arch_enable_sta_mode();
    return true;
}

[[nodiscard]] bool start_scanner_task() {
    g_request_sem = xSemaphoreCreateBinary();
    g_complete_sem = xSemaphoreCreateBinary();

    if (!g_request_sem || !g_complete_sem) {
        return false;
    }

    BaseType_t ret = xTaskCreate(
        scanner_task,
        "wifi_scan",
        SCANNER_STACK_SIZE,
        nullptr,
        SCANNER_PRIORITY,
        nullptr
    );

    return ret == pdPASS;
}

[[nodiscard]] bool request_scan(ScanResult* result, uint32_t timeout_ms) {
    if (!result || !g_request_sem || !g_complete_sem) {
        return false;
    }

    g_result_ptr = result;
    xSemaphoreGive(g_request_sem);

    return xSemaphoreTake(g_complete_sem, pdMS_TO_TICKS(timeout_ms)) == pdTRUE;
}

} // namespace wifi
