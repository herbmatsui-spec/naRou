"""engine.systems.pet_system モジュールのテスト (PetSystemHandler).

PetSystemHandler はペット進化・融合・演奏・祈り・祭壇・願いの杖を担当する。
Engine スタブは SimpleNamespace で構築し、MagicMock の予測不能な動作を避ける。
random や WishParser は patch でモック化する。
"""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from engine.systems.pet_system import PetSystemHandler
from constants import COLOR_GOLD_YELLOW, ENERGY_THRESHOLD
from run_summary import CAUSE_SELF

# pet_system 内部でローカル import する外部モジュールをスタブ化
sys.modules["ui_fx_systems"] = MagicMock()
_fx_stub = sys.modules["ui_fx_systems"]


# ---------------------------------------------------------------------------
# ファイア: テスト用スタブエンジンの構築 (SimpleNamespace)
# ---------------------------------------------------------------------------


def _make_engine(**overrides):
    """PetSystemHandler のメソッドが参照する属性を持つスタブエンジンを返す."""
    pet = SimpleNamespace()
    pet.hp = 10
    pet.max_hp = 20
    pet.pet_type = "puppy"
    pet.pet_ai = MagicMock()
    pet.name = "シエル"

    player = SimpleNamespace()
    player.pets = []
    player.skills = {}
    player.attributes = SimpleNamespace()
    player.attributes.charisma = 5
    player.energy = 100
    player.piety = 0
    player.gain_skill_exp = MagicMock()
    player.pray_to_god = MagicMock(return_value=(True, "ok"))

    entity_manager = SimpleNamespace()
    entity_manager.get_living_entities = MagicMock(return_value=[])

    survival = SimpleNamespace()
    survival.gold = 0

    inventory = SimpleNamespace()
    inventory.items = []
    inventory.remove_item = MagicMock()
    inventory.add_item = MagicMock(return_value=(True, "追加"))

    pet_evolution_manager = MagicMock()
    pet_fusion_manager = MagicMock()

    engine = SimpleNamespace()
    engine.pet = pet
    engine.pet_evolution_manager = pet_evolution_manager
    engine.pet_fusion_manager = pet_fusion_manager
    engine.player = player
    engine.entity_manager = entity_manager
    engine.survival = survival
    engine.inventory = inventory
    engine.altar_pos = (0, 0)
    engine.player.x = 0
    engine.player.y = 0
    engine.log = MagicMock()
    engine.game_state = "play"
    engine.wish_input = ""
    engine.advance_world = MagicMock()
    engine._record_harm_cause = MagicMock()
    for k, v in overrides.items():
        setattr(engine, k, v)
    return engine


def _make_handler(engine=None):
    if engine is None:
        engine = _make_engine()
    return PetSystemHandler(engine), engine


# ---------------------------------------------------------------------------
# use_pet_evolution_stone
# ---------------------------------------------------------------------------


def test_use_pet_evolution_stone_no_pet():
    """ペットがいない場合はログを出して早期リターン."""
    handler, engine = _make_handler()
    engine.pet = None
    handler.use_pet_evolution_stone()
    engine.log.assert_called_once_with("進化させられるペットがいません。")


def test_use_pet_evolution_stone_pet_dead():
    """ペットの HP <= 0 なら進化できない."""
    handler, engine = _make_handler()
    engine.pet.hp = 0
    handler.use_pet_evolution_stone()
    engine.log.assert_called_once_with("進化させられるペットがいません。")


def test_use_pet_evolution_stone_evolution_available():
    """進化候補があり、適用成功すれば進化ログと SE を鳴らす."""
    handler, engine = _make_handler()
    evo_target = MagicMock()
    engine.pet_evolution_manager.get_available_evolutions.return_value = [evo_target]
    engine.pet_evolution_manager.apply_evolution.return_value = True
    with patch("engine.systems.pet_system.SoundManager") as m_sound:
        m_sound.play_se.return_value = None
        handler.use_pet_evolution_stone()
    engine.pet_evolution_manager.get_available_evolutions.assert_called_once_with(
        "puppy", engine.pet.pet_ai, engine.pet
    )
    engine.pet_evolution_manager.apply_evolution.assert_called_once_with(
        engine.pet.pet_ai, evo_target, engine.pet
    )
    engine.log.assert_any_call(
        "★進化の秘石が輝き、【シエル】へと劇的進化した！", (255, 215, 0)
    )
    m_sound.play_se.assert_called_once_with("level_up")


