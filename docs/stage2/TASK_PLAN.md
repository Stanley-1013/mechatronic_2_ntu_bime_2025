# Stage 2 Task Plan

> PFC 任務規劃 - 2025-12-22
>
> 主任務 ID: `3d0f9cf8`

## 執行計畫總覽

| Phase | 描述 | 任務數 | 依賴 | 預期產出 |
|-------|------|--------|------|----------|
| Phase 1 | Uno Serial 格式修改 | 3 | - | 韌體更新、格式文檔 |
| Phase 2 | 後端核心架構 | 5 | Phase 1 | Serial Ingest、資料處理 |
| Phase 3 | 後端進階功能 | 5 | Phase 2 | 錄製/回放、切段、標註 |
| Phase 4 | REST API | 5 | Phase 3 | 完整 API 端點 |
| Phase 5 | 前端 SPA | 5 | Phase 4 | React 應用 |
| Phase 6 | 整合測試與文檔 | 4 | Phase 5 | 測試、文檔 |

**總計**: 27 個子任務

---

## Phase 1: Uno Serial 輸出格式修改

**Phase ID**: `f9cdf120`
**目標**: 將現有多行可讀格式改為標準 CSV（100Hz，每筆一行）

### 子任務列表

| 任務 ID | 描述 | 依賴 | 預期產出 |
|---------|------|------|----------|
| `3f91c5d9` | 修改 main_base.ino: 移除 print_packet_live()，新增 print_csv_line() | - | `firmware/base/main_base.ino` |
| `1948ffa4` | 修改 stats.cpp: 統計行以 # 開頭 | 3f91c5d9 | `firmware/base/stats.cpp` |
| `c5353648` | 建立 SERIAL_FORMAT.md 文檔 | 1948ffa4 | `docs/stage2/SERIAL_FORMAT.md` |

### CSV 格式規格（SRS 4.2）

```
seq,t_remote_ms,btn,ax1,ay1,az1,gx1,gy1,gz1,ax2,ay2,az2,gx2,gy2,gz2
1234,100500,0,16384,-200,16000,50,-30,10,16200,-150,16100,45,-25,8
```

- Baud: 115200
- 頻率: 100Hz（每 10ms 一行）
- 狀態/統計行以 `#` 開頭

---

## Phase 2: FastAPI 後端核心架構

**Phase ID**: `36b04cac`
**目標**: 建立後端基礎架構，實作 Serial 讀取與資料處理

### 子任務列表

| 任務 ID | 描述 | 依賴 | 預期產出 |
|---------|------|------|----------|
| `f01ffa6a` | 建立 backend/ 專案結構 | - | 目錄結構 + 配置檔 |
| `44821a56` | 實作 services/serial_ingest.py | f01ffa6a | Serial 讀取模組 |
| `bf02f452` | 實作 services/processor.py | 44821a56 | 資料前處理模組 |
| `6c3afb19` | 實作 services/ring_buffer.py | 44821a56 | 60秒滾動緩衝區 |
| `87028a3f` | 實作 models/sample.py + stats.py | f01ffa6a | Pydantic 模型 |

### 專案結構

```
backend/
├── main.py              # FastAPI app
├── config.py            # 配置參數
├── models/
│   ├── sample.py        # Sample 資料模型
│   └── stats.py         # 統計模型
├── services/
│   ├── serial_ingest.py # Serial 讀取
│   ├── processor.py     # 資料處理
│   └── ring_buffer.py   # 滾動緩衝區
└── api/
    ├── routes/          # REST 端點
    └── websocket.py     # WS 推送
```

---

## Phase 3: 後端進階功能

**Phase ID**: `ec0ac1ce`
**目標**: 實作錄製/回放、投籃切段、按鈕標註

### 子任務列表

| 任務 ID | 描述 | 依賴 | 預期產出 |
|---------|------|------|----------|
| `3b1c2fa3` | 實作 services/recorder.py | - | 錄製控制模組 |
| `8cbc0250` | 實作 services/player.py | 3b1c2fa3 | 回放控制模組 |
| `bf523d23` | 實作 services/segmenter.py | - | 投籃切段狀態機 |
| `9d3b84cd` | 實作 services/labeler.py | bf523d23 | 標籤對齊模組 |
| `151e6f9a` | 實作 api/websocket.py | 3b1c2fa3, bf523d23 | WebSocket 端點 |

### 切段狀態機（FR-P7）

```
IDLE -> ACTIVE (|a| > threshold_g)
ACTIVE -> COOLDOWN (|a| < threshold_g 持續 cooldown_ms)
COOLDOWN -> IDLE (cooldown 結束，儲存段落)
```

### 標註邏輯（FR-L1~L3）

