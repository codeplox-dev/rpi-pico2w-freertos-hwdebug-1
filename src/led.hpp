/**
 * @file led.hpp
 * @brief LED control for Pico W onboard LED.
 *
 * The Pico W's LED is connected through the CYW43 WiFi chip,
 * requiring cyw43_arch functions rather than direct GPIO.
 */

#ifndef LED_HPP
#define LED_HPP

#include <cstdint>

namespace led {

/**
 * @brief Turn LED on (solid).
 */
void on();

/**
 * @brief Turn LED off.
 */
void off();

/**
 * @brief Start LED blinking at specified interval.
 * @param interval_ms Blink interval in milliseconds
 */
void start_blink(uint32_t interval_ms = 50);

/**
 * @brief Stop blinking and turn LED on (solid).
 */
void stop_blink();

} // namespace led

#endif // LED_HPP
