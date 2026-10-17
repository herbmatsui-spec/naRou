"""クエスト報酬テーブル一元化のテスト (T35 R3案A)

data/main_quests.yaml の rewards: テーブルを唯一の報酬定義源とする一元化を検証する:
- 全クエストの報酬定義 (gold/exp/items/skill_points) がテーブルに存在すること
- 報酬値が正で、報酬アイテムが実在すること
- レベル帯に見合った報酬 (ゆるい単調増加カーブ) であること
- quest.QuestRewardResolver が解決・付与を単一入口で行い、
  FloatingText/ログ演出が一箇所からのみ発行されること (重複表示解消)
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from item_system import Inventory
from main_quest_system import MainQuestSystem, QuestStatus
from quest import QUEST_REWARD_KEYS, QuestRewardResolver

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAIN_QUESTS_PATH = PROJECT_ROOT / "data" / "main_quests.yaml"
ITEMS_PATH = PROJECT_ROOT / "data" / "items.yaml"

# クエスト鎖の想定レベル帯 (condition_dsl のゲート Lv5/Lv10/Lv15 と整合)
LEVEL_BANDS = {
    "prologue_01": 1,
    "awakening_01": 3,
    "exploration_01": 5,
    "confrontation_01": 10,
    "ascension_01": 15,
}

# exp_next = base * growth^(level-1) (Step 21: balance_standards.yaml の exp_curve)
EXP_CURVE_BASE = 120.0
EXP_CURVE_GROWTH = 1.35

# 統合テスト用の1クエスト報酬テーブル (world_phase はグローバル状態を汚すため含めない)
INTEGRATION_QUESTS_YAML = {
    "main_quests": [
        {
            "quest_id": "reward_test_q1",
            "title": "報酬試験",
            "description": "報酬付与の統合テスト。",
            "required_phase": "BEGINNING",
            "objectives": [
                {
                    "objective_id": "kill_dummy",
                    "description": "訓練用ターゲットを倒す",
                    "target_type": "kill",
                    "target_id": "dummy",
                    "required_count": 1,
                },
            ],
            "rewards": {
                "gold": 500,
                "exp": 300,
                "skill_points": 2,
                "items": {"potion_heal": 2},
            },
        },
    ]
}


# ============================================================================
# Helpers
# ============================================================================


@pytest.fixture
def reward_table() -> list[dict]:
    """data/main_quests.yaml を報酬テーブルとして読み込む"""
    with open(MAIN_QUESTS_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data.get("main_quests", [])


def _cumulative_exp_to_level(level: int) -> float:
    """レベル level 到達までに必要な累積経験値 (exp_next の積算)"""
    if level <= 1:
        return 0.0
    return EXP_CURVE_BASE * (EXP_CURVE_GROWTH ** (level - 1) - 1) / (EXP_CURVE_GROWTH - 1)


class FakeFxManager:
    """FloatingText の発行を記録するスタブ"""

    def __init__(self):
        self.floating_texts: list[dict] = []

    def add_floating_text(self, text: str, x: float, y: float, color: tuple) -> None:
        self.floating_texts.append({"text": text, "x": x, "y": y, "color": color})


class FakeEngine:
    """報酬付与と演出発行を観測できる最小エンジン"""

    def __init__(self):
        self.survival = SimpleNamespace(gold=0)
        self.inventory = FakeInventory()
        self.fx_manager = FakeFxManager()
        self.log_messages: list[str] = []

    def log(self, text: str, color: tuple = (230, 230, 230), level: str = "INFO") -> None:
        self.log_messages.append(text)


class FakePlayer:
    """報酬の受け手となる最小プレイヤー (gain_exp はレベルアップ処理の代理)"""

    def __init__(self):
        self.name = "reward_runner"
        self.x = 5.0
        self.y = 5.0
        self.exp = 0
        self.skill_points = 0
        self.total_skill_points_earned = 0

    def gain_exp(self, amount: int) -> list[str]:
        self.exp += amount
        return []


class FakeInventory:
    """アイテム追加を記録するスタブインベントリ"""

    def __init__(self):
        self.items: list = []

    def add_item(self, item) -> tuple[bool, str]:
        self.items.append(item)
        return True, "ok"


# ============================================================================
# 報酬テーブルの存在 (一元化)
# ============================================================================


class TestRewardTableIntegrity:
    def test_every_quest_defines_full_reward_table(self, reward_table):
        """全クエストの報酬定義がテーブルに存在する (gold/exp/items/skill_points)"""
        for quest in reward_table:
            rewards = quest.get("rewards")
            assert isinstance(rewards, dict), f"{quest['quest_id']}: rewards テーブルがない"
            for key in ("gold", "exp", "items", "skill_points"):
                assert key in rewards, f"{quest['quest_id']}: 報酬キー {key} がテーブルにない"

    def test_reward_keys_are_within_central_table(self, reward_table):
        """報酬キーは一元テーブル (QUEST_REWARD_KEYS) の範囲内のみ"""
        for quest in reward_table:
            extra = set(quest["rewards"]) - set(QUEST_REWARD_KEYS)
            assert not extra, f"{quest['quest_id']}: テーブル外キー {sorted(extra)}"

    def test_loaded_system_uses_yaml_table(self, reward_table):
        """MainQuestSystem にロードされた報酬が YAML テーブルと完全一致する"""
        system = MainQuestSystem(str(MAIN_QUESTS_PATH))
        for quest in reward_table:
            loaded = system.quests[quest["quest_id"]]
            assert loaded.rewards == quest["rewards"], quest["quest_id"]

    def test_system_grants_via_single_resolver(self):
        """報酬付与は QuestRewardResolver 一箇所のみを経由する"""
        system = MainQuestSystem(str(MAIN_QUESTS_PATH))
        assert isinstance(system.reward_resolver, QuestRewardResolver)

    def test_default_quest_matches_table_shape(self, tmp_path):
        """YAML 不在時のデフォルトクエストも一元テーブルと同じ報酬形状を持つ"""
        system = MainQuestSystem(str(tmp_path / "nowhere.yaml"))
        rewards = system.quests["prologue_01"].rewards
        assert rewards["gold"] == 100
        for key in ("gold", "exp", "items", "skill_points"):
            assert key in rewards


# ============================================================================
# 報酬値の妥当性
# ============================================================================


class TestRewardValues:
    def test_all_reward_values_positive(self, reward_table):
        """報酬値がすべて正である"""
        for quest in reward_table:
            rewards = quest["rewards"]
            assert rewards["gold"] > 0, quest["quest_id"]
            assert rewards["exp"] > 0, quest["quest_id"]
            assert rewards["skill_points"] > 0, quest["quest_id"]
            assert isinstance(rewards["items"], dict) and rewards["items"], quest["quest_id"]
            for item_id, count in rewards["items"].items():
                assert item_id, f"{quest['quest_id']}: アイテムIDが空"
                assert isinstance(count, int) and count > 0, (
                    f"{quest['quest_id']}: {item_id} の個数が正の整数でない"
                )

    def test_reward_items_exist_in_item_db(self, reward_table):
        """報酬アイテムが data/items.yaml に実在する"""
        with open(ITEMS_PATH, encoding="utf-8") as f:
            item_db = yaml.safe_load(f) or {}
        for quest in reward_table:
            for item_id in quest["rewards"]["items"]:
                assert item_id in item_db, (
                    f"{quest['quest_id']}: 報酬アイテム {item_id} が items.yaml に存在しない"
                )


# ============================================================================
# レベル帯に見合った報酬 (ゆるいカーブ)
# ============================================================================


class TestRewardCurve:
    def test_chain_order_matches_level_bands(self, reward_table):
        """クエスト鎖の並びがレベル帯の昇順と一致する"""
        assert {q["quest_id"] for q in reward_table} == set(LEVEL_BANDS)
        bands = [LEVEL_BANDS[q["quest_id"]] for q in reward_table]
        assert bands == sorted(bands)

    def test_gold_increases_gently(self, reward_table):
        """ゴールドは鎖に沿って単調増加し、隣接比が緩やか (最大10倍)"""
        golds = [q["rewards"]["gold"] for q in reward_table]
        for prev, cur in zip(golds, golds[1:]):
            assert cur > prev
            assert cur / prev <= 10.0, f"{prev} -> {cur}: カーブが急すぎる"

    def test_exp_increases_gently(self, reward_table):
        """EXP は鎖に沿って単調増加し、隣接比が緩やか (最大5.5倍)"""
        exps = [q["rewards"]["exp"] for q in reward_table]
        for prev, cur in zip(exps, exps[1:]):
            assert cur > prev
            assert cur / prev <= 5.5, f"{prev} -> {cur}: カーブが急すぎる"

    def test_exp_fits_level_band(self, reward_table):
        """EXP 報酬は想定レベル帯のおよそ +5 レベル分の累積経験値に収まる"""
        for quest in reward_table:
            band = LEVEL_BANDS[quest["quest_id"]]
            upper = _cumulative_exp_to_level(band + 5) - _cumulative_exp_to_level(band)
            exp_reward = quest["rewards"]["exp"]
            assert exp_reward <= upper, (
                f"{quest['quest_id']}: EXP {exp_reward} は Lv{band} 帯に対して過大 (上限 {upper:.0f})"
            )

    def test_skill_points_are_modest(self, reward_table):
        """スキルポイントは控えめ (1〜5) で鎖に沿って単調非減少"""
        skill_points = [q["rewards"]["skill_points"] for q in reward_table]
        assert all(1 <= sp <= 5 for sp in skill_points)
        assert skill_points == sorted(skill_points)


# ============================================================================
# QuestRewardResolver (解決・付与の単一入口)
# ============================================================================


class TestQuestRewardResolver:
    def test_resolve_full_table(self):
        resolver = QuestRewardResolver()
        resolved = resolver.resolve(
            {"gold": 500, "exp": 300, "skill_points": 2, "items": {"potion_heal": 2}}
        )
        assert [(r.kind, r.amount, r.item_name) for r in resolved] == [
            ("gold", 500, ""),
            ("exp", 300, ""),
            ("skill_points", 2, ""),
            ("item", 2, "potion_heal"),
        ]

    def test_reward_labels(self):
        """表示ラベル (+500 G / EXP+300 等) が FloatingText/ログ共通の形式"""
        resolver = QuestRewardResolver()
        labels = [
            r.label
            for r in resolver.resolve(
                {"gold": 500, "exp": 300, "skill_points": 2, "items": {"potion_heal": 2}}
            )
        ]
        assert labels == ["+500 G", "EXP+300", "SP+2", "potion_heal ×2"]

    def test_resolve_ignores_nonpositive_and_unknown(self):
        """非正値・非数・テーブル外キー (world_phase 等) は報酬として無視される"""
        resolver = QuestRewardResolver()
        resolved = resolver.resolve(
            {
                "gold": 0,
                "exp": -100,
                "skill_points": None,
                "items": {"potion_heal": 0, "potion_mana": -1},
                "world_phase": "EPILOGUE",
                "unknown_key": 5,
            }
        )
        assert resolved == []

    def test_resolve_accepts_empty_table(self):
        resolver = QuestRewardResolver()
        assert resolver.resolve(None) == []
        assert resolver.resolve({}) == []

    def test_grant_gold_prefers_engine_survival(self):
        resolver = QuestRewardResolver()
        engine = SimpleNamespace(survival=SimpleNamespace(gold=100))
        player = SimpleNamespace(gold=0)
        granted = resolver.grant(player, engine, {"gold": 500})
        assert engine.survival.gold == 600
        assert player.gold == 0
        assert [r.kind for r in granted] == ["gold"]

    def test_grant_gold_falls_back_to_player(self):
        resolver = QuestRewardResolver()
        player = SimpleNamespace(gold=10)
        engine = SimpleNamespace()  # survival を持たないエンジン
        granted = resolver.grant(player, engine, {"gold": 500})
        assert player.gold == 510
        assert len(granted) == 1

    def test_grant_exp_uses_gain_exp(self):
        resolver = QuestRewardResolver()
        player = FakePlayer()
        granted = resolver.grant(player, None, {"exp": 300})
        assert player.exp == 300
        assert [r.label for r in granted] == ["EXP+300"]

    def test_grant_exp_falls_back_to_exp_attr(self):
        resolver = QuestRewardResolver()
        player = SimpleNamespace(exp=0)
        resolver.grant(player, None, {"exp": 300})
        assert player.exp == 300

    def test_grant_skill_points_updates_both_counters(self):
        resolver = QuestRewardResolver()
        player = SimpleNamespace(skill_points=1, total_skill_points_earned=1)
        resolver.grant(player, None, {"skill_points": 2})
        assert player.skill_points == 3
        assert player.total_skill_points_earned == 3

    def test_grant_items_into_engine_inventory(self, monkeypatch):
        monkeypatch.setattr(
            "item_system.create_sample_item", lambda name, x=0, y=0: SimpleNamespace(name=name)
        )
        resolver = QuestRewardResolver()
        inventory = FakeInventory()
        engine = SimpleNamespace(inventory=inventory)
        player = SimpleNamespace(name="bare")  # components を持たないプレイヤー
        granted = resolver.grant(player, engine, {"items": {"potion_heal": 2}})
        assert len(inventory.items) == 2
        assert all(item.name == "potion_heal" for item in inventory.items)
        assert [r.label for r in granted] == ["potion_heal ×2"]

    def test_grant_items_into_player_components(self, monkeypatch):
        monkeypatch.setattr(
            "item_system.create_sample_item", lambda name, x=0, y=0: SimpleNamespace(name=name)
        )
        resolver = QuestRewardResolver()
        inventory = FakeInventory()
        player = SimpleNamespace(components={Inventory: inventory})
        granted = resolver.grant(player, None, {"items": {"potion_mana": 3}})
        assert len(inventory.items) == 3
        assert [r.label for r in granted] == ["potion_mana ×3"]

    def test_grant_skips_ungrantable_rewards(self):
        """付与先が一切ない場合は報酬をスキップし、戻り値に含めない"""
        resolver = QuestRewardResolver()
        player = SimpleNamespace(name="bare")
        granted = resolver.grant(player, None, {"gold": 500, "exp": 300, "skill_points": 1})
        assert granted == []


# ============================================================================
# クエスト完了フロー統合 (演出の一元発行)
# ============================================================================


class TestCompleteQuestRewardFlow:
    def _make_system(self, tmp_path) -> MainQuestSystem:
        path = tmp_path / "main_quests.yaml"
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(INTEGRATION_QUESTS_YAML, f, allow_unicode=True)
        return MainQuestSystem(str(path))

    def test_complete_quest_grants_each_reward_once(self, tmp_path, monkeypatch):
        """完了時に gold/exp/skill_points/items が各1回ずつ付与される"""
        monkeypatch.setattr(
            "item_system.create_sample_item", lambda name, x=0, y=0: SimpleNamespace(name=name)
        )
        system = self._make_system(tmp_path)
        engine = FakeEngine()
        player = FakePlayer()
        inventory = FakeInventory()
        player.components = {Inventory: inventory}

        system.update_progress(player, "kill", "dummy", 1, engine=engine)

        assert system.quests["reward_test_q1"].status is QuestStatus.COMPLETED
        assert engine.survival.gold == 500
        assert player.exp == 300
        assert player.skill_points == 2
        assert player.total_skill_points_earned == 2
        assert len(inventory.items) == 2

    def test_reward_feedback_emitted_from_single_place(self, tmp_path, monkeypatch):
        """FloatingText とログが報酬種別ぶん一度ずつ、一箇所からのみ発行される"""
        monkeypatch.setattr(
            "item_system.create_sample_item", lambda name, x=0, y=0: SimpleNamespace(name=name)
        )
        system = self._make_system(tmp_path)
        engine = FakeEngine()
        player = FakePlayer()

        logs = system.update_progress(player, "kill", "dummy", 1, engine=engine)

        floating_texts = engine.fx_manager.floating_texts
        labels = [ft["text"] for ft in floating_texts]
        assert labels == ["+500 G", "EXP+300", "SP+2", "potion_heal ×2"]
        assert len(set(labels)) == len(labels), "FloatingText が重複している"

        reward_logs = [m for m in engine.log_messages if m.startswith("報酬: ")]
        assert reward_logs == [f"報酬: {label}" for label in labels]
        assert len(set(reward_logs)) == len(reward_logs), "報酬ログが重複している"

        # 進行ログ側には報酬行を流さない (演出は engine.log の一箇所のみ)
        assert not any(line.startswith("報酬: ") for line in logs)

    def test_floating_text_follows_player_position(self, tmp_path, monkeypatch):
        """FloatingText はプレイヤー位置の頭上に出る"""
        monkeypatch.setattr(
            "item_system.create_sample_item", lambda name, x=0, y=0: SimpleNamespace(name=name)
        )
        system = self._make_system(tmp_path)
        engine = FakeEngine()
        player = FakePlayer()  # x=5.0, y=5.0

        system.update_progress(player, "kill", "dummy", 1, engine=engine)

        for ft in engine.fx_manager.floating_texts:
            assert ft["x"] == 5.0
            assert ft["y"] == 4.0  # y - 1.0

    def test_complete_quest_without_fx_support_does_not_crash(self, tmp_path):
        """演出手段を持たないエンジンでも報酬付与と完了処理が壊れない"""
        system = self._make_system(tmp_path)
        engine = SimpleNamespace(survival=SimpleNamespace(gold=0))
        player = SimpleNamespace(name="bare", x=0.0, y=0.0)

        logs = system.update_progress(player, "kill", "dummy", 1, engine=engine)

        assert engine.survival.gold == 500
        assert any("★メインクエスト【報酬試験】を完了した！" in line for line in logs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
