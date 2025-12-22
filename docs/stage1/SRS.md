
* **遠距端**：Arduino Nano + MPU6050 ×2 + 按鈕 + nRF24L01
* **桌面端**：Arduino Uno + nRF24L01 +（Serial 連電腦）+（可選 LED）

內容偏工程化、可直接拿來拆工作項目與驗收。

---

# 1. 目的與範圍

## 1.1 目的

建立一套可穿戴遠距端感測系統，能以 2.4GHz 無線（nRF24L01）將 **雙 IMU（MPU6050×2）資料 + 按鈕狀態**穩定傳送到桌面端，桌面端將資料以 Serial 輸出給電腦（或做簡單指示/處理）。

## 1.2 範圍

* 支援 **兩顆 MPU6050（I2C 位址 0x68 / 0x69）**同步採樣
* 支援 **按鈕事件/狀態**
* 支援 **nRF24 Auto-ACK 傳輸、重試、封包序號、掉包偵測**
* 支援桌面端 **資料解包、格式化輸出、基本監控（掉包率/延遲）**

---

# 2. 系統架構與模組切分

## 2.1 邏輯模組

### 遠距端（Nano Firmware）

1. 硬體抽象層 HAL
2. MPU6050 驅動與校正
3. 按鈕輸入與去抖
4. 採樣排程與時間戳
5. 封包打包與無線傳輸（nRF24 TX）
6. 狀態機與錯誤處理（故障降級/重連）

### 桌面端（Uno Firmware）

1. nRF24 RX 接收與錯誤統計
2. 封包解包與驗證（版本/長度/CRC/序號）
3. Serial 輸出介面（電腦端可讀）
4. 監控與指示（LED/統計輸出）

---

# 3. 介面規格

## 3.1 硬體介面（固定要求）

### 遠距端

* I2C：SDA=A4、SCL=A5（MPU6050×2 共用匯流排）
* MPU#1 AD0=0 → 位址 0x68；MPU#2 AD0=1 → 位址 0x69
* nRF24：SPI（D11 MOSI / D12 MISO / D13 SCK）、CE=D9、CSN=D10
* 按鈕：D2（INPUT_PULLUP），按下=LOW

### 桌面端

* nRF24：SPI（D11/D12/D13）、CE=D9、CSN=D10
* Serial：Uno → PC（USB）

## 3.2 無線參數（固定要求）

* 頻道：CH=76（可配置）
* DataRate：250kbps（預設）
* PA Level：LOW（預設，可配置）
* AutoACK：啟用
* Retries：delay=5、count=15（預設，可配置）
* CRC：CRC_16（固定）

---

# 4. 資料與封包規格

## 4.1 封包版本與相容性

* 每個封包包含：`protocol_version`（1 byte）
* 桌面端需拒收版本不符封包並記錄統計

## 4.2 最小資料內容（需求）

每筆傳輸資料需包含：

* 序號 `seq`（uint16）：遞增，用於掉包偵測
* 遠距端時間戳 `t_ms`（uint32）：`millis()` 或等效
* 按鈕狀態 `btn`（bit）：至少 1 bit
* 兩顆 MPU6050 原始值（建議 int16）：

  * MPU1：ax, ay, az, gx, gy, gz
  * MPU2：ax, ay, az, gx, gy, gz

> 可選欄位（非必須，但建議）

* 溫度 temp（int16 或 int8 量化）
* 遠距端狀態碼 status（bitfield：I2C error、IMU init fail、radio retry high…）

## 4.3 驗證與錯誤偵測（需求）

* 封包需包含一個 **簡單校驗**（至少 1 byte checksum 或 16-bit CRC 軟算）
* 桌面端必須驗證長度/版本/校驗，不通過則丟棄並計數

---

# 5. 功能需求（Functional Requirements）

## 5.1 遠距端功能需求

### FR-R1：開機初始化

* 初始化 Serial（可選，用於除錯）
* 初始化 I2C（Wire.begin）
* 探測兩顆 MPU6050（必須檢測 0x68、0x69 皆存在）
* 初始化 nRF24（begin、channel、datarate、PALevel、CRC、AutoACK、Retries）
* 初始化按鈕腳位 INPUT_PULLUP
* 若任一關鍵初始化失敗 → 進入錯誤狀態並提供可觀測行為（例如 LED 閃爍碼或 Serial 訊息）

### FR-R2：MPU6050 設定與讀取

* 設定量程（Accel/Gyro）為可配置（預設一組）
* 支援讀取 6 軸原始值（必要）
* 支援校正（至少 gyro offset；可選 accel offset）
* 支援讀取錯誤偵測（I2C NACK/timeout 計數）

### FR-R3：採樣排程

* 提供採樣頻率參數 `Fs`（例如 50/100 Hz；由你自行設定）
* 遠距端需在穩定週期下產生資料；若無線忙碌也不得阻塞到無限延後（需有策略：跳過/佇列/降頻其一）

### FR-R4：按鈕處理

