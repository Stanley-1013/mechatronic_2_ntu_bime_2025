# Mechtronic 2 - 投籃動作感測系統

雙 MPU6050 IMU 投籃動作感測 + 無線傳輸 + 即時分析系統

## 系統特色

- 雙 IMU 同步採集（100Hz）
- nRF24L01+ 無線傳輸（2.4GHz）
- 即時資料處理與視覺化
- 自動投籃段落切分
- 按鈕標註支援
- Session 錄製與回放
- 特徵提取與分析

---

## 快速開始

### 硬體需求

#### Remote Unit (遠距端 - 可攜帶)
- Arduino Nano
- MPU6050 x 2
- nRF24L01+
- 按鈕 x 1
- 電池供電

#### Base Station (桌面端 - USB 連接電腦)
- Arduino Uno
- nRF24L01+
- USB 線

### 軟體需求

- Python 3.9+
- 現代瀏覽器（Chrome/Firefox/Edge）
- Arduino IDE（上傳韌體用）

---

## 安裝步驟

### 1. 上傳韌體

使用 Arduino IDE 上傳韌體到對應板子：

**Remote Unit (Arduino Nano)**:
```
開啟 firmware/remote/main_remote.ino
選擇板子: Arduino Nano
選擇序列埠: /dev/ttyUSB0 (或對應埠)
上傳
```

**Base Station (Arduino Uno)**:
```
開啟 firmware/base/main_base.ino
選擇板子: Arduino Uno
選擇序列埠: /dev/ttyUSB0 (或對應埠)
上傳
```

### 2. 安裝 Python 依賴

```bash
cd backend
pip install -r requirements.txt
```

### 3. 啟動後端

```bash
cd backend
uvicorn main:app --reload --port 8000
```

或使用啟動腳本：

```bash
./start.sh
```

### 4. 開啟前端

用瀏覽器開啟：

```
frontend/index.html
```

或啟動本地 HTTP server：

```bash
python3 -m http.server 8080 --directory frontend
# 然後開啟 http://localhost:8080
```

---

## 使用方式

### 即時監測（Live View）

1. 確保 Remote Unit 和 Base Station 都已上電
2. 確保 Base Station 透過 USB 連接到電腦
3. 啟動後端（會自動連接 Serial）
4. 開啟前端 Live View
5. 即時查看 6 軸 IMU 資料圖表

### 錄製 Session

1. 在 Live View 點擊「Start Recording」
2. 輸入 Session 名稱（例如：「練習1」）
3. 開始投籃練習
4. 完成後點擊「Stop Recording」
5. Session 會自動儲存到 `backend/sessions/` 目錄

### 回放分析（Replay View）

1. 在 Replay View 選擇 Session
2. 點擊「Play」開始回放
3. 使用時間軸拖曳跳轉
4. 調整播放速度（0.5x ~ 2.0x）

### 標註投籃段落（Analysis View）

1. 系統會自動切分投籃段落（陀螺儀觸發）
2. 在 Analysis View 查看所有段落
3. 點擊段落查看詳細資料
4. 更新標籤（Good/Bad）
5. 匯出 CSV 進行進一步分析

### 按鈕即時標註

- 投籃後按下 Remote Unit 的按鈕
- 系統會自動標註最近 1 秒內的投籃為「Good」
- 可在 Analysis View 修改標籤

---

## 專案結構

```
mechtronic_2/
├── firmware/                # Arduino 韌體
│   ├── remote/             # 遠距端（Nano）
│   │   └── main_remote.ino
│   ├── base/               # 桌面端（Uno）
│   │   └── main_base.ino
│   └── common/             # 共用程式庫
│       ├── nrf24_config.h
│       └── mpu6050_dual.h
│
├── backend/                # Python 後端
│   ├── main.py            # FastAPI 入口
│   ├── config.py          # 配置
│   ├── requirements.txt   # 依賴套件
│   │
│   ├── models/            # 資料模型
│   │   ├── sample.py      # RawSample, ProcessedSample
│   │   └── session.py     # SessionInfo
│   │
│   ├── services/          # 核心服務
│   │   ├── ingest.py      # Serial 接收
│   │   ├── processor.py   # 資料處理
│   │   ├── buffer.py      # RingBuffer
│   │   ├── segmenter.py   # 投籃切段
│   │   ├── labeler.py     # 標註管理
│   │   ├── recorder.py    # 錄製存檔
│   │   ├── player.py      # 回放控制
│   │   └── core.py        # CoreService（整合）
│   │
│   ├── api/               # API 端點
│   │   ├── routes/
│   │   │   ├── sessions.py
│   │   │   ├── recording.py
│   │   │   ├── playback.py
│   │   │   ├── segments.py
│   │   │   └── stats.py
│   │   └── websocket.py   # WebSocket handler
│   │
│   ├── tests/             # 測試套件
│   │   ├── conftest.py
│   │   ├── test_models.py
│   │   └── test_api.py
│   │
│   └── sessions/          # 錄製檔案（.gitignore）
│
├── frontend/              # 前端 SPA
│   ├── index.html         # 主頁面
│   ├── live.html          # 即時監測
│   ├── replay.html        # 回放分析
│   ├── analysis.html      # 段落分析
│   │
│   ├── js/
│   │   ├── api.js         # API 封裝
│   │   ├── websocket.js   # WebSocket 封裝
│   │   ├── chart.js       # 圖表元件（uPlot）
│   │   └── utils.js       # 工具函數
│   │
│   └── lib/               # 第三方庫
│       ├── uplot.min.js
│       └── echarts.min.js
│
└── docs/                  # 文檔
    ├── stage1/            # 階段 1 文檔
    │   └── ...
    └── stage2/            # 階段 2 文檔
        ├── SERIAL_FORMAT.md    # Serial 通訊格式
        ├── API_SPEC.md         # API 規格
        ├── ARCHITECTURE.md     # 系統架構
        └── TASK_PLAN.md        # 任務規劃
```

