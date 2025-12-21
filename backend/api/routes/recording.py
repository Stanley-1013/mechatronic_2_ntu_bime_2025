"""
Recording API Routes
錄製控制端點
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.core import CoreService

router = APIRouter(prefix="/api/recording", tags=["recording"])


class StartRequest(BaseModel):
    """開始錄製請求"""
    name: str
    imu_positions: Optional[dict] = {
        "mpu1": "hand_back",
        "mpu2": "bicep"
    }


@router.post("/start")
async def start_recording(req: StartRequest):
    """
    開始錄製

    Args:
        req: StartRequest（包含 name 和 imu_positions）

    Returns:
        dict: 錄製狀態和 session_id

    Raises:
        HTTPException 400: 已經在錄製中
    """
    core = CoreService.get_instance()

    try:
        session_id = core.start_recording(req.name, req.imu_positions)
        return {
            "session_id": session_id,
            "status": "recording",
            "name": req.name
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/stop")
async def stop_recording():
    """
    停止錄製

    Returns:
        dict: 錄製結果（metadata）

    Raises:
        HTTPException 400: 未在錄製中
    """
    core = CoreService.get_instance()

    try:
        meta = core.stop_recording()
        return {
            "status": "stopped",
            "metadata": meta
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/status")
async def recording_status():
    """
    錄製狀態

    Returns:
        dict: 目前錄製狀態
    """
    core = CoreService.get_instance()
    recorder = core.recorder

    return {
        "is_recording": recorder.is_recording,
        "current_session": recorder.current_session,
        "sample_count": recorder.sample_count
    }
