#ifndef STATS_H
#define STATS_H

#include <stdint.h>
#include <stdbool.h>

// 統計數據結構
typedef struct {
    uint32_t packets_received;  // 收到封包總數
    uint32_t packets_lost;      // 掉包總數
    uint16_t last_seq;          // 上一個序號
    bool     seq_initialized;   // 序號是否已初始化

    // 速率計算用
    uint32_t rate_start_time;   // 速率計算起始時間
    uint32_t rate_packet_count; // 該時段封包數
    float    packets_per_sec;   // 每秒封包數
} Stats;

// 初始化統計
void stats_init(Stats* stats);

// 更新統計（每收到一個封包呼叫）
// current_seq: 當前封包的序號
void stats_update(Stats* stats, uint16_t current_seq);

// 更新速率統計（每秒呼叫一次）
void stats_update_rate(Stats* stats);

// 取得掉包率 (0.0 ~ 1.0)
float stats_get_loss_rate(const Stats* stats);

// 輸出統計到 Serial
void stats_print(const Stats* stats);

#endif