* 讀取按鈕狀態（按下 LOW）
* 必須具備去抖（軟體去抖：時間窗 20~50ms 或狀態機）
* 需提供兩種輸出至少其一：

  * `btn_level`（當下狀態）
  * `btn_event`（按下/放開事件）

### FR-R5：封包打包與傳送

* 每個採樣點組成一個封包，填入 `seq`、`t_ms`、雙 IMU、按鈕
* 啟用 AutoACK：`radio.write()` 回傳結果需被記錄
* 若連續 N 次傳送失敗（N 可配置，預設 20）：

  * 進入「無線故障狀態」並觸發復原流程（FR-R6）

### FR-R6：復原與降級

* 無線故障復原：重新初始化 nRF24（可限制頻率避免反覆重啟）
* I2C 故障復原：重新初始化 I2C/MPU（可限制頻率）
* 降級策略（至少一種）：

  * 降採樣率（減少傳輸壓力）
  * 僅送狀態封包（心跳），等待恢復後再送完整資料

### FR-R7：心跳/狀態回報（建議）

* 每 T 秒（例如 1s）送出狀態摘要（可與資料封包合併）
* 包含：重試次數統計、失敗次數、I2C error 次數、目前 Fs 等

---

## 5.2 桌面端功能需求

### FR-B1：接收初始化

* 初始化 nRF24（參數需與遠距端一致：channel、datarate、CRC、AutoACK）
* 啟動 listening pipe（固定 address）
* 初始化 Serial（例如 115200）

### FR-B2：封包接收與解包

* 持續監聽 `radio.available()`
* 讀取封包後驗證：長度、版本、校驗
* 解包出 seq、t_ms、btn、兩顆 IMU

### FR-B3：掉包與延遲統計

* 用 `seq` 偵測掉包（seq 不連續 → dropped += delta-1）
* 計算接收速率（packets/sec）
* 計算簡易延遲指標（若你用遠端 t_ms：可估 jitter；若需要真延遲可加桌面時間戳）

### FR-B4：Serial 輸出格式（需求）

* 提供穩定、機器可解析的輸出（建議 CSV 或 JSON line）
* 每筆資料至少輸出：

  * seq, t_ms, btn, mpu1(ax,ay,az,gx,gy,gz), mpu2(ax,ay,az,gx,gy,gz)
* 需提供可選「監控輸出」頻率（避免每筆都輸出造成瓶頸），例如：

  * 原始資料每筆輸出（預設）
  * 監控統計每 1 秒輸出一行

### FR-B5：指示與除錯（可選）

* LED 指示：收到資料閃爍/無資料超時亮起
* 可用 Serial 命令觸發模式切換（見 FR-B6）

### FR-B6：簡易控制通道（可選但實用）

桌面端從 Serial 接收簡單命令（例如單字命令）：

* `STAT`：輸出目前統計
* `RESET`：清統計
* `FS <n>`：請求遠端降/升採樣率（若你要做雙向通訊才需要；否則可略）

---

# 6. 非功能需求（Non-Functional Requirements）

## 6.1 穩定性

* 在 1–3 公尺、視距環境下，連續運行 10 分鐘：

  * RX 不應出現長時間（>1s）完全無資料
  * 掉包率可被量測並輸出（允許存在，但需可觀測）

## 6.2 即時性

* 以設定採樣率 Fs 運作時，桌面端輸出速率應接近 Fs（允許少量抖動）
* 單筆資料端到端延遲不做硬性保證，但需能透過統計量觀測 jitter

## 6.3 可維護性

* 需有清晰的模組邊界（IMU、RF、Button、Packet、Stats）
* 所有 magic number（channel、rate、retries、Fs）需集中可配置

## 6.4 資源限制

* 封包大小需符合 nRF24 32 bytes payload 限制（若超過需量化/壓縮/拆包）
* Serial 輸出需避免造成主迴圈阻塞（必要時降輸出頻率）

---

# 7. 驗收測試（Acceptance Criteria）

## 7.1 通訊層驗收

* ACK 模式下：TX 顯示大多 OK（接近 100% 在近距離）
* 桌面端能連續解包並輸出 seq 遞增資料

## 7.2 感測層驗收

* I2C 掃描能同時找到 0x68、0x69
* 手動移動兩顆 IMU，輸出值會合理變化且兩顆數據不同步時仍可同時讀到

## 7.3 按鈕驗收

* 按下/放開在輸出中可觀測（無明顯抖動連發）

## 7.4 壓力/穩定驗收

* 系統連續運行 10 分鐘不中斷
* 桌面端能輸出掉包統計（即使為 0 也要能顯示）

---

# 8. 交付物（Deliverables）

* 遠距端韌體：

  * `imu_driver.*`
  * `rf_link.*`
  * `button.*`
  * `packet.*`
  * `main_remote.ino`
* 桌面端韌體：

  * `rf_receiver.*`
  * `packet_parser.*`
  * `stats.*`
  * `main_base.ino`
* 文件：

  * 封包格式說明（版本、欄位、大小）
  * 參數表（channel、Fs、retries…）
  * 驗收測試步驟與預期結果


