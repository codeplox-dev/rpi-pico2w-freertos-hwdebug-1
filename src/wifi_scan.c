/*
 * WiFi Scanning Implementation
 */

#include "wifi_scan.h"
#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"
#include <string.h>
#include <stdio.h>

static wifi_scan_callback_t s_callback = NULL;
static void *s_user_data = NULL;

static int scan_result_handler(void *env, const cyw43_ev_scan_result_t *result) {
    if (result && s_callback) {
        wifi_scan_result_t scan_result;

        /* Copy SSID (may not be null-terminated) */
        size_t ssid_len = result->ssid_len < WIFI_SSID_MAX_LEN - 1 ?
                          result->ssid_len : WIFI_SSID_MAX_LEN - 1;
        memcpy(scan_result.ssid, result->ssid, ssid_len);
        scan_result.ssid[ssid_len] = '\0';

        scan_result.rssi = result->rssi;
        scan_result.channel = result->channel;
        scan_result.auth_mode = result->auth_mode;
        memcpy(scan_result.bssid, result->bssid, 6);

        s_callback(&scan_result, s_user_data);
    }
    return 0;
}

int wifi_scan_init(void) {
    printf("[WiFi] Initializing CYW43...\n");

    if (cyw43_arch_init()) {
        printf("[WiFi] ERROR: Failed to initialize CYW43\n");
        return -1;
    }

    cyw43_arch_enable_sta_mode();
    printf("[WiFi] CYW43 initialized in STA mode\n");
    return 0;
}

int wifi_scan_start(wifi_scan_callback_t callback, void *user_data) {
    s_callback = callback;
    s_user_data = user_data;

    cyw43_wifi_scan_options_t scan_options = {0};

    int err = cyw43_wifi_scan(&cyw43_state, &scan_options, NULL, scan_result_handler);
    if (err) {
        printf("[WiFi] ERROR: Scan failed with code %d\n", err);
        return err;
    }

    return 0;
}

bool wifi_scan_active(void) {
    return cyw43_wifi_scan_active(&cyw43_state);
}

const char* wifi_auth_mode_str(uint8_t auth_mode) {
    switch (auth_mode) {
        case 0: return "OPEN";
        case 1: return "WEP";
        case 2: return "WPA";
        case 3: return "WPA2";
        case 4: return "WPA/WPA2";
        case 5: return "WPA2-ENT";
        case 6: return "WPA3";
        case 7: return "WPA2/WPA3";
        default: return "UNKNOWN";
    }
}
