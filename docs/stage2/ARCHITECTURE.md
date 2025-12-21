# 系統架構

## 總覽

Mechtronic 2 是一個完整的投籃動作感測與分析系統，包含硬體（雙 MPU6050 IMU）、韌體（Arduino）、後端（Python）和前端（SPA）四層架構。

```
┌─────────────────────────────────────────────────────────────────┐
│                        Hardware Layer                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    nRF24L01+    ┌─────────────┐    USB       │
│  │ Remote Unit │ ─────────────> │ Base Station│ ──────────>   │
│  │ (Arduino    │   2.4GHz       │ (Arduino    │   Serial       │
│  │  Nano)      │   Wireless     │  Uno)       │   115200       │
│  │             │                │             │   baud         │
│  │ MPU6050 x2  │                │ nRF24L01+   │                │
│  │ Button      │                │             │                │
│  │ nRF24L01+   │                │             │                │
│  │ Battery     │                │             │                │
│  └─────────────┘                └─────────────┘                │
│       │                                                         │
│       └─ 100Hz sampling, 15-field CSV format                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                                         │
                                         │ Serial CSV
                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Backend (Python)                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐                                               │
│  │ SerialIngest │ ──> ┌───────────┐ ──> ┌────────────┐         │
│  │ (CSV 解析)    │     │ Processor │     │ RingBuffer │         │
│  │ - 100Hz recv │     │ (物理單位) │     │ (60秒緩衝)  │         │
│  │ - seq check  │     │ - accel   │     │ - 6000 smp │         │
│  └──────────────┘     │ - gyro    │     │ - FIFO     │         │
│                       │ - filter  │     └────────────┘         │
│                       │ - mag     │            │                │
│                       └───────────┘            │                │
│                              │                 ▼                │
│                              │           ┌───────────┐          │
│                              │           │ Segmenter │          │
│                              │           │ (切段)     │          │
│                              │           │ - g_mag   │          │
│                              │           │ - feature │          │
│                              │           └───────────┘          │
│                              ▼                  │                │
│                        ┌───────────┐            ▼                │
│                        │ Recorder  │      ┌───────────┐          │
│                        │ (存檔)    │      │ Labeler   │          │
│                        │ - parquet │      │ (標註)     │          │
│                        │ - meta    │      │ - btn evt │          │
│                        └───────────┘      │ - auto    │          │
│                                           └───────────┘          │
│                                                 │                │
│  ┌─────────────────────────────────────────────┼───────────────┐│
│  │                    CoreService              │               ││
│  │            (整合所有服務，單例模式)            │               ││
│  │  ┌──────────┐  ┌────────┐  ┌────────┐      │               ││
│  │  │ Ingest   │  │Processor│ │Recorder │      │               ││
│  │  │ Serial   │  │Buffer   │ │Player   │      │               ││
│  │  └──────────┘  └────────┘  └────────┘      │               ││
│  └─────────────────────────────────────────────┼───────────────┘│
│                                                 │                │
│  ┌─────────────┐    ┌─────────────┐            │                │
│  │ REST API    │    │ WebSocket   │ <──────────┘                │
│  │ (FastAPI)   │    │ (即時推送)   │                             │
│  │             │    │ - 30Hz smp  │                             │
│  │ /api/       │    │ - 1Hz stat  │                             │
│  │  sessions   │    │ - segment   │                             │
│  │  recording  │    │ - label     │                             │
│  │  playback   │    └─────────────┘                             │
│  │  segments   │                                                │
│  │  stats      │                                                │
│  └─────────────┘                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                    │                    │
                    │ HTTP REST          │ WebSocket
                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (SPA)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐    ┌─────────┐    ┌──────────┐                    │
│  │  Live   │    │ Replay  │    │ Analysis │                    │
│  │ (即時)   │    │ (回放)   │    │ (分析)    │                    │
│  │         │    │         │    │          │                    │
│  │ - chart │    │ - chart │    │ - label  │                    │
│  │ - stats │    │ - ctrl  │    │ - stats  │                    │
│  │ - rec   │    │ - seek  │    │ - export │                    │
│  └─────────┘    └─────────┘    └──────────┘                    │
│       │              │              │                           │
│  ┌────┴──────────────┴──────────────┴────┐                     │
│  │            Chart Components           │                     │
│  │                                        │                     │
│  │  ┌──────────┐     ┌─────────────┐     │                     │
│  │  │  uPlot   │     │  ECharts    │     │                     │
│  │  │  (時序圖) │     │  (散點圖)    │     │                     │
│  │  │          │     │             │     │                     │
│  │  │ - 6 axes │     │ - features  │     │                     │
│  │  │ - 1000+  │     │ - clusters  │     │                     │
│  │  │  points  │     │             │     │                     │
│  │  └──────────┘     └─────────────┘     │                     │
│  └───────────────────────────────────────┘                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 資料流

### 1. 即時錄製流程

```
Remote Unit (100Hz)
  → nRF24L01+ wireless
  → Base Station
  → Serial (115200 baud, CSV)
  → SerialIngest.parse_line()
  → Processor.process()
  → RingBuffer.add()
  → Segmenter.feed()
  → WebSocket (30Hz)
  → Frontend Chart
