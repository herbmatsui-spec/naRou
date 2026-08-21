# naRou リファクタリング実装計画 (72ステップ)

この計画は「低性能なLLMでも実装可能」な粒度に分割されています。
各ステップは **独立して実行可能** で、前提条件・変更ファイル・具体的な作業・検証方法が書かれています。
順番に従って進めてください。ステップ間の依存関係は「依存」欄に記載。

凡例:
- 📁 = 新規ファイル作成
- ✏️ = 既存ファイル修正
- 🔍 = 検証・確認のみ
- 優先度: [P0]致命 / [P1]高 / [P2]中 / [P3]低

---

## Phase A: 基礎基盤 (型・インターフェース)

### Step 1 — システム用 Protocol 定義ファイルを新規作成 [P1]
- 📁 新規: `packages/core/kernel/system_protocols.py`
- 作業: 以下の空の Protocol を定義（実装は後で埋める）
```python
from __future__ import annotations
from typing import Protocol, Any, runtime_checkable

@runtime_checkable
class ISystem(Protocol):
    name: str
    def initialize(self, engine: Any) -> None: ...
    def update(self, engine: Any, dt: float = 1.0) -> None: ...
```
- 検証: `python -c "from packages.core.kernel.system_protocols import ISystem; print('ok')"`

### Step 2 — コンスタント集約ファイルの確認・補完 [P2]
- 🔍 確認: `constants.py` が存在し、以下が定義済みか確認
  `AUTO_SAVE_INTERVAL, ENERGY_THRESHOLD, JOB_EXP_PER_TURN, JOB_LEVEL_UP_THRESHOLD, FACTION_INFLUENCE_INTERVAL, GUILD_QUEST_RESET_INTERVAL, SKILL_TREE_CHECK_INTERVAL, SKILL_POINTS_NOTIFICATION_THRESHOLD, PET_WALKING_BOND_DISTANCE, PET_NEGLECTED_BOND_DISTANCE, PET_PATH_LENGTH_CHECK`
- 作業: 不足していれば追記（既存の値を維持）。
- 検証: `python -c "import constants; print(constants.AUTO_SAVE_INTERVAL)"`

### Step 3 — `localize()` を単一場所に集約 [P1]
- ✏️ `localization_manager.py` に関数を追加（なければ新規）：
```python
def localize(key: str, language: str | None = None) -> str:
    return LocalizationManager().get_text(key, language)
```
- ✏️ `components.py:239` の `localize()` を削除し、import に変更:
  `from localization_manager import localize`
- ✏️ `core_framework.py:209` の `localize()` も同様に削除し import に変更。
- 検証: `python -c "from components import localize; from core_framework import localize; print('ok')"`
- 依存: なし

### Step 4 — 例外ログ関数のバグ修正 [P0]
- ✏️ `exceptions.py` の `ElonaError.log_to_file()` を修正:
```python
def log_to_file(self, log_dir="logs"):
    import sys
    os.makedirs(log_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    fn = os.path.join(log_dir, f"error_log_{ts}.txt")
    with open(fn, "w", encoding="utf-8") as f:
        f.write(f"=== Error: {self.__class__.__name__} ===\n{self.message}\n")
        exc = sys.exc_info()[1]
        if exc:
            traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
        else:
            traceback.print_stack(file=f)
    return fn
```
- 検証: `python -c "from exceptions import ElonaError; e=ElonaError('test'); print(e.log_to_file())"`
- 依存: なし

### Step 5 — `validate.py` のシェルインジェクション修正 [P1]
- ✏️ `validate.py` の `run_command` を `shell=False` に変更:
```python
import shlex
def run_command(cmd, cwd=None):
    print(f"Running: {cmd}")
    parts = shlex.split(cmd)
    result = subprocess.run(parts, cwd=cwd, capture_output=True, text=True)
    ...
```
- 検証: `python validate.py --code` がエラーなく走ること（lint未導入ならスキップ扱い）
- 依存: なし

