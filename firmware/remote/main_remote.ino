/*
 * Mechtronic 2 - Remote Unit (Arduino Nano)
 *
 * 雙 MPU6050 + nRF24L01+ 無線感測系統
 * 職責：採集原始資料並傳輸至桌面端
 */

#include "../common/packet.h"
#include "imu_driver.h"
#include "rf_link.h"
#include "button.h"

// ========== 配置參數 ==========
#define SAMPLE_INTERVAL_MS  10    // 採樣間隔 (100Hz)
#define RF_FAIL_THRESHOLD   20    // RF 連續失敗門檻
#define LED_PIN             LED_BUILTIN  // 狀態 LED (Nano D13)

// ========== 狀態變數 ==========
static SensorPacket packet;
static uint16_t seq_counter = 0;
static unsigned long last_sample_time = 0;
static bool system_ok = false;

// ========== 錯誤 LED 閃爍碼 ==========
// 1 閃 = MPU1 失敗
// 2 閃 = MPU2 失敗
// 3 閃 = RF 失敗
void error_blink(uint8_t code) {
    for (uint8_t i = 0; i < code; i++) {
        digitalWrite(LED_PIN, HIGH);
        delay(200);
        digitalWrite(LED_PIN, LOW);
        delay(200);
    }
    delay(1000);
}

// ========== Setup ==========
void setup() {
    // 初始化 LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH);  // 開機指示

    // 可選：除錯 Serial
    // Serial.begin(115200);
    // Serial.println(F("Mechtronic Remote Starting..."));

    // 初始化 IMU
    uint8_t imu_status = imu_init();
    if (imu_status != 0) {
        // IMU 初始化失敗
        while (1) {
            error_blink(imu_status);  // 1=MPU1, 2=MPU2, 3=both
        }
    }

    // 初始化 RF
    if (!rf_init()) {
        while (1) {
            error_blink(3);  // RF 失敗
        }
    }

    // 初始化按鈕
    button_init();

    // 初始化封包固定欄位
    packet.version = PROTOCOL_VERSION;

    // 初始化完成
    digitalWrite(LED_PIN, LOW);
    system_ok = true;
    last_sample_time = millis();
}

// ========== Main Loop ==========
void loop() {
    unsigned long now = millis();

    // 更新按鈕狀態（每次迴圈都要呼叫）
    button_update();

    // 檢查採樣時間
    if (now - last_sample_time < SAMPLE_INTERVAL_MS) {
        return;  // 尚未到採樣時間
    }
    last_sample_time = now;

    // 讀取雙 IMU
    IMU_RawData imu1, imu2;
    uint8_t imu_status = imu_read_both(&imu1, &imu2);

    // P0 修正：IMU 讀取錯誤處理
    if (imu_status != 0) {
        // 跳過此次發送，避免傳輸無效資料
        digitalWrite(LED_PIN, HIGH);  // LED 指示錯誤
        return;
    }

    // 填充封包
    packet.seq = seq_counter++;
    packet.timestamp = now;
    packet.button = button_get_state();

    // MPU1 資料
    packet.mpu1_ax = imu1.ax;
    packet.mpu1_ay = imu1.ay;
    packet.mpu1_az = imu1.az;
    packet.mpu1_gx = imu1.gx;
    packet.mpu1_gy = imu1.gy;
    packet.mpu1_gz = imu1.gz;

    // MPU2 資料
    packet.mpu2_ax = imu2.ax;
    packet.mpu2_ay = imu2.ay;
    packet.mpu2_az = imu2.az;
    packet.mpu2_gx = imu2.gx;
    packet.mpu2_gy = imu2.gy;
    packet.mpu2_gz = imu2.gz;

    // 發送封包
    bool sent = rf_send(&packet, sizeof(SensorPacket));

    // LED 指示發送狀態
    digitalWrite(LED_PIN, sent ? LOW : HIGH);

    // 檢查 RF 連續失敗
    if (rf_get_fail_count() >= RF_FAIL_THRESHOLD) {
        // P0 修正：檢查重新初始化回傳值
        if (!rf_reinit()) {
            // RF 無法恢復，進入錯誤狀態
            while (1) {
                error_blink(3);
            }
        }
    }
}
