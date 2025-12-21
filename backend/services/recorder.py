"""
錄製服務
將感測資料存檔為 CSV + meta.json

規格參考: SRS FR-P4
"""

import os
import json
import csv
from datetime import datetime, timezone
from typing import Optional, Union
from pathlib import Path
import logging

from services.serial_ingest import SerialSample
from services.processor import ProcessedSample

logger = logging.getLogger(__name__)


class Recorder:
    """錄製服務"""

    def __init__(self, base_dir: str = "recordings"):
        """初始化

        Args:
            base_dir: 錄製檔案存放目錄
        """
        self.base_dir = Path(base_dir)
        self._recording = False
        self._session_id: Optional[str] = None
        self._session_dir: Optional[Path] = None
        self._csv_file = None
        self._csv_writer = None

        # 錄製統計
        self._start_time: Optional[datetime] = None
        self._sample_count = 0
        self._first_sample_time_ms: Optional[int] = None
        self._last_sample_time_ms: Optional[int] = None

        # 錄製設定（從第一筆 sample 取得）
        self._accel_range = "2g"
        self._gyro_range = "250dps"
        self._imu_positions = {
            "mpu1": "hand_back",
            "mpu2": "bicep"
        }

    def start(self, name: str, imu_positions: Optional[dict] = None) -> str:
        """開始錄製

        Args:
            name: Session 名稱
            imu_positions: IMU 位置資訊（可選）
                {
                    "mpu1": "hand_back",
                    "mpu2": "bicep"
                }

        Returns:
            session_id（目錄名稱）

        Raises:
            RuntimeError: 已經在錄製中
        """
        if self._recording:
            raise RuntimeError("Already recording")

        # 建立 session ID（名稱 + 時間戳）
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._session_id = f"{name}_{timestamp}"

        # 建立目錄
        self._session_dir = self.base_dir / self._session_id
        self._session_dir.mkdir(parents=True, exist_ok=True)

        # 開啟 CSV 檔案
        csv_path = self._session_dir / "data.csv"
        self._csv_file = open(csv_path, 'w', newline='')
        self._csv_writer = csv.writer(self._csv_file)

        # 寫入 CSV header
        header = [
            "seq", "t_remote_ms", "btn",
            "ax1", "ay1", "az1", "gx1", "gy1", "gz1",
            "ax2", "ay2", "az2", "gx2", "gy2", "gz2",
            "ax1_g", "ay1_g", "az1_g", "gx1_dps", "gy1_dps", "gz1_dps",
            "ax2_g", "ay2_g", "az2_g", "gx2_dps", "gy2_dps", "gz2_dps",
            "g1_mag", "g2_mag", "a1_mag", "a2_mag"
        ]
        self._csv_writer.writerow(header)

        # 初始化統計
        self._start_time = datetime.now(timezone.utc)
        self._sample_count = 0
        self._first_sample_time_ms = None
        self._last_sample_time_ms = None

        # 更新 IMU 位置（如果有提供）
        if imu_positions:
            self._imu_positions = imu_positions

        self._recording = True
        logger.info(f"Recording started: {self._session_id}")

        return self._session_id

    def write_sample(self, sample: Union[SerialSample, ProcessedSample]) -> bool:
        """寫入一筆資料

        Args:
            sample: ProcessedSample 或 SerialSample

        Returns:
            是否成功寫入
        """
        if not self._recording or not self._csv_writer:
            return False

        try:
            # 根據類型寫入不同格式
            if isinstance(sample, ProcessedSample):
                # ProcessedSample：包含原始值和處理後的值
                row = [
                    sample.seq,
                    sample.t_remote_ms,
                    sample.btn,
                    # 原始值（反算回 raw，假設已經換算過）
                    # 如果需要原始值，應該在 ProcessedSample 中保留
                    # 這裡簡化處理，只記錄處理後的值
                    int(sample.ax1_g * 16384),
                    int(sample.ay1_g * 16384),
                    int(sample.az1_g * 16384),
                    int(sample.gx1_dps * 131),
                    int(sample.gy1_dps * 131),
                    int(sample.gz1_dps * 131),
                    int(sample.ax2_g * 16384),
                    int(sample.ay2_g * 16384),
                    int(sample.az2_g * 16384),
                    int(sample.gx2_dps * 131),
                    int(sample.gy2_dps * 131),
                    int(sample.gz2_dps * 131),
                    # 處理後的值（物理單位）
                    sample.ax1_g,
                    sample.ay1_g,
                    sample.az1_g,
                    sample.gx1_dps,
                    sample.gy1_dps,
                    sample.gz1_dps,
                    sample.ax2_g,
                    sample.ay2_g,
                    sample.az2_g,
                    sample.gx2_dps,
                    sample.gy2_dps,
                    sample.gz2_dps,
                    sample.g1_mag,
                    sample.g2_mag,
                    sample.a1_mag,
                    sample.a2_mag,
                ]
            elif isinstance(sample, SerialSample):
                # SerialSample：只有原始值
                row = [
                    sample.seq,
                    sample.t_remote_ms,
                    sample.btn,
                    sample.ax1,
                    sample.ay1,
                    sample.az1,
                    sample.gx1,
                    sample.gy1,
                    sample.gz1,
                    sample.ax2,
                    sample.ay2,
                    sample.az2,
                    sample.gx2,
                    sample.gy2,
                    sample.gz2,
                    # 物理單位（自動換算）
                    sample.ax1 / 16384.0,
                    sample.ay1 / 16384.0,
                    sample.az1 / 16384.0,
                    sample.gx1 / 131.0,
                    sample.gy1 / 131.0,
                    sample.gz1 / 131.0,
                    sample.ax2 / 16384.0,
                    sample.ay2 / 16384.0,
                    sample.az2 / 16384.0,
                    sample.gx2 / 131.0,
                    sample.gy2 / 131.0,
                    sample.gz2 / 131.0,
                    0.0,  # g1_mag（未計算）
                    0.0,  # g2_mag
                    0.0,  # a1_mag
                    0.0,  # a2_mag
                ]
            else:
                logger.warning(f"Unknown sample type: {type(sample)}")
                return False

            self._csv_writer.writerow(row)

            # 更新統計
            self._sample_count += 1
            if self._first_sample_time_ms is None:
                self._first_sample_time_ms = sample.t_remote_ms
            self._last_sample_time_ms = sample.t_remote_ms

            return True

        except Exception as e:
            logger.error(f"Failed to write sample: {e}")
            return False

    def stop(self) -> dict:
        """停止錄製

        Returns:
            meta.json 內容

        Raises:
            RuntimeError: 沒有正在錄製
        """
        if not self._recording:
            raise RuntimeError("Not recording")

        # 關閉 CSV 檔案
        if self._csv_file:
            self._csv_file.close()
            self._csv_file = None
            self._csv_writer = None

        # 計算統計資料
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - self._start_time).total_seconds() * 1000)

        # 計算實際採樣率（從資料時間戳推算）
        sample_rate = 100  # 預設值
        if self._sample_count > 1 and self._first_sample_time_ms is not None and self._last_sample_time_ms is not None:
            data_duration_ms = self._last_sample_time_ms - self._first_sample_time_ms
            if data_duration_ms > 0:
                sample_rate = int(self._sample_count * 1000 / data_duration_ms)

        # 建立 meta.json
        meta = {
            "name": self._session_id.rsplit('_', 2)[0],  # 移除時間戳部分
            "created_at": self._start_time.isoformat(),
            "duration_ms": duration_ms,
            "sample_count": self._sample_count,
            "sample_rate": sample_rate,
            "accel_range": self._accel_range,
            "gyro_range": self._gyro_range,
            "imu_positions": self._imu_positions,
            "columns": [
                "seq", "t_remote_ms", "btn",
                "ax1", "ay1", "az1", "gx1", "gy1", "gz1",
                "ax2", "ay2", "az2", "gx2", "gy2", "gz2",
                "ax1_g", "ay1_g", "az1_g", "gx1_dps", "gy1_dps", "gz1_dps",
                "ax2_g", "ay2_g", "az2_g", "gx2_dps", "gy2_dps", "gz2_dps",
                "g1_mag", "g2_mag", "a1_mag", "a2_mag"
            ]
        }

        # 寫入 meta.json
        meta_path = self._session_dir / "meta.json"
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)

        logger.info(f"Recording stopped: {self._session_id}, {self._sample_count} samples, {duration_ms}ms")

        # 重置狀態
        self._recording = False
        self._session_id = None
        self._session_dir = None

        return meta

    @property
    def is_recording(self) -> bool:
        """是否正在錄製"""
        return self._recording

    @property
    def current_session(self) -> Optional[str]:
        """目前錄製的 session ID"""
        return self._session_id if self._recording else None

    @property
    def sample_count(self) -> int:
        """已錄製筆數"""
        return self._sample_count if self._recording else 0
