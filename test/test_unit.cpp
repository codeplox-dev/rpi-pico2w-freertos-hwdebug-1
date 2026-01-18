/**
 * @file test_unit.cpp
 * @brief Unit tests for pure logic (no hardware dependencies).
 */

#include "test_harness.hpp"
#include "../src/scan_msg.hpp"

// =============================================================================
// AuthMode conversion tests
// =============================================================================

void test_auth_mode_to_string_open() {
    ASSERT_STREQ(auth_mode_to_string(AuthMode::OPEN), "OPEN");
    TEST_PASS();
}

void test_auth_mode_to_string_wep() {
    ASSERT_STREQ(auth_mode_to_string(AuthMode::WEP), "WEP");
    TEST_PASS();
}

void test_auth_mode_to_string_wpa() {
    ASSERT_STREQ(auth_mode_to_string(AuthMode::WPA_PSK), "WPA");
    TEST_PASS();
}

void test_auth_mode_to_string_wpa2() {
    ASSERT_STREQ(auth_mode_to_string(AuthMode::WPA2_PSK), "WPA2");
    TEST_PASS();
}

void test_auth_mode_to_string_wpa_wpa2() {
    ASSERT_STREQ(auth_mode_to_string(AuthMode::WPA_WPA2_PSK), "WPA/WPA2");
    TEST_PASS();
}

void test_auth_mode_to_string_wpa3() {
    ASSERT_STREQ(auth_mode_to_string(AuthMode::WPA3_PSK), "WPA3");
    TEST_PASS();
}

void test_auth_mode_to_string_unknown() {
    ASSERT_STREQ(auth_mode_to_string(AuthMode::UNKNOWN), "???");
    TEST_PASS();
}

// =============================================================================
// CYW43 auth bitmask conversion tests
// =============================================================================

void test_auth_from_cyw43_open() {
    ASSERT_EQ(auth_mode_from_cyw43(0), AuthMode::OPEN);
    TEST_PASS();
}

void test_auth_from_cyw43_wep() {
    ASSERT_EQ(auth_mode_from_cyw43(1), AuthMode::WEP);
    TEST_PASS();
}

void test_auth_from_cyw43_wpa() {
    ASSERT_EQ(auth_mode_from_cyw43(2), AuthMode::WPA_PSK);
    TEST_PASS();
}

void test_auth_from_cyw43_wpa2() {
    ASSERT_EQ(auth_mode_from_cyw43(4), AuthMode::WPA2_PSK);
    TEST_PASS();
}

void test_auth_from_cyw43_wpa_wpa2() {
    ASSERT_EQ(auth_mode_from_cyw43(6), AuthMode::WPA_WPA2_PSK);
    TEST_PASS();
}

void test_auth_from_cyw43_unknown() {
    // Bit 3 set (8) is undefined, should return UNKNOWN
    ASSERT_EQ(auth_mode_from_cyw43(8), AuthMode::UNKNOWN);
    TEST_PASS();
}

// =============================================================================
// APInfo tests
// =============================================================================

void test_apinfo_default_constructor() {
    APInfo ap;
    ASSERT_EQ(ap.ssid[0], '\0');
    ASSERT_EQ(ap.rssi, 0);
    ASSERT_EQ(ap.channel, 0);
    ASSERT_EQ(ap.auth, AuthMode::UNKNOWN);
    TEST_PASS();
}

void test_apinfo_format_bssid() {
    APInfo ap;
    ap.bssid[0] = 0xAA;
    ap.bssid[1] = 0xBB;
    ap.bssid[2] = 0xCC;
    ap.bssid[3] = 0xDD;
    ap.bssid[4] = 0xEE;
    ap.bssid[5] = 0xFF;

    char buf[18];
    ap.format_bssid(buf, sizeof(buf));
    ASSERT_STREQ(buf, "AA:BB:CC:DD:EE:FF");
    TEST_PASS();
}

void test_apinfo_format_bssid_zeros() {
    APInfo ap;  // BSSID initialized to zeros
    char buf[18];
    ap.format_bssid(buf, sizeof(buf));
    ASSERT_STREQ(buf, "00:00:00:00:00:00");
    TEST_PASS();
}

