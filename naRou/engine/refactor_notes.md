# 残りのリファクタリングステップ (49-72)

以下の手順で、engine.py内の残りの遅延インポートをトップレベルまたはブートストラップモジュールに移動します。

## 手順のパターン
1. メソッド内の遅延インポート行を特定し削除
2. 安全な場合はトップレベルインポートに移動（例外、頻繁に使用されるクラス等）
3. 循環参照のリスクがある場合はブートストラップモジュールに移動するか、TYPE_CHECKINGブロックを使用
4. メソッド内での使用を変更せずにインポートされたシンボルを参照するようにする

## 移動対象の遅延インポート一覧
以下はengine.py内でメソッドスコープに残っている遅延インポートの一覧です（ファイルの現在の状態により行番号は変動している可能性があります）。

### 例外クラス（トップレベルに移動推奨）
- from naRou.exceptions import DataParseError
- from naRou.exceptions import ResourceLoadError

### 入出力・システムクラス（トップレベルに移動推奨）
- from naRou.input_handler import InputHandler
- from naRou.skill_eater_territory_system import TerritoryState
- from naRou.procedural_quest_generator import REGISTRY, GENERATOR
- from naRou.skill_eater_system import CharacterState, SkillEaterRegistry
- from naRou.systems.skill_eater_husk_system import create_husk
- from naRou.ecs.components.components import HuskInventoryComponent
- from naRou.core.state_machine import StateMachine
- from naRou.managers.context_menu_builder import ContextMenuBuilder
- from naRou.managers.combat_manager import CombatManager
- from naRou.secret_area_system import SECRET_REGISTRY
- from naRou.item_system import Item

### エンジン補助システム（既に移動済みまたはブートストラップ候補）
- from naRou.core.systems.setup_coordinator import setup_systems （既にブートストラップに移動済み）
- from naRou.core.world_state_manager import GameStateInitializer （トップレベルに移動済み）
- from naRou.core.system_initializer import SystemInitializer （トップレベルに移動済み）

## 実装例（DataParseErrorの場合）

**変更前:**
```python
def _initialize_player_and_pet(self) -> None:
    from naRou.exceptions import DataParseError
    if not self.game_state_data.player or not self.game_state_data.pet:
        raise DataParseError("Player or Pet entity is missing from game_state_data during initialization")
```

**変更後:**
```python
# ファイルのトップレベルインポート群に追加（既存のSystemInitErrorの近く）
from naRou.exceptions import SystemInitError, DataParseError, ResourceLoadError

def _initialize_player_and_pet(self) -> None:
    if not self.game_state_data.player or not self.game_state_data.pet:
        raise DataParseError("Player or Pet entity is missing from game_state_data during initialization")
```

## 注意事項
1. 各インポートの移動後に、エンジンのインポートが正常に動作することを確認してください
2. 循環参照エラーが発生した場合は、該当するインポートをブートストラップモジュールに移動するか、TYPE_CHECKINGブロックを使用してください
3. ブートストラップモジュールに移動する場合は、engine.pyから`from naRou.engine.bootstrap import [シンボル]`としてインポートしてください
4. すべての変更後には、ベースラインと同様のインポート時間とテスト結果になることを確認してください

## 完了条件
- engine.py内のメソッドスコープ（トップレベル・TYPE_CHECKINGブロック以外）に遅延インポートが存在しないこと
- インポート時間がベースラインから著しく悪化していないこと（許容範囲：±10%）
- エンジン関連のテストがベースラインと同様にパスすること
echo "`n## Completed Steps (39-50)"
echo "Moved DataParseError, ResourceLoadError exceptions to top-level imports."
echo "Moved NATURAL_REGEN_HUNGER_THRESHOLD, NATURAL_REGEN_INTERVAL constants to top-level imports."
echo "Moved import time and import math to top-level imports."
echo "Removed corresponding lazy import lines from engine.py methods."


echo "`n## Completed Steps (51-70)"
echo "Moved InputHandler, TerritoryState, REGISTRY, GENERATOR, CharacterState, SkillEaterRegistry, create_husk, HuskInventoryComponent, StateMachine, ContextMenuBuilder, CombatManager, SECRET_REGISTRY, Item, MANAGER, SkillRewardManager, PetBondManager, FactionManager, MemoryFragmentGenerator, PersistenceManager, WorldNewsManager, TCODRenderer, LightingDrawCall, ParticleDrawCall, RenderContext, RenderSystem, TextRenderer, get_text_action, MovementAction, WaitAction, and feature_flags functions to top-level imports."
echo "Removed corresponding lazy import lines from engine.py methods."

