#ifndef IMU_DRIVER_H
#define IMU_DRIVER_H

#include <stdint.h>
#include <stdbool.h>

// I2C 位址
#define MPU6050_ADDR_1 0x68  // AD0 = GND
#define MPU6050_ADDR_2 0x69  // AD0 = VCC

// MPU6050 暫存器
#define MPU6050_REG_PWR_MGMT_1   0x6B
#define MPU6050_REG_ACCEL_XOUT_H 0x3B
#define MPU6050_REG_WHO_AM_I     0x75

// 6 軸原始資料結構
typedef struct {
    int16_t ax, ay, az;  // 加速度
    int16_t gx, gy, gz;  // 陀螺儀
} IMU_RawData;

// 初始化兩顆 MPU6050
// 回傳: 0=成功, 1=MPU1失敗, 2=MPU2失敗, 3=兩個都失敗
uint8_t imu_init(void);

// 讀取單顆 MPU6050 原始資料
// addr: MPU6050_ADDR_1 或 MPU6050_ADDR_2
// data: 輸出資料指標
// 回傳: true=成功, false=I2C錯誤
bool imu_read(uint8_t addr, IMU_RawData* data);

// 讀取兩顆 MPU6050（便利函數）
// 回傳: 0=全成功, 1=MPU1失敗, 2=MPU2失敗, 3=兩個都失敗
uint8_t imu_read_both(IMU_RawData* data1, IMU_RawData* data2);

#endif
