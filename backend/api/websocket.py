"""
WebSocket Endpoint for Real-time Data Push
即時資料推送 WebSocket 端點
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Set, Dict, Any, Optional
import asyncio
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class SampleBroadcaster:
    """
    降頻廣播器
    將高頻資料（100Hz）降頻到合理的推送頻率（25-50Hz）
    """

    def __init__(self, target_hz: int = 30):
        """
        初始化廣播器

        Args:
            target_hz: 目標推送頻率（預設 30Hz）
        """
        self.target_hz = target_hz
        self.interval_ms = 1000 / target_hz
        self.last_send_ms = 0

    def should_send(self, t_ms: int) -> bool:
        """
        判斷是否應該發送此樣本

        Args:
            t_ms: 當前樣本時間戳（毫秒）

        Returns:
            是否應該發送
        """
        if t_ms - self.last_send_ms >= self.interval_ms:
            self.last_send_ms = t_ms
            return True
        return False

    def reset(self):
        """重置計時器"""
        self.last_send_ms = 0


class ConnectionManager:
    """
    WebSocket 連線管理器
    管理所有活躍的 WebSocket 連線並處理廣播
    """

    def __init__(self, broadcast_hz: int = 30):
        """
        初始化連線管理器

        Args:
            broadcast_hz: 廣播頻率（預設 30Hz）
        """
        self.active_connections: Set[WebSocket] = set()
        self.broadcaster = SampleBroadcaster(target_hz=broadcast_hz)

    async def connect(self, websocket: WebSocket):
        """
        接受新連線

        Args:
            websocket: WebSocket 連線物件
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """
        斷開連線

        Args:
            websocket: WebSocket 連線物件
        """
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """
        廣播訊息給所有連線

        Args:
            message: 要廣播的訊息（字典格式）
        """
        if not self.active_connections:
            return

        data = json.dumps(message)
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception as e:
                logger.warning(f"Failed to send to connection: {e}")
                disconnected.append(connection)

        # 清理斷線的連線
        for conn in disconnected:
            self.disconnect(conn)

    async def send_sample(self, sample: Dict[str, Any]):
        """
        發送感測資料（降頻）

        訊息格式:
        {
            "type": "sample",
            "data": {
                "seq": 1234,
                "t_remote_ms": 100500,
                "btn": 0,
                "g1_mag": 45.2,
                "g2_mag": 38.7,
                "a1_mag": 1.02,
                "a2_mag": 0.98
            }
        }

        Args:
            sample: 樣本資料字典
        """
        # 降頻檢查
        t_ms = sample.get('t_remote_ms', 0)
        if not self.broadcaster.should_send(t_ms):
            return

        message = {
            "type": "sample",
            "data": sample
        }
        await self.broadcast(message)

    async def send_stat(self, stats: Dict[str, Any]):
        """
        發送統計資訊

        訊息格式:
        {
            "type": "stat",
            "data": {
                "pps": 98.5,
                "dropped": 2,
                "parse_err": 0,
                "buffer_size": 5000
            }
        }

        Args:
            stats: 統計資料字典
        """
        message = {
            "type": "stat",
            "data": stats
        }
        await self.broadcast(message)

    async def send_segment_event(
        self,
        event: str,
        segment: Dict[str, Any]
    ):
        """
        發送段落事件

        訊息格式:
        {
            "type": "segment",
            "event": "start" | "end",
            "data": {
                "shot_id": "abc123",
                "t_start_ms": 100000,
                "t_end_ms": 100800,
                "duration_ms": 800,
                "features": {...},
                "label": "unknown"
            }
        }

        Args:
            event: 事件類型 ("start" 或 "end")
            segment: 段落資料字典
        """
        message = {
            "type": "segment",
            "event": event,
            "data": segment
        }
        await self.broadcast(message)

    async def send_label_event(
        self,
        shot_id: str,
        label: str,
        t_label_ms: int
    ):
        """
        發送標籤事件

        訊息格式:
        {
            "type": "label",
            "data": {
                "shot_id": "abc123",
                "label": "good",
                "t_label_ms": 101500
            }
        }

        Args:
            shot_id: 段落 ID
            label: 標籤名稱
            t_label_ms: 標籤時間戳（毫秒）
        """
        message = {
            "type": "label",
            "data": {
                "shot_id": shot_id,
                "label": label,
                "t_label_ms": t_label_ms
            }
        }
        await self.broadcast(message)

    @property
    def connection_count(self) -> int:
        """
        目前連線數

        Returns:
            活躍連線數量
        """
        return len(self.active_connections)


# 全域連線管理器（單例）
manager = ConnectionManager(broadcast_hz=30)


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 端點處理函數

    此函數應註冊到 FastAPI 應用：
    app.websocket("/ws")(websocket_endpoint)

    Args:
        websocket: FastAPI WebSocket 物件
    """
    await manager.connect(websocket)

    try:
        while True:
            # 保持連線並接收客戶端訊息
            data = await websocket.receive_text()

            # 解析客戶端命令（可選功能）
            try:
                command = json.loads(data)
                await handle_client_command(websocket, command)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from client: {data}")
            except Exception as e:
                logger.error(f"Error handling client command: {e}")

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def handle_client_command(websocket: WebSocket, command: Dict[str, Any]):
    """
    處理客戶端命令（可選功能）

    支援的命令範例：
    - {"cmd": "ping"} -> 回應 pong
    - {"cmd": "get_status"} -> 回應目前狀態

    Args:
        websocket: 發送命令的 WebSocket 連線
        command: 命令字典
    """
    cmd = command.get("cmd")

    if cmd == "ping":
        response = {
            "type": "pong",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send_text(json.dumps(response))

    elif cmd == "get_status":
        response = {
            "type": "status",
            "data": {
                "connections": manager.connection_count,
                "broadcast_hz": manager.broadcaster.target_hz,
                "timestamp": datetime.now().isoformat()
            }
        }
        await websocket.send_text(json.dumps(response))

    else:
        logger.warning(f"Unknown command: {cmd}")


# 便利函數：供其他模組使用

def get_manager() -> ConnectionManager:
    """
    取得全域連線管理器

    Returns:
        ConnectionManager 實例
    """
    return manager


async def push_sample(sample: Dict[str, Any]):
    """
    推送樣本資料（降頻）

    Args:
        sample: 樣本資料
    """
    await manager.send_sample(sample)


async def push_stats(stats: Dict[str, Any]):
    """
    推送統計資訊

    Args:
        stats: 統計資料
    """
    await manager.send_stat(stats)


async def push_segment_start(segment: Dict[str, Any]):
    """
    推送段落開始事件

    Args:
        segment: 段落資料
    """
    await manager.send_segment_event("start", segment)


async def push_segment_end(segment: Dict[str, Any]):
    """
    推送段落結束事件

    Args:
        segment: 段落資料
    """
    await manager.send_segment_event("end", segment)


async def push_label(shot_id: str, label: str, t_label_ms: int):
    """
    推送標籤事件

    Args:
        shot_id: 段落 ID
        label: 標籤名稱
        t_label_ms: 標籤時間戳（毫秒）
    """
    await manager.send_label_event(shot_id, label, t_label_ms)
