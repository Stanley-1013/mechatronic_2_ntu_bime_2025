# 封包格式規格文件 (PACKET_SPEC.md)

## 設計原則

1. **Nano 端職責最小化**：只負責採集原始資料並傳輸
2. **資料處理後置**：校正、濾波、格式轉換交給 Uno 端和筆電處理
3. **封包大小限制**：必須 ≤ 32 bytes (nRF24L01+ 單次傳輸限制)
4. **可靠性保證**：依賴 nRF24L01+ 硬體 CRC_16 校驗，包含序號以偵測掉包

## 封包結構總覽

**封包總大小**: 32 bytes

| 欄位 | 類型 | 大小 | 位元組偏移 | 說明 |
|------|------|------|------------|------|
| protocol_version | uint8 | 1 byte | 0 | 協議版本號 |
| seq | uint16 | 2 bytes | 1-2 | 封包序號 |
| timestamp | uint32 | 4 bytes | 3-6 | 遠距端時間戳記 (millis) |
| button_state | uint8 | 1 byte | 7 | 按鈕狀態 |
| mpu1_ax | int16 | 2 bytes | 8-9 | MPU1 加速度 X 軸原始值 |
| mpu1_ay | int16 | 2 bytes | 10-11 | MPU1 加速度 Y 軸原始值 |
| mpu1_az | int16 | 2 bytes | 12-13 | MPU1 加速度 Z 軸原始值 |
| mpu1_gx | int16 | 2 bytes | 14-15 | MPU1 陀螺儀 X 軸原始值 |
| mpu1_gy | int16 | 2 bytes | 16-17 | MPU1 陀螺儀 Y 軸原始值 |
| mpu1_gz | int16 | 2 bytes | 18-19 | MPU1 陀螺儀 Z 軸原始值 |
| mpu2_ax | int16 | 2 bytes | 20-21 | MPU2 加速度 X 軸原始值 |
| mpu2_ay | int16 | 2 bytes | 22-23 | MPU2 加速度 Y 軸原始值 |
| mpu2_az | int16 | 2 bytes | 24-25 | MPU2 加速度 Z 軸原始值 |
| mpu2_gx | int16 | 2 bytes | 26-27 | MPU2 陀螺儀 X 軸原始值 |
| mpu2_gy | int16 | 2 bytes | 28-29 | MPU2 陀螺儀 Y 軸原始值 |
| mpu2_gz | int16 | 2 bytes | 30-31 | MPU2 陀螺儀 Z 軸原始值 |

**總計**: 32 bytes (剛好符合 nRF24L01+ 限制)

## 錯誤檢測機制

### 硬體 CRC 校驗
- nRF24L01+ 內建 **CRC_16** 硬體校驗
- 模組自動計算並驗證 CRC，錯誤封包會被自動丟棄
- 因此封包結構**不需要**額外的軟體 checksum 欄位
- 配置方式：在初始化時啟用 `radio.setCRCLength(RF24_CRC_16)`

### 軟體層級掉包偵測
- 使用 `seq` 欄位偵測封包遺失
- 接收端比對連續封包序號，若不連續則記錄掉包

## 欄位詳細說明

### 1. protocol_version (uint8)
- **位置**: Byte 0
- **值**: 0x01 (當前版本)
- **用途**: 區分不同版本的封包格式，確保相容性
- **範圍**: 0-255

### 2. seq (uint16)
- **位置**: Bytes 1-2
- **值**: 0-65535 循環計數
- **用途**:
  - 封包序號，用於偵測掉包
  - 每發送一個封包，序號自增 1
  - 達到 65535 後回到 0
- **掉包偵測**: 接收端比對連續封包的 seq，若不連續則表示掉包

### 3. timestamp (uint32)
- **位置**: Bytes 3-6
- **值**: Arduino `millis()` 返回值
- **用途**:
  - 記錄遠距端（Nano）的時間戳記
  - 用於計算延遲、同步時間軸
  - 約 49.7 天後會溢位重置為 0
- **範圍**: 0-4,294,967,295 (毫秒)

### 4. button_state (uint8)
- **位置**: Byte 7
- **值**: 位元遮罩
  - Bit 0: 按鈕 1 狀態 (0=未按下, 1=按下)
  - Bit 1: 按鈕 2 狀態
  - Bit 2-7: 保留 (未來擴充)
- **範例**:
  - `0x00`: 無按鈕按下
  - `0x01`: 按鈕 1 按下
  - `0x03`: 按鈕 1 和按鈕 2 同時按下

### 5-10. MPU1 原始值 (int16 × 6)
- **位置**: Bytes 8-19 (共 12 bytes)
- **資料格式**: 16-bit 有號整數
- **來源**: MPU6050 暫存器直接讀取的原始值
- **比例尺設定**:
  - 加速度 (ax, ay, az): ±2g 範圍 (LSB Sensitivity = 16384 LSB/g)
  - 陀螺儀 (gx, gy, gz): ±250°/s 範圍 (LSB Sensitivity = 131 LSB/°/s)
- **資料處理**:
  - **不在 Nano 端進行校正或濾波**
  - 原始值傳輸到 Uno 端後再進行處理
  - 保持 Nano 端程式簡潔高效

### 11-16. MPU2 原始值 (int16 × 6)
- **位置**: Bytes 20-31 (共 12 bytes)
- **說明**: 與 MPU1 相同，來自第二個 MPU6050 感測器

