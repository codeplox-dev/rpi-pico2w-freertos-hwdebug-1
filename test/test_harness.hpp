/**
 * @file test_harness.hpp
 * @brief Minimal test harness for unit and integration tests.
 */

#ifndef TEST_HARNESS_HPP
#define TEST_HARNESS_HPP

#include <cstdio>
#include <cstring>
#include <cstdlib>

namespace test {

inline int g_tests_run = 0;
inline int g_tests_passed = 0;
inline int g_tests_failed = 0;

inline void reset() {
    g_tests_run = 0;
    g_tests_passed = 0;
    g_tests_failed = 0;
}

inline void pass(const char* name) {
    g_tests_run++;
    g_tests_passed++;
    printf("  [PASS] %s\n", name);
}

inline void fail(const char* name, const char* file, int line, const char* msg) {
    g_tests_run++;
    g_tests_failed++;
    printf("  [FAIL] %s\n", name);
    printf("         %s:%d: %s\n", file, line, msg);
}

inline int summary() {
    printf("\n=== Test Summary ===\n");
    printf("Passed: %d/%d\n", g_tests_passed, g_tests_run);
    if (g_tests_failed > 0) {
        printf("Failed: %d\n", g_tests_failed);
        return 1;
    }
    printf("All tests passed!\n");
    return 0;
}

} // namespace test

#define TEST(name) \
    void test_##name(); \
    struct test_##name##_register { \
        test_##name##_register() { test_##name(); } \
    } test_##name##_instance; \
    void test_##name()

#define RUN_TEST(name) test_##name()

#define ASSERT_TRUE(cond) \
    do { \
        if (!(cond)) { \
            test::fail(__func__, __FILE__, __LINE__, #cond " is false"); \
            return; \
        } \
    } while(0)

#define ASSERT_FALSE(cond) \
    do { \
        if (cond) { \
            test::fail(__func__, __FILE__, __LINE__, #cond " is true"); \
            return; \
        } \
    } while(0)

#define ASSERT_EQ(a, b) \
    do { \
        if ((a) != (b)) { \
            test::fail(__func__, __FILE__, __LINE__, #a " != " #b); \
            return; \
        } \
    } while(0)

#define ASSERT_NE(a, b) \
    do { \
        if ((a) == (b)) { \
            test::fail(__func__, __FILE__, __LINE__, #a " == " #b); \
            return; \
        } \
    } while(0)

#define ASSERT_STREQ(a, b) \
    do { \
        if (std::strcmp((a), (b)) != 0) { \
            test::fail(__func__, __FILE__, __LINE__, #a " != " #b); \
            return; \
        } \
    } while(0)

#define TEST_PASS() test::pass(__func__)

#endif // TEST_HARNESS_HPP
