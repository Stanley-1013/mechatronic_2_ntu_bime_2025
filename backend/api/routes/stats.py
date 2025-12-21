"""
Stats API Routes
統計資訊與校正端點
"""
from fastapi import APIRouter
from typing import Optional

from services.core import CoreService

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
async def get_stats():
    """
    取得統計資訊

    Returns:
        dict: 統計資料（包含 sessions, segments, samples, shots）
    """
    core = CoreService.get_instance()
    return core.get_stats()


@router.post("/calibration/start")
async def start_calibration(duration_sec: Optional[float] = 2.0):
    """
    開始 Gyro 校正

    校正期間應保持設備靜止

    Args:
        duration_sec: 校正持續時間（秒）

    Returns:
        dict: 校正狀態
    """
    core = CoreService.get_instance()
    processor = core.processor

    processor.start_calibration(duration_sec=duration_sec)

    return {
        "status": "calibrating",
        "duration_sec": duration_sec,
        "message": "Keep device still during calibration"
    }


@router.get("/calibration/status")
async def calibration_status():
    """
    校正狀態

    Returns:
        dict: 校正狀態和偏移量
    """
    core = CoreService.get_instance()
    processor = core.processor

    is_calibrating = processor.is_calibrating()
    offset = processor.calibration_offset

    return {
        "is_calibrating": is_calibrating,
        "offset": offset,
        "status": "calibrating" if is_calibrating else "idle"
    }
