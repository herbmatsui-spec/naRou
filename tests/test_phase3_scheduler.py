"""
Phase 3 テスト: 5軸スケジューラ (時間・天候・季節・月齢・フェーズ)
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock

import pytest

from quest_scheduler import (
    LogicOperator,
    QuestSchedule,
    QuestScheduler,
    ScheduleCondition,
    ScheduleContext,
    TimeWindow,
)

# ---------------------------------------------------------------------------
# Step 9/10: スケジューラ基本機能
# ---------------------------------------------------------------------------


def test_time_window():
    """TimeWindow 基本判定"""
    tw = TimeWindow("05:00", "07:00")
    # 窓内
    dt = datetime(2024, 1, 1, 6, 0)
    assert tw.contains(dt) is True
    # 窓外
    dt = datetime(2024, 1, 1, 8, 0)
    assert tw.contains(dt) is False
    # 日付跨ぎ
    tw2 = TimeWindow("23:00", "03:00")
    dt = datetime(2024, 1, 1, 23, 30)
    assert tw2.contains(dt) is True
    dt = datetime(2024, 1, 2, 1, 0)
    assert tw2.contains(dt) is True
    dt = datetime(2024, 1, 1, 12, 0)
    assert tw2.contains(dt) is False


def test_schedule_condition_time():
    """ScheduleCondition: 時間帯判定"""
    cond = ScheduleCondition(time_windows=[TimeWindow("05:00", "07:00")])
    ctx = ScheduleContext(current_time=datetime(2024, 1, 1, 6, 0))
    assert cond.evaluate(ctx) is True

    ctx = ScheduleContext(current_time=datetime(2024, 1, 1, 12, 0))
    assert cond.evaluate(ctx) is False


def test_schedule_condition_day_of_week():
    """曜日判定"""
    cond = ScheduleCondition(day_of_week=5)  # 土曜
    # 2024-01-06 は土曜日
    ctx = ScheduleContext(current_time=datetime(2024, 1, 6, 12, 0))
    assert cond.evaluate(ctx) is True

    # 日曜日
    ctx = ScheduleContext(current_time=datetime(2024, 1, 7, 12, 0))
    assert cond.evaluate(ctx) is False


def test_schedule_condition_moon_phase():
    """月齢判定"""
    cond = ScheduleCondition(moon_phase="full")
    ctx = ScheduleContext(moon_phase="full")
    assert cond.evaluate(ctx) is True

    ctx = ScheduleContext(moon_phase="new")
    assert cond.evaluate(ctx) is False


def test_schedule_condition_season():
    """季節判定"""
    cond = ScheduleCondition(season="spring")
    ctx = ScheduleContext(season="spring")
    assert cond.evaluate(ctx) is True

    ctx = ScheduleContext(season="winter")
    assert cond.evaluate(ctx) is False


def test_schedule_condition_weather():
    """天候判定"""
    cond = ScheduleCondition(weather="rain")
    ctx = ScheduleContext(weather="rain")
    assert cond.evaluate(ctx) is True

    ctx = ScheduleContext(weather="clear")
    assert cond.evaluate(ctx) is False


def test_schedule_condition_world_phase():
    """ワールドフェーズ判定"""
    cond = ScheduleCondition(world_phase="AWAKENING")
    ctx = ScheduleContext(world_phase="AWAKENING")
    assert cond.evaluate(ctx) is True

    ctx = ScheduleContext(world_phase="EXPLORATION")
    assert cond.evaluate(ctx) is False


def test_schedule_condition_logic_and():
    """AND 条件"""
    cond1 = ScheduleCondition(time_windows=[TimeWindow("05:00", "07:00")])
    cond2 = ScheduleCondition(day_of_week=5)
    schedule = QuestSchedule(
        quest_id="test",
        conditions=[cond1, cond2],
        logic=LogicOperator.AND,
    )

    # 両方満たす
    ctx = ScheduleContext(current_time=datetime(2024, 1, 6, 6, 0))  # 土曜 6:00
    assert schedule.is_available(ctx) is True

    # 片方のみ
    ctx = ScheduleContext(current_time=datetime(2024, 1, 7, 6, 0))  # 日曜 6:00
    assert schedule.is_available(ctx) is False

    ctx = ScheduleContext(current_time=datetime(2024, 1, 6, 12, 0))  # 土曜 12:00
    assert schedule.is_available(ctx) is False


def test_schedule_condition_logic_or():
    """OR 条件"""
    cond1 = ScheduleCondition(season="spring")
    cond2 = ScheduleCondition(season="autumn")
    schedule = QuestSchedule(
        quest_id="test",
        conditions=[cond1, cond2],
        logic=LogicOperator.OR,
    )

    ctx = ScheduleContext(season="spring")
    assert schedule.is_available(ctx) is True

    ctx = ScheduleContext(season="autumn")
    assert schedule.is_available(ctx) is True

    ctx = ScheduleContext(season="summer")
    assert schedule.is_available(ctx) is False


def test_quest_scheduler_load_yaml():
    """YAML 読み込み"""
    scheduler = QuestScheduler("data/quest_schedules.yaml")
    assert "dawn_prayer" in scheduler._schedules
    assert "market_delivery" in scheduler._schedules
    assert "full_moon_ritual" in scheduler._schedules
    assert len(scheduler._templates) > 0


def test_scheduler_get_available():
    """利用可能クエスト取得"""
    scheduler = QuestScheduler("data/quest_schedules.yaml")

    # 夜明け時間 + 適切な条件
    ctx = ScheduleContext(
        current_time=datetime(2024, 1, 1, 6, 0),  # 6:00
        day_of_week=0,
        moon_phase="new",
        season="spring",
        weather="clear",
        world_phase="BEGINNING",
    )

    # プレイヤーモック
    class Player:
        level = 10
        skills = {}

    player = Player()
    available = scheduler.get_available_quests(ctx, player)

    # dawn_prayer は time_window 05:00-07:00 に一致
    quest_ids = [q.quest_id for q in available]
    assert "dawn_prayer" in quest_ids


def test_scheduler_override():
    """スケジュール上書き (無効化)"""
    scheduler = QuestScheduler("data/quest_schedules.yaml")
    # dawn_prayer は特定日付で無効化されているが、テスト日付では有効
    ctx = ScheduleContext(current_time=datetime(2024, 1, 1, 6, 0))
    assert scheduler.is_quest_available("dawn_prayer", ctx) is True


def test_next_available_time():
    """次回利用可能時刻予測"""
    scheduler = QuestScheduler("data/quest_schedules.yaml")
    # 夜明けクエスト: 次の 05:00-07:00
    from_time = datetime(2024, 1, 1, 12, 0)  # 昼
    next_time = scheduler.get_next_available_time("dawn_prayer", from_time, max_days=2)
    assert next_time is not None
    # 翌日または当日の夜明け
    assert next_time.hour in [5, 6]


# ---------------------------------------------------------------------------
# Step 11: 待機/睡眠フック統合
# ---------------------------------------------------------------------------


def test_advance_world_scheduler_hook():
    """advance_world でスケジューラ再評価が走る"""
    from game import Engine

    engine = Engine()
    # スケジューラが初期化されているか
    assert hasattr(engine, "quest_scheduler")
    assert engine.quest_scheduler is not None


# ---------------------------------------------------------------------------
# Step 12: ワールドイベント連携
# ---------------------------------------------------------------------------


def test_world_event_schedule_injection():
    """ワールドイベント発生時のスケジュール注入"""
    from quest_scheduler import QuestScheduler
    from world_event_system import REGISTRY as WE_REG
    from world_event_system import WorldEventData, WorldEventManager

    # レジストリクリア
    WE_REG._events.clear()
    WE_REG._loaded = False

    # テスト用イベント登録
    event_data = WorldEventData(
        id="spring_festival",
        name="春祭り",
        description="春の訪れを祝う祭り",
        duration=2400,
        rewards={"gold": 500},
    )
    WE_REG._events["spring_festival"] = event_data

    mgr = WorldEventManager()
    scheduler = QuestScheduler()

    player = Mock()
    player.active_world_events = []

    engine = Mock()
    engine.quest_scheduler = scheduler
    engine.log = Mock()

    # イベント発火
    mgr.trigger_event(player, "spring_festival", engine)

    # スケジュールが注入されているか
    assert "event_spring_festival_festival" in scheduler._schedules
    injected = scheduler._schedules["event_spring_festival_festival"]
    assert injected.conditions[0].season == "spring"


def test_world_event_moon_eclipse():
    """月食イベントのスケジュール注入"""
    from quest_scheduler import QuestScheduler
    from world_event_system import REGISTRY as WE_REG
    from world_event_system import WorldEventData, WorldEventManager

    WE_REG._events.clear()
    WE_REG._loaded = False

    event_data = WorldEventData(
        id="lunar_eclipse",
        name="月食",
        description="月が欠ける神秘的な夜",
        duration=300,
        rewards={"artifact": "moon_shard"},
    )
    WE_REG._events["lunar_eclipse"] = event_data

    mgr = WorldEventManager()
    scheduler = QuestScheduler()

    player = Mock()
    player.active_world_events = []
    engine = Mock()
    engine.quest_scheduler = scheduler
    engine.log = Mock()

    mgr.trigger_event(player, "lunar_eclipse", engine)

    assert "event_lunar_eclipse_moon" in scheduler._schedules
    injected = scheduler._schedules["event_lunar_eclipse_moon"]
    assert injected.conditions[0].moon_phase == "full"


def test_world_event_meteor():
    """流星群イベントのスケジュール注入"""
    from quest_scheduler import QuestScheduler
    from world_event_system import REGISTRY as WE_REG
    from world_event_system import WorldEventData, WorldEventManager

    WE_REG._events.clear()
    WE_REG._loaded = False

    event_data = WorldEventData(
        id="meteor_shower",
        name="流星群",
        description="夜空を流れる無数の星",
        duration=100,
        rewards={"items": {"star_dust": 3}},
    )
    WE_REG._events["meteor_shower"] = event_data

    mgr = WorldEventManager()
    scheduler = QuestScheduler()

    player = Mock()
    player.active_world_events = []
    engine = Mock()
    engine.quest_scheduler = scheduler
    engine.log = Mock()

    mgr.trigger_event(player, "meteor_shower", engine)

    assert "event_meteor_shower_meteor" in scheduler._schedules
    injected = scheduler._schedules["event_meteor_shower_meteor"]
    assert len(injected.conditions[0].time_windows) == 1


def test_schedule_context_from_engine():
    """ScheduleContext.from_engine でエンジンからコンテキスト生成"""
    from game import Engine
    from quest_scheduler import ScheduleContext

    engine = Engine()
    ctx = ScheduleContext.from_engine(engine)
    # ワールドフェーズは取得できるはず
    assert ctx.world_phase is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