---

## 文檔

- [Serial 通訊格式](docs/stage2/SERIAL_FORMAT.md) - 15 欄位 CSV 格式定義
- [API 規格](docs/stage2/API_SPEC.md) - REST API 和 WebSocket 文檔
- [系統架構](docs/stage2/ARCHITECTURE.md) - 完整系統架構說明
- [任務規劃](docs/stage2/TASK_PLAN.md) - 開發任務分解

---

## 技術規格

### 硬體

- **採樣率**: 100Hz
- **無線頻率**: 2.4GHz (nRF24L01+)
- **無線速度**: 250kbps
- **傳輸格式**: CSV (15 欄位)
- **Serial Baud**: 115200

### 韌體

- **MPU6050 設定**:
  - Accel: ±2g (16384 LSB/g)
  - Gyro: ±250°/s (131 LSB/°/s)
  - I2C 地址: 0x68, 0x69
- **資料封包**: 32 bytes (seq + t_ms + btn + 12 int16)

### 後端

- **Framework**: FastAPI 0.109
- **WebSocket**: 30Hz 推送（降頻）
- **Buffer**: 60 秒（6000 samples）
- **Storage**: Parquet 格式
- **測試**: pytest 7.4

### 前端

- **圖表庫**: uPlot 1.6（時序圖）, ECharts 5.4（散點圖）
- **WebSocket**: 原生 API
- **HTTP**: Fetch API

---

## API 端點

### REST API

```
GET    /api/sessions              列出 sessions
GET    /api/sessions/{id}         Session 詳情
DELETE /api/sessions/{id}         刪除 session
POST   /api/recording/start       開始錄製
POST   /api/recording/stop        停止錄製
GET    /api/recording/status      錄製狀態
POST   /api/playback/load/{id}    載入 session
POST   /api/playback/play         開始播放
POST   /api/playback/pause        暫停播放
POST   /api/playback/stop         停止播放
POST   /api/playback/seek         跳轉時間
GET    /api/playback/status       播放狀態
GET    /api/segments              列出段落
GET    /api/segments/{id}         段落詳情
PATCH  /api/segments/{id}/label   更新標籤
GET    /api/stats                 統計資訊
POST   /api/stats/calibration/start  開始校正
```

### WebSocket

```
ws://localhost:8000/ws
```

訊息類型：
- `sample`: 即時樣本（30Hz）
- `stat`: 統計資訊（1Hz）
- `segment`: 段落事件（start/end）
- `label`: 標註事件
- `calibration`: 校正狀態

詳細說明請見 [API_SPEC.md](docs/stage2/API_SPEC.md)

---

## 測試

```bash
cd backend
pytest tests/ -v
```

測試涵蓋：
- 資料模型（RawSample, ProcessedSample）
- API 端點（Sessions, Recording, Playback, Segments, Stats）

---

## 故障排除

### Serial 連接失敗

1. 確認 Base Station 已連接到電腦
2. 確認序列埠權限：`sudo chmod 666 /dev/ttyUSB0`
3. 檢查 `backend/config.py` 中的 `SERIAL_PORT` 設定
4. 確認沒有其他程式佔用序列埠（如 Arduino IDE Serial Monitor）

### 無線傳輸不穩定

1. 確認 Remote Unit 和 Base Station 的 nRF24L01+ 天線朝向相同方向
2. 減少距離（建議 <10m）
3. 檢查電源穩定性（nRF24L01+ 對電源敏感）
4. 確認 Radio Channel 設定一致（firmware 中 `RF24_CHANNEL`）

### 前端無法連接後端

1. 確認後端已啟動：`http://localhost:8000/health`
2. 檢查 CORS 設定（`backend/config.py` 中的 `CORS_ORIGINS`）
3. 確認防火牆未阻擋 8000 port

### 投籃段落切分不準確

1. 調整 `Segmenter` 中的閾值（`backend/services/segmenter.py`）
2. 檢查 Gyro 校正狀態：`GET /api/stats/calibration/status`
3. 重新校正：`POST /api/stats/calibration/start`（設備保持靜止 2 秒）

---

## 開發

### 新增 API 端點

1. 在 `backend/api/routes/` 新增 router
2. 在 `main.py` 註冊 router
3. 在 `tests/test_api.py` 新增測試
4. 更新 `docs/stage2/API_SPEC.md`

### 新增前端頁面

1. 在 `frontend/` 新增 HTML
2. 復用 `js/api.js` 和 `js/websocket.js`
3. 引入 chart 元件

### 修改韌體

1. 編輯 `firmware/remote/main_remote.ino` 或 `firmware/base/main_base.ino`
2. 如有共用邏輯，抽取到 `firmware/common/`
3. 重新上傳韌體
4. 更新 `docs/stage2/SERIAL_FORMAT.md`（如格式有變）

---

## License

MIT License

---

## 作者

Han - Mechtronic 2 Project

---

## 版本歷史

### v1.0.0 (2025-12-22)

- 雙 MPU6050 IMU 採集
- nRF24L01+ 無線傳輸
- 即時資料處理與視覺化
- Session 錄製與回放
- 自動投籃段落切分
- 按鈕標註功能
- REST API 和 WebSocket
- 完整測試套件
- 技術文檔