### Step 6 — グローバル設定シングルトンの遅延初期化整理 [P2]
- ✏️ `config_manager.py`: `get_config_manager()` はそのままだが、モジュール冒頭の `load_dotenv()` の順序を整理（import を先頭にまとめる）。
- 検証: `python -c "from config_manager import get_config_manager; get_config_manager(); print('ok')"`

---

## Phase B: 循環import解消

### Step 7 — `game.py` の遅延import化（初期化ブロック） [P1]
- ✏️ `game.py:117` の `Engine.__init__` 内で、パッケージロードを try の中に既にあるが、
  `from exceptions import SystemInitError` を関数内トップに持ってくる現状を維持しつつ、
  他のトップレベル import（`advanced_systems`, `data_manager` など `setup_systems` 内で使う物）を
  関数内 import に移動。
- 検証: `python -c "import game; print('ok')"` が通ること。
- 依存: Step 1

### Step 8 — `system_coordinator.py` の import 順序修正 [P2]
- ✏️ `system_coordinator.py`: `from packages.core.kernel.kernel import Kernel` を関数内に移動し、
  型注釈には `TYPE_CHECKING` を使用。
```python
from __future__ import annotations
from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from packages.core.kernel.kernel import Kernel
```
- 検証: `python -c "from system_coordinator import SystemCoordinator; print('ok')"`

### Step 9 — `engine.py` の import 整理 [P2]
- ✏️ `engine.py:12` `from localization_manager import LocalizationManager` を維持。
  `GameLocalizer.set_language` 内の遅延importを維持。追加で `atexit` ブロックはファイル末尾に移動済みなので変更なし。
- 検証: `python -c "import engine; print('ok')"`

### Step 10 — `entity.py` の遅延import整理 [P1]
- ✏️ `entity.py` のトップレベル import 群（`components`）は維持。
  関数内 import（`get_component` 内の `skill_tree_system` 等）は現状維持。
  新たに `PetAI.increase_bond` の `from pet_systems import PetBondSystem` は維持（循環しない）。
- 検証: `python -c "from entity import Entity; print('ok')"`

### Step 11 — `pet_systems.py` の遅延import確認 [P2]
- ✏️ `pet_systems.py:206` `PetBondSystem.increase_bond` 内の
  `from pet_contract_system import ...` は関数内なので OK。変更なし（確認のみ）。
- 検証: `python -c "from pet_systems import PetBondSystem; print('ok')"`

### Step 12 — Kernel の `get_system` に既定値オーバーロード追加 [P2]
- ✏️ `packages/core/kernel/kernel.py`: テスト用に `get_system(name, default=None)` を追加。
```python
def get_system(self, name: str, default: Any = None) -> Any:
    return self._systems.get(name, default)
```
（既存の `KeyError` 版は `get_system_strict` に rename）
- 検証: `python -c "from packages.core.kernel.kernel import Kernel; k=Kernel(); print(k.get_system('x', 'none'))"`

---

## Phase C: Engine 分解（マネージャ抽出）

### Step 13 — `CombatManager` 抽出（UIから分離） [P1]
- 📁 新規: `managers/combat_manager.py`
- 作業: `game.py` の `_on_kill` ロジックのうち「戦闘结算」部分を関数 `resolve_kill(engine, entity)` として移動。
- 命名: `CombatManager.handle_kill(self, engine, entity)`
- 検証: `python -c "from managers.combat_manager import CombatManager; print('ok')"`
- 依存: Step 7

### Step 14 — `SkillRewardManager` 抽出 [P2]
- ✏️ `game.py:_on_kill` のスキルポイント付与部分（1095-1102行）を `managers/skill_reward_manager.py` に移動。
- 検証: import が通ること。

### Step 15 — `PetBondManager` 抽出 [P2]
- ✏️ `game.py:advance_world` のペット絆度ロジック（1252-1261行）を `managers/pet_bond_manager.py` に移動。
- 検証: import が通ること。

