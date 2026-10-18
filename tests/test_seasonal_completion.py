"""季節システム完成度のテスト (T44 案B)

季節サイクル進行 (ターン/月ベース)・季節効果適用・季節転換イベント
(ログ+FloatingText+EventBus)・shop_system 統合 (季節割引の価格計算) を検証する。
"""

from __future__ import annotations

import pytest

from faction_war_system import REGISTRY as FACTION_REGISTRY
from faction_war_system import FactionWarData
from karma_system import DEFAULT_STAGES, KarmaData, KarmaManager
from season_system import (
    SEASON_COLOR,
    SEASON_EFFECTS,
    SEASON_SYSTEM,
    Season,
    SeasonEffects,
    SeasonSystem,
)
from shop_system import Shop, calculate_purchase_price

WINNER_FACTION = "season_test_winner"  # 戦争勝利派閥 (物価割引 -0.1)


# ---------------------------------------------------------------------------
# テスト用スタブ
# ---------------------------------------------------------------------------


class FakeFxManager:
    """FloatingText 発行を記録するスタブ"""

    def __init__(self) -> None:
        self.texts: list[tuple[str, float, float, tuple]] = []

    def add_floating_text(self, text: str, x: float, y: float, color: tuple) -> None:
        self.texts.append((text, x, y, color))


class FakeEngine:
    """log() と fx_manager を持つ最小エンジンスタブ"""

    def __init__(self) -> None:
        self.logs: list[tuple[str, tuple]] = []
        self.fx_manager = FakeFxManager()

    def log(self, text: str, color: tuple = (230, 230, 230), level: str = "INFO") -> None:
        self.logs.append((text, color))


class FakeEventBus:
    """publish() を記録する EventBus スタブ"""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    def publish(self, event_type: str, data: dict) -> None:
        self.published.append((event_type, data))


class StubPlayer:
    """FloatingText の表示座標参照用スタブ"""

    def __init__(self, x: int = 3, y: int = 5):
        self.x = x
        self.y = y


class ShopPlayer:
    """karma_good_evil と faction_reputation を持つ最小プレイヤースタブ"""

    def __init__(self, good_evil: int = 0, reputation: dict[str, int] | None = None):
        self.karma_good_evil = good_evil
        self.faction_reputation = reputation if reputation is not None else {}


class GoldHolder:
    """gold 属性を持つ所持金ホルダースタブ (survival 互換)"""

    def __init__(self, gold: int = 0):
        self.gold = gold


class StubItem:
    """商品テンプレートスタブ (Item 互換の最小フィールド)"""

    def __init__(self, name: str, base_value: int):
        self.name = name
        self.base_value = base_value


class StubKarmaRegistry:
    """DEFAULT_STAGES を返すカルマレジストリスタブ (data/karma.yaml 非依存)"""

    def get(self, karma_id: str = "default"):
        return KarmaData(
            id="default",
            name="テスト用カーマ",
            description="",
            alignment_ranges={},
            actions={},
            reincarnation_effects={},
            stages=list(DEFAULT_STAGES),
        )


@pytest.fixture
def karma_manager():
    return KarmaManager(StubKarmaRegistry())


@pytest.fixture
def faction_env():
    """テスト用派閥 (物価補正 -0.1) を登録し、終了後にレジストリを復元する"""
    saved_factions = dict(FACTION_REGISTRY._factions)
    FACTION_REGISTRY._factions[WINNER_FACTION] = FactionWarData(
        id=WINNER_FACTION,
        name="勝利派閥",
        price_modifier=-0.1,
    )
    yield FACTION_REGISTRY
    FACTION_REGISTRY._factions.clear()
    FACTION_REGISTRY._factions.update(saved_factions)


@pytest.fixture
def restore_global_season():
    """モジュールシングルトン SEASON_SYSTEM の季節状態を保存/復元する"""
    snapshot = SEASON_SYSTEM.to_dict()
    yield SEASON_SYSTEM
    SEASON_SYSTEM.from_dict(snapshot)


