"""
Serial Ingest Service
從 Arduino Uno 讀取 CSV 格式的 IMU 資料

資料格式參考: docs/stage2/SERIAL_FORMAT.md
"""

import asyncio
import serial
import time
from typing import Callable, Optional
from dataclasses import dataclass
from threading import Thread, Event
import logging

logger = logging.getLogger(__name__)


@dataclass
class SerialSample:
    """
    Serial 資料樣本（對應實際 CSV 格式）

    Format: seq,t_remote_ms,btn,ax1,ay1,az1,gx1,gy1,gz1,ax2,ay2,az2,gx2,gy2,gz2
    """
    seq: int            # 封包序號 (0~65535)
    t_remote_ms: int    # 遠距端時間戳 (ms)
    btn: int            # 按鈕狀態 (0/1)

    # MPU1 資料
    ax1: int            # 加速度 X raw
    ay1: int            # 加速度 Y raw
    az1: int            # 加速度 Z raw
    gx1: int            # 陀螺儀 X raw
    gy1: int            # 陀螺儀 Y raw
    gz1: int            # 陀螺儀 Z raw

    # MPU2 資料
    ax2: int            # 加速度 X raw
    ay2: int            # 加速度 Y raw
    az2: int            # 加速度 Z raw
    gx2: int            # 陀螺儀 X raw
    gy2: int            # 陀螺儀 Y raw
    gz2: int            # 陀螺儀 Z raw

    # 接收時間戳（本地）
    t_received_ns: int = 0  # 本地接收時間 (ns)