### Step 16 — `WorldNewsManager` 抽出 [P2]
- ✏️ `game.py:advance_world` の世界ニュース・称号・ジョブ経験値部分を `managers/world_news_manager.py` に移動。
- 検証: import が通ること。

### Step 17 — `PersistenceManager` 抽出 [P2]
- ✏️ `game.py:advance_world` のオートセーブ部分（1197-1200行）を `managers/persistence_manager.py` に移動。
- 検証: import が通ること。

### Step 18 — `FactionManager` 抽出 [P2]
- ✏️ `game.py:_on_kill` の派閥評判更新（1138-1142行）、`advance_world` の派閥影響力（1246-1250行）を `managers/faction_manager.py` に移動。
- 検証: import が通ること。

### Step 19 — `Engine` からマネージャ呼び出しへの置換 [P1]
- ✏️ `game.py` の `_on_kill` / `advance_world` 内で、Step13-18 で抽出したマネージャを呼び出すよう書き換え。
  元のインラインコードは削除。
- 検証: `python -c "import game; g=game.Engine.__new__(game.Engine); print('ok')"` （完全初期化は重いのでクラス定義のみ確認）

### Step 20 — `ContextMenuBuilder` 抽出 [P2]
- ✏️ `game.py:open_context_menu` （859-926行）を `managers/context_menu_builder.py` に移動。
  `Engine.open_context_menu` はビルダーを呼ぶだけにする。
- 検証: import が通ること。

### Step 21 — `StateMachine` 抽出 [P2]
- ✏️ `game.py:change_state` （822-849行）を `managers/state_machine.py` に移動。
  `GameState` のマッピング辞書は `constants.py` に移動。
- 検証: import が通ること。

### Step 22 — `Engine.setup_systems` の整理 [P2]
- ✏️ `game.py:setup_systems` を `managers/setup_coordinator.py` に移動し、`Engine` は委譲のみに。
- 検証: `python -c "from managers.setup_coordinator import setup_systems; print('ok')"`

---

## Phase D: Entity / ECS 純化

### Step 23 — `Entity` の重複フィールド削除（dataclass競合） [P1]
- ✏️ `entity.py:857-859` と `862-867` の `skill_tree_progress`, `skill_points`, `total_skill_points_earned` の
  クラス変数定義（`field(default_factory=...)`）を削除。これらはコンポーネント委譲プロパティのみにする。
- 検証: `python -c "from entity import Entity; e=Entity(); print(e.skill_points)"` が動くこと。

### Step 24 — `Entity` の直接属性をコンポーネント化（主能力以外） [P1]
- ✏️ `entity.py` の `__init__` で直接定義している以下を `components` 経由に変更:
  - `self.affection` → `AffectionComponent`（新規 dataclass を `components.py` に追加）
  - `self.is_mounted` → 上記コンポーネントに統合
  - `self.gene_skills` → `SkillFusionComponent` に既存
  - `self.pet_type`, `self.pet_fusion_history` → `PetComponent`（新規）
  - `self.emote_state` 等 → `EmoteComponent`（新規）
- 検証: `python -c "from entity import Entity; e=Entity(is_player=True); print(e.affection)"`

### Step 25 — `PetAI` をコンポーネントとして統合 [P2]
- ✏️ `entity.py` の `PetAI` クラスを `components.py` の `PetAIComponent` dataclass に変更。
  `Entity.pet_ai` は `get_component(PetAIComponent)` を返すプロパティに。
- 検証: `python -c "from entity import Entity; e=Entity(is_pet=True); print(e.pet_ai.bond)"`

### Step 26 — `GodInfo` のモジュール分離 [P2]
- 📁 新規: `god_system.py`
- ✏️ `entity.py` の `GodInfo` クラス全体を `god_system.py` に移動。
  `entity.py` は `from god_system import GodInfo` に変更。
