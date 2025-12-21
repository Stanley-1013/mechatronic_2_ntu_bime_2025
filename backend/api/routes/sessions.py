"""
Sessions API Routes
Session 管理端點
"""
from fastapi import APIRouter, HTTPException
from typing import List
from pathlib import Path
import shutil

from services.core import CoreService
from services.player import SessionInfo

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=List[SessionInfo])
async def list_sessions():
    """
    列出所有 sessions

    Returns:
        List[SessionInfo]: Session 摘要列表，按建立時間降序
    """
    core = CoreService.get_instance()
    player = core.player
    return player.list_sessions()


@router.get("/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """
    取得 session 詳情

    Args:
        session_id: Session ID

    Returns:
        SessionInfo: Session 詳細資訊

    Raises:
        HTTPException 404: Session 不存在
    """
    core = CoreService.get_instance()
    player = core.player

    sessions = player.list_sessions()
    for session in sessions:
        if session.id == session_id:
            return session

    raise HTTPException(status_code=404, detail=f"Session {session_id} not found")


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """
    刪除 session

    Args:
        session_id: Session ID

    Returns:
        dict: 刪除結果

    Raises:
        HTTPException 404: Session 不存在
        HTTPException 500: 刪除失敗
    """
    core = CoreService.get_instance()
    player = core.player

    # 找到 session 路徑
    sessions = player.list_sessions()
    session_path = None

    for session in sessions:
        if session.id == session_id:
            session_path = Path(session.path)
            break

    if not session_path or not session_path.exists():
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    # 刪除目錄
    try:
        shutil.rmtree(session_path)
        return {
            "session_id": session_id,
            "status": "deleted"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")
