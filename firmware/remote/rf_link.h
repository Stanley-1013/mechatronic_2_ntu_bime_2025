#ifndef RF_LINK_H
#define RF_LINK_H

#include <stdint.h>
#include <stdbool.h>

// nRF24 腳位
#define RF_CE_PIN   9
#define RF_CSN_PIN  10

// 無線參數
#define RF_CHANNEL     76
#define RF_DATARATE    RF24_250KBPS
#define RF_PA_LEVEL    RF24_PA_LOW
#define RF_RETRY_DELAY 5
#define RF_RETRY_COUNT 15

// 初始化 nRF24L01+ (TX 模式)
// 回傳: true=成功, false=失敗
bool rf_init(void);

// 發送資料
// data: 資料指標
// len: 資料長度 (最大 32)
// 回傳: true=ACK收到, false=發送失敗
bool rf_send(const void* data, uint8_t len);

// 取得連續失敗次數
uint16_t rf_get_fail_count(void);

// 重置失敗計數
void rf_reset_fail_count(void);

// 重新初始化（故障復原用）
bool rf_reinit(void);

#endif
