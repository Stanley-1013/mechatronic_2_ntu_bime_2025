"""
投籃切段服務單元測試
"""

import pytest
from services.segmenter import Segmenter, SegmentState, ShotSegment
from services.processor import ProcessedSample


def create_sample(t_ms: int, g1_mag: float, btn: int = 0) -> ProcessedSample:
    """建立測試用 ProcessedSample"""
    return ProcessedSample(
        seq=0,
        t_remote_ms=t_ms,
        t_received_ns=t_ms * 1_000_000,
        btn=btn,
        ax1_g=0, ay1_g=0, az1_g=0,
        gx1_dps=0, gy1_dps=0, gz1_dps=0,
        ax2_g=0, ay2_g=0, az2_g=0,
        gx2_dps=0, gy2_dps=0, gz2_dps=0,
        g1_mag=g1_mag,
        g2_mag=g1_mag * 0.8,  # 模擬 MPU2
        a1_mag=1.0,
        a2_mag=1.0,
    )


class TestSegmenter:
    """Segmenter 狀態機測試"""

    def test_initial_state(self):
        """初始狀態應為 IDLE"""
        seg = Segmenter()
        assert seg.state == SegmentState.IDLE
        assert len(seg.segments) == 0
        assert seg.current_segment is None

    def test_enter_active_state(self):
        """測試進入 ACTIVE 狀態"""
        seg = Segmenter(
            threshold_on=50.0,
            enter_duration_ms=80,
            adaptive=False
        )

        # 送入低於閾值的樣本，應保持 IDLE
        for i in range(5):
            result = seg.process(create_sample(i * 10, 30.0))
            assert seg.state == SegmentState.IDLE
            assert result is None

        # 送入高於閾值的樣本，但持續時間不足
        result = seg.process(create_sample(100, 60.0))
        assert seg.state == SegmentState.IDLE

        # 繼續送入高於閾值的樣本，達到持續時間
        for i in range(10):
            result = seg.process(create_sample(110 + i * 10, 60.0))

        # 應進入 ACTIVE
        assert seg.state == SegmentState.ACTIVE
        assert seg.current_segment is not None

    def test_exit_active_to_cooldown(self):
        """測試從 ACTIVE 進入 COOLDOWN"""
        seg = Segmenter(
            threshold_on=50.0,
            threshold_off=30.0,
            enter_duration_ms=80,
            exit_duration_ms=200,
            adaptive=False
        )

        # 進入 ACTIVE
        for i in range(10):
            seg.process(create_sample(i * 10, 60.0))
        assert seg.state == SegmentState.ACTIVE

        # 送入低於離開閾值的樣本
        for i in range(25):
            result = seg.process(create_sample(100 + i * 10, 20.0))

        # 應進入 COOLDOWN
        assert seg.state == SegmentState.COOLDOWN

    def test_complete_segment(self):
        """測試完整段落生成"""
        seg = Segmenter(
            threshold_on=50.0,
            threshold_off=30.0,
            enter_duration_ms=80,
            exit_duration_ms=200,
            min_segment_ms=300,
            cooldown_ms=400,
            adaptive=False
        )

        # IDLE -> ACTIVE
        for i in range(10):
            seg.process(create_sample(i * 10, 60.0))
        assert seg.state == SegmentState.ACTIVE

        # ACTIVE（保持 500ms）
        for i in range(50):
            seg.process(create_sample(100 + i * 10, 60.0))

        # ACTIVE -> COOLDOWN
        for i in range(25):
            seg.process(create_sample(600 + i * 10, 20.0))
        assert seg.state == SegmentState.COOLDOWN

        # COOLDOWN -> IDLE（完成段落）
        for i in range(50):
            result = seg.process(create_sample(850 + i * 10, 20.0))
            if result is not None:
                # 段落完成
                assert isinstance(result, ShotSegment)
                assert result.duration_ms >= 300
                assert 'g1_rms' in result.features
                assert 'g1_peak' in result.features
                break

        assert seg.state == SegmentState.IDLE
        assert len(seg.segments) == 1

    def test_segment_too_short(self):
        """測試太短的段落被丟棄"""
        seg = Segmenter(
            threshold_on=50.0,
            threshold_off=30.0,
            enter_duration_ms=50,
            exit_duration_ms=100,
            min_segment_ms=300,
            cooldown_ms=200,
            adaptive=False
        )

        # 短暫的動作（從 50ms 到 250ms，只有 200ms）
        for i in range(5):
            seg.process(create_sample(i * 10, 60.0))

        for i in range(15):  # 減少到 15 筆（150ms）
            seg.process(create_sample(50 + i * 10, 60.0))

        for i in range(15):
            seg.process(create_sample(200 + i * 10, 20.0))

        # 冷卻結束
        for i in range(30):
            result = seg.process(create_sample(350 + i * 10, 20.0))

        # 段落太短（200ms < 300ms），應被丟棄
        assert len(seg.segments) == 0

    def test_callback(self):
        """測試段落完成回調"""
        completed_segments = []

        def on_complete(segment: ShotSegment):
            completed_segments.append(segment)

        seg = Segmenter(
            threshold_on=50.0,
            threshold_off=30.0,
            enter_duration_ms=50,
            exit_duration_ms=100,
            min_segment_ms=300,
            cooldown_ms=200,
            adaptive=False
        )
        seg.set_on_segment_complete(on_complete)

        # 完成一個段落
        for i in range(5):
            seg.process(create_sample(i * 10, 60.0))

        for i in range(50):
            seg.process(create_sample(50 + i * 10, 60.0))

        for i in range(15):
            seg.process(create_sample(550 + i * 10, 20.0))

        for i in range(30):
            seg.process(create_sample(700 + i * 10, 20.0))

        # 回調應被觸發
        assert len(completed_segments) == 1

    def test_features_computation(self):
        """測試特徵計算"""
        seg = Segmenter(
            threshold_on=50.0,
            threshold_off=30.0,
            adaptive=False
        )

        # 模擬一個完整段落
        for i in range(10):
            seg.process(create_sample(i * 10, 60.0))

        for i in range(50):
            seg.process(create_sample(100 + i * 10, 70.0 + i % 10))

        for i in range(25):
            seg.process(create_sample(600 + i * 10, 20.0))

        for i in range(50):
            result = seg.process(create_sample(850 + i * 10, 20.0))
            if result:
                # 檢查特徵
                assert 'dur' in result.features
                assert 'g1_rms' in result.features
                assert 'g1_peak' in result.features
                assert 'g2_rms' in result.features
                assert 'g2_peak' in result.features
                assert 'dg_rms' in result.features

                assert result.features['g1_rms'] > 0
                assert result.features['g1_peak'] > result.features['g1_rms']
                break

    def test_get_segment_by_id(self):
        """測試依 ID 取得段落"""
        seg = Segmenter(adaptive=False)

        # 完成兩個段落
        for _ in range(2):
            for i in range(10):
                seg.process(create_sample(i * 10, 60.0))

            for i in range(50):
                seg.process(create_sample(100 + i * 10, 60.0))

            for i in range(25):
                seg.process(create_sample(600 + i * 10, 20.0))

            for i in range(50):
                seg.process(create_sample(850 + i * 10, 20.0))

        assert len(seg.segments) >= 1

        # 測試取得
        first_seg = seg.segments[0]
        retrieved = seg.get_segment(first_seg.shot_id)
        assert retrieved is not None
        assert retrieved.shot_id == first_seg.shot_id

    def test_clear_segments(self):
        """測試清空段落"""
        seg = Segmenter(adaptive=False)

        # 完成一個段落
        for i in range(10):
            seg.process(create_sample(i * 10, 60.0))

        for i in range(50):
            seg.process(create_sample(100 + i * 10, 60.0))

        for i in range(25):
            seg.process(create_sample(600 + i * 10, 20.0))

        for i in range(50):
            seg.process(create_sample(850 + i * 10, 20.0))

        assert len(seg.segments) >= 1

        # 清空
        seg.clear_segments()
        assert len(seg.segments) == 0
        assert seg.state == SegmentState.IDLE
