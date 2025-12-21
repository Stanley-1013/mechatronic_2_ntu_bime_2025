"""
Pytest Fixtures
測試共用配置
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# 將 backend 加入路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app


@pytest.fixture
def client():
    """
    FastAPI TestClient fixture
    """
    return TestClient(app)


@pytest.fixture
def sample_raw_data():
    """
    範例原始資料（15 欄位）
    對應 SERIAL_FORMAT.md 定義
    """
    return {
        "seq": 1234,
        "t_remote_ms": 100500,
        "btn": 0,
        "ax1": 16384,  # ~1g
        "ay1": 0,
        "az1": 0,
        "gx1": 0,
        "gy1": 0,
        "gz1": 0,
        "ax2": 16384,  # ~1g
        "ay2": 0,
        "az2": 0,
        "gx2": 0,
        "gy2": 0,
        "gz2": 0
    }


@pytest.fixture
def sample_processed_data():
    """
    範例處理後資料（物理單位）
    """
    return {
        "seq": 1234,
        "t_remote_ms": 100500,
        "t_received_ns": 1703200000000000000,
        "btn": 0,
        "ax1_g": 1.0,
        "ay1_g": 0.0,
        "az1_g": 0.0,
        "gx1_dps": 0.0,
        "gy1_dps": 0.0,
        "gz1_dps": 0.0,
        "ax2_g": 1.0,
        "ay2_g": 0.0,
        "az2_g": 0.0,
        "gx2_dps": 0.0,
        "gy2_dps": 0.0,
        "gz2_dps": 0.0,
        "g1_mag": 0.0,
        "g2_mag": 0.0,
        "a1_mag": 1.0,
        "a2_mag": 1.0
    }