- 検証: `python -c "from god_system import GodInfo; print(GodInfo.GODS)"`

### Step 27 — `Skill` / `Attributes` dataclass を `components.py` に移動 [P2]
- ✏️ `entity.py` の `Skill`, `Attributes` を `components.py` に移動。
  `entity.py` から import。
- 検証: `python -c "from components import Skill, Attributes; print('ok')"`

### Step 28 — `Entity.to_dict` / `from_dict` のコンポーネント対応 [P1]
- ✏️ `entity.py` の `to_dict` / `from_dict` を各コンポーネントの `to_dict` / `from_dict` を呼ぶよう書き換え。
  現状の `for comp_type, comp in self.components.items()` ループを保持。
- 検証: `python -c "from entity import Entity; e=Entity(is_player=True); d=e.to_dict(); print(len(d))"`

### Step 29 — ミュータブルデフォルトの一掃 [P1]
- ✏️ `components.py` の全 dataclass で `list` / `dict` / `set` デフォルトを `field(default_factory=...)` に。
  （現状ほぼ対応済みだが、`StorytellerComponent.current_choice_prompt` 等を確認）
- 検証: `python -c "from components import TitleComponent; a=TitleComponent(); b=TitleComponent(); assert a.titles is not b.titles"`

### Step 30 — ECS クエリヘルパー追加 [P2]
- 📁 新規: `ecs_query.py`
- 作業: `Entity` からコンポーネントを持つエンティティをフィルタする関数を追加。
```python
def entities_with(entities, *component_types):
    return [e for e in entities if all(e.has_component(c) for c in component_types)]
```
- 検証: `python -c "from ecs_query import entities_with; print('ok')"`

---

## Phase E: 定数・マジックナンバー

### Step 31 — `game.py` のマジックナンバーを定数化 [P1]
- ✏️ 以下を `constants.py` に追加し、`game.py` で参照:
  - `REINCARNATION_XP_PENALTY_BASE = 0.50`
  - `REINCARNATION_XP_PENALTY_STEP = 0.05`
  - `SKILL_DROP_CHANCE = 0.20`
  - `SKILL_DROP_MIN = 1`, `SKILL_DROP_MAX = 2`
  - `BOSS_FRAGMENT_DROP_CHANCE = 0.08`
  - `NATURAL_REGEN_HUNGER_THRESHOLD = 1000`
  - `BOND_WALKING_GAIN = 1`, `BOND_NEGLECTED_LOSS = 2`
  - `COMBAT_BOND_GAIN = 5`
- 検証: `python -c "import constants; print(constants.SKILL_DROP_CHANCE)"`

### Step 32 — `game.py` のターン間隔定数化 [P2]
- ✏️ 以下を `constants.py` に追加:
  - `NATURAL_REGEN_INTERVAL = 4`
  - `WORLD_NEWS_INTERVAL = 30`
  - `TITLE_CHECK_INTERVAL = 10` (既存)
  - `PET_BOND_CHECK_INTERVAL = 1`
- 検証: `python -c "import constants; print(constants.WORLD_NEWS_INTERVAL)"`

### Step 33 — ダメージ計算の定数化 [P2]
- ✏️ `game.py:_pet_ai`, `_npc_ai` の `max_hp * 0.3` (retreat threshold) を
  `PET_RETREAT_HP_RATIO = 0.3` に。
- 検証: `python -c "import constants; print(constants.PET_RETREAT_HP_RATIO)"`

### Step 34 — `god_id` デフォルト値の定数化 [P2]
- ✏️ `entity.py` の `self.god_id = "eyth"` を `DEFAULT_GOD_ID = "eyth"` (constants.py) に。
  `game.py` の `player.god_id = "jure"` も `STARTING_GOD_ID = "jure"` に。
- 検証: `python -c "import constants; print(constants.DEFAULT_GOD_ID)"`

---

## Phase F: 設定・バリデーション

