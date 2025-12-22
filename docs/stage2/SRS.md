
# 軟體需求規格書 SRS

**專題：雙 MPU6050 投籃動作感測 + 無線傳輸 + 分析與呈現頁面**
版本：v1.0（整合版）
範圍：遠距端韌體（Nano）、桌面端韌體（Uno）、PC 後端（FastAPI）、SPA 前端（JS/HTML/CSS）

---

## 1. 目的與範圍

### 1.1 目的

建置一套可穿戴感測系統，於投籃情境下收集雙 IMU（MPU6050×2）與按鈕狀態，透過 nRF24L01 無線傳輸至桌面端，再由 PC 端提供：

1. 即時監控頁面（Live Dashboard）
2. 錄製、回放（Replay）
3. 自動切段（投籃開始/結束）、特徵萃取、2D 散點分類（Analysis）
4. 按鈕作為「投完後標註好球」的標籤輸入

### 1.2 範圍（含/不含）

**包含**

* 雙 MPU6050 讀值、封包傳輸、Serial 可解析輸出
* PC 端資料擷取、存檔、回放、濾波、切段、特徵、視覺化
* 按鈕標註「好球」並對齊到最近一次投籃段落

**不包含**

* 筆電鏡頭/視覺輔助動作偵測
* 進階 ML 訓練與部署（可做簡單 k-means/kNN 但不要求深度模型）

---

## 2. 系統架構與模組切分

### 2.1 硬體節點

* 遠距端：Arduino Nano + MPU6050×2 + Button + nRF24L01
* 桌面端：Arduino Uno + nRF24L01 + USB Serial to PC
* PC：FastAPI 後端 + SPA 前端（原生 JS）

### 2.2 軟體模組

**遠距端 Nano Firmware**

* I2C/MPU 驅動、採樣排程、按鈕讀取、封包打包、nRF24 TX、狀態/錯誤處理

**桌面端 Uno Firmware**

* nRF24 RX、封包解包、Serial 輸出（機器可解析）、簡易統計（可選）

**PC 後端（Python FastAPI）**

* Serial ingest、資料標準化、ring buffer、錄製、回放、濾波、切段、特徵、標註對齊、WS 推送

**PC 前端（SPA）**

* Live/Replay/Analysis UI、時序圖、散點圖、段落列表、錄製控制、狀態顯示

---

## 3. 介面規格

### 3.1 遠距端硬體介面（固定）

* I2C：Nano SDA=A4、SCL=A5
* MPU 位址：MPU#1=0x68（AD0=0），MPU#2=0x69（AD0=1）
* nRF24：SPI D11(MOSI)/D12(MISO)/D13(SCK)、CE=D9、CSN=D10
* Button：D2（INPUT_PULLUP 建議；按下電平視既有實作）

### 3.2 桌面端硬體介面（固定）

* nRF24：SPI D11/D12/D13、CE=D9、CSN=D10
* Serial：Uno USB to PC

### 3.3 無線參數（固定/可配置）

* Channel：76（可配置）
* DataRate：250kbps（預設，穩定優先）
* PALevel：LOW（預設）
* AutoACK：啟用
* Retries：delay=5, count=15（預設）
* CRC：CRC_16（固定）

---

## 4. 資料與格式規格

### 4.1 基本資料欄位（邏輯）

每筆 sample 必須包含：

* `seq`：uint16 遞增（掉包偵測）
* `t_remote_ms`：uint32（遠距端 millis）
* `btn`：0/1（按鈕狀態 level；後端轉事件）
* 兩顆 MPU 的原始值（int16）：

  * MPU1：ax1,ay1,az1,gx1,gy1,gz1
  * MPU2：ax2,ay2,az2,gx2,gy2,gz2

### 4.2 Uno→PC Serial 輸出格式（硬性）

* Baud：115200
* **每筆 sample 一行 CSV（100Hz）**
* 欄位順序固定如下（raw int16）：

```
seq,t_remote_ms,btn,ax1,ay1,az1,gx1,gy1,gz1,ax2,ay2,az2,gx2,gy2,gz2
```

* 允許狀態行以 `#` 開頭（解析器忽略）：

```
#pps=100,dropped=0
```

