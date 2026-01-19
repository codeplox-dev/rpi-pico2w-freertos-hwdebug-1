/**
 * @file scan_msg.hpp
 * @brief Data types for WiFi scan results.
 */

#ifndef SCAN_MSG_HPP
#define SCAN_MSG_HPP

#include <array>
#include <cstdint>
#include <cstdio>
#include <cstring>

/// Maximum SSID length per 802.11 spec
inline constexpr std::size_t MAX_SSID_LEN = 32;

/// BSSID (MAC address) length
inline constexpr std::size_t BSSID_LEN = 6;

/// Maximum APs to store per scan
inline constexpr std::size_t MAX_SCAN_RESULTS = 32;

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
[[nodiscard]] constexpr const char* auth_mode_to_string(AuthMode auth) noexcept {
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
[[nodiscard]] constexpr AuthMode auth_mode_from_cyw43(uint8_t auth) noexcept {
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
    std::array<char, MAX_SSID_LEN + 1> ssid{};   ///< Null-terminated SSID
    std::array<uint8_t, BSSID_LEN> bssid{};      ///< MAC address
    int16_t rssi{0};                              ///< Signal strength in dBm
    uint8_t channel{0};                           ///< WiFi channel
    AuthMode auth{AuthMode::UNKNOWN};             ///< Authentication mode

    /**
     * @brief Format BSSID as MAC address string.
     * @param out Output buffer (must be at least 18 bytes)
     * @param out_len Size of output buffer
     */
    void format_bssid(char* out, std::size_t out_len) const noexcept {
        if (out && out_len >= 18) {
            std::snprintf(out, out_len, "%02X:%02X:%02X:%02X:%02X:%02X",
                          bssid[0], bssid[1], bssid[2], bssid[3], bssid[4], bssid[5]);
        }
    }
};

/**
 * @brief Result of a WiFi scan operation.
 */
struct ScanResult {
    bool success{false};                              ///< true if scan completed without error
    int32_t error_code{0};                            ///< Error code if !success
    uint16_t count{0};                                ///< Number of APs found
    std::array<APInfo, MAX_SCAN_RESULTS> networks{};  ///< Discovered networks

    /**
     * @brief Reset result for a new scan.
     */
    void reset() noexcept {
        success = false;
        error_code = 0;
        count = 0;
    }

    /**
     * @brief Add an AP to the results.
     * @return true if added, false if at capacity
     */
    [[nodiscard]] bool add(const APInfo& ap) noexcept {
        if (count < MAX_SCAN_RESULTS) {
            networks[count++] = ap;
            return true;
        }
        return false;
    }

    /**
     * @brief Check if results are at capacity.
     */
    [[nodiscard]] bool is_full() const noexcept {
        return count >= MAX_SCAN_RESULTS;
    }
};

#endif // SCAN_MSG_HPP
