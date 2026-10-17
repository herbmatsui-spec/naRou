"""セーブ永続化の互換性テスト (改善案5)。

pickle 本線と JSON 副線の両方で、以下が保持されることを検証:
- player/pet Entity の ECS コンポーネント (husks, personality, bond, favorite_food_tags)
- Item.enchants
- Survival 状態 (gold, platinum, hunger, thirst, sleep, sleepiness, karma, karma_law_chaos, legacy_skills)
- 既知制約: pickle 本線の Engine.__getstate__ は kernel/entity_manager/ハンドラ等を除外し、
  ロード後は engine.__dict__.update() によりライブ側の kernel が維持されるため、
  kernel 保持の skill_eater システム実行状態と敵エンティティはセーブ対象外。
"""

from __future__ import annotations

import gzip
import hashlib
import logging
import pickle
from types import SimpleNamespace

import pytest

from ecs.components import TitleComponent
from ecs.components.components import HuskComponent, HuskInventoryComponent
from ecs.entity import Entity
from engine.engine import Engine
from exceptions import SaveDataCorruptedError
from item_system import Item
from migration_pipeline import MigrationPipeline
from save_system import SaveSystem


def _make_pet() -> Entity:
    pet = Entity(name="pet", is_pet=True)
    pet.personality = "brave"
    pet.bond = 77
    pet.favorite_food_tags = ["meat", "fish"]
    return pet


def _make_player_with_husk() -> Entity:
    player = Entity(name="player", is_player=True)
    player.get_component(HuskInventoryComponent).husks.append(
        HuskComponent(husk_id="h1", source_monster="slime", tier=2, decay=3)
    )
    return player


def _make_enchanted_item() -> Item:
    return Item(name="sword", enchants=("sharp+1", "fire+2"))


def _minimal_engine_with_state():
    """serialize_engine_to_dict / deserialize_dict_to_engine が必要な属性のみを持つ Engine スタブ"""
    from types import SimpleNamespace

    engine = SimpleNamespace()
    engine.player = _make_player_with_husk()
    engine.pet = _make_pet()
    engine.dungeon_level = 5
    engine.turns = 123
    engine.game_state = "play"

    engine.survival = SimpleNamespace()
    engine.survival.gold = 5000
    engine.survival.platinum = 100
    engine.survival.hunger = 6000
    engine.survival.thirst = 300
    engine.survival.sleep = 700
    engine.survival.sleepiness = 200
    engine.survival.karma = 10
    engine.survival.karma_law_chaos = 5
    engine.survival.legacy_skills = ["fire_bolt", "heal"]

    engine.inventory = SimpleNamespace(items=[_make_enchanted_item()])
    engine.pet_inventory = None
    engine.items_on_ground = []
    engine.territory_state = None
    return engine


# ---------------------------------------------------------------------------
# JSON 副線: serialize/deserialize の対称性
# ---------------------------------------------------------------------------


def test_json_roundtrip_preserves_survival_full_state():
    engine = _minimal_engine_with_state()
    data = SaveSystem.serialize_engine_to_dict(engine)
    surv = data["survival"]
    assert surv["gold"] == 5000
    assert surv["platinum"] == 100
    assert surv["hunger"] == 6000
    assert surv["thirst"] == 300
    assert surv["sleep"] == 700
    assert surv["sleepiness"] == 200
    assert surv["karma"] == 10
    assert surv["karma_law_chaos"] == 5
    assert surv["legacy_skills"] == ["fire_bolt", "heal"]


def test_json_roundtrip_preserves_enchanted_item_and_husks():
    engine = _minimal_engine_with_state()
    data = SaveSystem.serialize_engine_to_dict(engine)
    assert data["inventory"][-1]["enchants"] == ["sharp+1", "fire+2"]
    assert "HuskInventoryComponent" in data["player"]["components"]
    assert data["pet"]["personality"] == "brave"
    assert data["pet"]["bond"] == 77
    assert data["pet"]["favorite_food_tags"] == ["meat", "fish"]