class SerialIngest:
    """
    Serial 讀取服務

    從 Arduino Uno (115200 baud) 讀取 CSV 格式資料，
    提供統計資訊（pps, dropped, parse_err）
    """

    def __init__(self, port: str, baud: int = 115200):
        """
        初始化 Serial 連接

        Args:
            port: Serial port (e.g. "/dev/ttyUSB0", "COM3")
            baud: Baud rate (default: 115200)
        """
        self.port = port
        self.baud = baud
        self.serial: Optional[serial.Serial] = None

        # 執行控制
        self._running = False
        self._stop_event = Event()
        self._thread: Optional[Thread] = None

        # 統計資料
        self._stats = {
            'pps': 0.0,          # 每秒封包數
            'dropped': 0,        # 累計掉包數
            'parse_err': 0,      # 累計解析錯誤
            'total_rx': 0,       # 累計接收封包數
        }

        # 掉包檢測
        self._last_seq: Optional[int] = None

        # PPS 計算
        self._pps_window_start = 0.0
        self._pps_window_count = 0
        self._pps_window_sec = 1.0  # 每秒更新一次

    async def start(self, on_sample: Callable[[SerialSample], None]):
        """
        開始讀取資料

        Args:
            on_sample: 每收到一筆有效資料時的回調函數

        Raises:
            serial.SerialException: Serial 連接失敗
        """
        if self._running:
            logger.warning("SerialIngest already running")
            return

        # 開啟 Serial
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baud,
                timeout=1.0,  # 1 秒 timeout
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
            )
            logger.info(f"Serial opened: {self.port} @ {self.baud} baud")
        except serial.SerialException as e:
            logger.error(f"Failed to open serial port {self.port}: {e}")
            raise

        # 初始化統計
        self._reset_stats()
        self._running = True
        self._stop_event.clear()

        # 啟動讀取線程（避免阻塞 asyncio）
        self._thread = Thread(target=self._read_loop, args=(on_sample,), daemon=True)
        self._thread.start()

        logger.info("SerialIngest started")

    def stop(self):
        """停止讀取"""
        if not self._running:
            return

        logger.info("Stopping SerialIngest...")
        self._running = False
        self._stop_event.set()

        # 等待線程結束
        if self._thread:
            self._thread.join(timeout=2.0)
            if self._thread.is_alive():
                logger.warning("Read thread did not stop gracefully")

        # 關閉 Serial
        if self.serial and self.serial.is_open:
            self.serial.close()
            logger.info("Serial closed")

        self._thread = None

    def _read_loop(self, on_sample: Callable[[SerialSample], None]):
        """
        讀取循環（運行在獨立線程）

        Args:
            on_sample: 回調函數
        """
        logger.info("Read loop started")

        while self._running and not self._stop_event.is_set():
            try:
                # 讀取一行
                if not self.serial or not self.serial.is_open:
                    logger.error("Serial not open")
                    break

                line_bytes = self.serial.readline()
                if not line_bytes:
                    continue  # timeout

                # 解碼
                try:
                    line = line_bytes.decode('utf-8', errors='ignore').strip()
                except Exception as e:
                    logger.debug(f"Decode error: {e}")
                    continue

                # 解析
                sample = self.parse_line(line)
                if sample:
                    # 記錄接收時間
                    sample.t_received_ns = time.time_ns()

                    # 掉包檢測
                    dropped = self._check_drop(sample.seq)
                    if dropped > 0:
                        self._stats['dropped'] += dropped
                        logger.warning(f"Dropped {dropped} packets (seq: {self._last_seq} -> {sample.seq})")

                    # 更新統計
                    self._stats['total_rx'] += 1
                    self._update_pps()

                    # 回調
                    try:
                        on_sample(sample)
                    except Exception as e:
                        logger.error(f"Callback error: {e}")

            except serial.SerialException as e:
                logger.error(f"Serial error: {e}")
                break
            except Exception as e:
                logger.error(f"Unexpected error in read loop: {e}")

        logger.info("Read loop ended")

    def parse_line(self, line: str) -> Optional[SerialSample]:
        """
        解析一行 CSV 資料

        Args:
            line: 一行 CSV 字串

        Returns:
            SerialSample 或 None（忽略 # 開頭或格式錯誤）
        """
        # 忽略空行和狀態行
        if not line or line.startswith('#'):
            return None

        # 分割 CSV
        parts = line.split(',')
        if len(parts) != 15:
            self._stats['parse_err'] += 1
            logger.debug(f"Invalid CSV format (expected 15 fields, got {len(parts)}): {line[:50]}")
            return None

        # 解析各欄位
        try:
            return SerialSample(
                seq=int(parts[0]),
                t_remote_ms=int(parts[1]),
                btn=int(parts[2]),
                ax1=int(parts[3]),
                ay1=int(parts[4]),
                az1=int(parts[5]),
                gx1=int(parts[6]),
                gy1=int(parts[7]),
                gz1=int(parts[8]),
                ax2=int(parts[9]),
                ay2=int(parts[10]),
                az2=int(parts[11]),
                gx2=int(parts[12]),
                gy2=int(parts[13]),
                gz2=int(parts[14]),
            )
        except ValueError as e:
            self._stats['parse_err'] += 1
            logger.debug(f"Parse error: {e}, line: {line[:50]}")
            return None

    def _check_drop(self, current_seq: int) -> int:
        """
        檢測掉包

        Args:
            current_seq: 當前封包序號

        Returns:
            掉包數量
        """
        if self._last_seq is None:
            self._last_seq = current_seq
            return 0

        expected = (self._last_seq + 1) % 65536
        if current_seq != expected:
            # 計算掉包數（處理 uint16 溢位）
            dropped = (current_seq - expected) % 65536
            self._last_seq = current_seq
            return dropped

        self._last_seq = current_seq
        return 0

    def _update_pps(self):
        """更新 PPS 統計（每秒計算一次）"""
        now = time.time()

        # 初始化窗口
        if self._pps_window_start == 0.0:
            self._pps_window_start = now
            self._pps_window_count = 0

        self._pps_window_count += 1

        # 每秒更新一次
        elapsed = now - self._pps_window_start
        if elapsed >= self._pps_window_sec:
            self._stats['pps'] = self._pps_window_count / elapsed
            self._pps_window_start = now
            self._pps_window_count = 0

    def _reset_stats(self):
        """重置統計資料"""
        self._stats = {
            'pps': 0.0,
            'dropped': 0,
            'parse_err': 0,
            'total_rx': 0,
        }
        self._last_seq = None
        self._pps_window_start = 0.0
        self._pps_window_count = 0

    @property
    def is_running(self) -> bool:
        """是否正在運行"""
        return self._running

    @property
    def stats(self) -> dict:
        """
        取得統計資訊

        Returns:
            {
                'pps': float,          # 每秒封包數
                'dropped': int,        # 累計掉包數
                'parse_err': int,      # 累計解析錯誤
                'total_rx': int,       # 累計接收封包數
            }
        """
        return self._stats.copy()
