"""データファイルが「空なのに正常に見える」状態を握り潰さないことの検証。

対象はキャラクター進行3システム (職業 / スキルツリー / スキル融合)。
data/jobs.yaml などは 13 バイトのプレースホルダで、十分に表面化しないまま
エントリ0件のレジストリになり、プレイヤーは「職業画面に何も出ないこと」を
正常な状態と誤認していた。ここでは原因ごとに区別された診断記録と、
入力があるときは実際にエントリが読めることを固定する。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import pytest

import job_system
import skill_fusion_system
import skill_tree_system

# リポジトリ同梱のプレースホルダと同じ 13 バイト
PLACEHOLDER_TEXT = "# placeholder"

JOBS_YAML = """\
jobs:
  warrior:
    name: 戦士
    tier: 1
    description: 近接戦闘的主力
    description_en: Warrior
    stat_modifiers:
      strength: 5
      endurance: 3
    equipment_restrictions:
      heavy_armor: true
    exclusive_skills: [shield_bash]
    unlock_conditions:
      level: 10
  mage:
    name: 魔法使い
    tier: 1
    description: 遠距離魔法攻撃
    stat_modifiers:
      magic: 5
"""

SKILL_TREES_YAML = """\
skill_trees:
  sword:
    name: 剣術
    icon: "⚔"
    tiers:
      - id: basic_sword
        name: 剣の基本
        description: 剣術の最初の段階
        cost: 5
        prerequisites: []
        effects:
          - type: damage_bonus
            value: 3
            target: melee
"""

SKILL_FUSION_YAML = """\
fusions:
  spellblade:
    name: 呪刃
    description: 剣に呪力を吹き込む
    required_skills: [basic_sword, spark]
    required_job: warrior
    result_skills: [spell_slash]
    bonus_effects:
      - type: elemental_damage
        value: 20
fusion_recipes:
  ember_blade:
    name: 炎の刃
    description: 炎の種で剣を仕上げる
    base_skill: basic_sword
    materials:
      fire_seed: 3
    output: fire_slash
    required_level: 5
    success_rate: 0.8