### Step 35 — YAML スキーマ検証ヘルパー追加 [P1]
- 📁 新規: `data_validation.py`
- 作業:
```python
import yaml
from pathlib import Path
from typing import Any

def load_yaml_validated(path: str, schema: dict | None = None) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing data file: {path}")
    with open(p, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if schema:
        for key, typ in schema.items():
            if key in data and not isinstance(data[key], typ):
                raise ValueError(f"Invalid type for {key} in {path}")
    return data
```
- 検証: `python -c "from data_validation import load_yaml_validated; print(load_yaml_validated('data/tutorial_guides.yaml'))"`

### Step 36 — `pet_systems.py` の YAML ロードを検証付きに [P2]
- ✏️ `pet_systems.py:15` の `_load_yaml` を `data_validation.load_yaml_validated` に置換。
- 検証: `python -c "from pet_systems import PetEquipmentManager; PetEquipmentManager(); print('ok')"`

### Step 37 — `config_manager.py` の設定ロード検証 [P2]
- ✏️ `ConfigManager._load_config` で `load_yaml_validated` を使用し、存在しない場合は空 dict ではなく警告ログ。
- 検証: `python -c "from config_manager import ConfigManager; ConfigManager('nonexistent.yaml'); print('ok')"`

### Step 38 — `GodInfo` の YAML ロード検証 [P2]
- ✏️ `god_system.py` の `get_all` で `load_yaml_validated("data/gods.yaml")` を使用。
- 検証: `python -c "from god_system import GodInfo; print(GodInfo.get_all())"`

### Step 39 — `Entity` シリアライズ時の例外安全化 [P2]
- ✏️ `entity.py:to_dict` の `for k, v in comp.__dict__.items()` ループで、
  シリアライズ不可能な値（関数等）を `try/except` でスキップ。
- 検証: `python -c "from entity import Entity; e=Entity(is_player=True); e.to_dict(); print('ok')"`

---

## Phase G: コード品質・重複排除

### Step 40 — 重複 `localize()` 完全削除確認 [P1]
- 🔍 `grep -rn "def localize" .` で `localization_manager.py` 以外に定義がないことを確認。
- 検証: `grep -rn "def localize" naRou/ | grep -v localization_manager` が空であること。

### Step 41 — `Entity` のプロパティ委譲を自動生成ヘルパーに [P2]
- 📁 新規: `delegate_utils.py`
- 作業:
```python
def delegate(component_getter, attr):
    def getter(self):
        return getattr(component_getter(self), attr)
    def setter(self, val):
        setattr(component_getter(self), attr, val)
    return property(getter, setter)
```
- ✏️ `entity.py` の代表的なプロパティ（hp, mp, gold 等）をこのヘルパーで生成。
  （全置換は大きいため、まず 5 個程度で例示）
- 検証: `python -c "from entity import Entity; e=Entity(is_player=True); e.hp=30; print(e.hp)"`

### Step 42 — 未使用 import の削除 [P3]
- 🔍 `ruff check --select F401 .` または手動で未使用 import を削除。
- 検証: 各ファイルで `python -c "import <module>"` が通ること。

### Step 43 — 未使用変数・代入の削除 [P3]
- 🔍 `ruff check --select F841 .` で検出し削除。
- 検証: 上記コマンドがクリーンになること。

### Step 44 — デッドコード（TODO コメント）の整理 [P3]
- 🔍 `grep -rn "TODO" naRou/*.py` をリスト化。
  実装済みのものはコメント削除、未実装は Issue 化（この計画外）。
- 検証: TODO リストを `TODO.md` に出力。

### Step 45 — ログ出力の統一 [P2]
- ✏️ `print()` を用いたデバッグ出力を `logger.debug()` / `logger.info()` に置換。
  対象: `main.py`, `game.py`, `pet_systems.py` の `print` 文。
- 検証: `grep -rn "print(" naRou/*.py` が最小限になること。

---

## Phase H: テスト容易性

