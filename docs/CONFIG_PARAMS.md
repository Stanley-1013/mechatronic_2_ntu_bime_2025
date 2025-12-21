# 系統參數配置表

## 概述
本文件列出 Mechtronic 2 系統所有可配置參數，包括 Remote Unit、Base Station 的編譯時常數與運行時參數。

---

## Remote Unit (Arduino Nano)

### 採樣與時序參數
| 參數名稱 | 位置 | 預設值 | 單位 | 說明 | 調整建議 |
|---------|------|--------|------|------|---------|
| `SAMPLE_INTERVAL_MS` | `main_remote.ino:14` | 10 | ms | 採樣間隔（對應 100Hz） | 降低可提升採樣率，但增加 RF 負載 |
| `RF_FAIL_THRESHOLD` | `main_remote.ino:15` | 20 | 次 | RF 連續失敗門檻 | 增加可減少誤重啟，但延遲故障偵測 |

**採樣率計算**:
- 100 Hz (10ms): 高速動作捕捉
- 50 Hz (20ms): 平衡效能與精度
- 20 Hz (50ms): 低速監控、省電模式

**RF_FAIL_THRESHOLD 影響**:
- 過低 (5-10): 對短暫干擾敏感，頻繁重啟
- 適中 (15-25): 平衡穩定性與反應速度
- 過高 (>50): 故障偵測延遲 > 0.5 秒

---

### GPIO 配置
| 參數名稱 | 位置 | 預設值 | 說明 | 可變更 |
|---------|------|--------|------|--------|
| `LED_PIN` | `main_remote.ino:16` | `LED_BUILTIN` (D13) | 狀態指示 LED | 可改為其他 GPIO |

**LED 腳位選擇建議**:
- `LED_BUILTIN` (D13): Nano 板載 LED，方便除錯
- D3/D5/D6: 支援 PWM，可做呼吸燈效果
- 需考慮與 SPI/I2C 衝突

---

### IMU 參數 (imu_driver.h)
| 參數名稱 | 預設值 | 說明 | 調整範圍 |
|---------|--------|------|---------|
| `MPU1_ADDR` | 0x68 | MPU #1 I2C 位址 (AD0=LOW) | 固定 |
| `MPU2_ADDR` | 0x69 | MPU #2 I2C 位址 (AD0=HIGH) | 固定 |
| Accel Range | ±2g | 加速度計量程 | ±2g / ±4g / ±8g / ±16g |
| Gyro Range | ±250°/s | 陀螺儀量程 | ±250 / ±500 / ±1000 / ±2000 °/s |
| DLPF | ? | 數位低通濾波器 | 0-6 (頻寬遞減) |

**量程選擇指引**:

| 應用場景 | Accel Range | Gyro Range | DLPF |
|---------|-------------|------------|------|
| 緩慢姿態追蹤 | ±2g | ±250°/s | 5-6 (低頻寬) |
| 一般人體動作 | ±4g | ±500°/s | 3-4 (中頻寬) |
| 高速機器人 | ±8g | ±1000°/s | 1-2 (高頻寬) |
| 衝擊偵測 | ±16g | ±2000°/s | 0 (無濾波) |

---

### 按鈕參數 (button.h)
| 參數名稱 | 預設值 | 說明 | 調整建議 |
|---------|--------|------|---------|
| `BUTTON_PIN` | ? | 按鈕輸入腳位 | 使用 D2-D12（避免 SPI/I2C） |
| `DEBOUNCE_DELAY` | ? | 去抖動延遲 (ms) | 10-50ms，視按鈕品質調整 |
| Pull-up/down | ? | 上拉/下拉模式 | 建議 `INPUT_PULLUP` |

**去抖動延遲設定**:
- 10ms: 品質良好的微動開關
- 20ms: 一般按鈕（推薦）
- 50ms: 觸摸開關或雜訊環境

---

### RF 參數 (rf_link.h)
| 參數名稱 | 預設值 | 說明 | 調整範圍 |
|---------|--------|------|---------|
| RF Channel | ? | 無線頻道 | 0-125 (2.400-2.525 GHz) |
| TX Power | ? | 發射功率 | MIN / LOW / HIGH / MAX |
| Data Rate | ? | 資料速率 | 250kbps / 1Mbps / 2Mbps |
| Pipe Address | ? | 通訊位址 | 5 bytes (須與 Base 一致) |
| Retry Count | ? | 重傳次數 | 0-15 |
| Retry Delay | ? | 重傳延遲 | 250us - 4000us |

**頻道選擇**:
- 避開 WiFi 熱點頻段 (1, 6, 11 channel → RF 0-25, 50-75, 100-125)
- 建議使用 40-60 或 80-100 (較少干擾)