"""

BROKEN_YAML = "jobs: [unclosed\n  - : :\n"


@dataclass(frozen=True)
class SystemUnderTest:
    """検証対象1システム分の記述 (fixture 内容と期待する分類)。"""

    id: str
    module_name: str
    registry_factory: type
    key: str
    populated_yaml: str
    expected_ids: tuple[str, ...]
    has_recipes: bool = False


JOB_SYSTEM = SystemUnderTest(
    id="job",
    module_name="job_system",
    registry_factory=job_system.JobRegistry,
    key="jobs",
    populated_yaml=JOBS_YAML,
    expected_ids=("warrior", "mage"),
)

SKILL_TREE_SYSTEM = SystemUnderTest(
    id="skill_tree",
    module_name="skill_tree_system",
    registry_factory=skill_tree_system.SkillTreeRegistry,
    key="skill_trees",
    populated_yaml=SKILL_TREES_YAML,
    expected_ids=("sword",),
)

FUSION_SYSTEM = SystemUnderTest(
    id="skill_fusion",
    module_name="skill_fusion_system",
    registry_factory=skill_fusion_system.SkillFusionRegistry,
    key="fusions",
    populated_yaml=SKILL_FUSION_YAML,
    expected_ids=("spellblade",),
    has_recipes=True,
)

SYSTEMS = [JOB_SYSTEM, SKILL_TREE_SYSTEM, FUSION_SYSTEM]
SYSTEM_IDS = [s.id for s in SYSTEMS]


@pytest.fixture(autouse=True)
def _capture_diagnostics(caplog):
    """3システムの記録を DEBUG まで拾い、終了時に実データへ状態を戻す。"""
    caplog.set_level(logging.DEBUG)
    yield caplog
    # レジストリはシングルトンなので、テスト後の状態をリポジトリの実データへ戻す
    JOB_SYSTEM.registry_factory().load()
    SKILL_TREE_SYSTEM.registry_factory().load()
    FUSION_SYSTEM.registry_factory().load()


def _records(caplog, system: SystemUnderTest) -> list[logging.LogRecord]:
    """対象モジュールが出したログ記録だけを返す。"""
    return [r for r in caplog.records if r.name == system.module_name]


def _diagnostic_text(caplog, system: SystemUnderTest) -> str:
    """対象モジュールが出した診断を連結した文字列。"""
    return "\n".join(r.getMessage() for r in _records(caplog, system))


def _complaints(caplog, system: SystemUnderTest) -> list[str]:
    """WARNING 以上の記録 (異常として提示されたもの) を返す。"""
    return [r.getMessage() for r in _records(caplog, system) if r.levelno >= logging.WARNING]


def _write(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def _load(system: SystemUnderTest, path: Path):
    """レジストリを実ファイルから読み直す (モックは使わない)。"""
    registry = system.registry_factory()
    registry.load(str(path))
    return registry


# --- 異常系: 原因ごとに区別された診断が出る ---------------------------------


@pytest.mark.parametrize("system", SYSTEMS, ids=SYSTEM_IDS)
def test_empty_file_reports_path_and_byte_size(tmp_path, caplog, system: SystemUnderTest):
    """実在するが中身が無いファイルは、パスとバイトサイズ付きの診断を出す。"""
    path = _write(tmp_path, f"{system.id}-empty.yaml", PLACEHOLDER_TEXT)
    registry = _load(system, path)

    status = registry.load_status
    assert status.outcome == "empty", f"空ファイルは empty と分類されるべき: {status}"
    assert status.path == str(path)
    assert status.byte_size == len(PLACEHOLDER_TEXT.encode("utf-8"))
    assert status.usable is False
    assert registry.all() == {}

    text = _diagnostic_text(caplog, system)
    assert str(path) in text, f"診断にファイルパスが含まれていない:\n{text}"
    assert str(len(PLACEHOLDER_TEXT.encode("utf-8"))) in text, f"診断にバイトサイズがない:\n{text}"


@pytest.mark.parametrize("system", SYSTEMS, ids=SYSTEM_IDS)
def test_zero_byte_file_is_empty_not_missing(tmp_path, caplog, system: SystemUnderTest):
    """0バイトはプレースホルダと同じ「空」であり、「欠損」とは別扱いにしない。"""
    path = _write(tmp_path, f"{system.id}-zero.yaml", "")
    registry = _load(system, path)

    assert registry.load_status.outcome == "empty"
    assert registry.load_status.byte_size == 0
    assert str(path) in _diagnostic_text(caplog, system)


@pytest.mark.parametrize("system", SYSTEMS, ids=SYSTEM_IDS)
def test_missing_file_reports_distinct_diagnostic(tmp_path, caplog, system: SystemUnderTest):
    """ファイルが無い場合は、空とは区別された診断を出す。"""
    path = tmp_path / f"{system.id}-absent.yaml"
    registry = _load(system, path)

    status = registry.load_status
    assert status.outcome == "missing", f"欠損は missing と分類されるべき: {status}"
    assert status.path == str(path)
    assert status.byte_size is None
    assert registry.all() == {}

    missing_text = _diagnostic_text(caplog, system)
    assert str(path) in missing_text

    # 空ファイル診断とは別のメッセージになること
    empty_path = _write(tmp_path, f"{system.id}-empty.yaml", PLACEHOLDER_TEXT)
    empty_registry = _load(system, empty_path)
    assert empty_registry.load_status.outcome == "empty"
    empty_messages = [
        m for m in _diagnostic_text(caplog, system).splitlines() if str(empty_path) in m
    ]
    assert all(str(path) not in m for m in empty_messages)
    assert empty_messages != []


@pytest.mark.parametrize("system", SYSTEMS, ids=SYSTEM_IDS)
def test_unparseable_file_reports_distinct_diagnostic(tmp_path, caplog, system: SystemUnderTest):
    """YAML として壊れたファイルは、欠損とも空とも別に扱い ERROR にする。"""
    path = _write(tmp_path, f"{system.id}-broken.yaml", BROKEN_YAML)
    registry = _load(system, path)

    assert registry.load_status.outcome == "unparseable"
    assert str(path) in _diagnostic_text(caplog, system)
    assert registry.all() == {}
    assert any(r.levelno >= logging.ERROR for r in _records(caplog, system))


@pytest.mark.parametrize("system", SYSTEMS, ids=SYSTEM_IDS)
def test_missing_expected_key_is_bad_shape_not_empty(tmp_path, caplog, system: SystemUnderTest):
    """中身はあるが想定キーが無い場合は、「空」ではなく「想定と違う形」として出す。"""
    path = _write(tmp_path, f"{system.id}-wrongkey.yaml", "something_else:\n  a: 1\n")
    registry = _load(system, path)

    status = registry.load_status
    assert status.outcome == "bad_shape", f"想定キー欠落は bad_shape と分類されるべき: {status}"
    assert status.key == system.key
    assert str(path) in _diagnostic_text(caplog, system)
    assert registry.all() == {}


@pytest.mark.parametrize("system", SYSTEMS, ids=SYSTEM_IDS)
def test_top_level_not_a_mapping_is_bad_shape(tmp_path, caplog, system: SystemUnderTest):
    """YAML として読めるが辞書でない場合も「空」に丸めない。"""
    path = _write(tmp_path, f"{system.id}-list.yaml", "- a\n- b\n")
    registry = _load(system, path)

    assert registry.load_status.outcome == "bad_shape"
    assert str(path) in _diagnostic_text(caplog, system)
    assert registry.all() == {}


@pytest.mark.parametrize("system", SYSTEMS, ids=SYSTEM_IDS)
def test_genuinely_no_entries_is_not_treated_as_failure(tmp_path, caplog, system: SystemUnderTest):
    """想定キーがあって 0 件は「まだ書かれていない」ので異常扱いしない。"""
    path = _write(tmp_path, f"{system.id}-noentries.yaml", f"{system.key}: {{}}\n")
    registry = _load(system, path)

    status = registry.load_status
    assert status.outcome == "no_entries", f"空マップは no_entries と分類されるべき: {status}"
    assert status.entry_count == 0
    assert registry.all() == {}
    assert _complaints(caplog, system) == []
    assert "has no entries yet" in _diagnostic_text(caplog, system)


# --- 正常系: 入力があれば実際に读到Mightれる --------------------------------


@pytest.mark.parametrize("system", SYSTEMS, ids=SYSTEM_IDS)
def test_populated_fixture_actually_returns_entries(tmp_path, caplog, system: SystemUnderTest):
    """入力があるときは実際にエントリを返し、異常診断を出しすぎない。"""
    path = _write(tmp_path, f"{system.id}-populated.yaml", system.populated_yaml)
    registry = _load(system, path)

    status = registry.load_status
    assert status.outcome == "ok", f"入力があれば ok になるべき: {status}"
    assert status.usable is True
    assert status.byte_size == len(system.populated_yaml.encode("utf-8"))
    assert status.entry_count == len(system.expected_ids)

    entries = registry.all()
    assert set(entries) == set(system.expected_ids), f"読めたエントリが想定と違う: {entries}"
    for entry_id in system.expected_ids:
        assert registry.get(entry_id) is not None
        assert registry.get(entry_id).name

    assert _complaints(caplog, system) == []


def test_populated_job_fixture_preserves_field_values(tmp_path):
    """職業データは各フィールドを解釈できる (既定値で潰れていない)。"""
    path = _write(tmp_path, "jobs-populated.yaml", JOBS_YAML)
    registry = _load(JOB_SYSTEM, path)

    warrior = registry.get("warrior")
    assert warrior.tier == 1
    assert warrior.stat_modifiers == {"strength": 5, "endurance": 3}
    assert warrior.equipment_restrictions == {"heavy_armor": True}
    assert warrior.exclusive_skills == ["shield_bash"]
    assert warrior.unlock_conditions == {"level": 10}
    assert warrior.description_en == "Warrior"
    assert registry.get("mage").stat_modifiers == {"magic": 5}


def test_populated_job_fixture_drives_manager(tmp_path):
    """ジョブマネージャは読み込まれたデータで転職判定できる。"""

    class Attributes:
        strength = 20
        endurance = 20

    class Player:
        level = 15
        attributes = Attributes()
        skills: dict = {}
        job = "novice"

    path = _write(tmp_path, "jobs-populated.yaml", JOBS_YAML)
    registry = _load(JOB_SYSTEM, path)
    manager = job_system.JobManager(registry)
    player = Player()

    assert manager.check_unlock_conditions(player, registry.get("warrior")) is True
    assert manager.change_job(player, "warrior") is True
    assert player.job == "warrior"
    assert player.job_level == 1
    assert player.previous_jobs == ["novice"]

    manager.apply_job_stats(player, registry.get("warrior"))
    assert player.attributes.strength == 25


def test_populated_skill_tree_fixture_preserves_tiers(tmp_path):
    """スキルツリーは階層とエフェクトを丸ごと解釈できる。"""
    path = _write(tmp_path, "trees-populated.yaml", SKILL_TREES_YAML)
    registry = _load(SKILL_TREE_SYSTEM, path)

    tree = registry.get("sword")
    assert tree is not None
    assert tree.name == "剣術"
    assert tree.icon == "⚔"
    assert [t.id for t in tree.tiers] == ["basic_sword"]

    tier = tree.tiers[0]
    assert tier.name == "剣の基本"
    assert tier.cost == 5
    assert tier.prerequisites == []
    assert [(e.type, e.value, e.target) for e in tier.effects] == [("damage_bonus", 3, "melee")]


def test_populated_skill_tree_fixture_drives_manager(tmp_path):
    """スキルツリマネージャは読み込まれたデータで習得判定できる。"""

    class Player:
        skill_points = 10
        skill_tree_progress: dict = {}
        total_skill_points_earned = 0

    path = _write(tmp_path, "trees-populated.yaml", SKILL_TREES_YAML)
    registry = _load(SKILL_TREE_SYSTEM, path)
    manager = skill_tree_system.SkillTreeManager(registry)
    player = Player()

    available = manager.get_available_skills(player)
    assert [s["tier_id"] for s in available] == ["basic_sword"]

    assert manager.learn_skill(player, "sword", "basic_sword") is True
    assert player.skill_tree_progress["sword"] == ["basic_sword"]
    assert player.skill_points == 5
    assert manager.learn_skill(player, "sword", "basic_sword") is False


def test_populated_fusion_fixture_preserves_recipes(tmp_path):
    """スキル融合は融合定義とレシピの両方を解釈できる (黙って捨てない)。"""
    path = _write(tmp_path, "fusion-populated.yaml", SKILL_FUSION_YAML)
    registry = _load(FUSION_SYSTEM, path)

    fusion = registry.get("spellblade")
    assert fusion is not None
    assert fusion.required_skills == ["basic_sword", "spark"]
    assert fusion.required_job == "warrior"
    assert fusion.result_skills == ["spell_slash"]
    assert [(e.type, e.value) for e in fusion.bonus_effects] == [("elemental_damage", 20)]

    recipe = registry.get_recipe("ember_blade")
    assert recipe is not None
    assert recipe.base_skill == "basic_sword"
    assert recipe.materials == {"fire_seed": 3}
    assert recipe.output == "fire_slash"
    assert recipe.required_level == 5
    assert recipe.success_rate == 0.8


def test_empty_fusion_file_reports_recipe_loss_too(tmp_path, caplog):
    """融合ファイルが空なら、レシピ側の読み落ちも黙って終わらせない。"""
    path = _write(tmp_path, "fusion-empty.yaml", PLACEHOLDER_TEXT)
    registry = _load(FUSION_SYSTEM, path)

    assert registry.all() == {}
    assert registry.all_recipes() == {}

    text = _diagnostic_text(caplog, FUSION_SYSTEM)
    assert str(path) in text
    assert "fusion_recipes" in text


def test_repository_placeholder_file_is_reported(tmp_path, caplog):
    """リポジトリ同梱のプレースホルダを実際にロードしても同じ診断になる。"""
    jobs_path = Path(__file__).resolve().parent.parent / "data" / "jobs.yaml"
    registry = _load(JOB_SYSTEM, jobs_path)

    assert registry.load_status.outcome == "empty"
    assert registry.load_status.byte_size == jobs_path.stat().st_size
    assert str(jobs_path) in _diagnostic_text(caplog, JOB_SYSTEM)
    assert registry.all() == {}
