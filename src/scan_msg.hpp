/**
 * @file scan_msg.hpp
 * @brief Data types for WiFi scan results.
 */

#ifndef SCAN_MSG_HPP
#define SCAN_MSG_HPP

#include <cstdint>
#include <cstdio>
#include <cstring>

/// Maximum SSID length per 802.11 spec
constexpr size_t MAX_SSID_LEN = 32;

/// BSSID (MAC address) length
constexpr size_t BSSID_LEN = 6;

/// Maximum APs to store per scan
constexpr size_t MAX_SCAN_RESULTS = 32;

/**
 * @brief Authentication mode of discovered AP.
 */
enum class AuthMode : uint8_t {
    OPEN = 0,
    WEP,
    WPA_PSK,
    WPA2_PSK,
    WPA_WPA2_PSK,
    WPA3_PSK,
    UNKNOWN
};

/**
 * @brief Convert AuthMode enum to display string.
 */
inline const char* auth_mode_to_string(AuthMode auth) {
    switch (auth) {
        case AuthMode::OPEN:         return "OPEN";
        case AuthMode::WEP:          return "WEP";
        case AuthMode::WPA_PSK:      return "WPA";
        case AuthMode::WPA2_PSK:     return "WPA2";
        case AuthMode::WPA_WPA2_PSK: return "WPA/WPA2";
        case AuthMode::WPA3_PSK:     return "WPA3";
        default:                     return "???";
    }
}

/**
 * @brief Convert CYW43 scan result auth bitmask to AuthMode.
 *
 * Scan results use a bitmask:
 *   Bit 0 (1): WEP
 *   Bit 1 (2): WPA
 *   Bit 2 (4): WPA2
 */
inline AuthMode auth_mode_from_cyw43(uint8_t auth) {
    if (auth == 0) return AuthMode::OPEN;
    if (auth == 1) return AuthMode::WEP;
    if ((auth & 4) && (auth & 2)) return AuthMode::WPA_WPA2_PSK;
    if (auth & 4) return AuthMode::WPA2_PSK;
    if (auth & 2) return AuthMode::WPA_PSK;
    return AuthMode::UNKNOWN;
}

/**
 * @brief Data for a single AP scan result.
 */
struct APInfo {
    char ssid[MAX_SSID_LEN + 1];  ///< Null-terminated SSID
    uint8_t bssid[BSSID_LEN];     ///< MAC address
    int16_t rssi;                  ///< Signal strength in dBm
    uint8_t channel;               ///< WiFi channel
    AuthMode auth;                 ///< Authentication mode

    APInfo() : rssi(0), channel(0), auth(AuthMode::UNKNOWN) {
        ssid[0] = '\0';
        std::memset(bssid, 0, sizeof(bssid));
    }

    /**
     * @brief Format BSSID as MAC address string.
     * @param out Output buffer (must be at least 18 bytes)
     * @param out_len Size of output buffer
     */
    void format_bssid(char* out, size_t out_len) const {
        std::snprintf(out, out_len, "%02X:%02X:%02X:%02X:%02X:%02X",
                      bssid[0], bssid[1], bssid[2], bssid[3], bssid[4], bssid[5]);
    }
};

/**
 * @brief Result of a WiFi scan operation.
 */
struct ScanResult {
    bool success;                       ///< true if scan completed without error
    int32_t error_code;                 ///< Error code if !success
    uint16_t count;                     ///< Number of APs found
    APInfo networks[MAX_SCAN_RESULTS];  ///< Discovered networks

    ScanResult() : success(false), error_code(0), count(0) {}

    /**
     * @brief Reset result for a new scan.
     */
    void reset() {
        success = false;
        error_code = 0;
        count = 0;
    }

    /**
     * @brief Add an AP to the results.
     * @return true if added, false if at capacity
     */
    bool add(const APInfo& ap) {
        if (count < MAX_SCAN_RESULTS) {
            networks[count++] = ap;
            return true;
        }
        return false;
    }

    /**
     * @brief Check if results are at capacity.
     */
    bool is_full() const {
        return count >= MAX_SCAN_RESULTS;
    }
};

#endif // SCAN_MSG_HPP
