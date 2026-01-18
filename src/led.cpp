/**
 * @file led.cpp
 * @brief LED control for Pico W.
 */

#include "led.hpp"
#include "pico/cyw43_arch.h"
#include "FreeRTOS.h"
#include "timers.h"

namespace {

TimerHandle_t blink_timer = nullptr;
bool led_state = false;

void set_led(bool state) {
    led_state = state;
    cyw43_arch_gpio_put(CYW43_WL_GPIO_LED_PIN, state);
}

void blink_tick(TimerHandle_t) {
    set_led(!led_state);
}

} // anonymous namespace

namespace led {

void on() {
    set_led(true);
}

void off() {
    set_led(false);
}

void start_blink(uint32_t interval_ms) {
    if (blink_timer) {
        xTimerStop(blink_timer, 0);
        xTimerDelete(blink_timer, 0);
    }
    blink_timer = xTimerCreate("led", pdMS_TO_TICKS(interval_ms), pdTRUE, nullptr, blink_tick);
    if (blink_timer) {
        set_led(true);
        xTimerStart(blink_timer, 0);
    }
}

void stop_blink() {
    if (blink_timer) {
        xTimerStop(blink_timer, 0);
        xTimerDelete(blink_timer, 0);
        blink_timer = nullptr;
    }
    set_led(true);  // Return to solid on
}

} // namespace led