def _make_shop() -> Shop:
    shop = Shop("テスト商店")
    shop.stock_item(StubItem("回復薬", 100))
    return shop


# ---------------------------------------------------------------------------
# 季節サイクル進行
# ---------------------------------------------------------------------------


class TestSeasonCycle:
    def test_from_turn_boundaries(self):
        """90ターンごとに 春→夏→秋→冬→春 と循環する (event_scheduler と同一規則)"""
        assert Season.from_turn(0) is Season.SPRING
        assert Season.from_turn(89) is Season.SPRING
        assert Season.from_turn(90) is Season.SUMMER
        assert Season.from_turn(179) is Season.SUMMER
        assert Season.from_turn(180) is Season.AUTUMN
        assert Season.from_turn(269) is Season.AUTUMN
        assert Season.from_turn(270) is Season.WINTER
        assert Season.from_turn(359) is Season.WINTER
        assert Season.from_turn(360) is Season.SPRING
        assert Season.from_turn(450) is Season.SUMMER

    def test_quarter_matches_world_event_definition(self):
        """quarter 1-4 は WorldEventData.quarter の既存定義 (1:春,2:夏,3:秋,4:冬) と一致"""
        assert Season.SPRING.quarter == 1
        assert Season.SUMMER.quarter == 2
        assert Season.AUTUMN.quarter == 3
        assert Season.WINTER.quarter == 4

    def test_season_ids_match_quest_scheduler(self):
        """season_id は quest_scheduler.ScheduleCondition.season の想定値と一致"""
        assert {s.season_id for s in Season} == {"spring", "summer", "autumn", "winter"}

    def test_from_month(self):
        """月 (1-12) から季節を判定する (3-5:春, 6-8:夏, 9-11:秋, 12,1,2:冬)"""
        assert Season.from_month(3) is Season.SPRING
        assert Season.from_month(5) is Season.SPRING
        assert Season.from_month(6) is Season.SUMMER
        assert Season.from_month(8) is Season.SUMMER
        assert Season.from_month(9) is Season.AUTUMN
        assert Season.from_month(11) is Season.AUTUMN
        assert Season.from_month(12) is Season.WINTER
        assert Season.from_month(1) is Season.WINTER
        assert Season.from_month(2) is Season.WINTER

    def test_next_season_cycle(self):
        """翌季節は 春→夏→秋→冬→春 と循環する"""
        assert Season.SPRING.next() is Season.SUMMER
        assert Season.SUMMER.next() is Season.AUTUMN
        assert Season.AUTUMN.next() is Season.WINTER
        assert Season.WINTER.next() is Season.SPRING


class TestSeasonSystemProgression:
    def test_update_tracks_season_boundaries(self):
        """季節境界 (90/180/270/360ターン) でのみ季節が更新される"""
        ss = SeasonSystem()
        assert ss.current_season is Season.SPRING
        assert ss.update(89) is None
        assert ss.current_season is Season.SPRING
        transition = ss.update(90)
        assert transition is not None
        assert transition.new_season is Season.SUMMER
        assert ss.update(100) is None
        assert ss.update(180).new_season is Season.AUTUMN
        assert ss.update(270).new_season is Season.WINTER
        assert ss.update(360).new_season is Season.SPRING

    def test_get_season_explicit_turn(self):
        """get_season(turn) は追跡状態に依存せずターンから判定する"""
        ss = SeasonSystem(start_turn=270)
        assert ss.current_season is Season.WINTER
        assert ss.get_season() is Season.WINTER
        assert ss.get_season(0) is Season.SPRING
        assert ss.get_season(90) is Season.SUMMER

    def test_multi_season_jump_single_transition(self):
        """複数季節をまたぐ更新でも 1 回の転換として扱う"""
        ss = SeasonSystem()
        transition = ss.update(200)
        assert transition.old_season is Season.SPRING
        assert transition.new_season is Season.AUTUMN

    def test_save_load_roundtrip(self):
        """季節状態はセーブ/ロードで保持される"""
        ss = SeasonSystem()
        ss.update(180)
        data = ss.to_dict()
        restored = SeasonSystem()
        restored.from_dict(data)
        assert restored.current_season is Season.AUTUMN

    def test_global_singleton_defaults_to_spring(self):
        """モジュールシングルトンの初期季節は春 (ターン0)"""
        assert SEASON_SYSTEM.current_season is Season.SPRING