def test_json_deserialize_restores_survival_state():
    engine = _minimal_engine_with_state()
    data = SaveSystem.serialize_engine_to_dict(engine)
    restored = SaveSystem.deserialize_dict_to_engine(data)
    assert restored.survival.gold == 5000
    assert restored.survival.platinum == 100
    assert restored.survival.hunger == 6000
    assert restored.survival.thirst == 300
    assert restored.survival.sleep == 700
    assert restored.survival.sleepiness == 200
    assert restored.survival.karma == 10
    assert restored.survival.karma_law_chaos == 5
    assert restored.survival.legacy_skills == ["fire_bolt", "heal"]


def test_json_deserialize_restores_inventory_and_pet():
    engine = _minimal_engine_with_state()
    data = SaveSystem.serialize_engine_to_dict(engine)
    restored = SaveSystem.deserialize_dict_to_engine(data)
    item = restored.inventory.items[-1]
    assert item.enchants == ("sharp+1", "fire+2")
    husks = restored.player.get_component(HuskInventoryComponent).husks
    assert len(husks) == 1
    assert husks[0].husk_id == "h1"
    assert restored.pet.personality == "brave"
    assert restored.pet.bond == 77


def test_json_deserialize_restores_engine_meta():
    engine = _minimal_engine_with_state()
    data = SaveSystem.serialize_engine_to_dict(engine)
    restored = SaveSystem.deserialize_dict_to_engine(data)
    assert restored.dungeon_level == 5
    assert restored.turns == 123
    assert restored.game_state == "play"


# ---------------------------------------------------------------------------
# pickle 本線: 既存動作の回帰固定
# ---------------------------------------------------------------------------


def test_pickle_roundtrip_preserves_pet_and_player_state():
    pet = _make_pet()
    restored = pickle.loads(pickle.dumps(pet))
    assert restored.personality == "brave"
    assert restored.bond == 77
    assert restored.favorite_food_tags == ["meat", "fish"]

    player = _make_player_with_husk()
    restored_player = pickle.loads(pickle.dumps(player))
    husks = restored_player.get_component(HuskInventoryComponent).husks
    assert len(husks) == 1
    assert husks[0].decay == 3


def test_pickle_roundtrip_preserves_enchanted_item():
    item = _make_enchanted_item()
    restored = pickle.loads(pickle.dumps(item))
    assert restored.enchants == ("sharp+1", "fire+2")


# ---------------------------------------------------------------------------
# 既知制約のドキュメント化 (docstring に記載済み、ここでは回帰固定のみ)
# ---------------------------------------------------------------------------


def test_save_system_docstring_mentions_getstate_exclusion():
    """pickle 本線が kernel/entity_manager を除外する既知制約を docstring に記載していること"""
    doc = SaveSystem.__doc__ or ""
    assert "kernel" in doc
    assert "entity_manager" in doc
    assert "__getstate__" in doc


# ---------------------------------------------------------------------------
# pickle 本線: __dict__.update によるライブ kernel 維持フローの回帰固定
# ---------------------------------------------------------------------------


def _stub_engine(**overrides) -> Engine:
    """__init__ を迂回し、unpicklable 属性をダミーで持つ Engine スタブ。

    entity_manager / renderer はプロパティのため __dict__ へ直接書き込む。
    """
    kernel = SimpleNamespace(get_system=lambda name: object())
    engine = Engine.__new__(Engine)
    engine.kernel = kernel
    engine.__dict__["entity_manager"] = object()
    engine.__dict__["renderer"] = object()
    engine.combat_handler = object()
    engine.skill_eater_handler = object()
    engine.web_server = object()
    engine.game_state_data = SimpleNamespace(turns=0, dungeon_level=1)
    engine.__dict__.update(overrides)
    return engine


def test_engine_getstate_excludes_unpicklable_attrs():
    """Engine.__getstate__ は kernel / entity_manager / 各ハンドラを pickle 対象外とする。"""
    engine = _stub_engine()
    state = engine.__getstate__()
    for key in (
        "kernel",
        "entity_manager",
        "combat_handler",
        "skill_eater_handler",
        "renderer",
        "web_server",
        "game_state_initializer",
    ):
        assert key not in state, f"{key} should be excluded from pickle state"
    # シリアル化可能な進行状態は保持される
    assert "game_state_data" in state


