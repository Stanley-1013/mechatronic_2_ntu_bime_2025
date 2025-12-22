"""
Segments API Routes
投籃段落管理端點
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from dataclasses import asdict
import numpy as np
from sklearn.cluster import KMeans

from services.core import CoreService
from services.segmenter import ShotSegment

router = APIRouter(prefix="/api/segments", tags=["segments"])


class UpdateLabelRequest(BaseModel):
    """更新標籤請求"""
    label: str  # 'good' | 'bad' | 'unknown'


class ClusterRequest(BaseModel):
    """K-means 分群請求"""
    n_clusters: int = 3
    features: List[str] = ["g1_rms", "dg_rms"]


def _get_segments() -> List[ShotSegment]:
    """從 CoreService 取得段落"""
    core = CoreService.get_instance()
    return core.segmenter.segments


def _segment_to_dict(seg: ShotSegment) -> dict:
    """將 ShotSegment 轉換為 dict（不含 samples）"""
    seg_dict = asdict(seg)
    seg_dict['sample_count'] = len(seg.samples)
    del seg_dict['samples']  # 移除 samples
    return seg_dict


@router.get("")
async def list_segments():
    """
    列出所有段落

    Returns:
        List[dict]: 段落列表（不含 samples）
    """
    segments = _get_segments()
    return [_segment_to_dict(seg) for seg in segments]


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
    segments = _get_segments()
    for seg in segments:
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
    segments = _get_segments()
    for seg in segments:
        if seg.shot_id == segment_id:
            seg.label = req.label
            return {
                "segment_id": segment_id,
                "label": req.label,
                "status": "updated"
            }

    raise HTTPException(status_code=404, detail=f"Segment {segment_id} not found")


@router.post("/cluster")
async def cluster_segments(req: ClusterRequest):
    """
    對段落進行 K-means 分群

    Args:
        req: ClusterRequest（包含 n_clusters 和 features）

    Returns:
        dict: 分群結果
            - clusters: 各群的資訊
            - assignments: 每個 segment 的分群結果

    Raises:
        HTTPException 400: 段落數不足或特徵無效
    """
    segments = _get_segments()

    # 檢查段落數
    if len(segments) < req.n_clusters:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough segments ({len(segments)}) for {req.n_clusters} clusters"
        )

    # 提取特徵
    feature_matrix = []
    valid_segments = []

    for seg in segments:
        features = seg.features or {}
        row = []
        valid = True

        for feat_name in req.features:
            if feat_name == 'dur' or feat_name == 'duration_ms':
                row.append(seg.duration_ms)
            elif feat_name in features and features[feat_name] is not None:
                row.append(features[feat_name])
            else:
                valid = False
                break

        if valid:
            feature_matrix.append(row)
            valid_segments.append(seg)

    if len(feature_matrix) < req.n_clusters:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough valid segments ({len(feature_matrix)}) with features {req.features}"
        )

    # 執行 K-means
    X = np.array(feature_matrix)

    # 標準化特徵
    X_mean = X.mean(axis=0)
    X_std = X.std(axis=0)
    X_std[X_std == 0] = 1  # 避免除零
    X_normalized = (X - X_mean) / X_std

    kmeans = KMeans(n_clusters=req.n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_normalized)

    # 計算群心（原始尺度）
    centers = kmeans.cluster_centers_ * X_std + X_mean

    # 組織結果
    clusters = []
    for i in range(req.n_clusters):
        cluster_indices = np.where(labels == i)[0]
        cluster_segments = [valid_segments[idx] for idx in cluster_indices]

        # 計算群統計
        good_count = sum(1 for seg in cluster_segments if seg.label == 'good')
        total_count = len(cluster_segments)

        clusters.append({
            "cluster_id": i,
            "center": {req.features[j]: float(centers[i][j]) for j in range(len(req.features))},
            "count": total_count,
            "good_count": good_count,
            "good_ratio": good_count / total_count if total_count > 0 else 0
        })

    # 每個 segment 的分群結果
    assignments = []
    for idx, seg in enumerate(valid_segments):
        assignments.append({
            "shot_id": seg.shot_id,
            "cluster_id": int(labels[idx]),
            "features": {req.features[j]: float(feature_matrix[idx][j]) for j in range(len(req.features))}
        })

    return {
        "n_clusters": req.n_clusters,
        "features": req.features,
        "total_segments": len(valid_segments),
        "clusters": clusters,
        "assignments": assignments
    }


@router.get("/stats")
async def get_segment_stats():
    """
    取得段落統計

    Returns:
        dict: 統計資訊
    """
    segments = _get_segments()

    total = len(segments)
    good = sum(1 for seg in segments if seg.label == 'good')
    bad = sum(1 for seg in segments if seg.label == 'bad')
    unknown = sum(1 for seg in segments if seg.label == 'unknown')

    # 特徵統計
    durations = [seg.duration_ms for seg in segments]
    g1_rms_values = [seg.features.get('g1_rms', 0) for seg in segments if seg.features]
    dg_rms_values = [seg.features.get('dg_rms', 0) for seg in segments if seg.features]

    return {
        "total": total,
        "good": good,
        "bad": bad,
        "unknown": unknown,
        "duration": {
            "min": min(durations) if durations else 0,
            "max": max(durations) if durations else 0,
            "avg": sum(durations) / len(durations) if durations else 0
        },
        "g1_rms": {
            "min": min(g1_rms_values) if g1_rms_values else 0,
            "max": max(g1_rms_values) if g1_rms_values else 0,
            "avg": sum(g1_rms_values) / len(g1_rms_values) if g1_rms_values else 0
        },
        "dg_rms": {
            "min": min(dg_rms_values) if dg_rms_values else 0,
            "max": max(dg_rms_values) if dg_rms_values else 0,
            "avg": sum(dg_rms_values) / len(dg_rms_values) if dg_rms_values else 0
        }
    }


@router.post("/clear")
async def clear_all_segments():
    """
    清空所有段落

    Returns:
        dict: 清除結果
    """
    core = CoreService.get_instance()
    count = len(core.segmenter.segments)
    core.segmenter.reset()

    return {
        "status": "cleared",
        "cleared_count": count
    }


# 輔助函數：供其他模組呼叫
def clear_segments():
    """清空所有段落（透過 CoreService）"""
    core = CoreService.get_instance()
    core.segmenter.reset()


def get_all_segments() -> List[ShotSegment]:
    """取得所有段落（含 samples）"""
    return _get_segments()
