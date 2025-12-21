# 硬體介面規格文件

## 系統架構

本系統採用雙 Arduino 架構，透過 nRF24L01+ 無線模組進行通訊：

- **遠距端 (Remote)**：Arduino Nano + MPU6050×2 + nRF24L01+ + 按鈕
- **桌面端 (Desktop)**：Arduino Uno + nRF24L01+ + USB Serial

---

## 1. 遠距端硬體配置 (Arduino Nano)

### 1.1 I2C 匯流排 (MPU6050 感測器)

| 功能 | Arduino Nano 腳位 | 說明 |
|------|------------------|------|
| SDA | A4 | I2C 資料線（兩顆 MPU6050 共用） |
| SCL | A5 | I2C 時鐘線（兩顆 MPU6050 共用） |

### 1.2 MPU6050 I2C 位址配置

| 感測器 | AD0 接線 | I2C 位址 | 用途 |
|--------|----------|----------|------|
| MPU6050 #1 | GND | 0x68 | 第一個感測器 |
| MPU6050 #2 | VCC (3.3V) | 0x69 | 第二個感測器 |

> **重要**：MPU6050 的 AD0 腳位決定 I2C 位址。接 GND 時位址為 0x68，接 VCC 時位址為 0x69。這允許兩顆 MPU6050 共用同一條 I2C 匯流排。

### 1.3 nRF24L01+ 無線模組 (SPI)

| nRF24L01+ 腳位 | Arduino Nano 腳位 | 說明 |
|---------------|------------------|------|
| MOSI | D11 | SPI 主出從入 |
| MISO | D12 | SPI 主入從出 |
| SCK | D13 | SPI 時鐘 |
| CE | D9 | 晶片致能腳位 |
| CSN | D10 | SPI 晶片選擇 |
| VCC | 3.3V | 電源正極 |
| GND | GND | 電源地 |

> **警告**：nRF24L01+ 僅支援 3.3V 電源。若使用 5V 可能損壞模組。

### 1.4 按鈕輸入

| 功能 | Arduino Nano 腳位 | 配置 |
|------|------------------|------|
| 按鈕 | D2 | INPUT_PULLUP 模式 |

- **正常狀態**：HIGH (上拉電阻)
- **按下時**：LOW (接地)
- **建議接線**：按鈕一端接 D2，另一端接 GND

---

## 2. 桌面端硬體配置 (Arduino Uno)

### 2.1 nRF24L01+ 無線模組 (SPI)

| nRF24L01+ 腳位 | Arduino Uno 腳位 | 說明 |
|---------------|-----------------|------|
| MOSI | D11 | SPI 主出從入 |
| MISO | D12 | SPI 主入從出 |
| SCK | D13 | SPI 時鐘 |
| CE | D9 | 晶片致能腳位 |
| CSN | D10 | SPI 晶片選擇 |
| VCC | 3.3V | 電源正極 |
| GND | GND | 電源地 |

### 2.2 USB Serial 通訊

| 功能 | Arduino Uno 腳位 | 說明 |
|------|-----------------|------|
| Serial TX | D1 (硬體 Serial) | 傳輸至 PC |
| Serial RX | D0 (硬體 Serial) | 接收自 PC |
| USB | USB 連接埠 | 連接至電腦 |

- **鮑率**：115200 bps (可於程式碼中配置)
- **用途**：將無線接收的資料轉發至 PC

### 2.3 狀態指示 LED (可選)

| 功能 | Arduino Uno 腳位 | 說明 |
|------|-----------------|------|
| 狀態 LED | D3 | 資料接收/連線狀態指示 |

---

## 3. 無線通訊參數配置

### 3.1 nRF24L01+ 固定參數

| 參數 | 數值 | 說明 |
|------|------|------|
| 通訊頻道 (Channel) | 76 | 2.476 GHz |
| 資料速率 (Data Rate) | 250kbps | 最低速率，最遠距離 |
| 發射功率 (PA Level) | LOW | 可配置 (MIN/LOW/HIGH/MAX) |
| 自動確認 (AutoACK) | 啟用 | 確保資料可靠傳輸 |
| 重傳延遲 (Retry Delay) | 5 | 對應約 1500μs |
| 重傳次數 (Retry Count) | 15 | 最多重試 15 次 |
| CRC 校驗 | CRC_16 | 16-bit 循環冗餘校驗 |

### 3.2 Pipe 位址配置

| Pipe | 位址 | 說明 |
|------|------|------|
| Pipe 0 (Reading) | 固定位址 | 接收管道 |
| Pipe 1 (Writing) | 固定位址 | 發送管道 |