### Step 46 — `Engine` の依存注入対応 [P1]
- ✏️ `game.py` の `Engine.__init__` で `kernel` を引数で受け取れるように:
```python
def __init__(self, renderer=None, kernel=None):
    self.kernel = kernel or Kernel()
    ...
```
- 検証: `python -c "import game; e=game.Engine.__new__(game.Engine); print('ok')"`

### Step 47 — テスト用フィクスチャ作成 [P2]
- 📁 新規: `tests/conftest.py`
- 作業: `make_test_engine()` ヘルパーを追加（最小限の Kernel を持つ Engine）。
- 検証: `python -c "from tests.conftest import make_test_engine; print('ok')"`

### Step 48 — 単体テスト: `Point` / `AStar` [P2]
- 📁 新規: `tests/test_core_framework.py`
- 作業: `Point` の演算、`bresenham_line`、`AStar.get_path` の正常系・異常系をテスト。
- 検証: `python -m pytest tests/test_core_framework.py -v`

### Step 49 — 単体テスト: `EventBus` [P2]
- 📁 新規: `tests/test_event_bus.py`
- 検証: `python -m pytest tests/test_event_bus.py -v`

### Step 50 — 単体テスト: `Entity` コンポーネント [P2]
- 📁 新規: `tests/test_entity.py`
- 作業: `Entity` 生成、コンポーネント取得、シリアライズ往復をテスト。
- 検証: `python -m pytest tests/test_entity.py -v`

### Step 51 — 単体テスト: `ConfigManager` [P2]
- 📁 新規: `tests/test_config_manager.py`
- 検証: `python -m pytest tests/test_config_manager.py -v`

### Step 52 — 単体テスト: `Kernel` パッケージロード [P2]
- 📁 新規: `tests/test_kernel.py`
- 検証: `python -m pytest tests/test_kernel.py -v`

---

## Phase I: ツール・スクリプト統合

### Step 53 — ツール CLI 骨組み作成 [P2]
- 📁 新規: `tools/cli.py`
- 作業: `argparse` サブコマンド構造:
```python
import argparse
def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("validate-assets")
    sub.add_parser("gen-manifest")
    # ... 既存ツールをサブコマンドとして登録
    args = parser.parse_args()
    ...
```
- 検証: `python tools/cli.py --help`

### Step 54 — `visual_regression.py` を CLI に統合 [P3]
- ✏️ `tools/visual_regression.py` の `main()` を `cli.py` のサブコマンドとして登録。
- 検証: `python tools/cli.py visual-regression`

### Step 55 — `verify_build.py` を CLI に統合 [P3]
- ✏️ 同上。
- 検証: `python tools/cli.py verify-build`

### Step 56 — `gen_release_notes.py` を CLI に統合 [P3]
- ✏️ 同上。
- 検証: `python tools/cli.py gen-release-notes`

### Step 57 — `bump_version.py` を CLI に統合 [P3]
- ✏️ 同上。
- 検証: `python tools/cli.py bump-version`

### Step 58 — `stats_assets.py` を CLI に統合 [P3]
- ✏️ 同上。
- 検証: `python tools/cli.py stats-assets`

### Step 59 — 未使用ツールの特定・削除 [P3]
- 🔍 `tools/` 内で `import` されていない、またはデッドなツールをリスト化し削除。
- 検証: `python -c "import tools.cli; print('ok')"`

### Step 60 — ツール共通ロガー追加 [P3]
- ✏️ `tools/cli.py` に `logging.basicConfig(level=logging.INFO)` を追加。
- 検証: 上記コマンド実行時にログが出ること。

---

## Phase J: ドキュメント・最終確認

### Step 61 — `README.md` の更新 [P3]
- ✏️ リファクタリング後のアーキテクチャ図を追加（Kernel / Packages / Managers / ECS）。
- 検証: ファイルが存在し、Markdown として読めること。

