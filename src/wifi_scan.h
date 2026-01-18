/*
 * WiFi Scanning Module
 */

#ifndef WIFI_SCAN_H
#define WIFI_SCAN_H

#include <stdint.h>
#include <stdbool.h>

#define WIFI_SSID_MAX_LEN 33

/* WiFi scan result */
typedef struct {
    char ssid[WIFI_SSID_MAX_LEN];
    int8_t rssi;
    uint8_t channel;
    uint8_t auth_mode;
    uint8_t bssid[6];
} wifi_scan_result_t;

/* Callback for each scan result */
typedef void (*wifi_scan_callback_t)(const wifi_scan_result_t *result, void *user_data);

/*
 * Initialize WiFi for scanning.
 * @return 0 on success, negative error code on failure
 */
int wifi_scan_init(void);

/*
 * Start a WiFi scan. Results are delivered via callback.
 * @param callback Function called for each result
 * @param user_data User data passed to callback
 * @return 0 on success, negative error code on failure
 */
int wifi_scan_start(wifi_scan_callback_t callback, void *user_data);

/*
 * Check if a scan is currently in progress.
 */
bool wifi_scan_active(void);

/*
 * Get auth mode as human-readable string.
 */
const char* wifi_auth_mode_str(uint8_t auth_mode);

#endif /* WIFI_SCAN_H */
