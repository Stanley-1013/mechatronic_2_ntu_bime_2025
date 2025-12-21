"""
資料前處理服務
負責：單位換算、Gyro bias 校正、低通濾波、計算模長

規格參考: SRS FR-P6, CONFIG_PARAMS.md
"""

import math
from dataclasses import dataclass
from typing import Optional
from services.serial_ingest import SerialSample


@dataclass
class ProcessedSample:
    """處理後的感測資料"""
    seq: int
    t_remote_ms: int
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
    g1_mag: float  # |gyro1| 模長
    g2_mag: float  # |gyro2| 模長
    a1_mag: float  # |accel1| 模長
    a2_mag: float  # |accel2| 模長


class Processor:
    """
    資料前處理器

    功能：
    1. 單位換算（raw → 物理單位）
    2. Gyro bias 校正（可選）
    3. 低通濾波（IIR 一階）
    4. 計算模長
    """

    # MPU6050 量程常數（依據 CONFIG_PARAMS.md）
    # Accel Range: ±2g → LSB Sensitivity = 16384 LSB/g
    ACCEL_SCALE = 16384.0

    # Gyro Range: ±250°/s → LSB Sensitivity = 131 LSB/(°/s)
    GYRO_SCALE = 131.0

    def __init__(self, sample_rate: int = 100):
        """
        初始化

        Args:
            sample_rate: 採樣率 Hz（用於計算濾波器係數）
        """
        self.sample_rate = sample_rate

        # Gyro bias 校正狀態
        self._calibrating = False
        self._calib_samples = []
        self._calib_target_count = 0
        self._gyro_offset = {
            'gx1': 0.0, 'gy1': 0.0, 'gz1': 0.0,
            'gx2': 0.0, 'gy2': 0.0, 'gz2': 0.0,
        }

        # 濾波器狀態（上一次的值）
        self._prev_g1_mag: Optional[float] = None
        self._prev_g2_mag: Optional[float] = None
        self._prev_a1_mag: Optional[float] = None
        self._prev_a2_mag: Optional[float] = None

        # 濾波器係數（alpha = dt / (rc + dt), rc = 1 / (2*pi*cutoff_freq)）
        self._alpha_gyro = self._calc_alpha(18.0)  # 18 Hz cutoff for gyro
        self._alpha_accel = self._calc_alpha(12.0)  # 12 Hz cutoff for accel

    def _calc_alpha(self, cutoff_freq: float) -> float:
        """
        計算 IIR 濾波器係數

        Args:
            cutoff_freq: 截止頻率 (Hz)

        Returns:
            alpha 係數 (0-1)
        """
        rc = 1.0 / (2.0 * math.pi * cutoff_freq)
        dt = 1.0 / self.sample_rate
        return dt / (rc + dt)

    def process(self, raw: SerialSample) -> ProcessedSample:
        """
        處理一筆原始資料

        Args:
            raw: 原始 Serial 資料

        Returns:
            處理後的資料（含物理單位與濾波後的模長）
        """
        # 1. 單位換算
        ax1_g = raw.ax1 / self.ACCEL_SCALE
        ay1_g = raw.ay1 / self.ACCEL_SCALE
        az1_g = raw.az1 / self.ACCEL_SCALE

        ax2_g = raw.ax2 / self.ACCEL_SCALE
        ay2_g = raw.ay2 / self.ACCEL_SCALE
        az2_g = raw.az2 / self.ACCEL_SCALE

        gx1_dps = raw.gx1 / self.GYRO_SCALE
        gy1_dps = raw.gy1 / self.GYRO_SCALE
        gz1_dps = raw.gz1 / self.GYRO_SCALE

        gx2_dps = raw.gx2 / self.GYRO_SCALE
        gy2_dps = raw.gy2 / self.GYRO_SCALE
        gz2_dps = raw.gz2 / self.GYRO_SCALE

        # 2. Gyro bias 校正（如果有校正資料）
        if self._calibrating:
            # 收集校正樣本
            self._calib_samples.append({
                'gx1': gx1_dps, 'gy1': gy1_dps, 'gz1': gz1_dps,
                'gx2': gx2_dps, 'gy2': gy2_dps, 'gz2': gz2_dps,
            })

            # 如果收集足夠，計算平均值作為 offset
            if len(self._calib_samples) >= self._calib_target_count:
                self._finish_calibration()

        # 套用校正偏移量
        gx1_dps -= self._gyro_offset['gx1']
        gy1_dps -= self._gyro_offset['gy1']
        gz1_dps -= self._gyro_offset['gz1']

        gx2_dps -= self._gyro_offset['gx2']
        gy2_dps -= self._gyro_offset['gy2']
        gz2_dps -= self._gyro_offset['gz2']

        # 3. 計算原始模長
        g1_mag_raw = math.sqrt(gx1_dps**2 + gy1_dps**2 + gz1_dps**2)
        g2_mag_raw = math.sqrt(gx2_dps**2 + gy2_dps**2 + gz2_dps**2)
        a1_mag_raw = math.sqrt(ax1_g**2 + ay1_g**2 + az1_g**2)
        a2_mag_raw = math.sqrt(ax2_g**2 + ay2_g**2 + az2_g**2)

        # 4. 低通濾波（一階 IIR）
        g1_mag = self._apply_filter(g1_mag_raw, self._prev_g1_mag, self._alpha_gyro)
        g2_mag = self._apply_filter(g2_mag_raw, self._prev_g2_mag, self._alpha_gyro)
        a1_mag = self._apply_filter(a1_mag_raw, self._prev_a1_mag, self._alpha_accel)
        a2_mag = self._apply_filter(a2_mag_raw, self._prev_a2_mag, self._alpha_accel)

        # 更新濾波器狀態
        self._prev_g1_mag = g1_mag
        self._prev_g2_mag = g2_mag
        self._prev_a1_mag = a1_mag
        self._prev_a2_mag = a2_mag

        # 5. 組裝結果
        return ProcessedSample(
            seq=raw.seq,
            t_remote_ms=raw.t_remote_ms,
            t_received_ns=raw.t_received_ns,
            btn=raw.btn,

            ax1_g=ax1_g,
            ay1_g=ay1_g,
            az1_g=az1_g,
            gx1_dps=gx1_dps,
            gy1_dps=gy1_dps,
            gz1_dps=gz1_dps,

            ax2_g=ax2_g,
            ay2_g=ay2_g,
            az2_g=az2_g,
            gx2_dps=gx2_dps,
            gy2_dps=gy2_dps,
            gz2_dps=gz2_dps,

            g1_mag=g1_mag,
            g2_mag=g2_mag,
            a1_mag=a1_mag,
            a2_mag=a2_mag,
        )

    def _apply_filter(self, current: float, previous: Optional[float], alpha: float) -> float:
        """
        套用一階 IIR 低通濾波器

        filtered = alpha * current + (1 - alpha) * previous

        Args:
            current: 當前值
            previous: 上一次濾波後的值（初始為 None）
            alpha: 濾波器係數 (0-1)

        Returns:
            濾波後的值
        """
        if previous is None:
            return current  # 第一筆資料直接返回

        return alpha * current + (1.0 - alpha) * previous

    def start_calibration(self, duration_sec: float = 2.0):
        """
        開始 gyro bias 校正

        校正期間應保持設備靜止，收集樣本計算平均偏移量

        Args:
            duration_sec: 校正持續時間（秒）
        """
        self._calibrating = True
        self._calib_samples = []
        self._calib_target_count = int(self.sample_rate * duration_sec)

    def _finish_calibration(self):
        """完成校正，計算平均偏移量"""
        if not self._calib_samples:
            self._calibrating = False
            return

        n = len(self._calib_samples)

        # 計算各軸平均值
        self._gyro_offset = {
            'gx1': sum(s['gx1'] for s in self._calib_samples) / n,
            'gy1': sum(s['gy1'] for s in self._calib_samples) / n,
            'gz1': sum(s['gz1'] for s in self._calib_samples) / n,
            'gx2': sum(s['gx2'] for s in self._calib_samples) / n,
            'gy2': sum(s['gy2'] for s in self._calib_samples) / n,
            'gz2': sum(s['gz2'] for s in self._calib_samples) / n,
        }

        self._calibrating = False
        self._calib_samples = []

    def is_calibrating(self) -> bool:
        """
        是否正在校正中

        Returns:
            True 表示正在收集校正樣本
        """
        return self._calibrating

    @property
    def calibration_offset(self) -> dict:
        """
        取得校正偏移量

        Returns:
            dict with keys: gx1, gy1, gz1, gx2, gy2, gz2 (單位: °/s)
        """
        return self._gyro_offset.copy()
