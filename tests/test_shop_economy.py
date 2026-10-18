"""店舗経済システムのテスト (T40 案B)

購入価格 = 基本価格 × (1 + 派閥物価補正) × カルマ店価格倍率 の計算、
派閥補正 (R4-A) / カルマ割引 (R4-C) の反映、在庫・所持金不足のエラー処理、
購入ログ (価格内訳) を検証する。
"""

from __future__ import annotations

import pytest

from faction_war_system import REGISTRY as FACTION_REGISTRY
from faction_war_system import FactionWarData
from karma_system import DEFAULT_STAGES, KarmaData, KarmaManager
from shop_system import (
    ERROR_INSUFFICIENT_GOLD,
    ERROR_OUT_OF_STOCK,
    ERROR_UNKNOWN_ITEM,
    Shop,
    calculate_purchase_price,
    get_faction_price_modifier,
    resolve_player_faction,
)

WINNER_FACTION = "shop_test_winner"  # 戦争勝利派閥 (物価割引)
LOSER_FACTION = "shop_test_loser"  # 戦争敗北派閥 (物価高騰)


# ---------------------------------------------------------------------------
# テスト用スタブ
# ---------------------------------------------------------------------------


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


class StubEngine:
    """log() を持つ最小エンジンスタブ"""

    def __init__(self):
        self.logs: list[tuple[str, str]] = []

    def log(self, text: str, color=None, level: str = "INFO"):
        self.logs.append((text, level))


@pytest.fixture
def karma_manager():
    """DEFAULT_STAGES を使う KarmaManager (YAML 変動の影響を受けない)"""
    return KarmaManager(StubKarmaRegistry())


@pytest.fixture
def faction_env():
    """テスト用派閥を登録し、終了後にレジストリを復元する"""
    saved_factions = dict(FACTION_REGISTRY._factions)
    FACTION_REGISTRY._factions[WINNER_FACTION] = FactionWarData(
        id=WINNER_FACTION,
        name="勝利派閥",
        price_modifier=-0.1,
    )
    FACTION_REGISTRY._factions[LOSER_FACTION] = FactionWarData(
        id=LOSER_FACTION,
        name="敗北派閥",
        price_modifier=0.2,
    )
    yield FACTION_REGISTRY
    FACTION_REGISTRY._factions.clear()
    FACTION_REGISTRY._factions.update(saved_factions)


# ---------------------------------------------------------------------------
# 拠点派閥の解決
# ---------------------------------------------------------------------------


class TestResolvePlayerFaction:
    def test_no_reputation_returns_none(self):
        """評判未登録なら拠点派閥なし"""
        assert resolve_player_faction(ShopPlayer()) is None
        assert resolve_player_faction(None) is None

    def test_highest_reputation_is_home_faction(self):
        """最も評判の高い派閥が拠点派閥"""
        player = ShopPlayer(reputation={"a": 10, "b": 30, "c": -5})
        assert resolve_player_faction(player) == "b"

    def test_all_negative_reputation_returns_none(self):
        """全評判が負なら拠点派閥なし"""
        player = ShopPlayer(reputation={"a": -10, "b": -1})
        assert resolve_player_faction(player) is None


class TestFactionPriceModifier:
    def test_no_faction_returns_zero(self, faction_env):
        """派閥未所属なら補正 0.0"""
        assert get_faction_price_modifier(ShopPlayer()) == (None, 0.0)

    def test_winner_faction_discount(self, faction_env):
        """勝利派閥の拠点は物価割引 (負の補正)"""
        player = ShopPlayer(reputation={WINNER_FACTION: 10})
        assert get_faction_price_modifier(player, faction_env) == (WINNER_FACTION, -0.1)

    def test_loser_faction_surcharge(self, faction_env):
        """敗北派閥の拠点は物価高騰 (正の補正)"""
        player = ShopPlayer(reputation={LOSER_FACTION: 10})
        assert get_faction_price_modifier(player, faction_env) == (LOSER_FACTION, 0.2)

    def test_unknown_faction_returns_zero(self, faction_env):
        """レジストリに存在しない派閥は補正 0.0"""
        player = ShopPlayer(reputation={"unknown_faction": 50})
        assert get_faction_price_modifier(player, faction_env) == ("unknown_faction", 0.0)


# ---------------------------------------------------------------------------
# 購入価格計算 (基本価格 × (1 + 派閥補正) × カルマ倍率)
# ---------------------------------------------------------------------------