# ---------------------------------------------------------------------------
# 季節効果
# ---------------------------------------------------------------------------


class TestSeasonEffects:
    def test_spring_heal_boost(self):
        """春は回復量+10% (他は影響なし)"""
        effects = SEASON_EFFECTS[Season.SPRING]
        assert effects.heal_multiplier == pytest.approx(1.10)
        assert effects.enemy_attack_multiplier == 1.0
        assert effects.hunger_consumption_multiplier == 1.0
        assert effects.gold_drop_multiplier == 1.0
        assert effects.shop_price_multiplier == 1.0

    def test_summer_enemy_attack_boost(self):
        """夏は敵攻撃+10%"""
        effects = SEASON_EFFECTS[Season.SUMMER]
        assert effects.enemy_attack_multiplier == pytest.approx(1.10)
        assert effects.heal_multiplier == 1.0

    def test_autumn_harvest_bonus(self):
        """秋はドロップ金+20% と 店価格10%引"""
        effects = SEASON_EFFECTS[Season.AUTUMN]
        assert effects.gold_drop_multiplier == pytest.approx(1.20)
        assert effects.shop_price_multiplier == pytest.approx(0.90)
        assert effects.enemy_attack_multiplier == 1.0

    def test_winter_hunger_boost(self):
        """冬はハングリー消費+20%"""
        effects = SEASON_EFFECTS[Season.WINTER]
        assert effects.hunger_consumption_multiplier == pytest.approx(1.20)
        assert effects.heal_multiplier == 1.0

    def test_accessors_follow_tracked_season(self):
        """効果アクセサは追跡中の現在季節の倍率を返す"""
        ss = SeasonSystem(start_turn=90)  # 夏
        assert ss.get_enemy_attack_multiplier() == pytest.approx(1.10)
        assert ss.get_heal_multiplier() == 1.0
        ss = SeasonSystem(start_turn=180)  # 秋
        assert ss.get_gold_drop_multiplier() == pytest.approx(1.20)
        assert ss.get_shop_price_multiplier() == pytest.approx(0.90)
        ss = SeasonSystem(start_turn=270)  # 冬
        assert ss.get_hunger_consumption_multiplier() == pytest.approx(1.20)

    def test_accessors_with_explicit_season(self):
        """効果アクセサに明示季節を渡すとその季節の倍率を返す"""
        ss = SeasonSystem()  # 春
        assert ss.get_heal_multiplier(Season.SPRING) == pytest.approx(1.10)
        assert ss.get_shop_price_multiplier(Season.AUTUMN) == pytest.approx(0.90)

    def test_effects_are_frozen_dataclass(self):
        """SeasonEffects はイミュータブル (frozen dataclass)"""
        with pytest.raises(Exception):
            SEASON_EFFECTS[Season.SUMMER].enemy_attack_multiplier = 1.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 季節転換イベント
# ---------------------------------------------------------------------------


