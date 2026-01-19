/**
 * @file test_integration.cpp
 * @brief Integration tests with mocked hardware dependencies.
 *
 * These tests verify behavior of components that normally depend on
 * hardware (WiFi, FreeRTOS), using mock implementations.
 */

#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest.h"
#include "../src/scan_msg.hpp"

// =============================================================================
// Mock infrastructure for LED module
// =============================================================================

namespace mock_led {
    bool g_on = false;
    bool g_blinking = false;
    uint32_t g_blink_interval = 0;
    int g_on_calls = 0;
    int g_off_calls = 0;
    int g_start_blink_calls = 0;
    int g_stop_blink_calls = 0;

    void reset() {
        g_on = false;
        g_blinking = false;
        g_blink_interval = 0;
        g_on_calls = 0;
        g_off_calls = 0;
        g_start_blink_calls = 0;
        g_stop_blink_calls = 0;
    }
}

// Mock LED functions (matching led.hpp API)
namespace led {
    void on() {
        mock_led::g_on = true;
        mock_led::g_blinking = false;
        mock_led::g_on_calls++;
    }

    void off() {
        mock_led::g_on = false;
        mock_led::g_blinking = false;
        mock_led::g_off_calls++;
    }

    void start_blink(uint32_t interval_ms) {
        mock_led::g_blinking = true;
        mock_led::g_blink_interval = interval_ms;
        mock_led::g_start_blink_calls++;
    }

    void stop_blink() {
        mock_led::g_blinking = false;
        mock_led::g_on = true;  // Returns to solid on
        mock_led::g_stop_blink_calls++;
    }
}

// =============================================================================
// LED behavior tests
// =============================================================================

TEST_CASE("LED behavior") {
    SUBCASE("starts off") {
        mock_led::reset();
        CHECK_FALSE(mock_led::g_on);
        CHECK_FALSE(mock_led::g_blinking);
    }

    SUBCASE("on") {
        mock_led::reset();
        led::on();
        CHECK(mock_led::g_on);
        CHECK_FALSE(mock_led::g_blinking);
        CHECK(mock_led::g_on_calls == 1);
    }

    SUBCASE("off") {
        mock_led::reset();
        led::on();
        led::off();
        CHECK_FALSE(mock_led::g_on);
        CHECK(mock_led::g_off_calls == 1);
    }

    SUBCASE("start blink") {
        mock_led::reset();
        led::start_blink(50);
        CHECK(mock_led::g_blinking);
        CHECK(mock_led::g_blink_interval == 50u);
        CHECK(mock_led::g_start_blink_calls == 1);
    }

    SUBCASE("stop blink returns to on") {
        mock_led::reset();
        led::start_blink(50);
        led::stop_blink();
        CHECK_FALSE(mock_led::g_blinking);
        CHECK(mock_led::g_on);  // Returns to solid on
        CHECK(mock_led::g_stop_blink_calls == 1);
    }
}

// =============================================================================
// Simulated scan workflow tests
// =============================================================================

// Simulate the scan callback behavior
void simulate_scan_callback(ScanResult& result, const char* ssid,
                            const uint8_t* bssid, int16_t rssi,
                            uint8_t channel, uint8_t auth) {
    if (result.is_full()) return;

    APInfo ap;
    std::strncpy(ap.ssid.data(), ssid, MAX_SSID_LEN);
    ap.ssid[MAX_SSID_LEN] = '\0';
    std::memcpy(ap.bssid.data(), bssid, BSSID_LEN);
    ap.rssi = rssi;
    ap.channel = channel;
    ap.auth = auth_mode_from_cyw43(auth);

    [[maybe_unused]] const bool added = result.add(ap);
}

TEST_CASE("Scan workflow") {
    SUBCASE("single AP") {
        ScanResult result;
        result.reset();

        uint8_t bssid[] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF};
        simulate_scan_callback(result, "TestNetwork", bssid, -50, 6, 4);

        result.success = true;

        CHECK(result.success);
        CHECK(result.count == 1);
        CHECK(strcmp(result.networks[0].ssid.data(), "TestNetwork") == 0);
        CHECK(result.networks[0].rssi == -50);
        CHECK(result.networks[0].channel == 6);
        CHECK(result.networks[0].auth == AuthMode::WPA2_PSK);
    }

    SUBCASE("multiple APs") {
        ScanResult result;
        result.reset();

        uint8_t bssid1[] = {0x11, 0x22, 0x33, 0x44, 0x55, 0x66};
        uint8_t bssid2[] = {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF};
        uint8_t bssid3[] = {0x00, 0x11, 0x22, 0x33, 0x44, 0x55};

        simulate_scan_callback(result, "Network1", bssid1, -40, 1, 4);  // WPA2
        simulate_scan_callback(result, "Network2", bssid2, -60, 6, 0);  // Open
        simulate_scan_callback(result, "Network3", bssid3, -80, 11, 6); // WPA/WPA2

        result.success = true;

        CHECK(result.count == 3);
        CHECK(result.networks[0].auth == AuthMode::WPA2_PSK);
        CHECK(result.networks[1].auth == AuthMode::OPEN);
        CHECK(result.networks[2].auth == AuthMode::WPA_WPA2_PSK);
    }

    SUBCASE("LED lifecycle") {
        mock_led::reset();

        // LED starts on (idle state)
        led::on();
        CHECK(mock_led::g_on);

        // Scan start - blink
        led::start_blink(50);
        CHECK(mock_led::g_blinking);

        // Simulate scan in progress...
        ScanResult result;
        result.reset();
        uint8_t bssid[] = {0x11, 0x22, 0x33, 0x44, 0x55, 0x66};
        simulate_scan_callback(result, "TestAP", bssid, -55, 6, 4);

        // Scan complete - back to solid on
        result.success = true;
        led::stop_blink();

        CHECK_FALSE(mock_led::g_blinking);
        CHECK(mock_led::g_on);
        CHECK(mock_led::g_start_blink_calls == 1);
        CHECK(mock_led::g_stop_blink_calls == 1);
    }

    SUBCASE("error handling") {
        mock_led::reset();
        ScanResult result;
        result.reset();

        // LED on (idle)
        led::on();

        // Scan start
        led::start_blink(50);

        // Error during scan
        result.error_code = -1;
        result.success = false;

        // LED returns to solid on
        led::stop_blink();

        CHECK_FALSE(result.success);
        CHECK(result.error_code == -1);
        CHECK(result.count == 0);
        CHECK(mock_led::g_on);
        CHECK_FALSE(mock_led::g_blinking);
    }

    SUBCASE("capacity limit") {
        ScanResult result;
        result.reset();

        uint8_t bssid[] = {0x00, 0x00, 0x00, 0x00, 0x00, 0x00};

        // Try to add more than MAX_SCAN_RESULTS
        for (size_t i = 0; i < MAX_SCAN_RESULTS + 5; i++) {
            char ssid[MAX_SSID_LEN + 1];
            std::snprintf(ssid, sizeof(ssid), "Network%zu", i);
            bssid[5] = static_cast<uint8_t>(i);
            simulate_scan_callback(result, ssid, bssid, -50, 6, 4);
        }

        result.success = true;

        // Should cap at MAX_SCAN_RESULTS
        CHECK(result.count == MAX_SCAN_RESULTS);
        CHECK(result.is_full());
    }
}
