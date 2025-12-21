"""
CoreService - Central Service Manager (Singleton)
統一管理所有後端服務的核心類別，整合完整的資料處理流程

資料流：
Serial Ingest → Processor → Ring Buffer → Segmenter → Labeler → Recorder
                                       ↓
                                  WebSocket Broadcast
"""
from typing import Optional
import threading
import asyncio
import logging

from .recorder import Recorder
from .player import Player
from .segmenter import Segmenter
from .processor import Processor
from .serial_ingest import SerialIngest, SerialSample
from .ring_buffer import RingBuffer
from .labeler import Labeler

logger = logging.getLogger(__name__)


class CoreService:
    """
    CoreService - 核心服務管理器（Singleton）

    統一管理所有服務實例，實現完整的資料處理流程
    確保系統使用同一組服務物件，避免重複實例
    """

    _instance: Optional['CoreService'] = None
    _lock = threading.Lock()

    def __init__(self):
        """
        初始化核心服務

        不應直接呼叫，請使用 get_instance()
        """
        # Serial Ingest (延遲初始化)
        self.serial_ingest: Optional[SerialIngest] = None

        # Data Processing Pipeline
        self.processor = Processor(sample_rate=100)
        self.ring_buffer = RingBuffer(max_seconds=60, sample_rate=100)
        self.segmenter = Segmenter()
        self.labeler = Labeler()

        # Recording & Playback
        self.recorder = Recorder()
        self.player = Player()

        # Runtime State
        self._running = False
        self._ws_manager = None  # WebSocket manager (延遲導入)

        # Stats & State
        self._stats = {
            "total_sessions": 0,
            "total_segments": 0,
            "total_samples": 0,
            "good_shots": 0,
            "bad_shots": 0,
            "unknown_shots": 0,
        }

    @classmethod
    def get_instance(cls) -> 'CoreService':
        """
        取得 CoreService 單例

        Returns:
            CoreService: 核心服務實例
        """
        if cls._instance is None:
            with cls._lock:
                # Double-check locking
                if cls._instance is None:
                    cls._instance = CoreService()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """
        重置單例（主要用於測試）

        警告：會清空所有服務狀態
        """
        with cls._lock:
            cls._instance = None

    # --- Serial 控制 ---

    async def start_serial(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200):
        """
        啟動 Serial 資料流

        Args:
            port: Serial port 路徑
            baudrate: Baud rate

        Raises:
            serial.SerialException: Serial 連接失敗
        """
        if self._running:
            logger.warning("Serial already running")
            return

        logger.info(f"Starting serial: {port} @ {baudrate} baud")

        # 初始化 Serial Ingest
        if self.serial_ingest is None:
            self.serial_ingest = SerialIngest(port, baudrate)

        # 延遲導入 WebSocket manager
        try:
            from api.websocket import manager as ws_manager
            self._ws_manager = ws_manager
        except ImportError:
            logger.warning("WebSocket manager not available")
            self._ws_manager = None

        # 啟動 Serial Ingest（傳遞回調）
        await self.serial_ingest.start(self._on_raw_sample)
        self._running = True
        logger.info("Serial started")

    def stop_serial(self):
        """停止 Serial 資料流"""
        if not self._running:
            return

        logger.info("Stopping serial...")
        self._running = False

        if self.serial_ingest:
            self.serial_ingest.stop()

        logger.info("Serial stopped")

    def _on_raw_sample(self, raw_sample: SerialSample):
        """
        處理原始資料的回調

        完整資料處理流程：
        1. 資料處理（單位轉換、濾波）
        2. 存入 ring buffer
        3. 切段偵測
        4. 標註處理
        5. 錄製
        6. WebSocket 廣播

        Args:
            raw_sample: SerialSample（原始資料）
        """
        try:
            # 1. 資料處理
            processed = self.processor.process(raw_sample)

            # 2. 存入 ring buffer
            self.ring_buffer.push(processed)

            # 3. 切段偵測
            segment = self.segmenter.process(processed)
            if segment:
                # 段落完成，廣播 segment_event
                logger.info(f"Shot segment completed: {segment.shot_id}, duration={segment.duration_ms}ms")
                if self._ws_manager:
                    asyncio.create_task(
                        self._ws_manager.send_segment_event('end', segment)
                    )

            # 4. 標註處理
            label_event = self.labeler.process_sample(processed, self.segmenter.segments)
            if label_event:
                # 標籤對齊成功，廣播 label_event
                logger.info(f"Label event: matched_shot_id={label_event.matched_shot_id}")
                if self._ws_manager:
                    asyncio.create_task(
                        self._ws_manager.send_label_event(
                            label_event.matched_shot_id,
                            'good',
                            label_event.t_host_ms
                        )
                    )

            # 5. 錄製
            if self.recorder.is_recording:
                self.recorder.write_sample(processed)

            # 6. WebSocket 廣播（降頻）
            # TODO: 實作降頻邏輯（例如每 10 筆廣播一次）
            if self._ws_manager:
                asyncio.create_task(
                    self._ws_manager.send_sample(processed)
                )

        except Exception as e:
            logger.error(f"Error processing sample: {e}", exc_info=True)

    # --- 錄製控制 ---

    def start_recording(self, name: str, imu_positions: dict = None) -> str:
        """
        開始錄製

        Args:
            name: Session 名稱
            imu_positions: IMU 位置映射

        Returns:
            str: session_id

        Raises:
            RuntimeError: 已在錄製中
        """
        if imu_positions is None:
            imu_positions = {"mpu1": "hand_back", "mpu2": "bicep"}

        session_id = self.recorder.start(name, imu_positions)
        logger.info(f"Recording started: {session_id}")
        return session_id

    def stop_recording(self) -> dict:
        """
        停止錄製

        Returns:
            dict: 錄製 metadata

        Raises:
            RuntimeError: 未在錄製中
        """
        meta = self.recorder.stop()

        # 更新統計
        self._stats["total_sessions"] += 1
        self._stats["total_samples"] += meta.get("sample_count", 0)

        logger.info(f"Recording stopped: {meta.get('sample_count', 0)} samples")
        return meta

    # --- 校正控制 ---

    def start_calibration(self, duration_sec: float = 2.0):
        """
        開始 Gyro bias 校正

        Args:
            duration_sec: 校正持續時間（秒）
        """
        logger.info(f"Starting gyro calibration for {duration_sec}s")
        self.processor.start_calibration(duration_sec)

    def is_calibrating(self) -> bool:
        """
        是否正在校正中

        Returns:
            True 表示正在收集校正樣本
        """
        return self.processor.is_calibrating()

    def get_calibration_offset(self) -> dict:
        """
        取得校正偏移量

        Returns:
            dict with keys: gx1, gy1, gz1, gx2, gy2, gz2 (單位: °/s)
        """
        return self.processor.calibration_offset

    # --- 切段控制 ---

    def reset_segmenter(self):
        """重置切段狀態（清空已完成的段落）"""
        self.segmenter.reset()
        logger.info("Segmenter reset")

    def get_segments(self) -> list:
        """
        取得已完成的段落列表

        Returns:
            List[ShotSegment]
        """
        return self.segmenter.segments

    # --- Ring Buffer 查詢 ---

    def get_recent_samples(self, seconds: float = 5.0) -> list:
        """
        取得最近 N 秒的資料

        Args:
            seconds: 往前取幾秒

        Returns:
            List[BufferedSample]
        """
        return self.ring_buffer.get_recent(seconds)

    def get_samples_by_time_range(self, start_ms: int, end_ms: int) -> list:
        """
        取得時間範圍內的資料

        Args:
            start_ms: 開始時間（t_remote_ms）
            end_ms: 結束時間（t_remote_ms）

        Returns:
            List[BufferedSample]
        """
        return self.ring_buffer.get_range(start_ms, end_ms)

    # --- 統計查詢 ---

    def get_stats(self) -> dict:
        """
        取得統計資訊

        Returns:
            dict: 統計資料（包含 serial stats、buffer、segments）
        """
        # 合併即時資料
        stats = self._stats.copy()

        # Serial 統計
        if self.serial_ingest:
            stats["serial"] = self.serial_ingest.stats
        else:
            stats["serial"] = {"pps": 0.0, "dropped": 0, "parse_err": 0, "total_rx": 0}

        # Buffer 統計
        stats["buffer_size"] = self.ring_buffer.size
        stats["buffer_capacity"] = self.ring_buffer.capacity

        # Segmenter 統計
        if hasattr(self.segmenter, 'segments'):
            segments = self.segmenter.segments
            stats["total_segments"] = len(segments)

            # 計算標籤統計
            good = sum(1 for seg in segments if seg.label == 'good')
            bad = sum(1 for seg in segments if seg.label == 'bad')
            unknown = sum(1 for seg in segments if seg.label == 'unknown')

            stats["good_shots"] = good
            stats["bad_shots"] = bad
            stats["unknown_shots"] = unknown

        # Recording 狀態
        stats["is_recording"] = self.recorder.is_recording
        stats["is_calibrating"] = self.processor.is_calibrating()
        stats["is_running"] = self._running

        return stats

    # --- 清理 ---

    def cleanup(self):
        """
        清理所有服務資源

        停止所有執行中的服務，釋放資源
        """
        logger.info("Cleaning up CoreService...")

        # 停止 Serial
        if self._running:
            self.stop_serial()

        # 停止錄製
        if self.recorder.is_recording:
            self.recorder.stop()

        # 停止回放
        if hasattr(self.player, 'is_playing') and self.player.is_playing:
            self.player.stop()

        logger.info("CoreService cleanup complete")

    def __repr__(self):
        return (
            f"<CoreService "
            f"running={self._running} "
            f"recording={self.recorder.is_recording} "
            f"sessions={self._stats['total_sessions']} "
            f"segments={self._stats['total_segments']}>"
        )


# 快捷方式：取得全域實例
def get_core() -> CoreService:
    """取得 CoreService 全域實例"""
    return CoreService.get_instance()
