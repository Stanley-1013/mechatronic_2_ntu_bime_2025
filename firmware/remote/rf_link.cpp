#include "rf_link.h"
#include <SPI.h>
#include <RF24.h>

// RF24 物件
static RF24 radio(RF_CE_PIN, RF_CSN_PIN);

// 發送管道位址 (5 bytes)
static const uint8_t tx_addr[5] = {'M','E','C','H','1'};

// 失敗計數
static uint16_t fail_count = 0;

bool rf_init(void) {
    if (!radio.begin()) {
        return false;
    }

    // 設定參數
    radio.setChannel(RF_CHANNEL);
    radio.setDataRate(RF24_250KBPS);
    radio.setPALevel(RF24_PA_LOW);
    radio.setRetries(RF_RETRY_DELAY, RF_RETRY_COUNT);
    radio.setPayloadSize(32);
    radio.setAutoAck(true);
    radio.setCRCLength(RF24_CRC_16);

    // 開啟發送管道
    radio.openWritingPipe(tx_addr);
    radio.stopListening();  // TX 模式

    fail_count = 0;
    return true;
}

bool rf_send(const void* data, uint8_t len) {
    bool ok = radio.write(data, len);

    if (!ok) {
        fail_count++;
    } else {
        fail_count = 0;  // 成功則重置
    }

    return ok;
}

uint16_t rf_get_fail_count(void) {
    return fail_count;
}

void rf_reset_fail_count(void) {
    fail_count = 0;
}

bool rf_reinit(void) {
    radio.powerDown();
    delay(10);
    return rf_init();
}