### 4.3 單位換算（PC 端）

目前量程固定：

* Accel：±2g → `acc_g = raw / 16384.0`
* Gyro：±250 dps → `gyro_dps = raw / 131.0`

---

## 5. 功能需求（Functional Requirements）

### 5.1 遠距端（Nano）功能需求

**FR-R1 開機初始化**

* 初始化 I2C、探測 MPU 0x68/0x69 皆存在
* 初始化 nRF24（參數一致）
* 初始化按鈕輸入（保持既有 wiring/logic）

**FR-R2 MPU 設定與讀取**

* 可配置量程（目前固定 ±2g/±250dps 亦可）
* 每次採樣讀取兩顆 MPU 6 軸 raw 值

**FR-R3 採樣排程**

* 感測採樣率 Fs_sense：**100Hz（10ms）**
* `seq` 每筆遞增
* 若無線傳輸暫時阻塞，不得造成永久卡死（可採：跳過/覆寫最新/短暫排隊其一）

**FR-R4 按鈕輸出**

* 封包內提供 `btn` 欄位（0/1 level）
* 不要求在遠距端生成事件（避免衝突）

**FR-R5 無線傳輸**

* 封包發送使用 AutoACK
* 記錄成功/失敗計數（供 debug 或 status）

---

### 5.2 桌面端（Uno）功能需求

**FR-B1 接收初始化**

* nRF24 參數與遠距端一致
* 連續接收封包並解包

**FR-B2 Serial 輸出**

* 按 4.2 固定格式輸出 CSV（每筆一行）
* 輸出速率與接收速率一致（目標 100Hz）

---

### 5.3 PC 後端（FastAPI）功能需求

**FR-P1 Serial Ingest**

* 連線到指定 Serial Port（可配置）
* 解析 CSV data line，忽略 `#` 開頭 stat line
* 解析失敗要計數 `parse_err` 並跳過該行

**FR-P2 掉包/速率統計**

* 以 `seq` 偵測掉包：非連續→累加 dropped
* 計算 pps（packets/sec）
* 提供 `/api/status` 與 WS `stat` 推送

**FR-P3 Ring Buffer**

* 保存最近 N 秒資料（預設 60s），供 Live 圖表與事件對齊

**FR-P4 錄製（Record）**

* `POST /api/record/start {name}` 開始錄製
* 存 `data.csv` + `meta.json`（至少包含 Fs、量程、欄位版本、IMU 安裝位置）
* `POST /api/record/stop` 結束錄製

**FR-P5 回放（Replay）**

* 能列出 sessions、讀取指定 session
* 能按原始時間戳或固定倍率回放到同一套資料管線（濾波/特徵/切段）

**FR-P6 前處理（Preprocess）**

* raw → 單位換算（g、dps）
* gyro bias 校正：啟動後靜止 2 秒估計 offset（或提供 API 觸發重校正）
* 低通濾波（可切換）：

  * gyro magnitude：15–20Hz（預設 18Hz）
  * accel magnitude：10–15Hz（預設 12Hz）
    （實作可用簡單 IIR 或 moving average，需保持即時性）

**FR-P7 投籃切段（Motion Detection）**

* 不依賴按鈕切段
* 以 IMU1（手背）為主：

  * `g1 = |gyro1|`
  * `g1_s = lowpass(g1)`
* 狀態機（必須）：

  * IDLE → ACTIVE → COOLDOWN
* 進入 ACTIVE（開始）條件：`g1_s > Th_on` 持續 ≥ 60–100ms
* 離開 ACTIVE（結束）條件：`g1_s < Th_off` 持續 ≥ 150–300ms
* 遲滯：`Th_on > Th_off`
* 最短段長：≥ 300ms（可配置）
* 冷卻時間：300–500ms（可配置）
* 閾值自適應（建議必做）：在 IDLE 估 baseline/noise，Th_on/Th_off 由 baseline + k*noise 計算（k 可配置）

**FR-P8 Release（出手瞬間）候選點（可選但建議）**

* 在 ACTIVE 段內找 `g1_s` 峰值時間 `t_release_ms`
* 或以 accel jerk 峰值做候選（可選）

---