> **注意**：具體位址值需在程式碼中定義，建議使用 5 bytes 位址以降低碰撞機率。

### 3.3 通訊方向

```
遠距端 (Nano)  ----[無線]---->  桌面端 (Uno)  ----[USB]---->  PC
    MPU×2                        nRF24                      應用程式
    按鈕                         Serial
    nRF24
```

---

## 4. 電源需求說明

### 4.1 遠距端 (Arduino Nano)

| 元件 | 電壓 | 電流 (典型) | 電流 (峰值) |
|------|------|------------|-----------|
| Arduino Nano | 5V | 15-20mA | 40mA |
| MPU6050 #1 | 3.3V | 3.5mA | 10mA |
| MPU6050 #2 | 3.3V | 3.5mA | 10mA |
| nRF24L01+ | 3.3V | 11mA (RX) | 13.5mA (TX) |

**總計 (估計)**：
- 正常運作：約 35-45mA @ 5V
- 峰值：約 75mA @ 5V

**建議電源**：
- USB 供電 (開發階段)
- 鋰電池 (實際使用)：7.4V LiPo + 穩壓模組，或 5V 行動電源

### 4.2 桌面端 (Arduino Uno)

| 元件 | 電壓 | 電流 (典型) | 電流 (峰值) |
|------|------|------------|-----------|
| Arduino Uno | 5V | 30-40mA | 50mA |
| nRF24L01+ | 3.3V | 11mA (RX) | 13.5mA (TX) |
| LED (D3) | 5V | 10mA | 20mA |

**總計 (估計)**：
- 正常運作：約 50-60mA @ 5V
- 峰值：約 85mA @ 5V

**建議電源**：
- USB 供電 (從 PC 直接供電即可)

---

## 5. 接線檢查清單

### 5.1 遠距端接線檢查

- [ ] MPU6050 #1: SDA → A4, SCL → A5, AD0 → GND
- [ ] MPU6050 #2: SDA → A4, SCL → A5, AD0 → VCC (3.3V)
- [ ] nRF24L01+: MOSI → D11, MISO → D12, SCK → D13, CE → D9, CSN → D10
- [ ] nRF24L01+ 電源：VCC → 3.3V, GND → GND
- [ ] 按鈕：一端 → D2, 另一端 → GND
- [ ] 電源供應：USB 或電池 → Nano VIN/5V

### 5.2 桌面端接線檢查

- [ ] nRF24L01+: MOSI → D11, MISO → D12, SCK → D13, CE → D9, CSN → D10
- [ ] nRF24L01+ 電源：VCC → 3.3V, GND → GND
- [ ] LED (可選)：正極 → D3 (經限流電阻), 負極 → GND
- [ ] USB 線：連接至 PC

---

## 6. 常見問題排除

### 6.1 I2C 通訊失敗

**症狀**：無法偵測到 MPU6050

**檢查項目**：
1. SDA/SCL 接線是否正確 (A4/A5)
2. MPU6050 電源是否正常 (3.3V 或 5V)
3. AD0 接線是否正確影響位址
4. 使用 I2C Scanner 程式掃描裝置

### 6.2 nRF24L01+ 通訊失敗

**症狀**：無法接收無線資料

**檢查項目**：
1. 電源是否為 3.3V (非 5V)
2. CE/CSN 腳位是否正確 (D9/D10)
3. SPI 接線是否正確 (D11/D12/D13)
4. 兩端頻道 (CH) 設定是否一致
5. Pipe 位址是否匹配
6. 加裝電容於 nRF24 電源腳 (10μF + 0.1μF)

### 6.3 資料遺失或不穩定

**可能原因**：
1. 電源不足 (nRF24 需要穩定 3.3V)
2. 距離過遠或有障礙物
3. 重傳參數不足

**解決方法**：
1. 使用獨立穩壓模組供電給 nRF24
2. 調整 PA Level 至 HIGH 或 MAX
3. 增加重傳次數
4. 縮短傳輸距離進行測試

---

## 7. 參考資料

- [MPU6050 Datasheet](https://invensense.tdk.com/products/motion-tracking/6-axis/mpu-6050/)
- [nRF24L01+ Datasheet](https://www.nordicsemi.com/products/nrf24-series)
- [Arduino Nano Pinout](https://docs.arduino.cc/hardware/nano/)
- [Arduino Uno Pinout](https://docs.arduino.cc/hardware/uno-rev3/)

---

**文件版本**：1.0
**最後更新**：2025-12-21
**維護者**：Mechtronic 2 Project Team