- btn level 變化 -> 去抖 250ms -> label_good 事件
- 標籤對齊到最近段落（0.2~3.0秒內）

---

## Phase 4: REST API 端點

**Phase ID**: `94f4af49`
**目標**: 實作完整的 REST API

### 子任務列表

| 任務 ID | 描述 | 依賴 | 預期產出 |
|---------|------|------|----------|
| `b8de4cbc` | 實作 sessions.py | - | Session CRUD |
| `a2d5bc95` | 實作 recording.py | - | 錄製控制 API |
| `530b97d9` | 實作 playback.py | - | 回放控制 API |
| `08dbf000` | 實作 segments.py | - | 段落查詢/標註 |
| `c2b44da7` | 實作 stats.py | - | 統計 API |

### API 端點清單

| Method | Path | 描述 |
|--------|------|------|
| GET | /sessions | 列出所有 session |
| GET | /sessions/{id} | 取得 session 詳情 |
| DELETE | /sessions/{id} | 刪除 session |
| POST | /recording/start | 開始錄製 |
| POST | /recording/stop | 停止錄製 |
| POST | /playback/load/{id} | 載入 session |
| POST | /playback/play | 播放 |
| POST | /playback/pause | 暫停 |
| POST | /playback/seek | 跳轉 |
| GET | /segments | 列出段落 |
| PATCH | /segments/{id}/label | 更新標籤 |
| GET | /stats | 取得統計資訊 |

---

## Phase 5: 前端 SPA 開發

**Phase ID**: `8a6107b2`
**目標**: 使用 React + Vite + Tailwind 開發三頁籤 SPA

### 子任務列表

| 任務 ID | 描述 | 依賴 | 預期產出 |
|---------|------|------|----------|
| `3faee323` | 初始化 frontend/ 專案 | - | Vite + React 專案 |
| `28fac057` | 實作共用元件 | 3faee323 | ConnectionStatus, Chart |
| `e89332c3` | 實作 Live 頁籤 | 28fac057 | 即時資料頁面 |
| `c42978f3` | 實作 Replay 頁籤 | 28fac057 | 回放頁面 |
| `3b00761f` | 實作 Analysis 頁籤 | 28fac057 | 分析頁面 |

### 前端結構

```
frontend/
├── src/
│   ├── components/
│   │   ├── ConnectionStatus.tsx
│   │   ├── TimeSeriesChart.tsx
│   │   └── SegmentCard.tsx
│   ├── pages/
│   │   ├── LiveTab.tsx
│   │   ├── ReplayTab.tsx
│   │   └── AnalysisTab.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   └── useSessions.ts
│   └── App.tsx
├── package.json
└── vite.config.ts
```

---

## Phase 6: 整合測試與文檔

**Phase ID**: `2ad2544f`
**目標**: 完成測試與技術文檔

### 子任務列表

| 任務 ID | 描述 | 依賴 | 預期產出 |
|---------|------|------|----------|
| `1f1c16ed` | 建立 tests/ 測試套件 | - | pytest 測試 |
| `002b10ea` | 建立 API_SPEC.md | - | OpenAPI 文檔 |
| `0c5ad0ec` | 建立 ARCHITECTURE.md | - | 架構圖 |
| `349d6158` | 建立 README 和啟動腳本 | 以上全部 | docker-compose.yml |

---

## 驗證標準

### Phase 1 驗證
- [ ] Serial 輸出為標準 CSV 格式
- [ ] 頻率達到 100Hz
- [ ] 統計行以 # 開頭

### Phase 2 驗證
- [ ] 能正確解析 CSV 資料
- [ ] Ring Buffer 維持 60 秒資料
- [ ] 單位換算正確（g, dps）

### Phase 3 驗證
- [ ] 錄製/回放功能正常
- [ ] 切段邏輯符合規格
- [ ] 標籤對齊準確

### Phase 4 驗證
- [ ] 所有 API 端點可用
- [ ] 回應格式符合規格

### Phase 5 驗證
- [ ] 三個頁籤功能完整
- [ ] WebSocket 連線穩定
- [ ] 圖表即時更新

### Phase 6 驗證
- [ ] 測試覆蓋率 >= 70%
- [ ] 文檔完整

---

## 執行說明

### 開始執行

對 Claude Code 說：
```
執行 Phase 1 任務
```

### 查看進度

```python
from servers.tasks import get_task_progress
progress = get_task_progress('3d0f9cf8')
print(progress)
```

### 恢復任務

如果中斷，說：
```
繼續任務 3d0f9cf8
```

---

**文件版本**: 1.0
**建立日期**: 2025-12-22
**PFC Agent**: Claude Opus 4.5
