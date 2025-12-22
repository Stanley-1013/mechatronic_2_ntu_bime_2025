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


class PlayRequest(BaseModel):
    """開始播放請求"""
    speed: float = 1.0


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

    # 轉換 SessionInfo 為可序列化的 dict
    session_info = {
        "id": player.loaded_session.id,
        "name": player.loaded_session.name,
        "created_at": player.loaded_session.created_at,
        "duration_ms": player.loaded_session.duration_ms,
        "sample_count": player.loaded_session.sample_count,
    }

    return {
        "session_id": session_id,
        "status": "loaded",
        "session_info": session_info
    }


@router.post("/play/{session_id}")
async def play(session_id: str, req: PlayRequest = None):
    """
    開始播放指定 session（透過 WebSocket 推送資料）

    Args:
        session_id: Session ID
        req: PlayRequest（包含 speed）

    Returns:
        dict: 播放狀態

    Raises:
        HTTPException 400: 已在播放中或 session 載入失敗
    """
    core = CoreService.get_instance()
    speed = req.speed if req else 1.0

    try:
        await core.start_playback(session_id, speed)
        return {
            "status": "playing",
            "session_id": session_id,
            "speed": speed
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/pause")
async def pause():
    """
    暫停播放

    Returns:
        dict: 暫停狀態

    Raises:
        HTTPException 400: 未在播放中
    """
    core = CoreService.get_instance()

    try:
        core.pause_playback()
        return {"status": "paused"}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/resume")
async def resume():
    """
    繼續播放

    Returns:
        dict: 播放狀態

    Raises:
        HTTPException 400: 未在暫停中
    """
    core = CoreService.get_instance()

    try:
        core.resume_playback()
        return {"status": "playing"}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop")
async def stop():
    """
    停止播放

    Returns:
        dict: 停止狀態
    """
    core = CoreService.get_instance()
    core.stop_playback()
    return {"status": "stopped"}


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

    core.seek_playback(req.time_ms)
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

    session_info = None
    if player.loaded_session:
        session_info = {
            "id": player.loaded_session.id,
            "name": player.loaded_session.name,
            "created_at": player.loaded_session.created_at,
            "duration_ms": player.loaded_session.duration_ms,
            "sample_count": player.loaded_session.sample_count,
        }

    return {
        "is_playing": player.is_playing,
        "is_paused": player.is_paused,
        "current_time_ms": player.current_time_ms,
        "total_duration_ms": player.total_duration_ms,
        "loaded_session": session_info
    }
