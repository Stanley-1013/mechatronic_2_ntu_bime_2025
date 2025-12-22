"""
標籤對齊服務
負責：按鈕事件偵測、標籤與投籃段落對齊

規格參考: SRS FR-L1, FR-L2, FR-L3
"""

from dataclasses import dataclass
from typing import Optional, List, Callable
import logging

from services.segmenter import ShotSegment
from services.processor import ProcessedSample

logger = logging.getLogger(__name__)


@dataclass
class LabelEvent:
    """標籤事件（FR-L1）"""
    kind: str  # 'label_good'
    t_host_ms: int
    seq: int
    matched_shot_id: Optional[str] = None
    delay_ms: Optional[int] = None  # 事件時間與段落結束時間的延遲


class Labeler:
    """
    標籤對齊服務

    功能：
    1. 按鈕事件偵測（去抖、邊緣檢測）
    2. 標籤與投籃段落對齊（時間窗、最近段落選擇）
    3. 手動標註支援
    """

    def __init__(
        self,
        debounce_ms: int = 250,
        pressed_level: int = 1,
        min_delay_ms: int = 50,      # FIXED: Reduced from 200ms to 50ms
        max_delay_ms: int = 3000
    ):
        """
        初始化

        Args:
            debounce_ms: 去抖冷卻時間（FR-L1: 250ms）
            pressed_level: 按下時的 level 值（1=按下為高，0=按下為低）
            min_delay_ms: 最小對齊延遲（FIXED: 50ms，原本 200ms 太長）
            max_delay_ms: 最大對齊延遲（FR-L2: 3000ms）
        """
        self._debounce_ms = debounce_ms
        self._pressed_level = pressed_level
        self._min_delay_ms = min_delay_ms
        self._max_delay_ms = max_delay_ms

        # 按鈕狀態
        self._last_btn_level: Optional[int] = None
        self._last_press_time_ms: Optional[int] = None

        # 標籤事件記錄
        self._events: List[LabelEvent] = []
        self._event_seq = 0

        # 回調
        self._on_label: Optional[Callable[[LabelEvent], None]] = None

        logger.info(f"Labeler initialized: pressed_level={pressed_level}, "
                   f"min_delay_ms={min_delay_ms}, max_delay_ms={max_delay_ms}")

    def process_sample(
        self,
        sample: ProcessedSample,
        segments: List[ShotSegment]
    ) -> Optional[LabelEvent]:
        """
        處理一筆資料，檢測按鈕事件

        Args:
            sample: ProcessedSample（需含 btn, t_remote_ms）
            segments: 目前所有段落

        Returns:
            若產生事件，回傳 LabelEvent；否則 None
        """
        current_level = sample.btn
        current_time_ms = sample.t_remote_ms

        # 首次運行，初始化狀態
        if self._last_btn_level is None:
            self._last_btn_level = current_level
            return None

        # 檢測按下邊緣（FR-L1）
        is_press_edge = (
            self._last_btn_level != self._pressed_level and
            current_level == self._pressed_level
        )

        # 更新狀態
        self._last_btn_level = current_level

        if not is_press_edge:
            return None

        # DEBUG: Log button press detection
        logger.debug(f"[Labeler] Button press detected! btn={current_level}, t={current_time_ms}ms")

        # 去抖檢查（FR-L1: 250ms 冷卻）
        if self._last_press_time_ms is not None:
            time_since_last_press = current_time_ms - self._last_press_time_ms
            if time_since_last_press < self._debounce_ms:
                # 太接近上次按壓，忽略
                logger.debug(f"[Labeler] Button press ignored (debounce): {time_since_last_press}ms < {self._debounce_ms}ms")
                return None

        # 更新按壓時間
        self._last_press_time_ms = current_time_ms

        # 產生標籤事件
        event = self._create_label_event(current_time_ms, sample.seq, segments)

        # 記錄事件
        self._events.append(event)

        # 觸發回調
        if self._on_label:
            self._on_label(event)

        return event

    def _create_label_event(
        self,
        event_time_ms: int,
        seq: int,
        segments: List[ShotSegment]
    ) -> LabelEvent:
        """
        建立標籤事件並嘗試對齊段落

        Args:
            event_time_ms: 事件時間（t_remote_ms）
            seq: 資料序號
            segments: 所有段落

        Returns:
            LabelEvent（可能有或沒有 matched_shot_id）
        """
        # DEBUG: Log available segments
        completed_segments = [s for s in segments if s.t_end_ms > 0]
        logger.debug(f"[Labeler] Looking for matching segment. "
                    f"Event time: {event_time_ms}ms, "
                    f"Completed segments: {len(completed_segments)}")

        # 嘗試找到匹配的段落（FR-L2）
        matched_segment = self._find_matching_segment(event_time_ms, segments)

        if matched_segment:
            # 對齊成功
            delay_ms = event_time_ms - matched_segment.t_end_ms

            # 更新段落標籤（FR-L3）
            matched_segment.label = 'good'
            matched_segment.label_time_ms = event_time_ms

            logger.info(f"[Labeler] Matched segment {matched_segment.shot_id}, delay={delay_ms}ms")

            event = LabelEvent(
                kind='label_good',
                t_host_ms=event_time_ms,
                seq=seq,
                matched_shot_id=matched_segment.shot_id,
                delay_ms=delay_ms
            )
        else:
            # 對齊失敗（找不到符合的段落）
            logger.warning(f"[Labeler] No matching segment found for button press at t={event_time_ms}ms. "
                          f"Available segments: {len(completed_segments)}")

            # Log details of recent segments for debugging
            for seg in completed_segments[-3:]:  # Last 3 segments
                delay = event_time_ms - seg.t_end_ms
                logger.debug(f"  - Segment {seg.shot_id}: t_end={seg.t_end_ms}ms, delay={delay}ms, "
                           f"in_range={self._min_delay_ms <= delay <= self._max_delay_ms}")

            event = LabelEvent(
                kind='label_good',
                t_host_ms=event_time_ms,
                seq=seq,
                matched_shot_id=None,
                delay_ms=None
            )

        self._event_seq += 1
        return event

    def _find_matching_segment(
        self,
        event_time_ms: int,
        segments: List[ShotSegment]
    ) -> Optional[ShotSegment]:
        """
        找到最近符合的段落（FR-L2）

        規則：
        - 選擇最近一個已結束段落
        - 條件：segment.t_end_ms <= event_time_ms
        - 時間窗：event_time_ms - segment.t_end_ms 在 [min_delay_ms, max_delay_ms]

        Args:
            event_time_ms: 事件時間
            segments: 所有段落

        Returns:
            匹配的段落，若找不到則為 None
        """
        # 從最新的段落往回找
        for seg in reversed(segments):
            # 跳過未結束的段落
            if seg.t_end_ms == 0:
                continue

            # 計算延遲
            delay_ms = event_time_ms - seg.t_end_ms

            # 檢查是否在時間窗內
            if self._min_delay_ms <= delay_ms <= self._max_delay_ms:
                return seg

            # 如果延遲太大，後面的段落更早，不用再找
            if delay_ms > self._max_delay_ms:
                break

        return None

    def label_segment(self, shot_id: str, segments: List[ShotSegment]) -> bool:
        """
        手動標註指定段落

        Args:
            shot_id: 段落 ID
            segments: 所有段落

        Returns:
            是否成功標註
        """
        for seg in segments:
            if seg.shot_id == shot_id:
                seg.label = 'good'
                seg.label_time_ms = None  # 手動標註無時間戳

                # 建立手動標註事件
                event = LabelEvent(
                    kind='label_good',
                    t_host_ms=seg.t_end_ms,  # 使用段落結束時間
                    seq=self._event_seq,
                    matched_shot_id=shot_id,
                    delay_ms=0
                )
                self._events.append(event)
                self._event_seq += 1

                # 觸發回調
                if self._on_label:
                    self._on_label(event)

                logger.info(f"[Labeler] Manual label: segment {shot_id} marked as good")
                return True

        logger.warning(f"[Labeler] Manual label failed: segment {shot_id} not found")
        return False

    def set_on_label(self, callback: Callable[[LabelEvent], None]):
        """
        設定標籤事件回調

        Args:
            callback: 當產生標籤事件時呼叫，參數為 LabelEvent
        """
        self._on_label = callback

    @property
    def last_event(self) -> Optional[LabelEvent]:
        """最近一次標籤事件"""
        if self._events:
            return self._events[-1]
        return None

    @property
    def events(self) -> List[LabelEvent]:
        """所有標籤事件（副本）"""
        return self._events.copy()

    def clear_events(self):
        """清空標籤事件"""
        self._events = []
        self._event_seq = 0

    @property
    def config(self) -> dict:
        """取得目前設定"""
        return {
            'debounce_ms': self._debounce_ms,
            'pressed_level': self._pressed_level,
            'min_delay_ms': self._min_delay_ms,
            'max_delay_ms': self._max_delay_ms,
        }
