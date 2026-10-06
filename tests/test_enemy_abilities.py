"""
test_enemy_abilities.py
モンスター宣言固有能力の配線リグレッションテスト — enemy-abilities / S1.1〜S1.5

検証対象は production 経路である `skill_eater/ai/ai_system.py` の
`AdvancedAISystem.process_ai()` と `AbilityAction`。
宣言そのものは `DataManager.create_monster()` が `data/monsters.yaml` から
`mob.skills`（id 文字列のリスト）と `mob.ai_role` を実体へ流し込む経路である。

前提:
  - 乱数は `random.seed()` で固定し、当たり/空振りの両方を作動ごとに決定的につくる。
  - 期待値は本番の定数 (`ENERGY_THRESHOLD`) と本番データ
    (`DataManager().skills` の表示名) から導く。技名のハードコードはしない。
"""

from __future__ import annotations

import os
import random
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import yaml  # noqa: E402

from constants import AI_ROLE_FLANKER, AI_ROLE_KITER, ENERGY_THRESHOLD  # noqa: E402
from core_framework import Point  # noqa: E402
from data_manager import DataManager  # noqa: E402
from game import Engine  # noqa: E402
from renderer import NullRenderer  # noqa: E402
from skill_eater.ai.ai_system import (  # noqa: E402
    ABILITY_REGISTRY,
    AdvancedAISystem,
)
from systems import STATUS_BLEEDING, STATUS_PARALYSIS, STATUS_POISON  # noqa: E402

MONSTERS_YAML = os.path.join(_ROOT, "data", "monsters.yaml")

# 当たり/空振りを固定するシード。使用可能な能力が一つのときは
# 技の抽選が起きず、ヒット判定だけで結果が決まる。
SEED_HIT = 1
SEED_MISS = 2


@pytest.fixture(scope="module")
def dm() -> DataManager:
    """モジュール共有の DataManager（yaml 読み込みは重いため 1 度だけ）"""
    return DataManager()


