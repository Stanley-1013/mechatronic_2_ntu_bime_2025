#include "rf_receiver.h"
#include <SPI.h>
#include <RF24.h>

// RF24 物件
static RF24 radio(RF_CE_PIN, RF_CSN_PIN);

// 接收管道位址（與遠距端發送位址相同）
static const uint8_t rx_addr[5] = {'M','E','C','H','1'};

bool rf_receiver_init(void) {
    if (!radio.begin()) {
        return false;
    }

    // 設定參數（與遠距端相同）
    radio.setChannel(RF_CHANNEL);
    radio.setDataRate(RF24_250KBPS);
    radio.setPALevel(RF24_PA_LOW);
    radio.setPayloadSize(32);
    radio.setAutoAck(true);
    radio.setCRCLength(RF24_CRC_16);

    // 開啟接收管道
    radio.openReadingPipe(1, rx_addr);
    radio.startListening();  // RX 模式

    return true;
}

bool rf_available(void) {
    return radio.available();
}

uint8_t rf_read(void* buffer, uint8_t len) {
    if (!radio.available()) {
        return 0;
    }

    radio.read(buffer, len);
    return len;
}
