"""
Sample Data Models
原始與處理後的 IMU 資料模型

對應 SERIAL_FORMAT.md 定義的雙 MPU6050 格式（15 欄位）
"""
from pydantic import BaseModel, Field
from typing import Optional


class RawSample(BaseModel):
    """
    原始 CSV 資料模型（15 欄位）
    對應 firmware 輸出的 CSV 格式

    Format: seq,t_remote_ms,btn,ax1,ay1,az1,gx1,gy1,gz1,ax2,ay2,az2,gx2,gy2,gz2
    """
    seq: int = Field(..., description="封包序號（0~65535 循環）")
    t_remote_ms: int = Field(..., description="遠距端 millis() 時間戳")
    btn: int = Field(..., description="按鈕狀態（0=未按，1=按下）")

    # MPU1 資料
    ax1: int = Field(..., description="MPU1 加速度 X 軸 raw 值")
    ay1: int = Field(..., description="MPU1 加速度 Y 軸 raw 值")
    az1: int = Field(..., description="MPU1 加速度 Z 軸 raw 值")
    gx1: int = Field(..., description="MPU1 陀螺儀 X 軸 raw 值")
    gy1: int = Field(..., description="MPU1 陀螺儀 Y 軸 raw 值")
    gz1: int = Field(..., description="MPU1 陀螺儀 Z 軸 raw 值")

    # MPU2 資料
    ax2: int = Field(..., description="MPU2 加速度 X 軸 raw 值")
    ay2: int = Field(..., description="MPU2 加速度 Y 軸 raw 值")
    az2: int = Field(..., description="MPU2 加速度 Z 軸 raw 值")
    gx2: int = Field(..., description="MPU2 陀螺儀 X 軸 raw 值")
    gy2: int = Field(..., description="MPU2 陀螺儀 Y 軸 raw 值")
    gz2: int = Field(..., description="MPU2 陀螺儀 Z 軸 raw 值")

    # 接收時間（本地）
    t_received_ns: Optional[int] = Field(None, description="本地接收時間戳 (ns)")

    class Config:
        json_schema_extra = {
            "example": {
                "seq": 1234,
                "t_remote_ms": 100500,
                "btn": 0,
                "ax1": 16384,
                "ay1": -200,
                "az1": 16000,
                "gx1": 50,
                "gy1": -30,
                "gz1": 10,
                "ax2": 16200,
                "ay2": -150,
                "az2": 16100,
                "gx2": 45,
                "gy2": -25,
                "gz2": 8,
                "t_received_ns": 1703200000000000000
            }
        }


class ProcessedSample(BaseModel):
    """
    處理後資料（物理單位）
    將原始值轉換為物理單位，並包含計算後的模長
    """
    seq: int = Field(..., description="封包序號")
    t_remote_ms: int = Field(..., description="遠距端時間戳 (ms)")
    t_received_ns: int = Field(..., description="本地接收時間戳 (ns)")
    btn: int = Field(..., description="按鈕狀態（0/1）")

    # MPU1 物理單位
    ax1_g: float = Field(..., description="MPU1 加速度 X (g)")
    ay1_g: float = Field(..., description="MPU1 加速度 Y (g)")
    az1_g: float = Field(..., description="MPU1 加速度 Z (g)")
    gx1_dps: float = Field(..., description="MPU1 陀螺儀 X (°/s)")
    gy1_dps: float = Field(..., description="MPU1 陀螺儀 Y (°/s)")
    gz1_dps: float = Field(..., description="MPU1 陀螺儀 Z (°/s)")

    # MPU2 物理單位
    ax2_g: float = Field(..., description="MPU2 加速度 X (g)")
    ay2_g: float = Field(..., description="MPU2 加速度 Y (g)")
    az2_g: float = Field(..., description="MPU2 加速度 Z (g)")
    gx2_dps: float = Field(..., description="MPU2 陀螺儀 X (°/s)")
    gy2_dps: float = Field(..., description="MPU2 陀螺儀 Y (°/s)")
    gz2_dps: float = Field(..., description="MPU2 陀螺儀 Z (°/s)")

    # 計算值（濾波後）
    g1_mag: float = Field(..., description="MPU1 陀螺儀模長 (°/s)")
    g2_mag: float = Field(..., description="MPU2 陀螺儀模長 (°/s)")
    a1_mag: float = Field(..., description="MPU1 加速度模長 (g)")
    a2_mag: float = Field(..., description="MPU2 加速度模長 (g)")

    class Config:
        json_schema_extra = {
            "example": {
                "seq": 1234,
                "t_remote_ms": 100500,
                "t_received_ns": 1703200000000000000,
                "btn": 0,
                "ax1_g": 1.0,
                "ay1_g": -0.012,
                "az1_g": 0.976,
                "gx1_dps": 0.382,
                "gy1_dps": -0.229,
                "gz1_dps": 0.076,
                "ax2_g": 0.988,
                "ay2_g": -0.009,
                "az2_g": 0.983,
                "gx2_dps": 0.344,
                "gy2_dps": -0.191,
                "gz2_dps": 0.061,
                "g1_mag": 0.456,
                "g2_mag": 0.398,
                "a1_mag": 1.001,
                "a2_mag": 0.995
            }
        }
