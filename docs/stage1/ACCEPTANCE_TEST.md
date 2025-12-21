# 驗收測試文件

## 1. 硬體連接測試

### 1.1 I2C 掃描測試
**目的**: 確認兩顆 MPU6050 正確連接
**測試對象**: Remote Unit (Arduino Nano)

**步驟**:
1. 上傳 I2C Scanner 程式到 Arduino Nano
2. 開啟 Serial Monitor (115200 baud)
3. 觀察輸出

**預期結果**:
- 找到位址 0x68 (MPU #1)
- 找到位址 0x69 (MPU #2)

**I2C Scanner 程式碼**:

```cpp
// I2C Scanner for Mechtronic Remote Unit
// 檢測兩顆 MPU6050 是否正確連接

#include <Wire.h>

void setup() {
    Wire.begin();
    Serial.begin(115200);
    while (!Serial);  // 等待 Serial Monitor 開啟

    Serial.println("\n=== I2C Scanner ===");
    Serial.println("Scanning for MPU6050...");
}

void loop() {
    byte error, address;
    int nDevices = 0;

    Serial.println("\nScanning I2C bus...");

    for(address = 1; address < 127; address++) {
        Wire.beginTransmission(address);
        error = Wire.endTransmission();

        if (error == 0) {
            Serial.print("Found device at 0x");
            if (address < 16) Serial.print("0");
            Serial.print(address, HEX);

            // 識別 MPU6050
            if (address == 0x68) Serial.print(" -> MPU6050 #1 (AD0=LOW)");
            if (address == 0x69) Serial.print(" -> MPU6050 #2 (AD0=HIGH)");

            Serial.println();
            nDevices++;
        }
    }

    Serial.print("\nTotal devices found: ");
    Serial.println(nDevices);

    if (nDevices == 0) {
        Serial.println("ERROR: No I2C devices found!");
        Serial.println("Check wiring:");
        Serial.println("  - SDA -> A4");
        Serial.println("  - SCL -> A5");
        Serial.println("  - VCC -> 3.3V");
        Serial.println("  - GND -> GND");
    } else if (nDevices == 2) {
        Serial.println("OK: Both MPU6050 detected!");
    } else {
        Serial.println("WARNING: Expected 2 devices, found different count");
    }

    delay(5000);  // 每 5 秒掃描一次
}
```

**故障排除**:
- 若無裝置: 檢查 SDA/SCL 接線、電源供應
- 若僅找到 0x68: 檢查 MPU#2 的 AD0 腳是否接 VCC
- 若僅找到 0x69: 檢查 MPU#1 的 AD0 腳是否接 GND

---

### 1.2 nRF24 初始化測試
**目的**: 確認 nRF24L01+ 正確連接
**測試對象**: Remote Unit & Base Station

**步驟**:
1. 上傳各自的 firmware 到 Arduino
2. 觀察 LED 閃爍碼（Remote）或 Serial 輸出（Base）

**預期結果 (Remote Unit)**:
- 開機時 LED 短暫亮起後熄滅
- **若連續閃 3 次**: RF 初始化失敗

**預期結果 (Base Station)**:
- Serial 輸出: `[OK] RF receiver ready`
- **若快速閃爍**: RF 初始化失敗

**Remote 錯誤閃爍碼對照表**:
| 閃爍次數 | 錯誤原因 |
|---------|---------|
| 1 次    | MPU1 初始化失敗 |
| 2 次    | MPU2 初始化失敗 |
| 3 次    | nRF24 初始化失敗或雙 MPU 失敗 |

**故障排除**:
- 檢查 nRF24 SPI 接線 (CE/CSN/SCK/MISO/MOSI)
- 確認 nRF24 電源供應穩定 (建議加 10uF 電容)
- 確認天線焊接良好

---

## 2. 功能測試

### 2.1 按鈕去抖測試
**目的**: 驗證按鈕輸入穩定性

**步驟**:
1. 啟動 Remote + Base 系統
2. 快速連按按鈕 5 次
3. 觀察 Base Station Serial 輸出的 `btn` 欄位

**預期結果**:
- 每次按壓應產生一次 `0→1` 或 `1→0` 變化
- 無明顯連發（短時間內多次 0↔1 跳動）
- 狀態變化穩定且可預測

**判定標準**:
- ✅ Pass: 5 次按壓產生 5 次明確狀態切換
- ❌ Fail: 出現連續跳動或遺漏狀態變化

---

### 2.2 雙 IMU 資料測試
**目的**: 驗證兩顆 MPU6050 獨立採樣

**步驟**:
1. 啟動系統，觀察 Base Station Serial 輸出
2. **僅晃動 MPU #1** (0x68)，靜置 MPU #2
3. 記錄 `m1ax~m1gz` 和 `m2ax~m2gz` 資料
4. **僅晃動 MPU #2** (0x69)，靜置 MPU #1
5. 記錄兩組 IMU 資料

**預期結果**:
- 晃動 MPU#1 時:
  - `m1ax, m1ay, m1az, m1gx, m1gy, m1gz` 有明顯變化
  - `m2ax~m2gz` 保持靜態（小幅雜訊可接受）
- 晃動 MPU#2 時:
  - `m2ax~m2gz` 有明顯變化
  - `m1ax~m1gz` 保持靜態

**判定標準**:
- 加速度變化範圍: 靜態時 ±500 內，晃動時 > ±2000
- 陀螺儀變化範圍: 靜態時 ±100 內，轉動時 > ±1000

---

### 2.3 無線通訊測試
**目的**: 驗證 nRF24 雙向通訊穩定性

**步驟**:
1. 同時啟動 Remote Unit 和 Base Station
2. 將兩裝置相距 1 公尺
3. 觀察 Base Station Serial 輸出 5 分鐘

**預期結果**:
- 收到連續的 CSV 資料流
- `seq` 欄位應遞增（允許少量遺漏）
- 每 5 秒輸出統計資訊
- 統計顯示 packet loss < 5%（近距離）
- 接收速率約 90-100 packets/sec (對應 100Hz 採樣率)

**CSV 輸出範例**:
```
seq,timestamp,btn,m1ax,m1ay,m1az,m1gx,m1gy,m1gz,m2ax,m2ay,m2az,m2gx,m2gy,m2gz
1,1024,0,245,-89,16384,12,-45,8,198,-102,16320,-5,32,15
2,1034,0,248,-91,16380,10,-43,7,195,-100,16318,-7,30,12
...
```

**故障排除**:
- 若無資料: 檢查 RF 初始化、天線方向
- 若掉包率 > 20%: 檢查電源供應、天線連接
- 若 `seq` 異常跳躍: 檢查 RF 頻道干擾

---

## 3. 壓力測試

### 3.1 連續運行測試
**目的**: 測試系統長時間穩定性

**步驟**:
1. 啟動系統
2. 連續運行 30 分鐘
3. 每 5 分鐘記錄一次統計數據
4. 計算平均掉包率

**預期結果**:
- 無資料中斷 > 2 秒
- 平均掉包率 < 5%（近距離 1-3m）
- 接收速率穩定在 90-100 pps
- 無記憶體洩漏導致的系統崩潰
- `seq` 計數器溢位後正確歸零 (65535→0)

**觀察指標**:
| 時間 (min) | 收到封包數 | 掉包率 | 平均速率 (pps) |
|-----------|-----------|--------|---------------|
| 0-5       |           |        |               |
| 5-10      |           |        |               |
| 10-15     |           |        |               |
| 15-20     |           |        |               |
| 20-25     |           |        |               |
| 25-30     |           |        |               |

---

### 3.2 距離測試
**目的**: 測試無線傳輸距離限制

**步驟**:
1. 從 1 公尺開始測試
2. 每次增加 1 公尺距離
3. 每個距離點測試 2 分鐘
4. 記錄掉包率直到無法通訊 (loss > 90%)

**預期結果**:
- 1-3 公尺: 掉包率 < 5%
- 3-5 公尺: 掉包率 5-15%
- 5-10 公尺: 掉包率 15-50%（依環境而定）

**測試記錄表**:
| 距離 (m) | 掉包率 (%) | 速率 (pps) | 備註 |
|---------|-----------|-----------|------|
| 1       |           |           |      |
| 2       |           |           |      |
| 3       |           |           |      |
| 5       |           |           |      |
| 7       |           |           |      |
| 10      |           |           |      |

**影響因素**:
- 天線方向（同向 vs 垂直）
- 障礙物（牆壁、金屬物）
- 環境干擾（WiFi、藍牙）

---

## 4. 故障復原測試

### 4.1 IMU 斷線測試
**目的**: 測試 IMU 故障時系統行為

**步驟**:
1. 啟動系統並確認正常運行
2. 在運行中拔除 MPU#1 的電源/I2C 線
3. 觀察 Remote Unit LED 和 Base Station 輸出
4. 重新連接 MPU#1，觀察恢復情形

**預期結果**:
- **斷線時**: Remote Unit LED 連續閃爍 1 次（錯誤碼 1）
- **Base Station**: 繼續收到封包，但 `m1ax~m1gz` 可能為異常值或 0
- **重連後**: 需重啟 Remote Unit 才能恢復（目前無熱插拔）

**改進建議**:
- 實作 IMU watchdog 定期檢測
- 在 loop 中加入重新初始化邏輯

---

### 4.2 RF 干擾測試
**目的**: 測試無線干擾下的系統韌性

**步驟**:
1. 啟動系統並確認正常運行
2. 用金屬物（如鋁箔）遮擋 nRF24 天線 10 秒
3. 觀察 Base Station 統計輸出
4. 移除遮擋物，觀察恢復情形

**預期結果**:
- **遮擋時**:
  - Base Station 掉包率急劇上升
  - LED 常亮（NO_DATA_TIMEOUT 觸發）
- **系統行為**: 不崩潰、不死機
- **移除遮擋後**:
  - 1-2 秒內恢復資料接收
  - 掉包率降回正常範圍

**Remote Unit 重試機制**:
- RF 連續失敗 20 次（`RF_FAIL_THRESHOLD`）後會自動重新初始化
- 重新初始化不應中斷 IMU 採樣

---

## 5. 整合驗證流程

### 完整系統測試 Checklist

**前置準備**:
- [ ] 硬體組裝完成並檢查接線
- [ ] 兩片 Arduino 已上傳最新 firmware
- [ ] Serial Monitor 設定為 115200 baud

**測試順序**:
1. [ ] I2C Scanner 測試 (1.1)
2. [ ] nRF24 初始化測試 (1.2)
3. [ ] 按鈕去抖測試 (2.1)
4. [ ] 雙 IMU 資料測試 (2.2)
5. [ ] 無線通訊測試 (2.3)
6. [ ] 連續運行測試 30 分鐘 (3.1)
7. [ ] 距離測試 (3.2)
8. [ ] 故障復原測試 (4.1, 4.2)

**驗收標準**:
- 所有硬體測試 (Section 1) 必須通過
- 功能測試 (Section 2) 至少 2/3 通過
- 連續運行測試不得出現系統崩潰

---

## 6. 已知問題與限制

### 當前版本限制
1. **IMU 熱插拔不支援**: 斷線後需重啟 Remote Unit
2. **RF 超時無重傳**: 封包遺失即丟棄，無 ACK 機制
3. **單向通訊**: Base Station 無法控制 Remote Unit
4. **電源敏感**: nRF24 需穩定 3.3V（建議加濾波電容）

### 環境要求
- 測試環境應遠離強 2.4GHz 干擾源（WiFi 路由器、微波爐）
- 建議在開闊空間進行距離測試
- 電源供應建議使用品質穩定的 USB 充電器

---

## 附錄 A: 快速除錯指南

### Remote Unit LED 閃爍碼
| 閃爍模式 | 原因 | 解決方法 |
|---------|------|---------|
| 常亮後熄滅 | 正常啟動 | - |
| 連續 1 閃 | MPU1 失敗 | 檢查 0x68 I2C 連接 |
| 連續 2 閃 | MPU2 失敗 | 檢查 0x69 I2C 連接 |
| 連續 3 閃 | RF 失敗 | 檢查 nRF24 接線與電源 |
| 不規則閃爍 | RF 發送失敗 | 檢查 Base Station、距離、干擾 |

### Base Station Serial 訊息
| 訊息 | 意義 | 處理 |
|------|------|------|
| `[OK] RF receiver ready` | 正常啟動 | - |
| `[ERROR] RF init failed!` | nRF24 初始化失敗 | 檢查接線、重啟 |
| `[WARN] Bad version: X` | 協議版本不符 | 更新 Remote firmware |
| LED 常亮 | 超過 1 秒無資料 | 檢查 Remote Unit 狀態 |

### 常見問題排查
**Q: Base Station 收不到資料**
- 確認兩端 nRF24 初始化成功
- 檢查 RF 頻道與位址設定一致
- 確認天線未遮擋、電源穩定

**Q: 資料封包亂碼或異常值**
- 檢查協議版本 (`PROTOCOL_VERSION`)
- 確認 `sizeof(SensorPacket)` 相同
- 重新編譯上傳 firmware

**Q: 掉包率異常高 (>50%)**
- 減少距離測試
- 更換測試環境（遠離 WiFi）
- 檢查 nRF24 電源供應品質
- 確認 `SAMPLE_INTERVAL_MS` 與系統處理能力匹配
