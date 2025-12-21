/*
 * Mechtronic 2 - Base Station (Arduino Uno)
 *
 * 接收無線資料並透過 Serial 輸出至 PC
 */

#include "../common/packet.h"
#include "rf_receiver.h"
#include "stats.h"

// 配置參數
#define SERIAL_BAUD     115200
#define LED_PIN         3        // 狀態 LED
#define STATS_INTERVAL  5000     // 統計輸出間隔 (ms)
#define NO_DATA_TIMEOUT 1000     // 無資料超時 (ms)
#define PRINT_INTERVAL  500      // Serial 輸出間隔 (ms)，設 0 = 每筆都輸出

// 狀態變數
static SensorPacket packet;
static Stats stats;
static unsigned long last_receive_time = 0;
static unsigned long last_stats_time = 0;
static unsigned long last_print_time = 0;

// 輸出 CSV 標題
void print_csv_header() {
    Serial.println(F("seq,timestamp,btn,m1ax,m1ay,m1az,m1gx,m1gy,m1gz,m2ax,m2ay,m2az,m2gx,m2gy,m2gz"));
}

// 輸出封包資料（易讀格式）
void print_packet_live(const SensorPacket* p) {
    Serial.println(F("--------------------"));
    Serial.print(F("seq="));
    Serial.print(p->seq);
    Serial.print(F("  btn="));
    Serial.println(p->button);

    // MPU1 加速度 (轉換成 g，±2g 量程)
    Serial.print(F("M1 A: "));
    Serial.print(p->mpu1_ax / 16384.0, 2);
    Serial.print(F("g, "));
    Serial.print(p->mpu1_ay / 16384.0, 2);
    Serial.print(F("g, "));
    Serial.print(p->mpu1_az / 16384.0, 2);
    Serial.println(F("g"));

    // MPU2 加速度
    Serial.print(F("M2 A: "));
    Serial.print(p->mpu2_ax / 16384.0, 2);
    Serial.print(F("g, "));
    Serial.print(p->mpu2_ay / 16384.0, 2);
    Serial.print(F("g, "));
    Serial.print(p->mpu2_az / 16384.0, 2);
    Serial.println(F("g"));
}

void setup() {
    // 初始化 Serial
    Serial.begin(SERIAL_BAUD);
    Serial.println(F("Mechtronic Base Station v1.0"));

    // 初始化 LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH);  // 開機指示

    // 初始化 RF 接收器
    if (!rf_receiver_init()) {
        Serial.println(F("[ERROR] RF init failed!"));
        while (1) {
            digitalWrite(LED_PIN, HIGH);
            delay(100);
            digitalWrite(LED_PIN, LOW);
            delay(100);
        }
    }
    Serial.println(F("[OK] RF receiver ready"));

    // 初始化統計
    stats_init(&stats);

    // 輸出 CSV 標題
    print_csv_header();

    digitalWrite(LED_PIN, LOW);
    last_receive_time = millis();
    last_stats_time = millis();
}

void loop() {
    unsigned long now = millis();

    // 檢查是否有資料
    if (rf_available()) {
        // 讀取封包
        rf_read(&packet, sizeof(SensorPacket));
        last_receive_time = now;

        // LED 快速閃爍表示收到資料
        digitalWrite(LED_PIN, HIGH);

        // 驗證協議版本
        if (packet.version != PROTOCOL_VERSION) {
            Serial.print(F("[WARN] Bad version: "));
            Serial.println(packet.version);
        } else {
            // 更新統計
            stats_update(&stats, packet.seq);

            // 降頻輸出（每 100ms 更新一次顯示）
            if (now - last_print_time >= PRINT_INTERVAL) {
                print_packet_live(&packet);
                last_print_time = now;
            }
        }

        digitalWrite(LED_PIN, LOW);
    }

    // 更新速率統計
    stats_update_rate(&stats);

    // 定期輸出統計
    if (now - last_stats_time >= STATS_INTERVAL) {
        stats_print(&stats);
        last_stats_time = now;
    }

    // 無資料超時指示
    if (now - last_receive_time > NO_DATA_TIMEOUT) {
        // LED 常亮表示無資料
        digitalWrite(LED_PIN, HIGH);
    }
}