**功率與速率平衡**:
| 目標 | TX Power | Data Rate | 特性 |
|------|----------|-----------|------|
| 最大距離 | MAX | 250kbps | 續航力低、抗干擾強 |
| 平衡模式 | HIGH | 1Mbps | 推薦設定 |
| 省電模式 | LOW | 2Mbps | 距離短、功耗低 |

---

### Serial 除錯 (可選)
```cpp
// main_remote.ino:45-46 (預設註解)
// Serial.begin(115200);
// Serial.println(F("Mechtronic Remote Starting..."));
```

**啟用方式**:
1. 取消註解上述兩行
2. 在關鍵位置加入 `Serial.print()` 除錯
3. **注意**: Serial 輸出會增加執行時間，可能影響採樣率

---

## Base Station (Arduino Uno)

### Serial 通訊參數
| 參數名稱 | 位置 | 預設值 | 單位 | 說明 | 調整建議 |
|---------|------|--------|------|------|---------|
| `SERIAL_BAUD` | `main_base.ino:12` | 115200 | baud | Serial 鮑率 | 可降至 57600 提升相容性 |

**鮑率選擇**:
- 9600: 最高相容性，但可能丟資料（100Hz × 14 欄位）
- 57600: 適用於舊電腦或長 USB 線
- 115200: 推薦，支援高速資料流
- 230400: 實驗性，部分系統不穩定

**計算傳輸需求**:
```
資料量 = 100 pps × (14 欄位 × 6 bytes + 分隔符) ≈ 10 KB/s = 80 kbps
建議鮑率 ≥ 2 × 80 kbps = 160 kbps  → 選用 115200 baud
```

---

### 狀態與監控參數
| 參數名稱 | 位置 | 預設值 | 單位 | 說明 | 調整建議 |
|---------|------|--------|------|------|---------|
| `LED_PIN` | `main_base.ino:13` | 3 | - | 狀態 LED 腳位 | 任意 GPIO |
| `STATS_INTERVAL` | `main_base.ino:14` | 5000 | ms | 統計輸出間隔 | 減少可增加監控頻率 |
| `NO_DATA_TIMEOUT` | `main_base.ino:15` | 1000 | ms | 無資料超時門檻 | 增加可減少誤報 |

**STATS_INTERVAL 設定**:
- 1000ms: 即時監控（每秒輸出）
- 5000ms: 平衡模式（推薦）
- 10000ms: 減少 Serial 輸出干擾

**NO_DATA_TIMEOUT 影響**:
- 500ms: 快速偵測斷線，但對短暫干擾敏感
- 1000ms: 推薦設定
- 2000ms: 允許較長的 RF 重試時間

---

### RF 接收參數 (rf_receiver.h)
| 參數名稱 | 預設值 | 說明 | 須與 Remote 一致 |
|---------|--------|------|-----------------|
| RF Channel | ? | 無線頻道 | ✓ |
| Pipe Address | ? | 接收位址 | ✓ |
| Data Rate | ? | 資料速率 | ✓ |

---

### 統計模組參數 (stats.h)
| 參數名稱 | 預設值 | 說明 | 用途 |
|---------|--------|------|------|
| Rate Window | ? | 速率計算視窗 (ms) | 平滑接收速率統計 |
| Max Seq Gap | ? | 最大序號間隙 | 超過視為 wrap-around |

**統計輸出範例**:
```
[STATS] Received: 1523 | Lost: 47 (3.0%) | Rate: 98.5 pps
```

---

## 共通協議參數 (packet.h)

### 封包定義
| 欄位 | 資料型別 | 大小 | 說明 |
|------|---------|------|------|
| `version` | uint8_t | 1 byte | 協議版本號 |
| `seq` | uint16_t | 2 bytes | 封包序號 (0-65535) |
| `timestamp` | uint32_t | 4 bytes | 時間戳記 (ms) |
| `button` | uint8_t | 1 byte | 按鈕狀態 |
| `mpu1_ax/ay/az` | int16_t | 6 bytes | MPU1 加速度 |
| `mpu1_gx/gy/gz` | int16_t | 6 bytes | MPU1 陀螺儀 |
| `mpu2_ax/ay/az` | int16_t | 6 bytes | MPU2 加速度 |
| `mpu2_gx/gy/gz` | int16_t | 6 bytes | MPU2 陀螺儀 |

**總封包大小**: 32 bytes (建議 ≤ nRF24 單次傳輸上限)

---

### 協議版本控制
| 參數名稱 | 位置 | 預設值 | 說明 |
|---------|------|--------|------|
| `PROTOCOL_VERSION` | `packet.h` | 1 | 協議版本 |

