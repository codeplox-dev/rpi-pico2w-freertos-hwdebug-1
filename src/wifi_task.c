/*
 * WiFi Scanning Task Implementation
 */

#include "wifi_task.h"
#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"
#include "FreeRTOS.h"
#include "task.h"
#include <string.h>
#include <stdio.h>

#define WIFI_TASK_STACK_SIZE    4096
#define WIFI_TASK_PRIORITY      (tskIDLE_PRIORITY + 1)
#define WIFI_SCAN_INTERVAL_MS   10000

static QueueHandle_t s_result_queue = NULL;

static int scan_callback(void *env, const cyw43_ev_scan_result_t *result) {
    if (result && s_result_queue) {
        wifi_msg_t msg;
        msg.type = WIFI_MSG_SCAN_RESULT;

        /* Copy SSID (may not be null-terminated) */
        size_t ssid_len = result->ssid_len < WIFI_SSID_MAX_LEN - 1 ?
                          result->ssid_len : WIFI_SSID_MAX_LEN - 1;
        memcpy(msg.data.scan_result.ssid, result->ssid, ssid_len);
        msg.data.scan_result.ssid[ssid_len] = '\0';

        msg.data.scan_result.rssi = result->rssi;
        msg.data.scan_result.channel = result->channel;
        msg.data.scan_result.auth_mode = result->auth_mode;
        memcpy(msg.data.scan_result.bssid, result->bssid, 6);

        /* Non-blocking send - drop if queue full */
        xQueueSend(s_result_queue, &msg, 0);
    }
    return 0;
}

static void wifi_task(void *params) {
    (void)params;

    printf("[WiFi] Initializing CYW43...\n");

    if (cyw43_arch_init()) {
        printf("[WiFi] ERROR: Failed to initialize CYW43\n");
        wifi_msg_t msg = { .type = WIFI_MSG_ERROR, .data.error_code = -1 };
        xQueueSend(s_result_queue, &msg, portMAX_DELAY);
        vTaskDelete(NULL);
        return;
    }

    cyw43_arch_enable_sta_mode();
    printf("[WiFi] CYW43 initialized in STA mode\n");

    cyw43_wifi_scan_options_t scan_options = {0};

    while (1) {
        printf("[WiFi] Starting scan...\n");

        int err = cyw43_wifi_scan(&cyw43_state, &scan_options, NULL, scan_callback);
        if (err) {
            printf("[WiFi] ERROR: Scan failed with code %d\n", err);
            wifi_msg_t msg = { .type = WIFI_MSG_ERROR, .data.error_code = err };
            xQueueSend(s_result_queue, &msg, 0);
        } else {
            /* Wait for scan to complete */
            while (cyw43_wifi_scan_active(&cyw43_state)) {
                vTaskDelay(pdMS_TO_TICKS(100));
            }

            /* Send scan complete message */
            wifi_msg_t msg = { .type = WIFI_MSG_SCAN_COMPLETE };
            xQueueSend(s_result_queue, &msg, 0);
        }

        /* Wait before next scan */
        vTaskDelay(pdMS_TO_TICKS(WIFI_SCAN_INTERVAL_MS));
    }
}

BaseType_t wifi_task_create(QueueHandle_t result_queue) {
    s_result_queue = result_queue;

    return xTaskCreate(
        wifi_task,
        "wifi",
        WIFI_TASK_STACK_SIZE,
        NULL,
        WIFI_TASK_PRIORITY,
        NULL
    );
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