class TestSeasonChangeEvent:
    def test_transition_fires_log_and_floating_text(self):
        """季節転換時にログと FloatingText「季節は夏へ」が発火する"""
        engine = FakeEngine()
        player = StubPlayer(x=3, y=5)
        ss = SeasonSystem()
        transition = ss.update(90, engine=engine, player=player)
        assert transition is not None
        assert transition.message == "季節は夏へ"
        assert any("季節は夏へ" in text for text, _ in engine.logs)
        assert ("季節は夏へ", 3.0, 5.0, SEASON_COLOR) in engine.fx_manager.texts

    def test_same_season_no_event(self):
        """同一季節内の更新ではイベントが発火しない"""
        engine = FakeEngine()
        ss = SeasonSystem()
        assert ss.update(10, engine=engine, player=StubPlayer()) is None
        assert engine.logs == []
        assert engine.fx_manager.texts == []

    def test_event_bus_notified(self):
        """季節転換時に EventBus へ SEASON_CHANGED が通知される"""
        bus = FakeEventBus()
        ss = SeasonSystem(event_bus=bus)
        ss.update(90)
        assert len(bus.published) == 1
        event_type, data = bus.published[0]
        assert event_type == "SEASON_CHANGED"
        assert data["old"] is Season.SPRING
        assert data["new"] is Season.SUMMER
        assert data["turn"] == 90

    def test_no_event_bus_no_error(self):
        """EventBus 未設定でも転換イベントは成立する"""
        ss = SeasonSystem()
        transition = ss.update(90, engine=FakeEngine())
        assert transition is not None

    def test_yearly_transition_cycle(self):
        """1年 (360ターン) で転換イベントは 4 回 (夏/秋/冬/春) 発火する"""
        engine = FakeEngine()
        ss = SeasonSystem()
        transitions = []
        for turn in range(0, 361, 30):
            t = ss.update(turn, engine=engine)
            if t is not None:
                transitions.append(t.new_season)
        assert transitions == [Season.SUMMER, Season.AUTUMN, Season.WINTER, Season.SPRING]
        assert len(engine.fx_manager.texts) == 4


# ---------------------------------------------------------------------------
# shop_system 統合 (季節割引の価格計算)
# ---------------------------------------------------------------------------


class TestSeasonShopIntegration:
    def test_default_spring_no_price_change(self, karma_manager):
        """既定 (春) では店価格倍率 1.0 で価格は変動しない"""
        price = calculate_purchase_price(100, ShopPlayer(), karma_manager=karma_manager)
        assert price.final_price == 100
        assert price.season_price_modifier == 1.0
        assert "季節[" not in price.to_log_parts()

    def test_autumn_seasonal_discount(self, karma_manager):
        """秋 (収穫祭) は店価格 10% 引が後段乗算で適用される"""
        price = calculate_purchase_price(
            100, ShopPlayer(), karma_manager=karma_manager, season=Season.AUTUMN
        )
        assert price.season_id == "autumn"
        assert price.season_price_modifier == pytest.approx(0.90)
        assert price.final_price == 90
        assert "季節[autumn] ×0.90" in price.to_log_parts()

    def test_full_chain_multiplication_order(self, faction_env, karma_manager):
        """乗算順序は 基本 → 派閥 → カルマ → 季節 の既存順序を維持する"""
        player = ShopPlayer(good_evil=60, reputation={WINNER_FACTION: 10})
        price = calculate_purchase_price(
            100, player, faction_env, karma_manager, season=Season.AUTUMN
        )
        # 100 × 0.9 (派閥) × 0.8 (大善) × 0.9 (秋) = 64.8 → 65
        assert price.final_price == int(round(100 * 0.9 * 0.8 * 0.9))
        assert price.final_price == 65
        assert price.price_after_faction == pytest.approx(90.0)

    def test_shop_buy_applies_global_current_season(self, restore_global_season):
        """SEASON_SYSTEM の現在季節が Shop.buy に自動反映される"""
        SEASON_SYSTEM.update(180)  # グローバル季節を秋へ進める
        assert SEASON_SYSTEM.current_season is Season.AUTUMN
        shop = _make_shop()
        holder = GoldHolder(1000)
        result = shop.buy("回復薬", holder, ShopPlayer())
        assert result.ok
        assert result.total_gold == 90
        assert holder.gold == 910
        record = shop.purchase_log[0]
        assert record["season_id"] == "autumn"
        assert record["season_price_modifier"] == pytest.approx(0.90)

    def test_shop_buy_spring_keeps_base_price(self, restore_global_season):
        """春の購入は季節割引なし (既存の価格計算と同一)"""
        shop = _make_shop()
        holder = GoldHolder(1000)
        result = shop.buy("回復薬", holder, ShopPlayer())
        assert result.ok
        assert result.total_gold == 100
        assert holder.gold == 900
        record = shop.purchase_log[0]
        assert record["season_id"] == "spring"
        assert record["season_price_modifier"] == 1.0