### Step 62 — `ARCHITECTURE.md` 新規作成 [P3]
- 📁 新規: `ARCHITECTURE.md`
- 作業: パッケージ一覧、マネージャ一覧、コンポーネント一覧を記載。
- 検証: ファイルが存在すること。

### Step 63 — `API.md` 新規作成 [P3]
- 📁 新規: `API.md`
- 作業: `Engine` の公開メソッド、`Kernel` の API を記載。
- 検証: ファイルが存在すること。

### Step 64 — `CHANGELOG.md` 更新 [P3]
- ✏️ リファクタリング内容をエントリとして追加。
- 検証: ファイルが存在すること。

### Step 65 — 型チェック設定追加 [P1]
- 📁 新規: `pyproject.toml` (または既存に追記)
- 作業: `[tool.mypy]` セクション、`[tool.ruff]` セクションを追加。
- 検証: `ruff check .` が走ること（未導入なら `pip install ruff` を案内）。

### Step 66 — `pre-commit` 設定 [P2]
- 📁 新規: `.pre-commit-config.yaml`
- 作業: `ruff`, `black`, `mypy` をフックに追加。
- 検証: `pre-commit run --all-files` が走ること（未導入なら案内）。

### Step 67 — CI ワークフロー確認・修正 [P2]
- ✏️ `.github/workflows/validate.yml` が `validate.py` を呼ぶ構成になっているか確認し、
  型チェック・テストを追加。
- 検証: ワークフローファイルが YAML として有効。

### Step 68 — 起動スクリプト `run.py` の確認 [P2]
- 🔍 `run.py` または同等のエントリポイントが `main.py` を正しく呼ぶか確認。
- 検証: `python main.py` がメニューを表示すること（対話入力は手動）。

### Step 69 — 依存関係ファイルの整備 [P2]
- 📁 新規/更新: `requirements.txt` または `pyproject.toml` の `[project.dependencies]`
- 作業: `tcod`, `pydantic`, `yaml`, `cryptography`, `python-dotenv` を明記。
- 検証: `pip install -r requirements.txt` が解決可能。

### Step 70 — 全テスト実行 [P1]
- ✏️ `python -m pytest tests/ -v` が全て通ることを確認。
- 検証: 全テスト緑。

### Step 71 — `validate.py` の統合確認 [P1]
- ✏️ `python validate.py` が `ruff` / `black` / `mypy` / `pytest` を順次実行すること。
- 検証: スクリプトが完了コード 0 で終わる。

### Step 72 — 最終レビュー・ドキュメント反映 [P1]
- 🔍 全ステップの結果を `REVIEW_RESULT.md` にまとめ。
- 作業: リファクタリング前後のコード行数・テストカバレッジ・パフォーマンス指標を記載。
- 検証: `REVIEW_RESULT.md` が存在し、内容が整合していること。

---

## 実装順序の依存グラフ

```
Phase A (1-6)  ──┐
                 ├──> Phase B (7-12) ──> Phase C (13-22) ──┐
Phase D (23-30) ─┤                                         │
Phase E (31-34) ─┤                                         ├──> Phase H (46-52) ──> Phase J (61-72)
Phase F (35-39) ─┤──> Phase G (40-45) ─────────────────────┤
Phase I (53-60) ─┘                                         │
                                                          └─> Phase I (53-60)
```

**最小実行パス（P0/P1 のみ）**: 4 → 5 → 7 → 13 → 19 → 23 → 28 → 31 → 35 → 46 → 65 → 70 → 71 → 72

---

## LLM 実装時の注意事項

1. **各ステップは独立**: 他のステップを待たずに実行可能。
2. **検証コマンド必須**: 各ステップの「検証」を必ず実行し、失敗したら停止。
3. **変更範囲最小化**: ステップで指定されたファイル・関数のみを変更。
4. **後方互換性**: `Engine` の公開 API は変更しない（内部実装のみ変更）。
5. **コミット単位**: 各ステップ完了ごとに `git commit` を推奨。