def test_dict_update_merge_preserves_live_kernel():
    """ロード後の engine.__dict__.update はライブ側 kernel を維持し、
    シリアル化可能な進行状態だけを上書き復元する (pickle 本線の正式フロー)。"""
    live = _stub_engine()
    sentinel = SimpleNamespace(get_system=lambda name: object())
    live.kernel = sentinel
    live.magic_number = 1

    loaded = _stub_engine()
    loaded.magic_number = 42
    # pickle 本線では kernel が除外済みであることを前提に、kernel を省いた状態をマージする。
    loaded_state = {k: v for k, v in loaded.__dict__.items() if k != "kernel"}
    live.__dict__.update(loaded_state)

    assert live.kernel is sentinel  # ライブ側 kernel は維持される
    assert live.magic_number == 42  # 進行状態のみ上書き復元
    assert live.entity_manager is not None  # ライブ側 entity_manager も維持


# ---------------------------------------------------------------------------
# セーブバージョン管理とフォールバック (T31 ラウンド2 案C)
# ---------------------------------------------------------------------------


def _version_engine(data_version: str | None = None, turns: int = 42):
    """save_version / 主要フィールドを持つ pickle 可能な最小 Engine スタブ"""
    player = SimpleNamespace(name="勇者", hp=100, max_hp=100)
    if data_version is not None:
        player.save_version = data_version
    return SimpleNamespace(
        player=player, pet=None, turns=turns, dungeon_level=3, game_state="play"
    )


def _save_blob(engine, container_version: int | None = 1) -> bytes:
    """SaveSystem と同じレイアウトでバイナリセーブを生成する。

    container_version=None で旧形式（バージョンヘッダなし）を生成する。
    """
    payload = gzip.compress(pickle.dumps(engine))
    blob = hashlib.sha256(payload).digest() + SaveSystem._compute_hmac(payload)
    if container_version is not None:
        blob += SaveSystem.SAVE_HEADER_MAGIC + container_version.to_bytes(2, "big")
    return blob + payload


def _redirect_save_path(tmp_path, monkeypatch):
    """SaveSystem.SAVE_PATH を tmp 配下へ向け、その Path を返す"""
    path = tmp_path / "savegame.bin"
    monkeypatch.setattr(SaveSystem, "SAVE_PATH", str(path))
    return path


def _engine_snapshot(engine) -> dict:
    """ラウンドトリップ同一性比較用の状態スナップショット"""
    return {
        "turns": engine.turns,
        "dungeon_level": engine.dungeon_level,
        "game_state": engine.game_state,
        "player_name": engine.player.name,
        "player_hp": engine.player.hp,
    }


# --- (a) 旧バージョン -> 新コードでロード成功 ---


@pytest.mark.parametrize("data_version", ["1.0.0", "1.1.0", "1.2.0"])
def test_legacy_data_version_loads_with_new_code(tmp_path, monkeypatch, data_version):
    """対応済みの旧データバージョン (player.save_version) は新コードでロードできる"""
    path = _redirect_save_path(tmp_path, monkeypatch)
    path.write_bytes(_save_blob(_version_engine(data_version=data_version), container_version=None))
    loaded, msg = SaveSystem.load(allow_backup_recovery=False)
    assert loaded is not None
    assert "ロード完了" in msg
    assert loaded.turns == 42
    assert loaded.player.save_version == data_version


def test_legacy_container_without_version_header_loads(tmp_path, monkeypatch):
    """バージョンヘッダを持たない旧形式セーブは形式バージョン 0 としてロードできる"""
    path = _redirect_save_path(tmp_path, monkeypatch)
    path.write_bytes(_save_blob(_version_engine(turns=7), container_version=None))
    loaded, msg = SaveSystem.load(allow_backup_recovery=False)
    assert loaded is not None
    assert "ロード完了" in msg
    assert loaded.turns == 7


# --- (b) 無効バージョン -> 明確なエラー + フォールバック ---


@pytest.mark.parametrize("bad_version", ["0.5.0", "3.0.0", "not-a-version"])
def test_invalid_data_version_rejected_with_clear_error(tmp_path, monkeypatch, bad_version):
    """未対応のデータバージョンは「未対応」を含む明確なエラーになる"""
    path = _redirect_save_path(tmp_path, monkeypatch)
    path.write_bytes(_save_blob(_version_engine(data_version=bad_version), container_version=1))
    loaded, msg = SaveSystem.load(allow_backup_recovery=False)
    assert loaded is None
    assert "未対応" in msg
    assert bad_version in msg


