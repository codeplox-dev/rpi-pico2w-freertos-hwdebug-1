/**
 * @file test_unit.cpp
 * @brief Unit tests for pure logic (no hardware dependencies).
 */

#define DOCTEST_CONFIG_IMPLEMENT_WITH_MAIN
#include "doctest.h"
#include "../src/scan_msg.hpp"

// =============================================================================
// AuthMode conversion tests
// =============================================================================

TEST_CASE("AuthMode string conversion") {
    SUBCASE("OPEN") {
        CHECK(strcmp(auth_mode_to_string(AuthMode::OPEN), "OPEN") == 0);
    }
    SUBCASE("WEP") {
        CHECK(strcmp(auth_mode_to_string(AuthMode::WEP), "WEP") == 0);
    }
    SUBCASE("WPA") {
        CHECK(strcmp(auth_mode_to_string(AuthMode::WPA_PSK), "WPA") == 0);
    }
    SUBCASE("WPA2") {
        CHECK(strcmp(auth_mode_to_string(AuthMode::WPA2_PSK), "WPA2") == 0);
    }
    SUBCASE("WPA/WPA2") {
        CHECK(strcmp(auth_mode_to_string(AuthMode::WPA_WPA2_PSK), "WPA/WPA2") == 0);
    }
    SUBCASE("WPA3") {
        CHECK(strcmp(auth_mode_to_string(AuthMode::WPA3_PSK), "WPA3") == 0);
    }
    SUBCASE("UNKNOWN") {
        CHECK(strcmp(auth_mode_to_string(AuthMode::UNKNOWN), "???") == 0);
    }
}

// =============================================================================
// CYW43 auth bitmask conversion tests
// =============================================================================

TEST_CASE("CYW43 auth bitmask conversion") {
    SUBCASE("OPEN (0)") {
        CHECK(auth_mode_from_cyw43(0) == AuthMode::OPEN);
    }
    SUBCASE("WEP (1)") {
        CHECK(auth_mode_from_cyw43(1) == AuthMode::WEP);
    }
    SUBCASE("WPA (2)") {
        CHECK(auth_mode_from_cyw43(2) == AuthMode::WPA_PSK);
    }
    SUBCASE("WPA2 (4)") {
        CHECK(auth_mode_from_cyw43(4) == AuthMode::WPA2_PSK);
    }
    SUBCASE("WPA/WPA2 (6)") {
        CHECK(auth_mode_from_cyw43(6) == AuthMode::WPA_WPA2_PSK);
    }
    SUBCASE("UNKNOWN (8)") {
        // Bit 3 set (8) is undefined, should return UNKNOWN
        CHECK(auth_mode_from_cyw43(8) == AuthMode::UNKNOWN);
    }
}

// =============================================================================
// APInfo tests
// =============================================================================

TEST_CASE("APInfo") {
    SUBCASE("default constructor") {
        APInfo ap;
        CHECK(ap.ssid[0] == '\0');
        CHECK(ap.rssi == 0);
        CHECK(ap.channel == 0);
        CHECK(ap.auth == AuthMode::UNKNOWN);
    }

    SUBCASE("format_bssid") {
        APInfo ap;
        ap.bssid[0] = 0xAA;
        ap.bssid[1] = 0xBB;
        ap.bssid[2] = 0xCC;
        ap.bssid[3] = 0xDD;
        ap.bssid[4] = 0xEE;
        ap.bssid[5] = 0xFF;

        char buf[18];
        ap.format_bssid(buf, sizeof(buf));
        CHECK(strcmp(buf, "AA:BB:CC:DD:EE:FF") == 0);
    }

    SUBCASE("format_bssid zeros") {
        APInfo ap;  // BSSID initialized to zeros
        char buf[18];
        ap.format_bssid(buf, sizeof(buf));
        CHECK(strcmp(buf, "00:00:00:00:00:00") == 0);
    }
}

// =============================================================================
// ScanResult tests
// =============================================================================

TEST_CASE("ScanResult") {
    SUBCASE("default constructor") {
        ScanResult result;
        CHECK_FALSE(result.success);
        CHECK(result.error_code == 0);
        CHECK(result.count == 0);
    }

    SUBCASE("reset") {
        ScanResult result;
        result.success = true;
        result.error_code = 42;
        result.count = 10;

        result.reset();

        CHECK_FALSE(result.success);
        CHECK(result.error_code == 0);
        CHECK(result.count == 0);
    }

    SUBCASE("add single") {
        ScanResult result;
        APInfo ap;
        std::strcpy(ap.ssid.data(), "TestNetwork");

        bool added = result.add(ap);

        CHECK(added);
        CHECK(result.count == 1);
        CHECK(strcmp(result.networks[0].ssid.data(), "TestNetwork") == 0);
    }

    SUBCASE("add multiple") {
        ScanResult result;

        for (int i = 0; i < 5; i++) {
            APInfo ap;
            std::snprintf(ap.ssid.data(), ap.ssid.size(), "Network%d", i);
            [[maybe_unused]] const bool added = result.add(ap);
        }

        CHECK(result.count == 5);
        CHECK(strcmp(result.networks[0].ssid.data(), "Network0") == 0);
        CHECK(strcmp(result.networks[4].ssid.data(), "Network4") == 0);
    }

    SUBCASE("add at capacity") {
        ScanResult result;

        // Fill to capacity
        for (size_t i = 0; i < MAX_SCAN_RESULTS; i++) {
            APInfo ap;
            std::snprintf(ap.ssid.data(), ap.ssid.size(), "Network%zu", i);
            bool added = result.add(ap);
            CHECK(added);
        }

        CHECK(result.count == MAX_SCAN_RESULTS);
        CHECK(result.is_full());

        // Try to add one more
        APInfo extra;
        std::strcpy(extra.ssid.data(), "Overflow");
        bool added = result.add(extra);
        CHECK_FALSE(added);
        CHECK(result.count == MAX_SCAN_RESULTS);
    }

    SUBCASE("is_full") {
        ScanResult result;
        CHECK_FALSE(result.is_full());

        for (size_t i = 0; i < MAX_SCAN_RESULTS; i++) {
            APInfo ap;
            [[maybe_unused]] const bool added = result.add(ap);
        }

        CHECK(result.is_full());
    }
}

// =============================================================================
// Constants tests
// =============================================================================

TEST_CASE("Constants") {
    CHECK(MAX_SSID_LEN == 32u);
    CHECK(BSSID_LEN == 6u);
    CHECK(MAX_SCAN_RESULTS == 32u);
}