class TestCalculatePurchasePrice:
    def test_base_price_without_modifiers(self, karma_manager):
        """補正なし (無所属・中立カルマ) なら基本価格のまま"""
        price = calculate_purchase_price(100, ShopPlayer(), karma_manager=karma_manager)
        assert price.base_price == 100
        assert price.faction_price_modifier == 0.0
        assert price.price_after_faction == pytest.approx(100.0)
        assert price.karma_stage_id == "neutral"
        assert price.karma_price_modifier == pytest.approx(1.0)
        assert price.final_price == 100

    def test_multiplication_order_faction_then_karma(self, faction_env, karma_manager):
        """乗算順序は 基本価格 → 派閥補正 → カルマ倍率 (中間値 price_after_faction で固定)"""
        player = ShopPlayer(good_evil=60, reputation={WINNER_FACTION: 10})
        price = calculate_purchase_price(100, player, faction_env, karma_manager)
        # 基本価格 × (1 + 派閥補正) が先に評価される
        assert price.price_after_faction == pytest.approx(100 * (1 + -0.1))
        # その後にカルマ倍率 (大善 0.8) が乗算される
        assert price.final_price == int(round(100 * 0.9 * 0.8))
        assert price.final_price == 72

    def test_faction_winner_discount_applied(self, faction_env, karma_manager):
        """勝利派閥の割引が購入価格へ反映される"""
        player = ShopPlayer(reputation={WINNER_FACTION: 10})
        price = calculate_purchase_price(100, player, faction_env, karma_manager)
        assert price.final_price == 90

    def test_faction_loser_surcharge_applied(self, faction_env, karma_manager):
        """敗北派閥の高騰が購入価格へ反映される"""
        player = ShopPlayer(reputation={LOSER_FACTION: 10})
        price = calculate_purchase_price(100, player, faction_env, karma_manager)
        assert price.final_price == 120

    def test_rounding_is_half_up_to_nearest_int(self, faction_env, karma_manager):
        """端数は四捨五入で整数化される (100 × 1.2 → 121.2 はカルマ 1.0 で 121)"""
        player = ShopPlayer(reputation={LOSER_FACTION: 10})
        price = calculate_purchase_price(101, player, faction_env, karma_manager)
        assert price.price_after_faction == pytest.approx(101 * 1.2)
        assert price.final_price == 121

    def test_karma_saint_discount(self, karma_manager):
        """大善 (good_evil >= 50) は割引倍率 0.8"""
        price = calculate_purchase_price(
            100, ShopPlayer(good_evil=60), karma_manager=karma_manager
        )
        assert price.karma_stage_id == "saint"
        assert price.karma_price_modifier == pytest.approx(0.8)
        assert price.final_price == 80

    def test_karma_demon_surcharge(self, karma_manager):
        """大悪 (good_evil <= -50) は割増倍率 1.3"""
        price = calculate_purchase_price(
            100, ShopPlayer(good_evil=-60), karma_manager=karma_manager
        )
        assert price.karma_stage_id == "demon"
        assert price.karma_price_modifier == pytest.approx(1.3)
        assert price.final_price == 130

    def test_default_karma_manager_is_used(self, faction_env):
        """karma_manager 未指定時は karma_system.KarmaManager が使われる (R4-C 接続)"""
        saint = calculate_purchase_price(100, ShopPlayer(good_evil=60), faction_env)
        neutral = calculate_purchase_price(100, ShopPlayer(good_evil=0), faction_env)
        demon = calculate_purchase_price(100, ShopPlayer(good_evil=-60), faction_env)
        # 善行段階ほど安く、悪行段階ほど高い (カルマ割引の方向性)
        assert saint.final_price < neutral.final_price
        assert neutral.final_price < demon.final_price

    def test_combined_faction_and_karma_breakdown_fields(self, faction_env, karma_manager):
        """内訳フィールド (派閥 ID / 補正値 / カルマ段階) が埋まる"""
        player = ShopPlayer(good_evil=60, reputation={WINNER_FACTION: 10})
        price = calculate_purchase_price(100, player, faction_env, karma_manager)
        assert price.faction_id == WINNER_FACTION
        assert price.faction_price_modifier == pytest.approx(-0.1)
        assert price.karma_stage_name == "大善"
        assert price.to_log_parts() == "基本100G → 派閥[shop_test_winner] -10.0% → 90G → カルマ[大善] ×0.80 → 72G"


# ---------------------------------------------------------------------------
# 店舗購入フロー (在庫 / 所持金 / 購入ログ)
# ---------------------------------------------------------------------------


def make_shop() -> Shop:
    """長剣 (基本価格 100) を 2 個仕入れた店舗"""
    shop = Shop("テスト商店")
    shop.stock_item(StubItem("長剣", 100), count=2, item_id="longsword")
    return shop