@pytest.mark.parametrize("bad_container", [0, 2, 999])
def test_invalid_container_version_rejected_with_clear_error(tmp_path, monkeypatch, bad_container):
    """形式バージョンが対応範囲外 (0 は旧形式専用 / SAVE_VERSION 超) なら明確なエラーになる"""
    path = _redirect_save_path(tmp_path, monkeypatch)
    path.write_bytes(_save_blob(_version_engine(), container_version=bad_container))
    loaded, msg = SaveSystem.load(allow_backup_recovery=False)
    assert loaded is None
    assert "未対応" in msg
    assert str(bad_container) in msg


def test_invalid_data_version_falls_back_to_backup(tmp_path, monkeypatch):
    """無効バージョンのメインセーブはバックアップから自動復元される"""
    path = _redirect_save_path(tmp_path, monkeypatch)
    SaveSystem.save(_version_engine(turns=7))
    SaveSystem.save(_version_engine(turns=8))  # bak1 = turns=7
    path.write_bytes(_save_blob(_version_engine(data_version="9.9.9", turns=999), container_version=1))
    loaded, msg = SaveSystem.load()
    assert loaded is not None
    assert loaded.turns == 7
    assert "復旧" in msg


def test_invalid_container_version_falls_back_to_backup(tmp_path, monkeypatch):
    """無効な形式バージョンのメインセーブもバックアップから自動復元される"""
    path = _redirect_save_path(tmp_path, monkeypatch)
    SaveSystem.save(_version_engine(turns=11))
    SaveSystem.save(_version_engine(turns=12))  # bak1 = turns=11
    path.write_bytes(_save_blob(_version_engine(turns=999), container_version=2))
    loaded, msg = SaveSystem.load()
    assert loaded is not None
    assert loaded.turns == 11
    assert "復旧" in msg


# --- (c) 壊れたセーブ -> クラッシュせず復元 ---


@pytest.mark.parametrize("mode", ["empty", "truncated", "byte_flip"])
def test_broken_save_recovers_from_backup_without_crash(tmp_path, monkeypatch, mode):
    """破損したメインセーブは例外を送出せずバックアップから復元される"""
    path = _redirect_save_path(tmp_path, monkeypatch)
    SaveSystem.save(_version_engine(turns=5))
    SaveSystem.save(_version_engine(turns=6))  # bak1 = turns=5
    data = bytearray(path.read_bytes())
    if mode == "empty":
        data = bytearray()
    elif mode == "truncated":
        data = data[:20]
    else:
        data[100] ^= 0xFF
    path.write_bytes(bytes(data))
    loaded, msg = SaveSystem.load()
    assert loaded is not None
    assert "復旧" in msg
    assert loaded.turns == 5


# --- (d) ラウンドトリップ同一性 ---


def test_current_format_roundtrip_identity(tmp_path, monkeypatch):
    """現行形式でのセーブ/ロードは状態を同一に復元する"""
    path = _redirect_save_path(tmp_path, monkeypatch)
    engine = _version_engine()
    SaveSystem.save(engine)
    loaded, msg = SaveSystem.load(allow_backup_recovery=False)
    assert "ロード完了" in msg
    assert _engine_snapshot(loaded) == _engine_snapshot(engine)
    assert loaded.player.save_version == SaveSystem.CURRENT_VERSION


def test_legacy_container_roundtrip_identity(tmp_path, monkeypatch):
    """旧形式で保存した状態も新コードのロードで同一に復元される"""
    path = _redirect_save_path(tmp_path, monkeypatch)
    engine = _version_engine(data_version="1.2.0", turns=99)
    engine.player.hp = 77
    path.write_bytes(_save_blob(engine, container_version=None))
    loaded, _msg = SaveSystem.load(allow_backup_recovery=False)
    assert _engine_snapshot(loaded) == _engine_snapshot(engine)
    assert loaded.player.save_version == "1.2.0"


# --- (e) 欠損フィールドのデフォルト補完 ---