```

### 2. 錄製存檔流程

```
User clicks "Start Recording"
  → POST /api/recording/start
  → CoreService.start_recording()
  → Recorder.start()
  → SerialIngest → Processor → Recorder.on_sample()
  → Write to parquet (batched)
  → User clicks "Stop Recording"
  → POST /api/recording/stop
  → Recorder.finalize()
  → Write metadata.json
```

### 3. 回放流程

```
User selects session
  → POST /api/playback/load/{id}
  → Player.load_session()
  → Read parquet + metadata
  → POST /api/playback/play
  → Player.play_loop()
  → WebSocket push (30Hz)
  → Frontend Chart (same as live)
```

### 4. 投籃切段流程

```
RingBuffer → Segmenter.feed()
  → Calculate g_mag (gyro magnitude)
  → Threshold detection (g_mag > 30 °/s)
  → Shot start/end detection
  → Feature extraction (RMS, peak, etc.)
  → ShotSegment creation
  → WebSocket "segment" event
  → Button press → Labeler → Auto-label last shot
```

---

## 模組說明

### Backend Services

#### 1. SerialIngest (services/ingest.py)

**職責**: Serial 連接與 CSV 解析

- 連接 Arduino Serial (115200 baud)
- 解析 15 欄位 CSV（seq, t_remote_ms, btn, 6 IMU values x2）
- 封包序號檢查（偵測 dropped packets）
- 附加本地時間戳 `t_received_ns`

#### 2. Processor (services/processor.py)

**職責**: 資料處理與單位轉換

- **單位轉換**:
  - Accel: raw → g (16384 LSB/g)
  - Gyro: raw → °/s (131 LSB/°/s)
- **濾波**: Low-pass filter (可選)
- **計算模長**: `g_mag = sqrt(gx^2 + gy^2 + gz^2)`
- **校正**: Gyro 零點偏移補償

#### 3. RingBuffer (services/buffer.py)

**職責**: 60 秒循環緩衝

- 容量: 6000 samples (100Hz × 60s)
- FIFO 模式（自動淘汰舊資料）
- 支援時間範圍查詢 `get_range(t_start, t_end)`

#### 4. Segmenter (services/segmenter.py)

**職責**: 投籃段落切分

- **觸發條件**: `g_mag > 30 °/s`（陀螺儀模長）
- **段落定義**: 從觸發前 100ms 到觸發後 700ms（800ms 總長）
- **特徵提取**:
  - `g1_rms`, `g1_peak`: MPU1 陀螺儀 RMS/峰值
  - `g2_rms`, `g2_peak`: MPU2 陀螺儀 RMS/峰值
  - `dg_rms`: 雙 IMU 陀螺儀差異
  - `a1_rms`, `a2_rms`: 加速度 RMS
- **輸出**: `ShotSegment` (含 samples + features)

#### 5. Labeler (services/labeler.py)

**職責**: 標註管理

- **觸發**: 按鈕按下事件（`btn=1` → `btn=0`）
- **策略**: 標註最近 1 秒內的投籃段落
- **標籤**: `good` / `bad` / `unknown`
- **儲存**: 更新 segment.label

#### 6. Recorder (services/recorder.py)

**職責**: Session 錄製與存檔

- **格式**: Parquet (列式儲存，壓縮)
- **Metadata**: JSON (包含 session info, IMU positions)
- **路徑**: `sessions/{session_id}/data.parquet`
- **批次寫入**: 每 1000 samples flush

#### 7. Player (services/player.py)

**職責**: Session 回放

- **載入**: 讀取 parquet + metadata
- **播放控制**: play / pause / stop / seek
- **速度控制**: 0.5x ~ 2.0x
- **狀態**: `PlayerState` (playing / paused / stopped)

#### 8. CoreService (services/core.py)

**職責**: 服務整合（單例模式）

- 統一管理所有服務實例
- 提供高層 API (`start_recording`, `stop_recording`)
- 協調 Serial → Processor → Buffer → Segmenter 流程

---

### Backend API

#### REST Endpoints

| 端點 | 方法 | 功能 |
|------|------|------|
| `/api/sessions` | GET | 列出 sessions |
| `/api/sessions/{id}` | GET | Session 詳情 |
| `/api/sessions/{id}` | DELETE | 刪除 session |
| `/api/recording/start` | POST | 開始錄製 |
| `/api/recording/stop` | POST | 停止錄製 |
| `/api/recording/status` | GET | 錄製狀態 |
| `/api/playback/load/{id}` | POST | 載入 session |
| `/api/playback/play` | POST | 開始播放 |
| `/api/playback/pause` | POST | 暫停播放 |
| `/api/playback/stop` | POST | 停止播放 |
| `/api/playback/seek` | POST | 跳轉時間 |
| `/api/playback/status` | GET | 播放狀態 |
| `/api/segments` | GET | 列出段落 |
| `/api/segments/{id}` | GET | 段落詳情 |
| `/api/segments/{id}/label` | PATCH | 更新標籤 |
| `/api/stats` | GET | 統計資訊 |
| `/api/stats/calibration/start` | POST | 開始校正 |

#### WebSocket Messages

| 類型 | 頻率 | 內容 |
|------|------|------|
| `sample` | 30Hz | 即時樣本（降頻） |
| `stat` | 1Hz | 統計資訊（PPS, dropped） |
| `segment` | Event | 段落開始/結束 |
| `label` | Event | 標註事件 |
| `calibration` | Event | 校正狀態 |

---

### Frontend Modules

#### 1. Live View

**功能**:
- 即時圖表（uPlot 6 軸時序圖）
- 統計資訊顯示（PPS, dropped）
- 錄製控制（Start/Stop）
- 校正控制

**技術**:
- WebSocket 接收 30Hz 資料
- uPlot 高效渲染（1000+ points）
- 自動捲動視窗（60 秒）

#### 2. Replay View

**功能**:
- Session 選擇
- 播放控制（Play/Pause/Stop）
- 時間軸拖曳（Seek）
- 速度調整（0.5x ~ 2.0x）

**技術**:
- 復用 Live View 圖表元件
- 播放進度條
- WebSocket 接收回放資料

#### 3. Analysis View

**功能**:
- 投籃段落列表
- 標籤編輯（Good/Bad）
- 特徵散點圖（ECharts）
- 統計匯總

**技術**:
- REST API 查詢段落
- ECharts 互動式散點圖
- CSV 匯出

---

## 資料模型

### RawSample

15 欄位原始資料（Serial CSV）

```python
seq: int              # 封包序號 (0~65535)
t_remote_ms: int      # 遠距端時間戳 (ms)
btn: int              # 按鈕狀態 (0/1)
ax1, ay1, az1: int    # MPU1 加速度 raw
gx1, gy1, gz1: int    # MPU1 陀螺儀 raw
ax2, ay2, az2: int    # MPU2 加速度 raw
gx2, gy2, gz2: int    # MPU2 陀螺儀 raw
```

### ProcessedSample

處理後資料（物理單位）

```python
seq, t_remote_ms, t_received_ns, btn
ax1_g, ay1_g, az1_g: float      # MPU1 加速度 (g)
gx1_dps, gy1_dps, gz1_dps: float # MPU1 陀螺儀 (°/s)
ax2_g, ay2_g, az2_g: float      # MPU2 加速度 (g)
gx2_dps, gy2_dps, gz2_dps: float # MPU2 陀螺儀 (°/s)
g1_mag, g2_mag: float           # 陀螺儀模長
a1_mag, a2_mag: float           # 加速度模長
```

### ShotSegment

投籃段落

```python
shot_id: str          # UUID
t_start_ms: int       # 開始時間
t_end_ms: int         # 結束時間
duration_ms: int      # 持續時間
label: str            # 標籤 (good/bad/unknown)
samples: List[ProcessedSample]  # 段落樣本
features: dict        # 特徵 (RMS, peak, etc.)
```

### SessionInfo

Session 資訊

```python
id: str               # session_id
name: str             # 自訂名稱
path: str             # 檔案路徑
created_at: str       # 建立時間 (ISO 8601)
duration_ms: int      # 總時長
sample_count: int     # 樣本數
imu_positions: dict   # IMU 位置 (mpu1/mpu2)
```

---

## 技術選型

### Backend

- **Framework**: FastAPI 0.109
- **WebSocket**: FastAPI native
- **Serial**: pyserial 3.5
- **Data**: pandas 2.1, numpy 1.26
- **Storage**: Parquet (pyarrow)
- **Testing**: pytest 7.4

### Frontend

- **HTML/CSS/JS**: Vanilla (無框架)
- **Chart**: uPlot 1.6 (time-series), ECharts 5.4 (scatter)
- **HTTP**: Fetch API
- **WebSocket**: native WebSocket API

### Firmware

- **Platform**: Arduino
- **Radio**: nRF24L01+ (RF24 library)
- **IMU**: MPU6050 (I2C, 100Hz)
- **Format**: CSV (15 fields)

---

## 效能指標

| 項目 | 目標 | 實際 |
|------|------|------|
| Sampling Rate | 100Hz | 98-100Hz |
| Packet Loss | <2% | ~1-2% |
| WebSocket Push | 30Hz | 30Hz |
| Buffer Size | 60s (6000 samples) | 6000 |
| Playback Latency | <50ms | ~30ms |
| Chart Render | 60fps | 50-60fps |
| Segmentation Delay | <100ms | ~50ms |

---

## 部署

### 開發環境

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
# 直接用瀏覽器開啟 frontend/index.html
# 或用本地 server:
python3 -m http.server 8080 --directory frontend
```

### 生產環境（未實作）

建議使用：
- Docker Compose（backend + frontend）
- Nginx（反向代理）
- Systemd（服務管理）

---

## 未來擴展

### 短期

- [ ] Session 分頁與搜尋
- [ ] 匯出 CSV/JSON
- [ ] 更多特徵提取（FFT, 姿態角）

### 中期

- [ ] 機器學習分類（Good/Bad）
- [ ] 即時姿態視覺化（3D）
- [ ] 多使用者支援

### 長期

- [ ] 雲端同步
- [ ] 手機 App（藍牙連接）
- [ ] 進階分析（運動學模型）
