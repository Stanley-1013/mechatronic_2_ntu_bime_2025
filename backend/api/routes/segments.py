"""
Segments API Routes
投籃段落管理端點
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dataclasses import asdict

from services.segmenter import ShotSegment

router = APIRouter(prefix="/api/segments", tags=["segments"])

# 全域段落儲存（實際應用中應從 database 或 session 管理）
# 這裡簡化處理，使用記憶體儲存
_segments: List[ShotSegment] = []


class UpdateLabelRequest(BaseModel):
    """更新標籤請求"""
    label: str  # 'good' | 'bad' | 'unknown'


@router.get("")
async def list_segments():
    """
    列出所有段落

    Returns:
        List[dict]: 段落列表（不含 samples）
    """
    # 轉換為 dict 並移除 samples（避免傳輸過大）
    result = []
    for seg in _segments:
        seg_dict = asdict(seg)
        seg_dict['sample_count'] = len(seg.samples)
        del seg_dict['samples']  # 移除 samples
        result.append(seg_dict)

    return result


@router.get("/{segment_id}")
async def get_segment(segment_id: str):
    """
    取得段落詳情

    Args:
        segment_id: Segment ID (shot_id)

    Returns:
        dict: 段落詳細資訊（含 samples）

    Raises:
        HTTPException 404: 段落不存在
    """
    for seg in _segments:
        if seg.shot_id == segment_id:
            # 轉換為 dict（含 samples）
            seg_dict = asdict(seg)
            seg_dict['sample_count'] = len(seg.samples)
            return seg_dict

    raise HTTPException(status_code=404, detail=f"Segment {segment_id} not found")


@router.patch("/{segment_id}/label")
async def update_label(segment_id: str, req: UpdateLabelRequest):
    """
    更新段落標籤

    Args:
        segment_id: Segment ID (shot_id)
        req: UpdateLabelRequest（包含 label）

    Returns:
        dict: 更新結果

    Raises:
        HTTPException 404: 段落不存在
        HTTPException 400: 無效的標籤
    """
    # 驗證標籤值
    if req.label not in ['good', 'bad', 'unknown']:
        raise HTTPException(status_code=400, detail=f"Invalid label: {req.label}")

    # 找到段落並更新
    for seg in _segments:
        if seg.shot_id == segment_id:
            seg.label = req.label
            return {
                "segment_id": segment_id,
                "label": req.label,
                "status": "updated"
            }

    raise HTTPException(status_code=404, detail=f"Segment {segment_id} not found")


# 輔助函數：供其他模組呼叫（如 WebSocket handler）
def add_segment(segment: ShotSegment):
    """新增段落到記憶體儲存"""
    _segments.append(segment)


def clear_segments():
    """清空所有段落"""
    _segments.clear()


def get_all_segments() -> List[ShotSegment]:
    """取得所有段落（含 samples）"""
    return _segments.copy()