## 6. 按鈕標註（Good Shot Labeling）需求（整合你最新需求）

### 6.1 定義

* **按鈕唯一用途**：使用者投完一球後短按一次，標註「上一球 = good」
* 不要求標註 miss；未標註視為 `unknown`

### 6.2 btn_level → label_good 事件生成（相容既有實作）

**FR-L1 去抖與邊緣偵測**

* 後端從 `btn` level 生成事件
* 去抖冷卻 `T_debounce`：200–300ms（預設 250ms）
* 按下邊緣判定需可配置（避免你 btn 邏輯與 INPUT_PULLUP 相反造成衝突）：

  * 例：`pressed_level = 0 or 1` 由 metadata 設定（預設不寫死）

**輸出事件**

```json
{"type":"event","kind":"label_good","t_host_ms":..., "seq":...}
```

### 6.3 好球標籤對齊到段落

**FR-L2 對齊規則**

* 系統維護 `ShotSegment[]`（由 FR-P7 切段產生）
* 當 `label_good` 發生，選擇「最近一個已結束段落」且符合時間窗：

  * `segment.t_end <= event.t_host_ms`
  * `event.t_host_ms - segment.t_end ∈ [T_min, T_max]`
  * 預設：`T_min=0.2s`、`T_max=3.0s`
* 找不到符合者需提示（UI 顯示 “no shot to label”），不中斷系統

**FR-L3 段落資料模型**
每段至少：

* `shot_id`
* `t_start_ms`, `t_end_ms`
* （可選）`t_release_ms`
* `features`（見下）
* `label`：`unknown | good`
* `label_time_ms`（可選）

---

## 7. 特徵與分類（Analysis）

### 7.1 段落摘要特徵（每段必做）

至少產生：

* `dur`：段落長度
* `g1_rms`、`g1_peak`（手背角速度模長）
* `g2_rms`、`g2_peak`（二頭肌角速度模長）
* `dg_rms`：RMS(|g2|-|g1|) 或 RMS(|g2|-|g1|)（相對差異）

### 7.2 2D 散點分類（簡單、可展示）

* x = `g1_rms`
* y = `dg_rms` 或 `corr(g1,g2)`
* 分群：k-means（k=2~4，可配置）
* UI 顯示每段一點，可點選回看時序

---

## 8. 前端（SPA）需求

### 8.1 頁面（Tab）

1. Live：連線狀態、pps/dropped、錄製控制、時序圖（|g1|、|g2|、Δ|g|）、事件/段落標記
2. Replay：session 選擇、播放控制、同樣時序圖
3. Analysis：段落列表（含 label good/unknown）、散點圖、段落摘要

### 8.2 圖表

* 時序：uPlot（建議）
* 散點：ECharts（建議）

---

## 9. 非功能需求（NFR）

* Live 模式下 UI 更新頻率建議 25–50Hz（後端下採樣推送），但錄檔需保存完整 100Hz
* 系統需可連續運行 ≥10 分鐘不崩潰
* 解析失敗、掉包、無段落可標註等狀況需可觀測（stat/UI 提示）

---

## 10. 驗收條件（Acceptance Criteria）

### 10.1 資料鏈路

* Live ingest 連續 10 分鐘，pps 接近 100，無長時間（>1s）斷流
* dropped、parse_err 有顯示與統計

### 10.2 切段

* 連續投籃多次，系統能產生多個 ShotSegment（不要求完全精準，但需合理）
* 每段具有 start/end、dur、至少 3 個特徵值

### 10.3 好球標註

* 投完一球後 0.2–3.0 秒內短按按鈕
* 系統將最近結束段落標為 good，UI 立即反映
* 連續快速按不會造成重複標錯（去抖生效）

### 10.4 回放與分析

* 錄製一段資料後可回放
* Analysis 可生成散點圖與分群結果

---

## 11. 交付物（Deliverables）

* Uno/Nano 韌體：能穩定傳輸與輸出 CSV
* PC 後端：FastAPI + WS + 存檔/回放/切段/特徵/標註對齊
* 前端 SPA：Live/Replay/Analysis 三頁籤 + 圖表
* 文件：欄位定義、meta.json 規格、參數表、驗收步驟

---


