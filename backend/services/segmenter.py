"""
投籃切段服務
負責：使用狀態機偵測投籃動作開始/結束，產生 ShotSegment

規格參考: SRS FR-P7, FR-L3
"""

import uuid
import math
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from services.processor import ProcessedSample


class SegmentState(Enum):
    """切段狀態機"""
    IDLE = "idle"         # 閒置，無動作
    ACTIVE = "active"     # 投籃動作進行中
    COOLDOWN = "cooldown" # 冷卻期，準備儲存段落


@dataclass
class ShotSegment:
    """投籃段落資料模型（FR-L3）"""
    shot_id: str
    t_start_ms: int
    t_end_ms: int = 0
    t_release_ms: Optional[int] = None  # 出手瞬間（可選）
    duration_ms: int = 0
    features: dict = field(default_factory=dict)
    label: str = "unknown"  # 'unknown' | 'good'
    label_time_ms: Optional[int] = None
    samples: List = field(default_factory=list)


class Segmenter:
    """
    投籃切段服務

    使用狀態機偵測投籃動作：
    - IDLE → ACTIVE: |gyro| > Th_on 持續 >= 60-100ms
    - ACTIVE → COOLDOWN: |gyro| < Th_off 持續 >= 150-300ms
    - COOLDOWN → IDLE: cooldown 結束，儲存段落

    支援自適應閾值（IDLE 期間估計 baseline/noise）
    """

    def __init__(
        self,
        threshold_on: float = 50.0,      # °/s
        threshold_off: float = 30.0,     # °/s
        enter_duration_ms: int = 80,
        exit_duration_ms: int = 200,
        min_segment_ms: int = 300,
        cooldown_ms: int = 400,
        adaptive: bool = True
    ):
        """
        初始化

        Args:
            threshold_on: 進入閾值（°/s）
            threshold_off: 離開閾值（°/s）
            enter_duration_ms: 進入持續時間
            exit_duration_ms: 離開持續時間
            min_segment_ms: 最短段長
            cooldown_ms: 冷卻時間
            adaptive: 是否自適應閾值
        """
        # 閾值設定
        self._threshold_on = threshold_on
        self._threshold_off = threshold_off
        self._enter_duration_ms = enter_duration_ms
        self._exit_duration_ms = exit_duration_ms
        self._min_segment_ms = min_segment_ms
        self._cooldown_ms = cooldown_ms
        self._adaptive = adaptive

        # 狀態機
        self._state = SegmentState.IDLE
        self._current_seg: Optional[ShotSegment] = None
        self._segments: List[ShotSegment] = []

        # 計時器（用於條件持續時間判定）
        self._condition_start_ms: Optional[int] = None
        self._cooldown_start_ms: Optional[int] = None

        # 自適應閾值（IDLE 期間統計）
        self._idle_samples: List[float] = []
        self._max_idle_samples = 500  # 最多保留 500 筆（約 5 秒）

        # 回調
        self._on_segment_complete: Optional[Callable[[ShotSegment], None]] = None

    def process(self, sample: ProcessedSample) -> Optional[ShotSegment]:
        """
        處理一筆資料

        Args:
            sample: ProcessedSample（需含 g1_mag）

        Returns:
            若段落結束，回傳 ShotSegment；否則 None
        """
        gyro_mag = sample.g1_mag  # 使用 MPU1 角速度模長
        t_ms = sample.t_remote_ms

        # 更新自適應閾值
        if self._adaptive and self._state == SegmentState.IDLE:
            self._update_adaptive_threshold(gyro_mag)

        # 狀態機處理
        if self._state == SegmentState.IDLE:
            return self._handle_idle(sample, gyro_mag, t_ms)

        elif self._state == SegmentState.ACTIVE:
            return self._handle_active(sample, gyro_mag, t_ms)

        elif self._state == SegmentState.COOLDOWN:
            return self._handle_cooldown(sample, t_ms)

        return None

    def _handle_idle(self, sample: ProcessedSample, gyro_mag: float, t_ms: int) -> Optional[ShotSegment]:
        """處理 IDLE 狀態"""
        # 檢查是否超過進入閾值
        if gyro_mag > self._threshold_on:
            if self._condition_start_ms is None:
                self._condition_start_ms = t_ms

            # 持續時間夠長 -> 進入 ACTIVE
            duration = t_ms - self._condition_start_ms
            if duration >= self._enter_duration_ms:
                self._enter_active(sample, t_ms)
                self._condition_start_ms = None
        else:
            # 未滿足條件，重置計時
            self._condition_start_ms = None

        return None

    def _handle_active(self, sample: ProcessedSample, gyro_mag: float, t_ms: int) -> Optional[ShotSegment]:
        """處理 ACTIVE 狀態"""
        # 記錄樣本
        if self._current_seg:
            self._current_seg.samples.append(sample)

        # 檢查是否低於離開閾值
        if gyro_mag < self._threshold_off:
            if self._condition_start_ms is None:
                self._condition_start_ms = t_ms

            # 持續時間夠長 -> 進入 COOLDOWN
            duration = t_ms - self._condition_start_ms
            if duration >= self._exit_duration_ms:
                self._enter_cooldown(t_ms)
                self._condition_start_ms = None
        else:
            # 仍在活動中，重置計時
            self._condition_start_ms = None

        return None

    def _handle_cooldown(self, sample: ProcessedSample, t_ms: int) -> Optional[ShotSegment]:
        """處理 COOLDOWN 狀態"""
        # 冷卻期間也記錄樣本（可能包含落地等後續動作）
        if self._current_seg:
            self._current_seg.samples.append(sample)

        # 檢查冷卻時間是否結束
        if self._cooldown_start_ms is None:
            return None

        elapsed = t_ms - self._cooldown_start_ms
        if elapsed >= self._cooldown_ms:
            return self._finish_segment()

        return None

    def _enter_active(self, sample: ProcessedSample, t_ms: int):
        """進入 ACTIVE 狀態，開始新段落"""
        self._state = SegmentState.ACTIVE
        shot_id = str(uuid.uuid4())[:8]

        self._current_seg = ShotSegment(
            shot_id=shot_id,
            t_start_ms=t_ms,
            samples=[sample]
        )

    def _enter_cooldown(self, t_ms: int):
        """進入 COOLDOWN 狀態，記錄段落結束時間"""
        self._state = SegmentState.COOLDOWN
        self._cooldown_start_ms = t_ms

        # 在進入冷卻時就記錄段落結束時間
        if self._current_seg:
            self._current_seg.t_end_ms = t_ms
            self._current_seg.duration_ms = t_ms - self._current_seg.t_start_ms

    def _finish_segment(self) -> Optional[ShotSegment]:
        """完成段落，計算特徵並儲存"""
        if not self._current_seg:
            self._state = SegmentState.IDLE
            self._cooldown_start_ms = None
            return None

        # 檢查最短段長
        if self._current_seg.duration_ms < self._min_segment_ms:
            # 太短，丟棄
            self._current_seg = None
            self._state = SegmentState.IDLE
            self._cooldown_start_ms = None
            return None

        # 計算特徵（FR 7.1）
        self._compute_features(self._current_seg)

        # 儲存段落
        completed_seg = self._current_seg
        self._segments.append(completed_seg)

        # 呼叫回調
        if self._on_segment_complete:
            self._on_segment_complete(completed_seg)

        # 重置狀態
        self._current_seg = None
        self._state = SegmentState.IDLE
        self._cooldown_start_ms = None

        return completed_seg

    def _compute_features(self, segment: ShotSegment):
        """
        計算段落特徵（FR 7.1）

        特徵：
        - dur: 段落長度 ms
        - g1_rms: MPU1 角速度 RMS
        - g1_peak: MPU1 角速度峰值
        - g2_rms: MPU2 角速度 RMS
        - g2_peak: MPU2 角速度峰值
        - dg_rms: RMS(|g2|-|g1|)
        """
        if not segment.samples:
            return

        n = len(segment.samples)

        # 提取資料
        g1_vals = [s.g1_mag for s in segment.samples]
        g2_vals = [s.g2_mag for s in segment.samples]
        dg_vals = [abs(g2 - g1) for g1, g2 in zip(g1_vals, g2_vals)]

        # 計算 RMS
        g1_rms = math.sqrt(sum(x**2 for x in g1_vals) / n)
        g2_rms = math.sqrt(sum(x**2 for x in g2_vals) / n)
        dg_rms = math.sqrt(sum(x**2 for x in dg_vals) / n)

        # 峰值
        g1_peak = max(g1_vals)
        g2_peak = max(g2_vals)

        # 儲存特徵
        segment.features = {
            'dur': segment.duration_ms,
            'g1_rms': round(g1_rms, 2),
            'g1_peak': round(g1_peak, 2),
            'g2_rms': round(g2_rms, 2),
            'g2_peak': round(g2_peak, 2),
            'dg_rms': round(dg_rms, 2),
        }

    def _update_adaptive_threshold(self, gyro_mag: float):
        """
        更新自適應閾值

        在 IDLE 期間收集樣本，估計 baseline 和 noise：
        Th_on = baseline + k * noise
        """
        self._idle_samples.append(gyro_mag)

        # 限制樣本數量
        if len(self._idle_samples) > self._max_idle_samples:
            self._idle_samples.pop(0)

        # 至少需要 50 筆樣本才開始調整
        if len(self._idle_samples) < 50:
            return

        # 計算 baseline（中位數）和 noise（標準差）
        sorted_samples = sorted(self._idle_samples)
        median_idx = len(sorted_samples) // 2
        baseline = sorted_samples[median_idx]

        mean = sum(self._idle_samples) / len(self._idle_samples)
        variance = sum((x - mean)**2 for x in self._idle_samples) / len(self._idle_samples)
        noise = math.sqrt(variance)

        # 更新閾值（k=3 倍標準差）
        k = 3.0
        self._threshold_on = baseline + k * noise
        self._threshold_off = baseline + (k - 1) * noise  # 保持遲滯

    def set_on_segment_complete(self, callback: Callable[[ShotSegment], None]):
        """設定段落完成回調"""
        self._on_segment_complete = callback

    @property
    def state(self) -> SegmentState:
        """目前狀態"""
        return self._state

    @property
    def segments(self) -> List[ShotSegment]:
        """所有已完成段落"""
        return self._segments.copy()

    @property
    def current_segment(self) -> Optional[ShotSegment]:
        """目前進行中的段落（ACTIVE 時）"""
        return self._current_seg

    def get_segment(self, shot_id: str) -> Optional[ShotSegment]:
        """取得指定段落"""
        for seg in self._segments:
            if seg.shot_id == shot_id:
                return seg
        return None

    def clear_segments(self):
        """清空段落"""
        self._segments = []
        self._current_seg = None
        self._state = SegmentState.IDLE
        self._condition_start_ms = None
        self._cooldown_start_ms = None
