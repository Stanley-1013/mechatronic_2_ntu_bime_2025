"""
Backend Configuration
配置參數（Serial port, sample rate 等）
"""
import os
from typing import Optional

# Serial 設定
SERIAL_PORT: str = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
SERIAL_BAUD: int = int(os.getenv("SERIAL_BAUD", "115200"))

# 資料處理設定
SAMPLE_RATE: int = 100  # Hz
RING_BUFFER_SECONDS: int = 60  # 秒

# 單位換算
ACCEL_SCALE: float = 16384.0  # ±2g
GYRO_SCALE: float = 131.0     # ±250 dps

# CORS 設定
CORS_ORIGINS: list[str] = [
    "http://localhost:3000",  # React dev server
    "http://localhost:5173",  # Vite dev server
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]

# API 設定
API_PREFIX: str = "/api"
API_VERSION: str = "v1"