def test_use_pet_evolution_stone_no_evolution_candidates():
    """進化候補がなければ条件未達ログを出す."""
    handler, engine = _make_handler()
    engine.pet_evolution_manager.get_available_evolutions.return_value = []
    handler.use_pet_evolution_stone()
    engine.log.assert_called_once_with(
        "ペットの絆度またはレベルが進化条件に達していません。"
    )


# ---------------------------------------------------------------------------
# use_alchemy_lab
# ---------------------------------------------------------------------------


def test_use_alchemy_lab_not_enough_pets():
    """ペットが 2 体未満なら融合不可ログを出す."""
    handler, engine = _make_handler()
    engine.player.pets = []  # engine.pet だけで 1 体
    handler.use_alchemy_lab()
    engine.log.assert_called_once_with("融合には2体以上のペットが必要です。")


def test_use_alchemy_lab_cannot_fuse():
    """融合条件を満たさなければ条件未達ログを出す."""
    handler, engine = _make_handler()
    p2 = SimpleNamespace()
    p2.name = "ペットB"
    engine.player.pets = [p2]
    engine.pet_fusion_manager.can_fuse.return_value = None
    handler.use_alchemy_lab()
    engine.log.assert_called_once_with(
        "融合条件（種族・絆度・レベル等）を満たしていません。"
    )


def test_use_alchemy_lab_fuse_success():
    """融合成功時は engine.pet を差し替え、FX を再生する."""
    handler, engine = _make_handler()
    p2 = SimpleNamespace()
    p2.name = "ペットB"
    engine.player.pets = [p2]
    pet_original = engine.pet  # can_fuse 呼び出し時の元のペット参照を保持
    fused = SimpleNamespace()
    fused.name = "融合ペット"
    engine.pet_fusion_manager.can_fuse.return_value = "res_001"
    engine.pet_fusion_manager.execute_fusion.return_value = fused
    _fx_stub.play_pet_fusion_fx.return_value = None
    handler.use_alchemy_lab()
    engine.pet_fusion_manager.can_fuse.assert_called_once_with([pet_original, p2], engine.player)
    engine.pet_fusion_manager.execute_fusion.assert_called_once_with(
        [pet_original, p2], engine.player, "res_001"
    )
    assert engine.pet is fused
    _fx_stub.play_pet_fusion_fx.assert_called_once_with(engine, pet_original.name, "ペットB", "融合ペット")


# ---------------------------------------------------------------------------
# play_music
# ---------------------------------------------------------------------------


def test_play_music_no_performance_skill_defaults_lv1():
    """演奏スキルがなければ lv=1 から始める."""
    handler, engine = _make_handler()
    engine.player.skills = {}
    engine.entity_manager.get_living_entities.return_value = []
    with patch("engine.systems.pet_system.random") as m_random:
        m_random.randint.return_value = 50  # 成功率未達
        handler.play_music()
    assert engine.player.gain_skill_exp.call_args[0][0] == "performance"
    assert engine.player.gain_skill_exp.call_args[0][1] == 35


def test_play_music_charisma_bonus():
    """カリスマボーナスが演奏レベルに加算され、エネルギーを消費し advance_world を呼ぶ."""
    handler, engine = _make_handler()
    engine.player.attributes.charisma = 9  # 9 // 3 = 3
    engine.player.skills = {}
    engine.player.energy = 100
    engine.entity_manager.get_living_entities.return_value = []
    with patch("engine.systems.pet_system.random") as m_random:
        m_random.randint.return_value = 50
        handler.play_music()
    assert engine.player.energy == 100 - ENERGY_THRESHOLD
    engine.advance_world.assert_called_once()


def test_play_music_entity_applauds_gives_tip():
    """視界内エンティティが拍手すればチップを獲得する."""
    handler, engine = _make_handler()
    entity = SimpleNamespace()
    entity.name = "街人A"
    entity.hp = 5
    engine.entity_manager.get_living_entities.return_value = [entity]
    engine.player.skills = {}
    engine.player.attributes.charisma = 5
    engine.survival.gold = 0
    with patch("engine.systems.pet_system.random") as m_random:
        # 成功判定 (randint(1,100) <= success_rate=21), チップ額
        m_random.randint.side_effect = [15, 7]  # 成功, チップ7G
        handler.play_music()
    assert engine.survival.gold == 7
    engine.log.assert_any_call("街人Aが拍手を送った！ (+7G)", (255, 220, 100))


