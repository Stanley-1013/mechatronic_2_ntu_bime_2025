"""
Ring Buffer Service
滾動緩衝區，保存最近 N 秒的感測資料
供 Live 圖表與事件對齊使用
"""
from collections import deque
from typing import List, Optional, Any
from dataclasses import dataclass
import threading


@dataclass
class BufferedSample:
    """緩衝區中的資料

    繼承 ProcessedSample 的所有欄位，額外加上 index 供查詢
    """
    index: int
    seq: int
    t_remote_ms: int  # 用於時間範圍查詢
    t_received_ns: int
    btn: int

    # MPU1 物理單位
    ax1_g: float
    ay1_g: float
    az1_g: float
    gx1_dps: float
    gy1_dps: float
    gz1_dps: float

    # MPU2 物理單位
    ax2_g: float
    ay2_g: float
    az2_g: float
    gx2_dps: float
    gy2_dps: float
    gz2_dps: float

    # 計算值（濾波後）
    g1_mag: float
    g2_mag: float
    a1_mag: float
    a2_mag: float

    @classmethod
    def from_processed_sample(cls, sample: Any, index: int) -> 'BufferedSample':
        """從 ProcessedSample 轉換為 BufferedSample

        Args:
            sample: ProcessedSample 物件（dataclass 或 Pydantic model）
            index: 緩衝區索引

        Returns:
            BufferedSample 實例
        """
        if isinstance(sample, dict):
            return cls(
                index=index,
                seq=sample['seq'],
                t_remote_ms=sample['t_remote_ms'],
                t_received_ns=sample['t_received_ns'],
                btn=sample['btn'],

                ax1_g=sample['ax1_g'],
                ay1_g=sample['ay1_g'],
                az1_g=sample['az1_g'],
                gx1_dps=sample['gx1_dps'],
                gy1_dps=sample['gy1_dps'],
                gz1_dps=sample['gz1_dps'],

                ax2_g=sample['ax2_g'],
                ay2_g=sample['ay2_g'],
                az2_g=sample['az2_g'],
                gx2_dps=sample['gx2_dps'],
                gy2_dps=sample['gy2_dps'],
                gz2_dps=sample['gz2_dps'],

                g1_mag=sample['g1_mag'],
                g2_mag=sample['g2_mag'],
                a1_mag=sample['a1_mag'],
                a2_mag=sample['a2_mag'],
            )
        else:
            # Pydantic model or dataclass
            return cls(
                index=index,
                seq=sample.seq,
                t_remote_ms=sample.t_remote_ms,
                t_received_ns=sample.t_received_ns,
                btn=sample.btn,

                ax1_g=sample.ax1_g,
                ay1_g=sample.ay1_g,
                az1_g=sample.az1_g,
                gx1_dps=sample.gx1_dps,
                gy1_dps=sample.gy1_dps,
                gz1_dps=sample.gz1_dps,

                ax2_g=sample.ax2_g,
                ay2_g=sample.ay2_g,
                az2_g=sample.az2_g,
                gx2_dps=sample.gx2_dps,
                gy2_dps=sample.gy2_dps,
                gz2_dps=sample.gz2_dps,

                g1_mag=sample.g1_mag,
                g2_mag=sample.g2_mag,
                a1_mag=sample.a1_mag,
                a2_mag=sample.a2_mag,
            )


