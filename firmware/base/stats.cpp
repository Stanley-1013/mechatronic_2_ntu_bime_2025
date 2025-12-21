#include "stats.h"
#include <Arduino.h>

void stats_init(Stats* stats) {
    stats->packets_received = 0;
    stats->packets_lost = 0;
    stats->last_seq = 0;
    stats->seq_initialized = false;
    stats->rate_start_time = millis();
    stats->rate_packet_count = 0;
    stats->packets_per_sec = 0.0f;
}

void stats_update(Stats* stats, uint16_t current_seq) {
    stats->packets_received++;
    stats->rate_packet_count++;

    if (!stats->seq_initialized) {
        // 第一個封包，初始化序號
        stats->seq_initialized = true;
    } else {
        // 檢查掉包
        uint16_t expected = stats->last_seq + 1;
        if (current_seq != expected) {
            // 計算掉失數量（處理 uint16 溢位）
            uint16_t lost;
            if (current_seq > expected) {
                // 正常情況：current > expected
                lost = current_seq - expected;
            } else {
                // 溢位情況：expected 溢位或 current 較小
                // 使用模運算處理：(current - expected) mod 65536
                lost = (uint16_t)(current_seq - expected);
            }
            stats->packets_lost += lost;
        }
    }

    stats->last_seq = current_seq;
}

void stats_update_rate(Stats* stats) {
    unsigned long now = millis();
    unsigned long elapsed = now - stats->rate_start_time;

    if (elapsed >= 1000) {  // 至少 1 秒
        stats->packets_per_sec = (float)stats->rate_packet_count * 1000.0f / elapsed;
        stats->rate_packet_count = 0;
        stats->rate_start_time = now;
    }
}

float stats_get_loss_rate(const Stats* stats) {
    uint32_t total = stats->packets_received + stats->packets_lost;
    if (total == 0) return 0.0f;
    return (float)stats->packets_lost / total;
}

void stats_print(const Stats* stats) {
    Serial.print(F("[STAT] rx="));
    Serial.print(stats->packets_received);
    Serial.print(F(" lost="));
    Serial.print(stats->packets_lost);
    Serial.print(F(" rate="));
    Serial.print(stats->packets_per_sec, 1);
    Serial.print(F("pps loss="));
    Serial.print(stats_get_loss_rate(stats) * 100.0f, 2);
    Serial.println(F("%"));
}
