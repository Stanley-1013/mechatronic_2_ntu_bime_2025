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

// 狀態變數
static SensorPacket packet;
static Stats stats;
static unsigned long last_receive_time = 0;
static unsigned long last_stats_time = 0;

// 輸出 CSV 資料行（每筆一行，100Hz）
// 格式: seq,t_remote_ms,btn,ax1,ay1,az1,gx1,gy1,gz1,ax2,ay2,az2,gx2,gy2,gz2
void print_csv_line(const SensorPacket* p) {
    Serial.print(p->seq);
    Serial.print(',');
    Serial.print(p->timestamp);
    Serial.print(',');
    Serial.print(p->button);
    Serial.print(',');
    // MPU1
    Serial.print(p->mpu1_ax);
    Serial.print(',');
    Serial.print(p->mpu1_ay);
    Serial.print(',');
    Serial.print(p->mpu1_az);
    Serial.print(',');
    Serial.print(p->mpu1_gx);
    Serial.print(',');
    Serial.print(p->mpu1_gy);
    Serial.print(',');
    Serial.print(p->mpu1_gz);
    Serial.print(',');
    // MPU2
    Serial.print(p->mpu2_ax);
    Serial.print(',');
    Serial.print(p->mpu2_ay);
    Serial.print(',');
    Serial.print(p->mpu2_az);
    Serial.print(',');
    Serial.print(p->mpu2_gx);
    Serial.print(',');
    Serial.print(p->mpu2_gy);
    Serial.print(',');
    Serial.println(p->mpu2_gz);
}

void setup() {
    // 初始化 Serial
    Serial.begin(SERIAL_BAUD);
    // 狀態訊息以 # 開頭（解析器忽略）
    Serial.println(F("#Mechtronic Base Station v2.0"));

    // 初始化 LED
    pinMode(LED_PIN, OUTPUT);
    digitalWrite(LED_PIN, HIGH);  // 開機指示

    // 初始化 RF 接收器
    if (!rf_receiver_init()) {
        Serial.println(F("#[ERROR] RF init failed!"));
        while (1) {
            digitalWrite(LED_PIN, HIGH);
            delay(100);
            digitalWrite(LED_PIN, LOW);
            delay(100);
        }
    }
    Serial.println(F("#[OK] RF receiver ready"));

    // 初始化統計
    stats_init(&stats);

    // 輸出 CSV 標題（以 # 開頭，解析器可選擇解析或忽略）
    Serial.println(F("#seq,t_remote_ms,btn,ax1,ay1,az1,gx1,gy1,gz1,ax2,ay2,az2,gx2,gy2,gz2"));

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
            Serial.print(F("#[WARN] Bad version: "));
            Serial.println(packet.version);
        } else {
            // 更新統計
            stats_update(&stats, packet.seq);

            // 每筆都輸出 CSV（100Hz）
            print_csv_line(&packet);
        }

        digitalWrite(LED_PIN, LOW);
    }

    // 更新速率統計
    stats_update_rate(&stats);

    // 定期輸出統計（以 # 開頭）
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