**版本變更規則**:
- 變更封包結構 → 遞增版本號
- 兩端版本號不符 → Base Station 輸出警告
- 向下相容性由應用層處理

---

## 編譯與上傳設定

### Arduino IDE 設定
| 項目 | Remote Unit | Base Station |
|------|-------------|--------------|
| 板型 | Arduino Nano | Arduino Uno |
| Processor | ATmega328P (Old Bootloader) | ATmega328P |
| Port | /dev/ttyUSB0 (依系統) | /dev/ttyUSB1 (依系統) |

### 必要函式庫
```cpp
// 所有單元共通
#include <Wire.h>          // I2C 通訊 (內建)
#include <SPI.h>           // SPI 通訊 (內建)

// Remote Unit
#include <MPU6050.h>       // 或自製 driver

// RF 通訊 (兩端)
#include <RF24.h>          // nRF24L01+ 函式庫
```

**函式庫版本建議**:
- RF24: v1.4.x (穩定版)
- MPU6050: 視 driver 實作而定

---

## 效能調校指南

### 最大化採樣率
```cpp
// Remote Unit 優化
SAMPLE_INTERVAL_MS = 5;  // 200Hz
// 需確保:
// 1. I2C 速度足夠 (400kHz)
// 2. RF 頻寬足夠
// 3. Base Serial 鮑率提高至 230400
```

### 最大化傳輸距離
```cpp
// Remote & Base (rf_*.h)
RF_CHANNEL = 40;         // 避開 WiFi
TX_POWER = RF24_PA_MAX;  // 最大功率
DATA_RATE = RF24_250KBPS; // 低速高穩定
RETRY_COUNT = 15;        // 最大重試
RETRY_DELAY = 1500;      // 較長延遲
```

### 最小化功耗
```cpp
// Remote Unit
SAMPLE_INTERVAL_MS = 50;  // 降至 20Hz
TX_POWER = RF24_PA_LOW;   // 低功率
// 加入 sleep mode (需額外實作)
```

---

## 參數變更 Checklist

### 變更前檢查
- [ ] 備份當前 firmware 版本
- [ ] 記錄原始參數值
- [ ] 確認變更目的（效能/距離/功耗）

### 變更後驗證
- [ ] 重新編譯無錯誤
- [ ] 上傳到硬體成功
- [ ] 執行基本功能測試 (2.1-2.3)
- [ ] 確認副作用（採樣率/掉包率/延遲）

### 建議測試流程
1. 單一參數變更
2. 執行 5 分鐘穩定性測試
3. 記錄效能指標
4. 若異常則回退原值

---

## 已知參數限制

### 硬體限制
- **I2C 速度**: 預設 100kHz，可提升至 400kHz（需在 `setup()` 加入 `Wire.setClock(400000)`）
- **nRF24 封包**: 單次最大 32 bytes（當前已滿）
- **Arduino Nano SRAM**: 2KB，需注意全域變數使用

### 軟體限制
- **uint16_t seq 溢位**: 65535 後歸零（已處理）
- **millis() 溢位**: 約 49.7 天後歸零（長期運行需處理）

---

## 環境相關參數

### 溫度補償
**注意**: MPU6050 對溫度敏感，長時間運行後 offset 會飄移

**建議**:
- 開機預熱 30 秒再開始記錄
- 定期校正零點（實作 calibration 模式）

### 電源供應
| 組件 | 電壓 | 電流 | 備註 |
|------|------|------|------|
| Arduino Nano | 5V | ~100mA | USB 供電 |
| MPU6050 × 2 | 3.3V | ~7mA | Nano 3.3V 輸出 |
| nRF24L01+ | 3.3V | ~12mA (TX) | 建議加 10-100uF 電容 |

**穩定性建議**:
- nRF24 VCC 加 10uF 陶瓷電容 + 100uF 電解電容
- 避免 USB 線過長（壓降問題）
- 必要時使用外部 3.3V 穩壓模組

---

## 附錄：參數快速查找表

### 提升採樣率
- `SAMPLE_INTERVAL_MS` ↓
- `Wire.setClock(400000)` (I2C 加速)
- `SERIAL_BAUD` ↑ (Base Station)

### 降低掉包率
- `TX_POWER` ↑
- `DATA_RATE` ↓
- `RF_CHANNEL` 改至乾淨頻段
- 減少距離或移除障礙物

### 減少功耗
- `SAMPLE_INTERVAL_MS` ↑
- `TX_POWER` ↓
- 關閉 Serial 除錯輸出

### 除錯連線問題
- 啟用 Remote Unit Serial 輸出
- `STATS_INTERVAL` ↓ (更頻繁統計)
- `NO_DATA_TIMEOUT` ↓ (快速偵測)
