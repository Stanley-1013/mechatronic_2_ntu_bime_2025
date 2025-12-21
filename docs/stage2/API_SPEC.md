# API 規格文檔

## 基本資訊

- **Base URL**: `http://localhost:8000`
- **WebSocket**: `ws://localhost:8000/ws`
- **文件格式**: JSON
- **API 文檔**: `http://localhost:8000/api/docs` (Swagger UI)

## 認證

目前無需認證（本地開發）

---

## REST API

### 1. Sessions

#### GET /api/sessions

列出所有錄製的 sessions

**Response**:
```json
[
  {
    "id": "session_20251222_103000",
    "name": "練習1",
    "path": "/path/to/sessions/session_20251222_103000",
    "created_at": "2025-12-22T10:30:00Z",
    "duration_ms": 60000,
    "sample_count": 6000,
    "imu_positions": {
      "mpu1": "hand_back",
      "mpu2": "bicep"
    }
  }
]
```

#### GET /api/sessions/{session_id}

取得 session 詳情

**Parameters**:
- `session_id` (path): Session ID

**Response**:
```json
{
  "id": "session_20251222_103000",
  "name": "練習1",
  "path": "/path/to/sessions/session_20251222_103000",
  "created_at": "2025-12-22T10:30:00Z",
  "duration_ms": 60000,
  "sample_count": 6000,
  "imu_positions": {
    "mpu1": "hand_back",
    "mpu2": "bicep"
  }
}
```

**Error Responses**:
- `404 Not Found`: Session 不存在

#### DELETE /api/sessions/{session_id}

刪除 session

**Parameters**:
- `session_id` (path): Session ID

**Response**:
```json
{
  "session_id": "session_20251222_103000",
  "status": "deleted"
}
```

**Error Responses**:
- `404 Not Found`: Session 不存在
- `500 Internal Server Error`: 刪除失敗

---

### 2. Recording

#### POST /api/recording/start

開始錄製

**Request Body**:
```json
{
  "name": "練習1",
  "imu_positions": {
    "mpu1": "hand_back",
    "mpu2": "bicep"
  }
}
```

**Response**:
```json
{
  "session_id": "session_20251222_103000",
  "status": "recording",
  "name": "練習1"
}
```

**Error Responses**:
- `400 Bad Request`: 已經在錄製中

#### POST /api/recording/stop

停止錄製

**Response**:
```json
{
  "status": "stopped",
  "metadata": {
    "session_id": "session_20251222_103000",
    "name": "練習1",
    "created_at": "2025-12-22T10:30:00Z",
    "duration_ms": 60000,
    "sample_count": 6000
  }
}
```

**Error Responses**:
- `400 Bad Request`: 未在錄製中

#### GET /api/recording/status

取得錄製狀態

**Response**:
```json
{
  "is_recording": true,
  "current_session": "session_20251222_103000",
  "sample_count": 1234
}
```

---

### 3. Playback

#### POST /api/playback/load/{session_id}

載入 session 供回放

**Parameters**:
- `session_id` (path): Session ID

**Response**:
```json
{
  "session_id": "session_20251222_103000",
  "status": "loaded",
  "session_info": {
    "id": "session_20251222_103000",
    "name": "練習1",
    "duration_ms": 60000,
    "sample_count": 6000
  }
}
```

**Error Responses**:
- `404 Not Found`: Session 不存在或載入失敗

#### POST /api/playback/play

開始播放（需先載入 session）

**Response**:
```json
{
  "status": "playing",
  "session_id": "session_20251222_103000"
}
```

**Error Responses**:
- `400 Bad Request`: 未載入 session

**Note**: 實際播放資料透過 WebSocket 推送

#### POST /api/playback/pause

暫停播放

**Response**:
```json
{
  "status": "paused"
}
```

#### POST /api/playback/stop

停止播放

**Response**:
```json
{
  "status": "stopped"
}
```

#### POST /api/playback/seek

跳轉到指定時間

**Request Body**:
```json
{
  "time_ms": 30000
}
```

**Response**:
```json
{
  "status": "seeked",
  "time_ms": 30000
}
```

**Error Responses**:
- `400 Bad Request`: 未載入 session

#### GET /api/playback/status

取得播放狀態

**Response**:
```json
{
  "is_playing": true,
  "is_paused": false,
  "current_time_ms": 15000,
  "total_duration_ms": 60000,
  "loaded_session": {
    "id": "session_20251222_103000",
    "name": "練習1"
  }
}
```

---

### 4. Segments

#### GET /api/segments

列出所有投籃段落

**Response**:
```json
[
  {
    "shot_id": "shot_abc123",
    "t_start_ms": 10000,
    "t_end_ms": 10800,
    "duration_ms": 800,
    "label": "unknown",
    "sample_count": 80,
    "features": {
      "g1_rms": 45.2,
      "g1_peak": 120.5,
      "g2_rms": 38.7,
      "g2_peak": 95.3,
      "dg_rms": 12.1
    }
  }
]
```

**Note**: 不含 samples（避免傳輸過大）

#### GET /api/segments/{segment_id}

取得段落詳情（含 samples）

**Parameters**:
- `segment_id` (path): Segment ID (shot_id)

**Response**:
```json
{
  "shot_id": "shot_abc123",
  "t_start_ms": 10000,
  "t_end_ms": 10800,
  "duration_ms": 800,
  "label": "unknown",
  "sample_count": 80,
  "features": {
    "g1_rms": 45.2,
    "g1_peak": 120.5
  },
  "samples": [
    {
      "seq": 1234,
      "t_remote_ms": 10000,
      "btn": 0,
      "g1_mag": 45.2,
      "g2_mag": 38.7
    }
  ]
}
```