class TestShopBuy:
    def test_buy_success_deducts_gold_and_stock(self, faction_env, karma_manager):
        """購入成功: 所持金減少と在庫減算が行われる"""
        shop = make_shop()
        holder = GoldHolder(500)
        player = ShopPlayer(reputation={WINNER_FACTION: 10})  # 100 → 90G

        result = shop.buy("longsword", holder, player)

        assert result.ok is True
        assert result.error is None
        assert result.total_gold == 90
        assert holder.gold == 500 - 90
        assert result.remaining_stock == 1
        assert shop.get_stock_count("longsword") == 1

    def test_buy_unknown_item_fails_without_changes(self):
        """未登録商品は unknown_item エラーで所持金/在庫とも変化しない"""
        shop = make_shop()
        holder = GoldHolder(500)

        result = shop.buy("nonexistent", holder, ShopPlayer())

        assert result.ok is False
        assert result.error == ERROR_UNKNOWN_ITEM
        assert holder.gold == 500
        assert shop.get_stock_count("longsword") == 2

    def test_buy_out_of_stock_fails_without_changes(self):
        """在庫不足は out_of_stock エラーで所持金/在庫とも変化しない"""
        shop = make_shop()
        holder = GoldHolder(10000)

        result = shop.buy("longsword", holder, ShopPlayer(), count=3)

        assert result.ok is False
        assert result.error == ERROR_OUT_OF_STOCK
        assert holder.gold == 10000
        assert shop.get_stock_count("longsword") == 2

    def test_buy_insufficient_gold_fails_without_changes(self, faction_env, karma_manager):
        """所持金不足は insufficient_gold エラーで所持金/在庫とも変化しない"""
        shop = make_shop()
        holder = GoldHolder(89)  # 90G に 1G 足りない
        player = ShopPlayer(reputation={WINNER_FACTION: 10})

        result = shop.buy("longsword", holder, player)

        assert result.ok is False
        assert result.error == ERROR_INSUFFICIENT_GOLD
        assert result.total_gold == 90
        assert holder.gold == 89
        assert shop.get_stock_count("longsword") == 2
        assert shop.purchase_log == []

    def test_buy_without_gold_holder_raises(self):
        """gold 属性を持たない所持金ホルダーは ValueError (item_system と同一契約)"""
        shop = make_shop()
        with pytest.raises(ValueError):
            shop.buy("longsword", object(), ShopPlayer())

    def test_buy_multiple_counts(self):
        """複数個購入は単価 × 個数で所持金から引かれる"""
        shop = make_shop()
        holder = GoldHolder(500)

        result = shop.buy("longsword", holder, ShopPlayer(), count=2)

        assert result.ok is True
        assert result.total_gold == 200  # 100G × 2 (補正なし)
        assert holder.gold == 300
        assert result.remaining_stock == 0

    def test_buy_price_calculation_matches_quote(self, faction_env, karma_manager):
        """buy の適用価格は quote (見積もり) と一致する"""
        shop = make_shop()
        player = ShopPlayer(good_evil=60, reputation={WINNER_FACTION: 10})

        quote = shop.quote("longsword", player)
        assert quote.ok is True
        holder = GoldHolder(1000)
        result = shop.buy("longsword", holder, player)

        assert quote.price == result.price
        assert quote.total_gold == result.total_gold == 72
        assert holder.gold == 1000 - 72


class TestPurchaseLog:
    def test_purchase_log_records_price_breakdown(self, faction_env, karma_manager):
        """購入ログに基本価格と補正後価格の内訳が記録される"""
        shop = make_shop()
        holder = GoldHolder(500)
        player = ShopPlayer(good_evil=60, reputation={WINNER_FACTION: 10})

        result = shop.buy("longsword", holder, player)

        assert len(shop.purchase_log) == 1
        record = shop.purchase_log[0]
        assert record["shop"] == "テスト商店"
        assert record["item_id"] == "longsword"
        assert record["item_name"] == "長剣"
        assert record["count"] == 1
        assert record["base_price"] == 100
        assert record["faction_id"] == WINNER_FACTION
        assert record["faction_price_modifier"] == pytest.approx(-0.1)
        assert record["price_after_faction"] == pytest.approx(90.0)
        assert record["karma_stage_id"] == "saint"
        assert record["karma_price_modifier"] == pytest.approx(0.8)
        assert record["final_price"] == 72
        assert record["total_gold"] == 72
        assert result.message == (
            "【購入】長剣 ×1 = 72G "
            "(基本100G → 派閥[shop_test_winner] -10.0% → 90G → カルマ[大善] ×0.80 → 72G)"
        )

    def test_purchase_log_sent_to_engine(self):
        """engine.log へ購入メッセージ (内訳付き) が流れる"""
        shop = make_shop()
        holder = GoldHolder(500)
        engine = StubEngine()

        shop.buy("longsword", holder, ShopPlayer(), engine=engine)

        assert len(engine.logs) == 1
        text, level = engine.logs[0]
        assert "【購入】長剣 ×1 = 100G" in text
        assert "基本100G" in text
        assert level == "SUCCESS"
