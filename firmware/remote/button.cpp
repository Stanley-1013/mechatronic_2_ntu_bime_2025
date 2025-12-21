#include "button.h"
#include <Arduino.h>

// 去抖狀態
static bool current_state = false;      // 當前穩定狀態
static bool last_reading = false;       // 上次讀取值
static unsigned long last_change = 0;   // 上次變化時間

void button_init(void) {
    pinMode(BUTTON_PIN, INPUT_PULLUP);
    current_state = false;
    last_reading = digitalRead(BUTTON_PIN) == LOW;
    last_change = millis();
}

void button_update(void) {
    bool reading = (digitalRead(BUTTON_PIN) == LOW);  // LOW = 按下
    unsigned long now = millis();

    if (reading != last_reading) {
        // 狀態變化，重置計時
        last_change = now;
        last_reading = reading;
    }

    // 超過去抖時間，更新穩定狀態
    if ((now - last_change) >= DEBOUNCE_MS) {
        current_state = last_reading;
    }
}

bool button_is_pressed(void) {
    return current_state;
}

uint8_t button_get_state(void) {
    return current_state ? 0x01 : 0x00;
}
