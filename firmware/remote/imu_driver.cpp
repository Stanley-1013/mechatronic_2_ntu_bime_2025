#include "imu_driver.h"
#include <Wire.h>

// 內部函數：寫入暫存器
static bool write_reg(uint8_t addr, uint8_t reg, uint8_t value) {
    Wire.beginTransmission(addr);
    Wire.write(reg);
    Wire.write(value);
    return (Wire.endTransmission() == 0);
}

// 內部函數：檢查 MPU6050 存在
static bool check_device(uint8_t addr) {
    Wire.beginTransmission(addr);
    Wire.write(MPU6050_REG_WHO_AM_I);
    if (Wire.endTransmission(false) != 0) return false;

    Wire.requestFrom(addr, (uint8_t)1);
    if (Wire.available() < 1) return false;

    uint8_t who = Wire.read();
    return (who == 0x68);  // MPU6050 WHO_AM_I 回傳 0x68
}

// 初始化單顆 MPU6050
static bool init_single(uint8_t addr) {
    if (!check_device(addr)) return false;

    // 喚醒 MPU6050 (清除 sleep bit)
    if (!write_reg(addr, MPU6050_REG_PWR_MGMT_1, 0x00)) return false;

    // P1 修正：明確設定量程（不依賴預設值）
    // 設定陀螺儀量程 ±250°/s (GYRO_CONFIG = 0x00)
    if (!write_reg(addr, 0x1B, 0x00)) return false;

    // 設定加速度量程 ±2g (ACCEL_CONFIG = 0x00)
    if (!write_reg(addr, 0x1C, 0x00)) return false;

    return true;
}

uint8_t imu_init(void) {
    Wire.begin();
    Wire.setClock(400000);  // 400kHz I2C

    uint8_t result = 0;
    if (!init_single(MPU6050_ADDR_1)) result |= 1;
    if (!init_single(MPU6050_ADDR_2)) result |= 2;

    return result;
}

bool imu_read(uint8_t addr, IMU_RawData* data) {
    Wire.beginTransmission(addr);
    Wire.write(MPU6050_REG_ACCEL_XOUT_H);
    if (Wire.endTransmission(false) != 0) return false;

    // 讀取 14 bytes: AX(2) + AY(2) + AZ(2) + TEMP(2) + GX(2) + GY(2) + GZ(2)
    Wire.requestFrom(addr, (uint8_t)14);
    if (Wire.available() < 14) return false;

    // 注意：MPU6050 是 Big-Endian
    data->ax = (Wire.read() << 8) | Wire.read();
    data->ay = (Wire.read() << 8) | Wire.read();
    data->az = (Wire.read() << 8) | Wire.read();
    Wire.read(); Wire.read();  // 跳過溫度
    data->gx = (Wire.read() << 8) | Wire.read();
    data->gy = (Wire.read() << 8) | Wire.read();
    data->gz = (Wire.read() << 8) | Wire.read();

    return true;
}

uint8_t imu_read_both(IMU_RawData* data1, IMU_RawData* data2) {
    uint8_t result = 0;
    if (!imu_read(MPU6050_ADDR_1, data1)) result |= 1;
    if (!imu_read(MPU6050_ADDR_2, data2)) result |= 2;
    return result;
}
