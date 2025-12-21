# Mechtronic 2 - Quick Start Guide

## Windows 環境啟動

### 1. 啟動後端
```powershell
cd C:\path\to\mechtronic_2\backend
..\venv\Scripts\Activate.ps1
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 瀏覽器訪問

| URL | 說明 |
|-----|------|
| `http://localhost:8000` | 前端主頁面 |
| `http://localhost:8000/api/docs` | Swagger API 文件 |
| `http://localhost:8000/api/redoc` | ReDoc API 文件 |
| `http://localhost:8000/health` | 健康檢查 |

### 3. Serial 連接
- Arduino IDE 必須**關閉**（釋放 COM port）
- 在前端點擊「連接」，選擇 COM8（或正確的 port）

---

## WSL 環境啟動

### 1. 啟動後端
```bash
cd ~/claude_project/mechtronic_2/backend
source ../venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. USB 轉發（WSL 無法直接存取 USB）
Windows PowerShell (管理員):
```powershell
usbipd list                    # 找到 Arduino 的 BUSID
usbipd bind --busid <BUSID>    # 首次綁定
usbipd attach --wsl --busid <BUSID>
```

WSL:
```bash
ls /dev/ttyACM* /dev/ttyUSB*   # 確認裝置出現
```

---

## 專案結構

```
mechtronic_2/
├── backend/                 # FastAPI 後端
│   ├── main.py             # 入口點
│   ├── api/
│   │   ├── routes/         # API 路由
│   │   │   ├── serial.py   # Serial 連接 API
│   │   │   ├── recording.py
│   │   │   └── ...
│   │   └── websocket.py    # WebSocket 端點
│   └── services/
│       ├── core.py         # 核心服務管理器
│       ├── serial_ingest.py
│       ├── processor.py
│       ├── recorder.py
│       └── ...
├── frontend/               # 原生 JS 前端
│   ├── index.html
│   └── js/
│       ├── app.js
│       ├── websocket.js
│       ├── tabs/
│       │   ├── live.js     # 即時監控
│       │   ├── replay.js   # 回放
│       │   └── analysis.js # 分析
│       └── components/
│           └── chart.js    # uPlot 圖表
├── firmware/               # Arduino 韌體
│   └── stage2_uno_receiver/
└── venv/                   # Python 虛擬環境
```

---

## API 端點

| Method | Endpoint | 說明 |
|--------|----------|------|
| GET | `/api/serial/ports` | 列出可用 Serial ports |
| POST | `/api/serial/connect?port=COM8` | 連接 Serial |
| POST | `/api/serial/disconnect` | 斷開連接 |
| GET | `/api/serial/status` | 連接狀態 |
| POST | `/api/recording/start` | 開始錄製 `{"name": "session_name"}` |
| POST | `/api/recording/stop` | 停止錄製 |
| GET | `/api/recording/status` | 錄製狀態 |
| WS | `/ws` | WebSocket 即時資料 |

---

## PFC 任務系統

### 查看專案任務
```bash
cd ~/.claude/neuromorphic && python3 -c "
import sys; sys.path.insert(0, '.')
from servers.memory import get_project_context
ctx = get_project_context('mechtronic_2')
for t in ctx.get('active_tasks', []):
    print(f'{t[\"id\"][:8]}: {t[\"status\"]} - {t[\"description\"][:50]}')"
```

### 更新任務狀態
```bash
cd ~/.claude/neuromorphic && python3 -c "
import sys; sys.path.insert(0, '.')
from servers.tasks import update_task_status
update_task_status('TASK_ID', 'done', result='完成說明')"
```

---

## 常見問題

### PowerShell 無法執行 Activate.ps1
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Serial port 被佔用
- 關閉 Arduino IDE
- 關閉 Serial Monitor
- 檢查其他程式是否佔用

### WebSocket 403 錯誤
確認 `backend/main.py` 有註冊 WebSocket:
```python
app.websocket("/ws")(websocket_endpoint)
```

### 前端沒有資料顯示
1. 確認 Serial 已連接（檢查後端 log）
2. 開啟瀏覽器 DevTools Console 查看錯誤
3. 強制重新整理: `Ctrl+Shift+R`

---

## 修改後同步到 Windows

需要複製的檔案（從 WSL 到 Windows）:
```
backend/services/core.py
backend/services/serial_ingest.py
backend/api/routes/serial.py
backend/main.py
frontend/js/tabs/live.js
frontend/js/components/chart.js
```
