#ifndef RF_RECEIVER_H
#define RF_RECEIVER_H

#include <stdint.h>
#include <stdbool.h>

// nRF24 腳位（與遠距端相同）
#define RF_CE_PIN   9
#define RF_CSN_PIN  10

// 無線參數（與遠距端相同）
#define RF_CHANNEL     76
#define RF_DATARATE    RF24_250KBPS
#define RF_PA_LEVEL    RF24_PA_LOW

// 初始化 nRF24L01+ (RX 模式)
// 回傳: true=成功, false=失敗
bool rf_receiver_init(void);

// 檢查是否有資料可讀
bool rf_available(void);

// 讀取封包
// buffer: 接收緩衝區指標
// len: 要讀取的長度
// 回傳: 實際讀取的長度
uint8_t rf_read(void* buffer, uint8_t len);

#endif
