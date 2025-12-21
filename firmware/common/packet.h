#ifndef PACKET_H
#define PACKET_H

#include <stdint.h>

#define PROTOCOL_VERSION 0x01
#define PACKET_SIZE 32

// 封包結構 (32 bytes，無填充)
typedef struct __attribute__((packed)) {
    uint8_t  version;        // Byte 0: 協議版本
    uint16_t seq;            // Bytes 1-2: 序號
    uint32_t timestamp;      // Bytes 3-6: millis()
    uint8_t  button;         // Byte 7: 按鈕狀態
    int16_t  mpu1_ax;        // Bytes 8-9
    int16_t  mpu1_ay;        // Bytes 10-11
    int16_t  mpu1_az;        // Bytes 12-13
    int16_t  mpu1_gx;        // Bytes 14-15
    int16_t  mpu1_gy;        // Bytes 16-17
    int16_t  mpu1_gz;        // Bytes 18-19
    int16_t  mpu2_ax;        // Bytes 20-21
    int16_t  mpu2_ay;        // Bytes 22-23
    int16_t  mpu2_az;        // Bytes 24-25
    int16_t  mpu2_gx;        // Bytes 26-27
    int16_t  mpu2_gy;        // Bytes 28-29
    int16_t  mpu2_gz;        // Bytes 30-31
} SensorPacket;

// 編譯時檢查封包大小 (使用 C++ 相容語法)
#ifdef __cplusplus
static_assert(sizeof(SensorPacket) == PACKET_SIZE, "Packet size must be 32 bytes");
#else
_Static_assert(sizeof(SensorPacket) == PACKET_SIZE, "Packet size must be 32 bytes");
#endif

#endif // PACKET_H