def test_play_music_entity_throws_stone_damage():
    """演奏失敗時は HP が 1 減少し、自傷死因を記録する."""
    handler, engine = _make_handler()
    entity = SimpleNamespace()
    entity.name = "街人B"
    entity.hp = 5
    engine.entity_manager.get_living_entities.return_value = [entity]
    engine.player.skills = {}
    engine.player.attributes.charisma = 1
    engine.player.hp = 10
    with patch("engine.systems.pet_system.random") as m_random:
        m_random.randint.side_effect = [95, 3]  # 失敗判定 (success_rate 低め)
        handler.play_music()
    engine._record_harm_cause.assert_called_once_with(CAUSE_SELF)
    assert engine.player.hp == 9  # 10 - 1


# ---------------------------------------------------------------------------
# pray
# ---------------------------------------------------------------------------


def test_pray_success():
    """祈り成功時はエネルギー消費と advance_world を行う."""
    handler, engine = _make_handler()
    engine.player.pray_to_god.return_value = (True, "神が微笑んだ")
    engine.player.energy = 100
    handler.pray()
    engine.log.assert_called_once()
    assert engine.player.energy == 100 - ENERGY_THRESHOLD
    engine.advance_world.assert_called_once()


def test_pray_failure():
    """祈り失敗時はエネルギー消費・advance_world は行わない."""
    handler, engine = _make_handler()
    engine.player.pray_to_god.return_value = (False, "沈黙")
    engine.player.energy = 100
    handler.pray()
    assert engine.player.energy == 100
    engine.advance_world.assert_not_called()


# ---------------------------------------------------------------------------
# offer_altar
# ---------------------------------------------------------------------------


def test_offer_altar_not_at_altar():
    """祭壇の上に立っていなければ供物を捧げられない."""
    handler, engine = _make_handler()
    engine.player.x = 10
    engine.player.y = 10
    engine.altar_pos = (0, 0)
    handler.offer_altar()
    engine.log.assert_called_once_with("祭壇の上に立っていない。")


def test_offer_altar_has_offering():
    """祭壇上で肉・鉱石・パン・ハーブを含むアイテムを捧げると信仰度が上昇する."""
    handler, engine = _make_handler()
    engine.player.x = 0
    engine.player.y = 0
    item = SimpleNamespace()
    item.name = "鹿肉"
    engine.inventory.items = [item]
    engine.player.piety = 0
    handler.offer_altar()
    engine.inventory.remove_item.assert_called_once_with(item, count=1)
    assert engine.player.piety == 30
    engine.advance_world.assert_called_once()


def test_offer_altar_no_offering():
    """供物がなければ「捧げる供物がない」ログを出す."""
    handler, engine = _make_handler()
    engine.player.x = 0
    engine.player.y = 0
    engine.inventory.items = [SimpleNamespace(name="鉄の剣")]  # 肉・鉱石・パン・ハーブを含まない
    handler.offer_altar()
    engine.log.assert_called_once_with(
        "捧げる供物がない（肉・鉱石・パン・ハーブなど）。"
    )


# ---------------------------------------------------------------------------
# use_wish_rod
# ---------------------------------------------------------------------------


def test_use_wish_rod_has_rod():
    """願いの杖を持っていればゲーム状態を wish に遷移し入力を受け付ける."""
    handler, engine = _make_handler()
    rod = SimpleNamespace()
    rod.name = "願いの杖"
    engine.inventory.items = [rod]
    handler.use_wish_rod()
    assert engine.game_state == "wish"
    assert engine.wish_input == ""
    engine.log.assert_called_once()


def test_use_wish_rod_no_rod():
    """願いの杖を持っていなければ「持っていない」ログを出す."""
    handler, engine = _make_handler()
    engine.inventory.items = [SimpleNamespace(name="鉄の剣")]
    handler.use_wish_rod()
    engine.log.assert_called_once_with("願いの杖を持っていない。")


# ---------------------------------------------------------------------------
# confirm_wish
# ---------------------------------------------------------------------------


def test_confirm_wish_parses_and_resets_state():
    """WishParser で願いを解釈し、ゲーム状態を play に戻し入力をクリアする."""
    handler, engine = _make_handler()
    engine.wish_input = "金貨 100 枚"
    with patch("engine.systems.pet_system.WishParser") as m_wp:
        m_wp.parse.return_value = "願いが叶った！"
        handler.confirm_wish()
    m_wp.parse.assert_called_once_with(
        "金貨 100 枚", engine.player, engine.inventory, engine.survival
    )
    engine.log.assert_called_once()
    assert engine.game_state == "play"
    assert engine.wish_input == ""