def test_load_fills_missing_player_fields_with_defaults(tmp_path, monkeypatch):
    """save_version 等を持たない旧プレイヤーはロード時に既定フィールドが補完される"""
    path = _redirect_save_path(tmp_path, monkeypatch)
    player = SimpleNamespace(name="勇者", hp=10, max_hp=10)
    engine = SimpleNamespace(player=player, pet=None, turns=1, dungeon_level=1, game_state="play")
    path.write_bytes(_save_blob(engine, container_version=None))
    loaded, msg = SaveSystem.load(allow_backup_recovery=False)
    assert loaded is not None
    assert "ロード完了" in msg
    assert loaded.player.save_version == "2.0.0"  # 補完された既定値
    assert loaded.player.titles == []
    assert loaded.player.meta_progression == {}
    assert loaded.player.job == "novice"
    assert TitleComponent in loaded.player.components


def test_json_deserialize_fills_missing_survival_defaults():
    """JSON 副線: survival の欠損フィールドは既定値で補完される"""
    data = {"save_version": "2.0.0", "player": None, "pet": None, "survival": {}, "inventory": []}
    restored = SaveSystem.deserialize_dict_to_engine(data)
    assert restored.survival.gold == 0
    assert restored.survival.hunger == 8000
    assert restored.survival.karma == 20
    assert restored.survival.legacy_skills == []


# --- JSON 副線: バージョン移行 (migration_pipeline) ---


@pytest.mark.parametrize(
    "source_version",
    ["1.0.0", "1.1.0", "1.2.0", None],
    ids=["v1.0.0", "v1.1.0", "v1.2.0", "missing"],
)
def test_json_migrate_bumps_every_legacy_version_to_latest(source_version):
    """JSON 副線: すべての旧バージョン（と欠損）は v2.0.0 へ移行される"""
    data = {"player": {"name": "勇者"}}
    if source_version is not None:
        data["save_version"] = source_version
    migrated = MigrationPipeline.migrate(data)
    assert migrated["save_version"] == "2.0.0"
    assert migrated["player"]["components"] == {}


def test_json_migrate_current_version_is_noop():
    """現行バージョンのデータはマイグレーションで変化しない"""
    data = {"save_version": "2.0.0", "player": {"name": "勇者", "components": {"k": 1}}}
    migrated = MigrationPipeline.migrate(data)
    assert migrated["save_version"] == "2.0.0"
    assert migrated["player"]["components"] == {"k": 1}


@pytest.mark.parametrize("bad_version", ["0.5.0", "9.9.9", "garbage"])
def test_json_migrate_rejects_unknown_version(bad_version):
    """JSON 副線: 未対応バージョンは明確なエラーになる（黙認しない）"""
    with pytest.raises(SaveDataCorruptedError):
        MigrationPipeline.migrate({"save_version": bad_version, "player": {}})


# --- ログメッセージ ---


def test_load_failure_logs_backup_recovery_notice(tmp_path, monkeypatch, caplog):
    """ロード失敗時は「バックアップから復元を試みます」のログが出る"""
    path = _redirect_save_path(tmp_path, monkeypatch)
    SaveSystem.save(_version_engine(turns=5))
    SaveSystem.save(_version_engine(turns=6))
    data = bytearray(path.read_bytes())
    data[100] ^= 0xFF
    path.write_bytes(bytes(data))
    with caplog.at_level(logging.WARNING, logger="save_system"):
        loaded, msg = SaveSystem.load()
    assert loaded is not None
    assert "バックアップから復元を試みます" in caplog.text
    assert "復旧" in msg


def test_load_failure_without_backup_logs_recovery_abandon(tmp_path, monkeypatch, caplog):
    """バックアップが無い場合は復元断念のエラーログが出てロード失敗が返る"""
    path = _redirect_save_path(tmp_path, monkeypatch)
    SaveSystem.save(_version_engine(turns=5))  # 初回セーブ: バックアップ無し
    data = bytearray(path.read_bytes())
    data[100] ^= 0xFF
    path.write_bytes(bytes(data))
    with caplog.at_level(logging.WARNING, logger="save_system"):
        loaded, msg = SaveSystem.load()
    assert loaded is None
    assert "ロード失敗" in msg
    assert "バックアップからの復元に失敗しました" in caplog.text