// =============================================================================
// ScanResult tests
// =============================================================================

void test_scanresult_default_constructor() {
    ScanResult result;
    ASSERT_FALSE(result.success);
    ASSERT_EQ(result.error_code, 0);
    ASSERT_EQ(result.count, 0);
    TEST_PASS();
}

void test_scanresult_reset() {
    ScanResult result;
    result.success = true;
    result.error_code = 42;
    result.count = 10;

    result.reset();

    ASSERT_FALSE(result.success);
    ASSERT_EQ(result.error_code, 0);
    ASSERT_EQ(result.count, 0);
    TEST_PASS();
}

void test_scanresult_add_single() {
    ScanResult result;
    APInfo ap;
    std::strcpy(ap.ssid, "TestNetwork");

    bool added = result.add(ap);

    ASSERT_TRUE(added);
    ASSERT_EQ(result.count, 1);
    ASSERT_STREQ(result.networks[0].ssid, "TestNetwork");
    TEST_PASS();
}

void test_scanresult_add_multiple() {
    ScanResult result;

    for (int i = 0; i < 5; i++) {
        APInfo ap;
        std::snprintf(ap.ssid, MAX_SSID_LEN, "Network%d", i);
        result.add(ap);
    }

    ASSERT_EQ(result.count, 5);
    ASSERT_STREQ(result.networks[0].ssid, "Network0");
    ASSERT_STREQ(result.networks[4].ssid, "Network4");
    TEST_PASS();
}

void test_scanresult_add_at_capacity() {
    ScanResult result;

    // Fill to capacity
    for (size_t i = 0; i < MAX_SCAN_RESULTS; i++) {
        APInfo ap;
        std::snprintf(ap.ssid, MAX_SSID_LEN, "Network%zu", i);
        bool added = result.add(ap);
        ASSERT_TRUE(added);
    }

    ASSERT_EQ(result.count, MAX_SCAN_RESULTS);
    ASSERT_TRUE(result.is_full());

    // Try to add one more
    APInfo extra;
    std::strcpy(extra.ssid, "Overflow");
    bool added = result.add(extra);
    ASSERT_FALSE(added);
    ASSERT_EQ(result.count, MAX_SCAN_RESULTS);
    TEST_PASS();
}

void test_scanresult_is_full() {
    ScanResult result;
    ASSERT_FALSE(result.is_full());

    for (size_t i = 0; i < MAX_SCAN_RESULTS; i++) {
        APInfo ap;
        result.add(ap);
    }

    ASSERT_TRUE(result.is_full());
    TEST_PASS();
}

// =============================================================================
// Constants tests
// =============================================================================

void test_constants() {
    ASSERT_EQ(MAX_SSID_LEN, 32u);
    ASSERT_EQ(BSSID_LEN, 6u);
    ASSERT_EQ(MAX_SCAN_RESULTS, 32u);
    TEST_PASS();
}

// =============================================================================
// Main
// =============================================================================

int main() {
    printf("=== Unit Tests ===\n\n");

    printf("AuthMode string conversion:\n");
    test_auth_mode_to_string_open();
    test_auth_mode_to_string_wep();
    test_auth_mode_to_string_wpa();
    test_auth_mode_to_string_wpa2();
    test_auth_mode_to_string_wpa_wpa2();
    test_auth_mode_to_string_wpa3();
    test_auth_mode_to_string_unknown();

    printf("\nCYW43 auth bitmask conversion:\n");
    test_auth_from_cyw43_open();
    test_auth_from_cyw43_wep();
    test_auth_from_cyw43_wpa();
    test_auth_from_cyw43_wpa2();
    test_auth_from_cyw43_wpa_wpa2();
    test_auth_from_cyw43_unknown();

    printf("\nAPInfo:\n");
    test_apinfo_default_constructor();
    test_apinfo_format_bssid();
    test_apinfo_format_bssid_zeros();

    printf("\nScanResult:\n");
    test_scanresult_default_constructor();
    test_scanresult_reset();
    test_scanresult_add_single();
    test_scanresult_add_multiple();
    test_scanresult_add_at_capacity();
    test_scanresult_is_full();

    printf("\nConstants:\n");
    test_constants();

    return test::summary();
}
