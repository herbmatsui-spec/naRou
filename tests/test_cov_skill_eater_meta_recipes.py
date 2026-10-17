"""Coverage tests for skill_eater_meta_recipes (MetaRecipeCraftingEngine)."""

from __future__ import annotations

import pytest

from skill_eater_meta_recipes import JunkItem, MetaRecipeCraftingEngine


@pytest.fixture
def engine() -> MetaRecipeCraftingEngine:
    return MetaRecipeCraftingEngine()


class TestJunkItem:
    def test_fields(self) -> None:
        junk = JunkItem(item_id="J1", name="粘液", category="CHEMICAL", description="ねばねば")
        assert junk.category == "CHEMICAL"
        assert junk.description == "ねばねば"


class TestDefaultRecipes:
    def test_c4_bomb_recipe_registered(self, engine: MetaRecipeCraftingEngine) -> None:
        key = frozenset(["SLIME_MUCUS", "FLINT_STONE", "SULFUR_POWDER"])
        assert key in engine.known_recipes
        recipe = engine.known_recipes[key]
        assert recipe["result_id"] == "ITEM_C4_MAGIC_BOMB"
        assert recipe["power"] == 350
        assert recipe["meta_bonus"] == 150

    def test_initial_meta_score_zero(self, engine: MetaRecipeCraftingEngine) -> None:
        assert engine.meta_score == 0

    def test_award_meta_points_accumulates(self, engine: MetaRecipeCraftingEngine) -> None:
        assert engine.award_meta_points(150) == 150
        assert engine.award_meta_points(50) == 200
        assert engine.meta_score == 200


class TestCrafting:
    def test_craft_c4_bomb(self, engine: MetaRecipeCraftingEngine) -> None:
        res = engine.craft_with_meta_knowledge(["SULFUR_POWDER", "SLIME_MUCUS", "FLINT_STONE"])
        assert res is not None
        assert res["success"] is True
        assert res["item_id"] == "ITEM_C4_MAGIC_BOMB"
        assert res["name"] == "即席C4魔力爆弾"
        assert res["effect"] == "AOE_EXPLOSION_DEFENSE_PIERCE"
        assert "メタ調合成功" in res["message"]

    def test_order_independent(self, engine: MetaRecipeCraftingEngine) -> None:
        res = engine.craft_with_meta_knowledge(["FLINT_STONE", "SULFUR_POWDER", "SLIME_MUCUS"])
        assert res is not None
        assert res["success"] is True

    def test_unknown_mix_returns_none(self, engine: MetaRecipeCraftingEngine) -> None:
        # NOTE: 本番コードは未登録レシピで None を返す (失敗辞書なし) — 記録済みの挙動
        res = engine.craft_with_meta_knowledge(["JUNK_A", "JUNK_B"])
        assert res is None


class TestNegotiation:
    def test_expose_exploitation_discount(self, engine: MetaRecipeCraftingEngine) -> None:
        res = engine.negotiate_with_meta_secrets("broker_01", "CHOICE_EXPOSE_SLUM_EXPLOITATION")
        assert res is not None
        assert res["success"] is True
        assert res["discount_percent"] == 40
        assert "裏帳簿" in res["reaction"]

    def test_unknown_choice_returns_none(self, engine: MetaRecipeCraftingEngine) -> None:
        # NOTE: 本番コードは未知の choice で None を返す — 記録済みの挙動
        assert engine.negotiate_with_meta_secrets("broker_01", "CHOICE_POLITE") is None


class TestItemFX:
    def test_c4_bomb_fx(self, engine: MetaRecipeCraftingEngine) -> None:
        fx = engine.get_meta_item_fx("ITEM_C4_MAGIC_BOMB")
        assert fx is not None
        assert fx["sound"] == "se_heavy_explosion_c4.ogg"
        assert fx["screen_shake"] == "SHAKE_EXTREME"
        assert fx["particles"] == "FIERY_DEBRIS_SMOKE"

    def test_unknown_item_fx_returns_none(self, engine: MetaRecipeCraftingEngine) -> None:
        assert engine.get_meta_item_fx("ITEM_UNKNOWN") is None


class TestForagingNodes:
    def test_three_nodes_with_expected_yields(self, engine: MetaRecipeCraftingEngine) -> None:
        nodes = engine.get_slum_foraging_nodes()
        assert len(nodes) == 3
        yields = {n["yield_item"] for n in nodes}
        assert yields == {"SLIME_MUCUS", "FLINT_STONE", "SULFUR_POWDER"}
        for node in nodes:
            assert len(node["pos"]) == 2
            assert node["node_id"].startswith("NODE_")
            assert node["label"]
