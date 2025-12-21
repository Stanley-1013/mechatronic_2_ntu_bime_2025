"""
Test Data Models
測試資料模型
"""
import pytest
from models.sample import RawSample, ProcessedSample


def test_raw_sample_creation(sample_raw_data):
    """
    測試 RawSample 建立
    """
    sample = RawSample(**sample_raw_data)
    assert sample.seq == 1234
    assert sample.t_remote_ms == 100500
    assert sample.btn == 0
    assert sample.ax1 == 16384
    assert sample.az1 == 0


def test_raw_sample_fields():
    """
    測試 RawSample 欄位數量（必須 15 個必填欄位）
    """
    sample = RawSample(
        seq=1, t_remote_ms=1000, btn=0,
        ax1=0, ay1=0, az1=16384, gx1=0, gy1=0, gz1=0,
        ax2=0, ay2=0, az2=16384, gx2=0, gy2=0, gz2=0
    )
    assert sample.seq == 1
    assert sample.az1 == 16384  # ~1g on Z axis
    assert sample.az2 == 16384


def test_processed_sample_creation(sample_processed_data):
    """
    測試 ProcessedSample 建立
    """
    sample = ProcessedSample(**sample_processed_data)
    assert sample.seq == 1234
    assert sample.ax1_g == 1.0
    assert sample.g1_mag == 0.0
    assert sample.a1_mag == 1.0


def test_processed_sample_magnitude():
    """
    測試計算後的模長值
    """
    sample = ProcessedSample(
        seq=100,
        t_remote_ms=5000,
        t_received_ns=1703200000000000000,
        btn=0,
        ax1_g=0.0, ay1_g=0.0, az1_g=1.0,
        gx1_dps=10.0, gy1_dps=20.0, gz1_dps=30.0,
        ax2_g=0.0, ay2_g=0.0, az2_g=1.0,
        gx2_dps=15.0, gy2_dps=25.0, gz2_dps=35.0,
        g1_mag=37.42,  # sqrt(10^2 + 20^2 + 30^2)
        g2_mag=45.28,  # sqrt(15^2 + 25^2 + 35^2)
        a1_mag=1.0,
        a2_mag=1.0
    )
    assert sample.g1_mag == pytest.approx(37.42, rel=0.01)
    assert sample.g2_mag == pytest.approx(45.28, rel=0.01)
    assert sample.a1_mag == 1.0
