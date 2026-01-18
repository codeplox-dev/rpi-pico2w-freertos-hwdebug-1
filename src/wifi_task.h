/*
 * WiFi Scanning Task
 *
 * Scans for nearby WiFi networks and publishes results to a FreeRTOS queue.
 */

#ifndef WIFI_TASK_H
#define WIFI_TASK_H

#include "FreeRTOS.h"
#include "queue.h"

#define WIFI_SSID_MAX_LEN       33
#define WIFI_SCAN_RESULT_QUEUE_LEN 16

/* WiFi scan result */
typedef struct {
    char ssid[WIFI_SSID_MAX_LEN];
    int8_t rssi;
    uint8_t channel;
    uint8_t auth_mode;
    uint8_t bssid[6];
} wifi_scan_result_t;

/* Message types sent from WiFi task to console task */
typedef enum {
    WIFI_MSG_SCAN_RESULT,
    WIFI_MSG_SCAN_COMPLETE,
    WIFI_MSG_ERROR
} wifi_msg_type_t;

/* Message wrapper for queue */
typedef struct {
    wifi_msg_type_t type;
    union {
        wifi_scan_result_t scan_result;
        int error_code;
    } data;
} wifi_msg_t;

/*
 * Create the WiFi task.
 *
 * @param result_queue Queue handle for publishing scan results
 * @return pdPASS on success, pdFAIL on failure
 */
BaseType_t wifi_task_create(QueueHandle_t result_queue);

/*
 * Get auth mode as human-readable string.
 */
const char* wifi_auth_mode_str(uint8_t auth_mode);

#endif /* WIFI_TASK_H */
