#ifndef BUTTON_H
#define BUTTON_H

#include <stdint.h>
#include <stdbool.h>

// 按鈕腳位
#define BUTTON_PIN 2

// 去抖時間 (ms)
#define DEBOUNCE_MS 20

// 初始化按鈕
void button_init(void);

// 更新按鈕狀態（每個主迴圈呼叫一次）
void button_update(void);

// 取得按鈕狀態
// 回傳: true=按下, false=未按下
bool button_is_pressed(void);

// 取得按鈕狀態位元（用於封包）
// 回傳: 0x01=按下, 0x00=未按下
uint8_t button_get_state(void);

#endif