**Error Responses**:
- `404 Not Found`: 段落不存在

#### PATCH /api/segments/{segment_id}/label

更新段落標籤

**Parameters**:
- `segment_id` (path): Segment ID (shot_id)

**Request Body**:
```json
{
  "label": "good"
}
```

**Valid labels**: `good`, `bad`, `unknown`

**Response**:
```json
{
  "segment_id": "shot_abc123",
  "label": "good",
  "status": "updated"
}
```

**Error Responses**:
- `400 Bad Request`: 無效的標籤
- `404 Not Found`: 段落不存在

---

### 5. Stats

#### GET /api/stats

取得統計資訊

**Response**:
```json
{
  "serial": {
    "pps": 98.5,
    "dropped": 2,
    "parse_err": 0
  },
  "buffer_size": 5000,
  "segments_count": 15,
  "sessions_count": 3,
  "is_recording": false,
  "is_playing": false
}
```

#### POST /api/stats/calibration/start

開始 Gyro 校正（保持設備靜止）

**Query Parameters**:
- `duration_sec` (optional): 校正持續時間（預設 2.0 秒）

**Response**:
```json
{
  "status": "calibrating",
  "duration_sec": 2.0,
  "message": "Keep device still during calibration"
}
```

#### GET /api/stats/calibration/status

取得校正狀態

**Response**:
```json
{
  "is_calibrating": false,
  "offset": {
    "gx1": 0.12,
    "gy1": -0.08,
    "gz1": 0.03,
    "gx2": 0.15,
    "gy2": -0.10,
    "gz2": 0.05
  },
  "status": "idle"
}
```

---

## WebSocket API

### 連線

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  console.log('WebSocket 已連線');
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  handleMessage(msg);
};
```

### 訊息類型

#### 1. sample

即時樣本資料（30Hz 降頻推送）

```json
{
  "type": "sample",
  "data": {
    "seq": 1234,
    "t_remote_ms": 100500,
    "btn": 0,
    "g1_mag": 45.2,
    "g2_mag": 38.7,
    "a1_mag": 1.02,
    "a2_mag": 0.98,
    "gx1_dps": 10.5,
    "gy1_dps": -5.2,
    "gz1_dps": 2.1,
    "gx2_dps": 8.3,
    "gy2_dps": -4.8,
    "gz2_dps": 1.9
  }
}
```

#### 2. stat

統計資訊更新（每秒一次）

```json
{
  "type": "stat",
  "data": {
    "pps": 98.5,
    "dropped": 2,
    "parse_err": 0,
    "buffer_size": 5000
  }
}
```

#### 3. segment

段落事件（投籃開始/結束）

```json
{
  "type": "segment",
  "event": "start",
  "data": {
    "shot_id": "shot_abc123",
    "t_start_ms": 10000
  }
}
```

```json
{
  "type": "segment",
  "event": "end",
  "data": {
    "shot_id": "shot_abc123",
    "t_start_ms": 10000,
    "t_end_ms": 10800,
    "duration_ms": 800,
    "features": {
      "g1_rms": 45.2,
      "g1_peak": 120.5
    }
  }
}
```

#### 4. label

標註事件（按鈕觸發）

```json
{
  "type": "label",
  "data": {
    "shot_id": "shot_abc123",
    "label": "good",
    "t_label_ms": 101500
  }
}
```

#### 5. calibration

校正狀態更新

```json
{
  "type": "calibration",
  "data": {
    "status": "completed",
    "offset": {
      "gx1": 0.12,
      "gy1": -0.08,
      "gz1": 0.03
    }
  }
}
```

---

## 健康檢查

#### GET /health

**Response**:
```json
{
  "status": "ok",
  "service": "mechtronic-2-backend",
  "version": "1.0.0"
}
```

#### GET /

根端點

**Response**:
```json
{
  "message": "Mechtronic 2 Backend API",
  "docs": "/api/docs",
  "version": "1.0.0"
}
```

---

## 錯誤回應格式

所有錯誤遵循標準 HTTP 狀態碼，並包含詳細訊息：

```json
{
  "detail": "Error message here"
}
```

常見狀態碼：
- `400 Bad Request`: 請求參數錯誤或狀態不符
- `404 Not Found`: 資源不存在
- `500 Internal Server Error`: 伺服器內部錯誤

---

## 使用範例

### 錄製 Session

```javascript
// 1. 開始錄製
const startRes = await fetch('http://localhost:8000/api/recording/start', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: '練習1',
    imu_positions: { mpu1: 'hand_back', mpu2: 'bicep' }
  })
});
const { session_id } = await startRes.json();

// 2. 連接 WebSocket 接收即時資料
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === 'sample') {
    // 更新圖表
    updateChart(msg.data);
  }
};

// 3. 停止錄製
await fetch('http://localhost:8000/api/recording/stop', { method: 'POST' });
```

### 回放 Session

```javascript
// 1. 載入 session
await fetch(`http://localhost:8000/api/playback/load/${session_id}`, {
  method: 'POST'
});

// 2. 開始播放
await fetch('http://localhost:8000/api/playback/play', { method: 'POST' });

// 3. 跳轉到 30 秒
await fetch('http://localhost:8000/api/playback/seek', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ time_ms: 30000 })
});
```

### 標註投籃段落

```javascript
// 1. 取得所有段落
const segments = await fetch('http://localhost:8000/api/segments')
  .then(r => r.json());

// 2. 更新標籤
await fetch(`http://localhost:8000/api/segments/${shot_id}/label`, {
  method: 'PATCH',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ label: 'good' })
});
```