## 位元組序 (Endianness)

**採用 Little-Endian (小端序)**

- Arduino 平台原生使用 Little-Endian
- 多位元組資料的低位元組存放在低位址

### 範例
假設 `seq = 0x1234` (十進位 4660):
```
Byte 1: 0x34 (低位元組)
Byte 2: 0x12 (高位元組)
```

### C/C++ 結構體定義

**建議使用共享標頭檔**: `firmware/common/packet.h`

```c
#include "common/packet.h"

// 使用 SensorPacket 結構體
SensorPacket packet;
packet.version = PROTOCOL_VERSION;
packet.seq = seq_counter++;
packet.timestamp = millis();
// ... 填充其他欄位
```

完整定義參考 `/home/han/claude_project/mechtronic_2/firmware/common/packet.h`。

## 版本相容性規則

### 版本號定義
- **主版本變更** (0x01 → 0x10): 不相容變更，需更新所有端點
- **次版本變更** (0x01 → 0x02): 向後相容的新增功能

### 相容性指引

#### v1.0 (protocol_version = 0x01) - 當前版本
- 基礎封包格式
- 2 個 MPU6050 感測器
- 基礎按鈕輸入
- 依賴 nRF24 硬體 CRC_16 校驗

#### 未來版本建議
如需新增欄位（例如第三個感測器），建議：
1. **選項 A**: 增加 protocol_version，定義新的 32-byte 格式
2. **選項 B**: 使用不同的封包類型欄位（需重新設計結構）

### 接收端版本檢查
```c
void handle_packet(SensorPacket* packet) {
    if (packet->version != PROTOCOL_VERSION) {
        // 版本不符，丟棄或記錄錯誤
        return;
    }
    // 處理封包...
}
```

## 封包處理流程

### Nano 端（發送端）
1. 讀取兩個 MPU6050 的原始資料（6 個 int16 值）
2. 讀取按鈕狀態
3. 填充封包欄位：
   - `version = PROTOCOL_VERSION`
   - `seq++` (自增序號)
   - `timestamp = millis()`
   - `button = digital_read(...)`
   - `mpu1_*`, `mpu2_*` (原始值直接填入)
4. 透過 nRF24L01+ 發送 32 bytes（硬體自動附加 CRC）

### Uno 端（接收端）
1. 接收 32 bytes 封包（nRF24 硬體已驗證 CRC）
2. 驗證 protocol_version
3. 檢查 seq 偵測掉包
4. 提取原始 MPU 資料進行後續處理：
   - 應用校正參數（offset、scale）
   - 低通濾波
   - 座標系轉換
5. 透過 Serial 傳送處理後的資料到筆電

## 錯誤處理

### 掉包偵測
```c
static uint16_t last_seq = 0xFFFF;
uint16_t current_seq = packet.seq;

if (last_seq != 0xFFFF) {
    uint16_t expected = (last_seq + 1) % 65536;
    if (current_seq != expected) {
        // 封包掉失
        int lost = (current_seq - expected + 65536) % 65536;
        log_packet_loss(lost);
    }
}
last_seq = current_seq;
```

### CRC 錯誤
- nRF24 硬體自動丟棄 CRC 錯誤的封包
- 應用程式層不會收到損壞的封包
- 可透過 nRF24 狀態暫存器讀取統計資訊

### 版本不符
- 記錄錯誤
- 可選：進入安全模式，停止處理

## 效能考量

### 發送頻率
- **建議**: 50-100 Hz (10-20ms 間隔)
- **最大**: 受 nRF24L01+ 和 I2C 讀取速度限制
- **平衡**: 資料即時性 vs. 掉包率

### 資料處理流程
```
[Nano] 採集原始資料 → 封包 → nRF24 發送 (+ 硬體 CRC)
   ↓
[Uno] nRF24 接收 (驗證 CRC) → 檢查版本/seq → 校正/濾波 → Serial 輸出
   ↓
[筆電] Serial 接收 → 資料分析/可視化
```

## 附錄：範例封包 (十六進位)

```
01 2F 00 A0 86 01 00 42
10 20 30 40 50 60 70 80
90 A0 B0 C0 11 21 31 41
51 61 71 81 91 A1 B1 C1

解析：
- protocol_version: 0x01
- seq: 0x002F (47)
- timestamp: 0x000186A0 (100000 ms)
- button_state: 0x42 (按鈕 2 按下)
- mpu1_ax: 0x2010 (8208)
- mpu1_ay: 0x4030 (16432)
- mpu1_az: 0x6050 (24656)
- mpu1_gx: 0x8070 (-32656)
- mpu1_gy: 0xA090 (-24432)
- mpu1_gz: 0xC0B0 (-16208)
- mpu2_ax: 0x2111 (8465)
- mpu2_ay: 0x4131 (16689)
- mpu2_az: 0x6151 (24913)
- mpu2_gx: 0x8171 (-32399)
- mpu2_gy: 0xA191 (-24175)
- mpu2_gz: 0xC1B1 (-15951)

註：nRF24 硬體會自動附加 2-byte CRC（在 32 bytes 封包之外）
```

---

**文件版本**: 1.1
**最後更新**: 2025-12-21
**更新內容**: 移除軟體 checksum，改用 nRF24 硬體 CRC_16 校驗
**維護者**: Mechtronic 2 Project Team
