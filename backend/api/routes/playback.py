"""
Playback API Routes
回放控制端點
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.core import CoreService
from services.player import PlayerState

router = APIRouter(prefix="/api/playback", tags=["playback"])


class LoadRequest(BaseModel):
    """載入 session 請求"""
    pass


class SeekRequest(BaseModel):
    """跳轉請求"""
    time_ms: int


@router.post("/load/{session_id}")
async def load_session(session_id: str):
    """
    載入 session

    Args:
        session_id: Session ID

    Returns:
        dict: 載入結果

    Raises:
        HTTPException 404: Session 不存在或載入失敗
    """
    core = CoreService.get_instance()
    player = core.player

    success = player.load_session(session_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"Failed to load session {session_id}")

    return {
        "session_id": session_id,
        "status": "loaded",
        "session_info": player.loaded_session
    }


@router.post("/play")
async def play():
    """
    開始播放

    Note: 實際播放需要透過 WebSocket 連接

    Returns:
        dict: 播放狀態

    Raises:
        HTTPException 400: 未載入 session
    """
    core = CoreService.get_instance()
    player = core.player

    if not player.loaded_session:
        raise HTTPException(status_code=400, detail="No session loaded")

    # 實際播放由 WebSocket handler 控制
    # 這裡僅回傳狀態
    return {
        "status": "playing",
        "session_id": player.loaded_session.id
    }


@router.post("/pause")
async def pause():
    """
    暫停播放

    Returns:
        dict: 暫停狀態
    """
    core = CoreService.get_instance()
    player = core.player

    player.pause()
    return {
        "status": "paused"
    }


@router.post("/stop")
async def stop():
    """
    停止播放

    Returns:
        dict: 停止狀態
    """
    core = CoreService.get_instance()
    player = core.player

    player.stop()
    return {
        "status": "stopped"
    }


@router.post("/seek")
async def seek(req: SeekRequest):
    """
    跳轉到指定時間

    Args:
        req: SeekRequest（包含 time_ms）

    Returns:
        dict: 跳轉結果

    Raises:
        HTTPException 400: 未載入 session
    """
    core = CoreService.get_instance()
    player = core.player

    if not player.loaded_session:
        raise HTTPException(status_code=400, detail="No session loaded")

    player.seek(req.time_ms)
    return {
        "status": "seeked",
        "time_ms": req.time_ms
    }


@router.get("/status")
async def playback_status():
    """
    回放狀態

    Returns:
        dict: 目前回放狀態
    """
    core = CoreService.get_instance()
    player = core.player

    return {
        "is_playing": player.is_playing,
        "is_paused": player.is_paused,
        "current_time_ms": player.current_time_ms,
        "total_duration_ms": player.total_duration_ms,
        "loaded_session": player.loaded_session
    }