class RingBuffer:
    """滾動緩衝區

    保存最近 N 秒的感測資料，自動淘汰舊資料
    線程安全，支援多種查詢方式
    """

    def __init__(self, max_seconds: float = 60.0, sample_rate: int = 100):
        """初始化緩衝區

        Args:
            max_seconds: 最大保存秒數（預設 60 秒）
            sample_rate: 採樣率 Hz（預設 100 Hz）
        """
        self._max_seconds = max_seconds
        self._sample_rate = sample_rate
        self._capacity = int(max_seconds * sample_rate)  # 100Hz × 60s = 6000 筆

        self._buffer: deque[BufferedSample] = deque(maxlen=self._capacity)
        self._lock = threading.Lock()
        self._next_index = 0  # 全域索引計數器

    def push(self, sample: Any) -> int:
        """加入一筆資料

        Args:
            sample: ProcessedSample 物件或字典

        Returns:
            分配給此資料的全域索引
        """
        with self._lock:
            buffered = BufferedSample.from_processed_sample(sample, self._next_index)
            self._buffer.append(buffered)
            current_index = self._next_index
            self._next_index += 1
            return current_index

    def get_recent(self, seconds: float = 5.0) -> List[BufferedSample]:
        """取得最近 N 秒資料

        Args:
            seconds: 往前取幾秒（預設 5 秒）

        Returns:
            最近 N 秒的資料列表（按時間順序）
        """
        with self._lock:
            if not self._buffer:
                return []

            latest_time = self._buffer[-1].t_remote_ms
            cutoff_time = latest_time - int(seconds * 1000)

            # 從後往前找第一個超過 cutoff 的位置
            result = []
            for sample in reversed(self._buffer):
                if sample.t_remote_ms >= cutoff_time:
                    result.append(sample)
                else:
                    break

            return list(reversed(result))  # 反轉回正序

    def get_range(self, start_ms: int, end_ms: int) -> List[BufferedSample]:
        """取得時間範圍內的資料

        Args:
            start_ms: 開始時間（t_remote_ms）
            end_ms: 結束時間（t_remote_ms）

        Returns:
            時間範圍內的資料列表（按時間順序）
        """
        with self._lock:
            return [
                sample for sample in self._buffer
                if start_ms <= sample.t_remote_ms <= end_ms
            ]

    def get_by_index(self, start_idx: int, count: int) -> List[BufferedSample]:
        """取得指定 index 範圍的資料

        Args:
            start_idx: 起始索引（全域索引）
            count: 要取的數量

        Returns:
            索引範圍內的資料列表（按時間順序）
        """
        with self._lock:
            end_idx = start_idx + count
            return [
                sample for sample in self._buffer
                if start_idx <= sample.index < end_idx
            ]

    def get_latest(self) -> Optional[BufferedSample]:
        """取得最新一筆資料

        Returns:
            最新的資料，若緩衝區為空則回傳 None
        """
        with self._lock:
            return self._buffer[-1] if self._buffer else None

    @property
    def size(self) -> int:
        """目前資料筆數"""
        with self._lock:
            return len(self._buffer)

    @property
    def capacity(self) -> int:
        """最大容量"""
        return self._capacity

    @property
    def max_seconds(self) -> float:
        """最大保存秒數"""
        return self._max_seconds

    @property
    def sample_rate(self) -> int:
        """採樣率"""
        return self._sample_rate

    @property
    def next_index(self) -> int:
        """下一個將分配的索引（全域計數器）"""
        with self._lock:
            return self._next_index

    def clear(self):
        """清空緩衝區（保留索引計數器）"""
        with self._lock:
            self._buffer.clear()

    def reset(self):
        """重置緩衝區（包含索引計數器）"""
        with self._lock:
            self._buffer.clear()
            self._next_index = 0

    def get_time_range(self) -> tuple[Optional[int], Optional[int]]:
        """取得緩衝區的時間範圍

        Returns:
            (最早時間, 最晚時間) 的 tuple，若緩衝區為空則回傳 (None, None)
        """
        with self._lock:
            if not self._buffer:
                return None, None
            return self._buffer[0].t_remote_ms, self._buffer[-1].t_remote_ms

    def get_index_range(self) -> tuple[Optional[int], Optional[int]]:
        """取得緩衝區的索引範圍

        Returns:
            (最小索引, 最大索引) 的 tuple，若緩衝區為空則回傳 (None, None)
        """
        with self._lock:
            if not self._buffer:
                return None, None
            return self._buffer[0].index, self._buffer[-1].index

    def __len__(self) -> int:
        """支援 len() 運算子"""
        return self.size

    def __repr__(self) -> str:
        """字串表示"""
        with self._lock:
            min_idx, max_idx = self.get_index_range()
            min_time, max_time = self.get_time_range()
            return (
                f"RingBuffer(size={len(self._buffer)}/{self._capacity}, "
                f"index=[{min_idx}..{max_idx}], "
                f"time=[{min_time}..{max_time}]ms)"
            )
