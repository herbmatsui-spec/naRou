"""ギルド昇格フローのテスト (T41 案C)

昇格条件判定・段階順序・特典反映 (報酬倍率/専用クエスト解放)・条件未達の
不昇格・昇格イベント (ログ+FloatingText+SE) を実データ (data/*.yaml) で検証する。
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml

from guild_quest_system import GuildQuestManager, GuildQuestRegistry
from guild_system import (
    DEFAULT_RANK_ORDER,
    GuildManager,
    GuildRankRegistry,
    GuildRegistry,
)
from sound_manager import SoundManager

if TYPE_CHECKING:
    from ecs.entity import Entity

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GUILDS_YAML = PROJECT_ROOT / "data" / "guilds.yaml"
GUILD_REWARDS_YAML = PROJECT_ROOT / "data" / "guild_rewards.yaml"
GUILD_RANKS_YAML = PROJECT_ROOT / "data" / "guild_ranks.yaml"
GUILD_QUESTS_YAML = PROJECT_ROOT / "data" / "guild_quests.yaml"

# data/guild_ranks.yaml の昇格条件 (adventurers_guild)
QUESTS_NEEDED = {"member": 3, "veteran": 10, "officer": 25, "leader": 50}
CONTRIBUTION_NEEDED = {"member": 100, "veteran": 500, "officer": 2000, "leader": 5000}


def _make_player() -> Entity:
    from ecs.entity import Entity

    return Entity(0, 0, "@", name="tester")


@pytest.fixture
def guild_env() -> tuple[GuildManager, Entity]:
    """実データをロードした GuildManager と冒険者ギルド加入済みプレイヤー"""
    guild_reg = GuildRegistry()
    guild_reg.load(str(GUILDS_YAML), str(GUILD_REWARDS_YAML))
    rank_reg = GuildRankRegistry()
    rank_reg.load(str(GUILD_RANKS_YAML))
    manager = GuildManager(guild_reg, rank_reg)
    player = _make_player()
    assert manager.join_guild(player, "adventurers_guild")
    assert player.guild_rank == "novice"
    return manager, player


def _load_quest_manager(guild_manager: Any) -> GuildQuestManager:
    quest_reg = GuildQuestRegistry()
    quest_reg.load(str(GUILD_QUESTS_YAML))
    return GuildQuestManager(quest_reg, guild_manager=guild_manager)


class _FakeFxManager:
    def __init__(self) -> None:
        self.texts: list[tuple[str, float, float, tuple]] = []

    def add_floating_text(self, text: str, x: float, y: float, color: tuple) -> None:
        self.texts.append((text, x, y, color))


class _FakeEngine:
    def __init__(self) -> None:
        self.logs: list[tuple[str, tuple]] = []
        self.fx_manager = _FakeFxManager()

    def log(self, text: str, color: tuple = (230, 230, 230), level: str = "INFO") -> None:
        self.logs.append((text, color))


def test_guild_ranks_yaml_defines_five_stages() -> None:
    """guild_ranks.yaml がREADMEどおりの5段階を定義し、guilds.yaml の貢献度要件と一致する"""
    with open(GUILD_RANKS_YAML, encoding="utf-8") as f:
        ranks_data = yaml.safe_load(f)
    with open(GUILDS_YAML, encoding="utf-8") as f:
        guilds_data = yaml.safe_load(f)

    ranks = ranks_data["guild_ranks"]["adventurers_guild"]["ranks"]
    assert list(ranks.keys()) == DEFAULT_RANK_ORDER
    requirements = guilds_data["guilds"]["adventurers_guild"]["rank_requirements"]
    for rank_name, req in requirements.items():
        assert ranks[rank_name]["contribution"] == req


def test_promotion_requires_contribution_and_quests(
    guild_env: tuple[GuildManager, Entity],
) -> None:
    """昇格には貢献度とギルドクエスト達成数の両方が必要"""
    manager, player = guild_env
    # 貢献度のみでは member (必要: 貢献度100+クエスト3回) に昇格できない
    player.guild_contribution = 100
    assert manager.meets_promotion_requirements(player, "member") is False
    assert manager.get_promotable_rank(player) is None

    # クエスト達成数を満たせば昇格可能になる
    player.guild_completed_quests = 3
    assert manager.meets_promotion_requirements(player, "member") is True
    assert manager.get_promotable_rank(player) == "member"


def test_promotion_follows_stage_order(guild_env: tuple[GuildManager, Entity]) -> None:
    """段階の飛び越しはできず、novice→member→veteran→officer→leader の順に昇格する"""
    manager, player = guild_env
    # 貢献度が leader 分あっても達成クエスト0では昇格不可
    player.guild_contribution = 5000
    player.guild_completed_quests = 0
    assert manager.get_promotable_rank(player) is None
    assert manager.process_promotion(player) is None

    # 各段階の条件を満たしながら1段階ずつ昇格する
    for expected_rank in DEFAULT_RANK_ORDER[1:]:
        player.guild_contribution = CONTRIBUTION_NEEDED[expected_rank]
        player.guild_completed_quests = QUESTS_NEEDED[expected_rank]
        # 貢献度は以降の段階も満たすが、次の1段階のみが昇格対象
        assert manager.get_promotable_rank(player) == expected_rank
        assert manager.process_promotion(player) == expected_rank
        assert player.guild_rank == expected_rank

    # leader は最上位段階なのでそれ以上昇格しない
    assert manager.get_next_rank(player) is None
    assert manager.process_promotion(player) is None


def test_no_promotion_when_conditions_unmet(
    guild_env: tuple[GuildManager, Entity],
) -> None:
    """条件未達の場合は昇格せず、ランク・称号ともに変化しない"""
    manager, player = guild_env

    # 貢献度不足 (クエスト達成数は充足)
    player.guild_contribution = 50
    player.guild_completed_quests = QUESTS_NEEDED["member"]
    before_titles = list(player.titles)
    assert manager.process_promotion(player) is None
    assert player.guild_rank == "novice"
    assert player.titles == before_titles

    # クエスト達成数不足 (貢献度は充足)
    player.guild_contribution = CONTRIBUTION_NEEDED["member"]
    player.guild_completed_quests = QUESTS_NEEDED["member"] - 1
    assert manager.process_promotion(player) is None
    assert player.guild_rank == "novice"
    assert player.titles == before_titles


def test_promotion_benefits_applied(guild_env: tuple[GuildManager, Entity]) -> None:
    """昇格時に称号・報酬倍率・専用クエスト解放・ステータスボーナスが反映される"""
    manager, player = guild_env
    assert manager.get_reward_multiplier(player) == pytest.approx(1.0)
    assert manager.get_unlocked_quest_ids(player) == []

    # novice → member: 称号+報酬倍率1.05+専用クエスト解放
    player.guild_contribution = CONTRIBUTION_NEEDED["member"]
    player.guild_completed_quests = QUESTS_NEEDED["member"]
    assert manager.process_promotion(player) == "member"
    assert "guild_member" in player.titles
    assert manager.get_reward_multiplier(player) == pytest.approx(1.05)
    assert manager.get_unlocked_quest_ids(player) == ["member_beast_cull"]

    # member → veteran: stat_bonus (筋力+2) と追加解放が累積反映される
    strength_before = player.attributes.strength
    player.guild_contribution = CONTRIBUTION_NEEDED["veteran"]
    player.guild_completed_quests = QUESTS_NEEDED["veteran"]
    assert manager.process_promotion(player) == "veteran"
    assert "guild_veteran" in player.titles
    assert player.attributes.strength >= strength_before + 2
    assert manager.get_reward_multiplier(player) == pytest.approx(1.10)
    unlocked = manager.get_unlocked_quest_ids(player)
    assert "member_beast_cull" in unlocked
    assert "veteran_ancient_dragon" in unlocked


def test_quest_completion_applies_multiplier_and_counts(
    guild_env: tuple[GuildManager, Entity],
) -> None:
    """ギルドクエスト達成で達成数が加算され、ランク特典の報酬倍率が報酬に掛かる"""
    manager, player = guild_env
    quest_manager = _load_quest_manager(manager)

    quest_manager.update_quest_progress(player, "slay_goblins", 100)
    ok, msg, _ = quest_manager.complete_quest(player, "slay_goblins")
    assert ok
    assert player.guild_completed_quests == 1
    # novice の倍率は 1.0 なので報酬はそのまま
    assert player.guild_contribution == 50
    assert player.gold == 100

    # member に昇格すると倍率 1.05 が貢献度・金貨の両方に適用される
    player.guild_contribution = CONTRIBUTION_NEEDED["member"]
    player.guild_completed_quests = QUESTS_NEEDED["member"]
    assert manager.process_promotion(player) == "member"

    quest_manager.update_quest_progress(player, "slay_goblins", 100)
    ok, msg, _ = quest_manager.complete_quest(player, "slay_goblins")
    assert ok
    assert player.guild_contribution == CONTRIBUTION_NEEDED["member"] + int(
        round(50 * 1.05)
    )
    assert player.gold == 100 + int(round(100 * 1.05))
    assert "報酬×1.05" in msg


def test_dedicated_quests_unlock_by_rank(guild_env: tuple[GuildManager, Entity]) -> None:
    """min_rank つき専用クエストは昇格ランクでのみ受領可能になる"""
    manager, player = guild_env
    quest_manager = _load_quest_manager(manager)

    # novice では専用クエストは非解放 (通常クエストは常に解放)
    assert quest_manager.get_available_quests(player, "special") == []
    daily_ids = [q.id for q in quest_manager.get_available_quests(player, "daily")]
    assert "slay_goblins" in daily_ids

    # member への昇格で member 向け専用クエストのみ解放
    player.guild_contribution = CONTRIBUTION_NEEDED["member"]
    player.guild_completed_quests = QUESTS_NEEDED["member"]
    assert manager.process_promotion(player) == "member"
    special_ids = [q.id for q in quest_manager.get_available_quests(player, "special")]
    assert special_ids == ["member_beast_cull"]

    # guild_manager 未注入では専用クエストは常に非解放 (安全側)
    plain_quest_manager = _load_quest_manager(None)
    assert plain_quest_manager.get_available_quests(player, "special") == []


def test_promotion_event_feedback(
    guild_env: tuple[GuildManager, Entity], monkeypatch: pytest.MonkeyPatch
) -> None:
    """昇格時にログ+FloatingText+SE (level_up) が発行される"""
    manager, player = guild_env
    _load_quest_manager(manager)  # 専用クエスト名解決用にロードだけ実施
    engine = _FakeEngine()
    se_calls: list[str] = []
    monkeypatch.setattr(SoundManager, "play_se", lambda se_type: se_calls.append(se_type))

    player.guild_contribution = CONTRIBUTION_NEEDED["member"]
    player.guild_completed_quests = QUESTS_NEEDED["member"]
    assert manager.process_promotion(player, engine) == "member"

    # ログ: 昇格・段階名・報酬倍率・専用クエスト解放が 1 行で通知される
    assert len(engine.logs) == 1
    text, color = engine.logs[0]
    assert "昇格" in text
    assert "正会員" in text
    assert "報酬倍率×1.05" in text
    assert "【専用】魔獣の大規模駆除" in text
    assert color == (255, 215, 0)

    # FloatingText: プレイヤー頭上に昇格表示
    assert len(engine.fx_manager.texts) == 1
    assert "昇格" in engine.fx_manager.texts[0][0]

    # SE: level_up が再生される
    assert se_calls == ["level_up"]

    # engine なし (テスト等) では演出を省略して昇格のみ行う
    player.guild_contribution = CONTRIBUTION_NEEDED["veteran"]
    player.guild_completed_quests = QUESTS_NEEDED["veteran"]
    assert manager.process_promotion(player, None) == "veteran"
    assert len(engine.logs) == 1
    assert len(engine.fx_manager.texts) == 1
    assert se_calls == ["level_up"]
