"""
Player Service - 回放控制模組
載入錄製的 session 並按時間戳回放
"""
import os
import json
import csv
import asyncio
from typing import List, Optional, Callable, Dict, Any
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class PlayerState(Enum):
    """回放狀態"""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class SessionInfo:
    """Session 摘要"""
    id: str
    name: str
    created_at: str
    duration_ms: int
    sample_count: int
    path: str


class Player:
    """回放服務

    載入錄製的 session 並按時間戳回放，支援暫停、繼續、跳轉功能。
    """

    def __init__(self, base_dir: str = "recordings"):
        """初始化回放服務

        Args:
            base_dir: 錄製檔案基礎目錄
        """
        self.base_dir = Path(base_dir)
        self._state = PlayerState.IDLE
        self._loaded_session: Optional[SessionInfo] = None
        self._samples: List[Dict[str, Any]] = []
        self._current_index: int = 0
        self._play_task: Optional[asyncio.Task] = None
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # 初始為非暫停狀態
        self._stop_flag = False

    def list_sessions(self) -> List[SessionInfo]:
        """列出所有 sessions

        Returns:
            Session 摘要列表，按建立時間降序排列
        """
        sessions = []

        if not self.base_dir.exists():
            return sessions

        # 掃描 base_dir 下的所有 session 目錄
        for session_dir in self.base_dir.iterdir():
            if not session_dir.is_dir():
                continue

            # FIXED: Support both meta.json (new format) and metadata.json (old format)
            meta_path = session_dir / "meta.json"
            if not meta_path.exists():
                meta_path = session_dir / "metadata.json"

            data_path = session_dir / "data.csv"

            if not meta_path.exists() or not data_path.exists():
                continue

            try:
                with open(meta_path, 'r') as f:
                    meta = json.load(f)

                # 讀取樣本數（扣除 header）
                with open(data_path, 'r') as f:
                    sample_count = sum(1 for _ in f) - 1  # 扣除 header

                # 計算時長（從 metadata 或從資料推算）
                duration_ms = meta.get('duration_ms', 0)

                sessions.append(SessionInfo(
                    id=meta.get('session_id', session_dir.name),
                    name=meta.get('name', session_dir.name),
                    created_at=meta.get('created_at', ''),
                    duration_ms=duration_ms,
                    sample_count=sample_count,
                    path=str(session_dir)
                ))
            except (json.JSONDecodeError, OSError) as e:
                # 跳過損壞的 session
                print(f"[WARN] 跳過損壞的 session {session_dir.name}: {e}")
                continue

        # 按建立時間降序排列
        sessions.sort(key=lambda s: s.created_at, reverse=True)
        return sessions

    def load_session(self, session_id: str) -> bool:
        """載入指定 session

        Args:
            session_id: Session ID

        Returns:
            是否成功載入
        """
        # 找到對應的 session
        session_dir = self.base_dir / session_id

        # FIXED: Support both meta.json (new format) and metadata.json (old format)
        meta_path = session_dir / "meta.json"
        if not meta_path.exists():
            meta_path = session_dir / "metadata.json"

        data_path = session_dir / "data.csv"

        if not session_dir.exists() or not meta_path.exists() or not data_path.exists():
            print(f"[ERROR] Session {session_id} 不存在或檔案不完整")
            return False

        try:
            # 讀取 metadata
            with open(meta_path, 'r') as f:
                meta = json.load(f)

            # 讀取資料
            samples = []
            with open(data_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 將所有數值欄位轉為適當類型
                    sample = {}
                    for k, v in row.items():
                        try:
                            # Try int first, then float
                            if '.' in str(v):
                                sample[k] = float(v)
                            else:
                                sample[k] = int(v)
                        except ValueError:
                            sample[k] = v  # 保留字串（如有）
                    samples.append(sample)

            if not samples:
                print(f"[ERROR] Session {session_id} 無資料")
                return False

            # 計算時長（從第一筆到最後一筆的時間差）
            first_t = samples[0].get('t_remote_ms', 0)
            last_t = samples[-1].get('t_remote_ms', 0)
            duration_ms = last_t - first_t

            # 建立 SessionInfo
            self._loaded_session = SessionInfo(
                id=meta.get('session_id', session_id),
                name=meta.get('name', session_id),
                created_at=meta.get('created_at', ''),
                duration_ms=duration_ms,
                sample_count=len(samples),
                path=str(session_dir)
            )

            self._samples = samples
            self._current_index = 0
            self._state = PlayerState.IDLE

            print(f"[OK] 已載入 session {session_id}，共 {len(samples)} 筆，時長 {duration_ms}ms")
            return True

        except (json.JSONDecodeError, OSError, csv.Error) as e:
            print(f"[ERROR] 載入 session {session_id} 失敗: {e}")
            return False

    async def play(self,
                   on_sample: Callable[[Dict[str, Any]], None],
                   speed: float = 1.0,
                   start_ms: int = 0):
        """開始回放

        Args:
            on_sample: 每筆資料的 callback（接收 sample dict）
            speed: 回放速度（1.0=原速，2.0=兩倍速，0.5=半速）
            start_ms: 起始時間戳（相對於 session 開始）
        """
        if not self._loaded_session or not self._samples:
            print("[ERROR] 未載入 session，無法回放")
            return

        if self._state == PlayerState.PLAYING:
            print("[WARN] 已在回放中")
            return

        # 找到起始位置
        if start_ms > 0:
            self.seek(start_ms)

        self._state = PlayerState.PLAYING
        self._stop_flag = False
        self._pause_event.set()  # 確保非暫停狀態

        try:
            first_t = self._samples[0].get('t_remote_ms', 0)

            while self._current_index < len(self._samples) and not self._stop_flag:
                # 等待暫停解除
                await self._pause_event.wait()

                if self._stop_flag:
                    break

                current_sample = self._samples[self._current_index]

                # 呼叫 callback（支援 async 和 sync）
                result = on_sample(current_sample)
                if asyncio.iscoroutine(result):
                    await result

                # 計算下一筆的延遲時間
                if self._current_index + 1 < len(self._samples):
                    current_t = current_sample.get('t_remote_ms', 0)
                    next_t = self._samples[self._current_index + 1].get('t_remote_ms', 0)
                    delay_ms = (next_t - current_t) / speed

                    if delay_ms > 0:
                        await asyncio.sleep(delay_ms / 1000.0)

                self._current_index += 1

            # 回放結束
            if not self._stop_flag:
                print(f"[OK] 回放完成（共 {len(self._samples)} 筆）")
                self._state = PlayerState.STOPPED
            else:
                print("[OK] 回放已停止")
                self._state = PlayerState.STOPPED

        except Exception as e:
            print(f"[ERROR] 回放過程發生錯誤: {e}")
            self._state = PlayerState.STOPPED

    def pause(self):
        """暫停回放"""
        if self._state != PlayerState.PLAYING:
            print("[WARN] 非回放狀態，無法暫停")
            return

        self._state = PlayerState.PAUSED
        self._pause_event.clear()
        print("[OK] 已暫停")

    def resume(self):
        """繼續回放"""
        if self._state != PlayerState.PAUSED:
            print("[WARN] 非暫停狀態，無法繼續")
            return

        self._state = PlayerState.PLAYING
        self._pause_event.set()
        print("[OK] 已繼續")

    def stop(self):
        """停止回放"""
        if self._state not in (PlayerState.PLAYING, PlayerState.PAUSED):
            print("[WARN] 非回放狀態，無法停止")
            return

        self._stop_flag = True
        self._pause_event.set()  # 確保不會卡在暫停狀態
        self._state = PlayerState.STOPPED
        print("[OK] 已停止")

    def seek(self, time_ms: int):
        """跳轉到指定時間

        Args:
            time_ms: 相對於 session 開始的時間（毫秒）
        """
        if not self._loaded_session or not self._samples:
            print("[ERROR] 未載入 session，無法跳轉")
            return

        first_t = self._samples[0].get('t_remote_ms', 0)
        target_t = first_t + time_ms

        # 二分搜尋找到最接近的 index
        left, right = 0, len(self._samples) - 1
        result_index = 0

        while left <= right:
            mid = (left + right) // 2
            mid_t = self._samples[mid].get('t_remote_ms', 0)

            if mid_t <= target_t:
                result_index = mid
                left = mid + 1
            else:
                right = mid - 1

        self._current_index = result_index
        print(f"[OK] 已跳轉到 {time_ms}ms（index={result_index}）")

    @property
    def is_playing(self) -> bool:
        """是否正在回放"""
        return self._state == PlayerState.PLAYING

    @property
    def is_paused(self) -> bool:
        """是否暫停中"""
        return self._state == PlayerState.PAUSED

    @property
    def current_time_ms(self) -> int:
        """目前回放時間（相對於 session 開始）"""
        if not self._samples or self._current_index >= len(self._samples):
            return 0

        first_t = self._samples[0].get('t_remote_ms', 0)
        current_t = self._samples[self._current_index].get('t_remote_ms', 0)
        return current_t - first_t

    @property
    def total_duration_ms(self) -> int:
        """總時長"""
        if self._loaded_session:
            return self._loaded_session.duration_ms
        return 0

    @property
    def loaded_session(self) -> Optional[SessionInfo]:
        """目前載入的 session"""
        return self._loaded_session