@pytest.fixture(scope="module")
def monsters_yaml() -> dict:
    """`data/monsters.yaml` の生データ。宣言そのものを検証する时被参照する"""
    with open(MONSTERS_YAML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _skill_name(dm: DataManager, skill_id: str) -> str:
    """宣言スキルの本番表示名（ログの検証に使う）"""
    return dm.skills.get(skill_id).name


def _engine() -> Engine:
    return Engine(renderer=NullRenderer())


def _place(dm: DataManager, monster_id: str, dx: int, dy: int = 0) -> tuple[Engine, object]:
    """プレイヤーから相対位置 (dx, dy) に production 経路のモンスターを1体配置する"""
    engine = _engine()
    mob = dm.create_monster(monster_id, x=engine.player.x + dx, y=engine.player.y + dy)
    mob.energy = ENERGY_THRESHOLD * 3
    engine.entity_manager.add_entity(mob)
    assert engine.has_los(Point(mob.x, mob.y), Point(engine.player.x, engine.player.y)), (
        f"前提: {monster_id} からプレイヤーへの視線が通ること"
    )
    return engine, mob


def _block_summon(dm: DataManager, engine: Engine, mob) -> None:
    """召喚を封じるため、対象個人の左右に味方モンスターを2体立てる

    召喚は「屍体が居ないときだけ」しか唱えない。これがないと候補が2つになり、
    どちらが选中されるかが乱数依存になってしまう。
    （味方2体は挟撃判定で陣形を flanker に切り替えるが、そのツリーも能力判定が先頭なので影響しない）
    """
    for dx in (-1, 1):
        engine.entity_manager.add_entity(
            dm.create_monster("kobold", x=mob.x + dx, y=mob.y)
        )


def _logs(engine: Engine) -> list[str]:
    return [m.text for m in engine.msg_log.messages]


def _cheb(a, b) -> int:
    return max(abs(a.x - b.x), abs(a.y - b.y))


# ==================== S1.1 宣言された能力は必ず発動する ====================


def test_every_declared_ability_has_a_dispatcher(monsters_yaml: dict):
    """契約 S1.1: `data/monsters.yaml` が宣言する全 id に実行体が存在する

    実行体のない id は「宣言されているのに永久に起きない能力」になる。
    刃の無い宣言が表に残ったまま放置されるのを、データ側から押さえる。
    """
    declared = {
        str(getattr(s, "root", s))
        for entry in monsters_yaml.values()
        for s in (entry.get("skills") or [])
    }
    assert declared, "前提: monsters.yaml からスキル id を読み出せたこと"

    missing = sorted(declared - set(ABILITY_REGISTRY))
    assert not missing, f"実行体のない宣言能力がある: {missing}"


def test_goblin_fires_declared_throw_stone(dm: DataManager):
    """契約 S1.1: ゴブリン (skills: [throw_stone]) が投石を成立させる"""
    engine, mob = _place(dm, "goblin", 3)
    before = engine.player.hp

    random.seed(SEED_HIT)
    AdvancedAISystem().process_ai(mob, engine)

    assert engine.player.hp < before, "投石が命中してもダメージが入っていない"
    assert any(_skill_name(dm, "throw_stone") in t for t in _logs(engine)), (
        "技名がログに出ない = プレイヤーに挙動が見えない"
    )


def test_orc_fires_declared_power_bash(dm: DataManager):
    """契約 S1.1: オーク (skills: [power_bash]) が力強打を成立させる"""
    engine, mob = _place(dm, "orc", 1)
    before = engine.player.hp

    random.seed(SEED_HIT)
    AdvancedAISystem().process_ai(mob, engine)

    assert engine.player.hp < before
    assert any(_skill_name(dm, "power_bash") in t for t in _logs(engine))


def test_rogue_thief_backstabs_a_broke_player(dm: DataManager):
    """契約 S1.1: 金の無いプレイヤーを相手にバックスタブへ切り替わる"""
    engine, mob = _place(dm, "rogue_thief", 1)
    engine.player.gold = 0
    before = engine.player.hp

    random.seed(SEED_HIT)
    AdvancedAISystem().process_ai(mob, engine)

    assert engine.player.hp < before
    assert any(_skill_name(dm, "backstab") in t for t in _logs(engine))


# ==================== S1.2 空振りでもターンを消費し、プレイヤーに見える ====================


def test_missed_ability_still_costs_turn_and_is_legible(dm: DataManager):
    """契約 S1.2: 空振りしても無言では済まない

    旧実装の `CastSpellAction` は `random.randint(8,16)` を 40% で叩き、
    外すと `return False` で **ログもエネルギー消費も起きなかった**。
    ここでは「空振り → 1ターン消費 + 技名入りの失敗ログ」を要求する。
    """
    engine, mob = _place(dm, "goblin", 3)
    before_hp = engine.player.hp
    before_energy = mob.energy
    before_pos = (mob.x, mob.y)

    random.seed(SEED_MISS)
    AdvancedAISystem().process_ai(mob, engine)

    assert engine.player.hp == before_hp, "この seed は空振り前提（ダメージを受けてはいけない）"
    assert mob.energy == before_energy - ENERGY_THRESHOLD, "空振りしても行動は1ターン分消費される"
    assert (mob.x, mob.y) == before_pos, "空振りしたターンが移動に使われてはいない"
    logs = _logs(engine)
    assert any(_skill_name(dm, "throw_stone") in t for t in logs), (
        f"空振りログが無い = プレイヤーに見えない。{logs}"
    )


def test_ranged_ability_accuracy_depends_on_defender(dm: DataManager):
    """契約 S1.2: 命中率が防御側に依存する（防御ロール不在の回帰防止）

    同じ攻撃者を、防御の高低2種類の相手に向け、試行して命中数を比べる。
    防御を無視する実装なら両者は同じになる。
    """
    hits = {}
    for defender_dex, label in ((2, "防御が薄い"), (40, "防御が厚い")):
        total = 0
        for _ in range(60):
            engine, mob = _place(dm, "goblin", 3)
            engine.player.attributes.dexterity = defender_dex
            engine.player.hp = 99999
            engine.player.max_hp = 99999
            before = engine.player.hp
            random.seed(random.randrange(1 << 30))
            AdvancedAISystem().process_ai(mob, engine)
            total += engine.player.hp < before
        hits[label] = total

    assert hits["防御が厚い"] < hits["防御が薄い"], f"防御側有利で命中が減っていない: {hits}"


# ==================== S1.3 属性耐性が効く ====================


def test_fire_breath_damage_is_reduced_by_fire_resistance(dm: DataManager):
    """契約 S1.3: 炎の息吹はプレイヤーの炎耐性を軽減する"""
    totals = {}
    for resistance, label in ((0, "炎耐性なし"), (80, "炎耐性80")):
        dealt = 0
        for _ in range(40):
            engine, mob = _place(dm, "hound_fire", 3)
            engine.player.resistances.fire = resistance
            engine.player.hp = 99999
            engine.player.max_hp = 99999
            before = engine.player.hp
            random.seed(random.randrange(1 << 30))
            AdvancedAISystem().process_ai(mob, engine)
            dealt += before - engine.player.hp
        totals[label] = dealt

    assert totals["炎耐性80"] < totals["炎耐性なし"], (
        f"炎耐性が火炎攻撃を軽減していない: {totals}"
    )


# ==================== S1.4 非攻撃系能力も実体を動かす ====================


def test_steal_gold_moves_gold(dm: DataManager):
    """契約 S1.4: 金の窃盗は実際に金を動かす"""
    engine, mob = _place(dm, "rogue_thief", 5)
    engine.player.gold = 500
    before_player = engine.player.gold
    before_thief = mob.gold

    AdvancedAISystem().process_ai(mob, engine)

    assert engine.player.gold < before_player, "プレイヤーの金が減っていない"
    assert mob.gold > before_thief, "奪った金がモンスター側に無い"
    assert engine.player.gold + mob.gold == before_player + before_thief, "金が凭空で生滅している"
    assert any(_skill_name(dm, "steal_gold") in t for t in _logs(engine))


def test_heal_self_restores_hp(dm: DataManager):
    """契約 S1.4: 己の癒しは自分の HP を戻す"""
    engine, mob = _place(dm, "novice_wizard", 6)  # 呪毒弾の射程外 = 己の癒しだけ残る
    mob.hp = mob.max_hp - 5
    before = mob.hp

    AdvancedAISystem().process_ai(mob, engine)

    assert mob.hp > before, "HP が回復していない"
    assert mob.hp <= mob.max_hp
    assert any(_skill_name(dm, "heal_self") in t for t in _logs(engine))


def test_summon_undead_adds_an_entity(dm: DataManager):
    """契約 S1.4: 亡者の召喚はエンティティを増やす"""
    engine, mob = _place(dm, "lich", 8)  # 火球術は射程外、敵の魔力切れ = 召喚だけ残る
    engine.player.mp = 0
    before = len(engine.entity_manager.get_living_entities())

    AdvancedAISystem().process_ai(mob, engine)

    assert len(engine.entity_manager.get_living_entities()) > before, "召喚体が居ない"
    assert any(_skill_name(dm, "summon_undead") in t for t in _logs(engine))


def test_drain_mp_moves_mana(dm: DataManager):
    """契約 S1.4: 魔力吸引は魔力を相手から自身へ移す"""
    engine, mob = _place(dm, "lich", 8)  # 火球術は射程外
    _block_summon(dm, engine, mob)
    engine.player.mp = 40
    before_player_mp = engine.player.mp
    before_mob_mp = mob.mp

    AdvancedAISystem().process_ai(mob, engine)

    assert engine.player.mp < before_player_mp, "相手の魔力を持ち去っていない"
    assert mob.mp > before_mob_mp, "吸い上げた魔力が要塞に無い"
    assert any(_skill_name(dm, "drain_mp") in t for t in _logs(engine))


def test_cast_fireball_burns_at_range(dm: DataManager):
    """契約 S1.4: 火球術は射程内なら属性ダメージを通す"""
    engine, mob = _place(dm, "lich", 5)
    _block_summon(dm, engine, mob)
    engine.player.mp = 40
    before = engine.player.hp

    random.seed(SEED_HIT)
    AdvancedAISystem().process_ai(mob, engine)

    assert engine.player.hp < before
    assert any(_skill_name(dm, "cast_fireball") in t for t in _logs(engine))


def test_roar_is_player_facing_and_bolsters_self(dm: DataManager):
    """契約 S1.4: 戦吼はプレイヤーに見え、自分の防御を上げる"""
    engine, mob = _place(dm, "minotaur", 3)  # 豪快な大袈裟は射程1 = 戦吼だけ残る
    before_end = mob.endurance

    AdvancedAISystem().process_ai(mob, engine)

    assert mob.endurance > before_end, "自分の防御が上がっていない"
    assert any(_skill_name(dm, "roar") in t for t in _logs(engine))


def test_intimidate_staggers_the_player(dm: DataManager):
    """契約 S1.4: 威嚇はプレイヤーに状態異常を付ける"""
    engine, mob = _place(dm, "dragon_red", 8)  # 息吹は射程6 = 威嚇だけ残る

    AdvancedAISystem().process_ai(mob, engine)

    assert any(s.name == STATUS_PARALYSIS for s in engine.player.status_effects), (
        "威嚇してもプレイヤーに何も起こらない"
    )
    assert any(_skill_name(dm, "intimidate") in t for t in _logs(engine))


@pytest.mark.parametrize(
    ("monster_id", "skill_id", "status", "dx"),
    [
        ("novice_wizard", "cast_dart", STATUS_POISON, 4),
        ("minotaur", "heavy_cleave", STATUS_BLEEDING, 1),
    ],
)
def test_status_bearing_abilities_apply_their_declared_status(
    dm: DataManager, monster_id: str, skill_id: str, status: str, dx: int
):
    """契約 S1.4: 呪毒弾と豪快な大袈裟は宣言どおりの状態異常を付ける"""
    hits = 0
    for _ in range(40):
        engine, mob = _place(dm, monster_id, dx)
        engine.player.hp = 99999
        engine.player.max_hp = 99999
        random.seed(random.randrange(1 << 30))
        AdvancedAISystem().process_ai(mob, engine)
        hits += any(s.name == status for s in engine.player.status_effects)
    assert hits > 0, f"{monster_id} の {skill_id} が {status} を一度も付けない"


# ==================== S1.5 ai_role の宣言が実際に効く ====================


def test_declared_ai_role_reaches_the_entity(dm: DataManager, monsters_yaml: dict):
    """契約 S1.5: monsters.yaml の ai_role 宣言が実体へ流れる"""
    declared = {mid: entry["ai_role"] for mid, entry in monsters_yaml.items() if entry.get("ai_role")}
    assert declared, "前提: monsters.yaml に ai_role 宣言があること"

    for monster_id, role in declared.items():
        mob = dm.create_monster(monster_id)
        assert mob.ai_role == role, f"{monster_id} の ai_role が {role} になっていない"


def test_kiter_declaration_grants_a_preferred_range(dm: DataManager, monsters_yaml: dict):
    """契約 S1.5: kiter 宣言には間合いの希望値が伴う"""
    kiters = [mid for mid, e in monsters_yaml.items() if e.get("ai_role") == AI_ROLE_KITER]
    assert kiters, "前提: kiter を宣言したモンスターがいること"

    for monster_id in kiters:
        assert dm.create_monster(monster_id).preferred_range > 1, (
            f"{monster_id} は kiter なのに間合いの希望値がない"
        )


def test_name_substring_fallback_still_applies(dm: DataManager, monsters_yaml: dict):
    """契約 S1.5: 明示宣言のないモンスターは名前部分一致の既定が生きている"""
    assert "ai_role" not in monsters_yaml["novice_wizard"], (
        "前提: このモンスターは明示宣言していない（既定経路の検証用）"
    )
    assert dm.create_monster("novice_wizard").ai_role == AI_ROLE_KITER, (
        "名前部分一致の既定が失われた"
    )


def test_kiter_monster_keeps_its_distance(dm: DataManager):
    """契約 S1.5: kiter の行動ツリーが到達し、隣接されると離れる"""
    engine, mob = _place(dm, "goblin", 1)
    before_hp = engine.player.hp
    before_dist = _cheb(mob, engine.player)

    random.seed(SEED_MISS)
    AdvancedAISystem().process_ai(mob, engine)

    assert _cheb(mob, engine.player) > before_dist, (
        "kiter が隣接を許容した = kiter ツリーに到達していない"
    )
    assert engine.player.hp == before_hp


def test_flanker_monster_meleees_instead_of_kiting(dm: DataManager):
    """契約 S1.5: flanker の行動ツリーが到達し、隣接すれば殴る（間合いを取らない）"""
    engine, mob = _place(dm, "kobold", 1)
    assert mob.ai_role == AI_ROLE_FLANKER
    before_hp = engine.player.hp

    random.seed(SEED_HIT)
    AdvancedAISystem().process_ai(mob, engine)

    assert engine.player.hp < before_hp, (
        "kobold (flanker) が隣接しているのに攻撃しない = flanker ツリーに到達していない"
    )


def test_flanker_tree_is_registered():
    """契約 S1.5: flanker/kiter のツリーが登録されている"""
    trees = AdvancedAISystem().trees
    assert AI_ROLE_KITER in trees
    assert AI_ROLE_FLANKER in trees