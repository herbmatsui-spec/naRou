# 巨大ファイル分割 実装計画（systems_core / procedural_quest_generator）

優先度: 高
対象: `naRou/systems/systems_core.py` (26KB/688行) と `naRou/procedural_quest_generator.py` (56KB/1352行)
目的: 責務ごとに小ファイルへ分割し、保守性・開発効率を向上させる。

---

## 0. 重要な事前発見（実装前に読む）

1. **`naRou/systems.py`（ルート）は死んだコードです。**
   Python は `import naRou.systems` のとき `naRou/systems/`（パッケージ）を優先し、
   ルートの `naRou/systems.py` は「到達不能」になっています。
   実際の実装は `naRou/systems/systems_core.py` にあり、`naRou/systems/__init__.py` が
   `from .systems_core import *` で再公開しています。
   → 分割の真のターゲットは `naRou/systems/systems_core.py` です。

2. **本リポジトリには既に「分割パターン」があります。**
   実モジュールは `naRou/systems/<name>.py` にあり、ルートの `naRou/<name>.py` は
   1行の転送用シム（`from naRou.systems.<name> import *`）です。
   この慣習に合わせます。

3. **潜在バグを同時に修正します。**
   `emergency_quest_injector.py:23` は `PROCEDURAL_QUEST_GENERATOR` を import していますが、
   元ファイルにはその名前が存在しません（実行時 NameError）。
   新パッケージで `PROCEDURAL_QUEST_GENERATOR = GENERATOR` を定義し修正します。

4. **不変条件（全ステップで守る）**
   どのステップ終了時も `from naRou.systems import <全シンボル>` と
   `from naRou.procedural_quest_generator import <全シンボル>` が成功すること。
   そのため `__init__.py` には「新サブモジュールの import」を **既存の systems_core import より前** に置き、
   未移動のシンボルは systems_core が補完するようにします。

---

## フェーズ0: 準備とベースライン（ステップ 1-5）

**ステップ 1** — 作業ブランチを作成。
```powershell
cd E:\narou4; git checkout -b refactor/split-large-files
```

**ステップ 2** — ベースライン動作確認（後で比較するため）。
```powershell
cd E:\narou4; python -c "import naRou.systems, naRou.procedural_quest_generator; print('OK baseline')"
```

**ステップ 3** — 既存テストのベースラインを記録。
```powershell
cd E:\narou4; pytest -q 2>&1 | Tee-Object -Variable baseline
```
（合格数をメモする）

**ステップ 4** — 影響範囲（importer）をファイルに書き出して安全確認用に保持。
```powershell
cd E:\narou4
Select-String -Path naRou -Pattern 'from naRou\.systems import|from naRou import systems|naRou\.systems\.' -Recurse |
  Out-File -Encoding utf8 refactor_systems_importers.txt
Select-String -Path naRou -Pattern 'procedural_quest_generator' -Recurse |
  Out-File -Encoding utf8 refactor_pqg_importers.txt
```

**ステップ 5** — 新パッケージ用ディレクトリと空の `__init__.py` を作成。
```powershell
cd E:\narou4; New-Item -ItemType Directory -Force -Path naRou/quest_generation | Out-Null
Set-Content -Encoding utf8 naRou/quest_generation/__init__.py '"""Quest generation package.""""
'
```

---

## フェーズ1: systems_core.py の分割（ステップ 6-37）

### 1-A. combat_core.py（定数 + 小データクラス）

**ステップ 6** — `naRou/systems/combat_core.py` を作成し、ヘッダと import を書く。
内容:
```python
"""Combat-related constants and small data classes (status effects, resistances, aggro)."""
from __future__ import annotations
import logging
logger = logging.getLogger(__name__)
from naRou.constants import Element
```

**ステップ 7** — `systems_core.py` の行 23-30（STATUS_POISON ～ STATUS_RETURN）を `combat_core.py` にコピー。

**ステップ 8** — `systems_core.py` の行 33-36（FACTION_PLAYER ～ FACTION_GUARD）を `combat_core.py` にコピー。

**ステップ 9** — `systems_core.py` の行 40-47（`class StatusEffect`）を `combat_core.py` にコピー。

**ステップ 10** — `systems_core.py` の行 49-70（`class ResistanceSet`）を `combat_core.py` にコピー。

**ステップ 11** — `systems_core.py` の行 72-85（`class AggroList`）を `combat_core.py` にコピー。

**ステップ 12** — `naRou/systems/__init__.py` を編集し、既存の `from .systems_core import *` の **上** に追加。
```python
from .combat_core import *
from .systems_core import *
```

**ステップ 13** — 検証。
```powershell
cd E:\narou4; python -c "from naRou.systems import StatusEffect, ResistanceSet, AggroList, STATUS_POISON, FACTION_PLAYER, FACTION_GUARD; print('OK 13')"
```

### 1-B. combat_system.py（CombatSystem クラス）

**ステップ 14** — `naRou/systems/combat_system.py` を作成。ヘッダ + import をコピー（systems_core の行 6-21 相当）。
`from naRou.systems import` 系は相対 import に変える：
```python
from __future__ import annotations
import logging, random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from naRou.constants import Element
from naRou import combat
if TYPE_CHECKING:
    from naRou.ecs.entity import Entity
    from naRou.item_system import Item
from .combat_core import StatusEffect, ResistanceSet, AggroList, STATUS_BLEEDING, STATUS_PARALYSIS
```

**ステップ 15** — `systems_core.py` の行 87-507（`class CombatSystem` 全体）を `combat_system.py` にコピー。

**ステップ 16** — `__init__.py` に `from .combat_system import *` を `from .systems_core import *` の上に追加（combat_core の下で可）。
```python
from .combat_core import *
from .combat_system import *
from .systems_core import *
```

**ステップ 17** — 検証。
```powershell
cd E:\narou4; python -c "from naRou.systems import CombatSystem; print('OK 17')"
```

### 1-C. survival_system.py（SurvivalSystem クラス）

**ステップ 18** — 現在のスタブ `naRou/systems/survival_system.py`（216バイト）を確認し、ただのスタブであることを記録（中身を Read）。

**ステップ 19** — `naRou/systems/survival_system.py` を上書き。ヘッダ + import：
```python
"""Survival system: hunger, sleep, karma, ether disease."""
from __future__ import annotations
import random
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from naRou.ecs.entity import Entity
    from naRou.item_system import Item
```
その後 `systems_core.py` の行 509-565（`class SurvivalSystem`）をコピー。

**ステップ 20** — `__init__.py` に `from .survival_system import *` を追加（systems_core の上）。

**ステップ 21** — 検証。
```powershell
cd E:\narou4; python -c "from naRou.systems import SurvivalSystem; print('OK 21')"
```

### 1-D. quest.py（Quest データクラス）

**ステップ 22** — `naRou/systems/quest.py` を作成し、`systems_core.py` の行 567-575（`class Quest`）をコピー。

**ステップ 23** — `__init__.py` に `from .quest import *` を追加。

**ステップ 24** — 検証。
```powershell
cd E:\narou4; python -c "from naRou.systems import Quest; print('OK 24')"
```

### 1-E. monster_preset.py（MonsterPreset クラス）

**ステップ 25** — `naRou/systems/monster_preset.py` を作成。import：
```python
from __future__ import annotations
from naRou.config_manager import DataCache
from naRou.ecs.entity import Attributes, Entity
from .combat_core import FACTION_MONSTER, AggroList, ResistanceSet
```
その後 `systems_core.py` の行 577-688（`class MonsterPreset`）をコピー。

**ステップ 26** — `__init__.py` に `from .monster_preset import *` を追加。

**ステップ 27** — 検証。
```powershell
cd E:\narou4; python -c "from naRou.systems import MonsterPreset; print('OK 27')"
```

### 1-F. systems_core.py からの削除（最後にまとめて）

**ステップ 28** — `systems_core.py` から行 23-85（定数 + StatusEffect/ResistanceSet/AggroList）を削除。

**ステップ 29** — 検証（systems_core はまだ CombatSystem 等を持つので壊れない）。
```powershell
cd E:\narou4; python -c "from naRou.systems import StatusEffect, CombatSystem; print('OK 29')"
```

**ステップ 30** — `systems_core.py` から `class CombatSystem`（行 87-507）を削除。

**ステップ 31** — `systems_core.py` から `class SurvivalSystem`（行 509-565）を削除。

**ステップ 32** — `systems_core.py` から `class Quest`（行 567-575）を削除。

**ステップ 33** — `systems_core.py` から `class MonsterPreset`（行 577-688）を削除。

**ステップ 34** — `systems_core.py` が空（または import のみ）になったので、`__init__.py` から `from .systems_core import *` を削除。
最終 `__init__.py`:
```python
"""Systems package."""
from .combat_core import *
from .combat_system import *
from .survival_system import *
from .quest import *
from .monster_preset import *
```

**ステップ 35** — `naRou/systems/systems_core.py` を削除。

**ステップ 36** — 検証（全シンボル）。
```powershell
cd E:\narou4; python -c "from naRou.systems import CombatSystem, SurvivalSystem, Quest, MonsterPreset, StatusEffect, ResistanceSet, AggroList, STATUS_POISON, FACTION_GUARD; print('OK 36')"
```

**ステップ 37** — importer スモーク（systems を使う主要ファイルが import できるか）。
```powershell
cd E:\narou4; python -c "import naRou.data_manager, naRou.game_state, naRou.interfaces, naRou.core.world_state_manager, naRou.packages.character.package, naRou.packages.gameplay.package, naRou.player_actions; print('OK 37')"
```

---

## フェーズ2: 死んだルート systems.py の削除（ステップ 38-41）

**ステップ 38** — ルート `naRou/systems.py` が誰からもパスで直接 import されていないことを確認（refactor_systems_importers.txt を見直し、該当なしを確認）。

**ステップ 39** — ルート `naRou/systems.py` を削除（パッケージにシャドウされて到達不能なため安全）。
※もし何らかのツールがファイルパスで直接ロードする場合は、同日付で
`from naRou.systems import *` というシムに置き換える。

**ステップ 40** — 検証。
```powershell
cd E:\narou4; python -c "import naRou.systems; print(naRou.systems.__file__); print('OK 40')"
```
（`__file__` が `naRou/systems/__init__.py` であることを確認）

**ステップ 41** — 古い `__pycache__` を削除して迷走を防ぐ。
```powershell
cd E:\narou4; Remove-Item -Recurse -Force naRou/__pycache__/systems.* naRou/systems/__pycache__/systems_core* 2>$null; echo done
```

---

## フェーズ3: procedural_quest_generator.py の分割（ステップ 42-57）

新パッケージ `naRou/quest_generation/` を作成。ルートの `naRou/procedural_quest_generator.py` は最後に転送シムにする。

### 3-A. models.py（データクラス群）

**ステップ 42** — `naRou/quest_generation/models.py` を作成。ヘッダ + import：
```python
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
import yaml
from typing_extensions import Self
```

**ステップ 43** — 行 28-86（`def _get_enemy_name_map`）を `models.py` にコピー（データ補助）。

**ステップ 44** — 順にコピー：QuestArchetype(87-100), DifficultyTier(101-113), RewardTable(114-126),
StageSetting(127-140), NPCQuestTheme(141-151), QuestObjectiveSpec(152-187), GeneratedQuest(188-261)。

**ステップ 45** — 検証（サブモジュール単体）。
```powershell
cd E:\narou4; python -c "import naRou.quest_generation.models as m; print(hasattr(m,'GeneratedQuest'), hasattr(m,'QuestArchetype')); print('OK 45')"
```

### 3-B. registry.py（QuestGenerationRegistry）

**ステップ 46** — `naRou/quest_generation/registry.py` を作成。
```python
from __future__ import annotations
import logging, random, yaml
from typing import Any
from .models import _get_enemy_name_map, QuestArchetype, DifficultyTier, RewardTable, StageSetting, NPCQuestTheme, QuestObjectiveSpec, GeneratedQuest
```
その後行 262-444（`class QuestGenerationRegistry`）をコピー。

**ステップ 47** — 検証。
```powershell
cd E:\narou4; python -c "import naRou.quest_generation.registry as r; print(hasattr(r,'QuestGenerationRegistry')); print('OK 47')"
```

### 3-C. generator.py（ProceduralQuestGenerator）

**ステップ 48** — `naRou/quest_generation/generator.py` を作成。
```python
from __future__ import annotations
import logging, random, yaml
from typing import TYPE_CHECKING, Any
from .models import (QuestArchetype, DifficultyTier, RewardTable, StageSetting,
                     NPCQuestTheme, QuestObjectiveSpec, GeneratedQuest)
from .registry import QuestGenerationRegistry
if TYPE_CHECKING:
    from naRou.ecs.entity import Entity
```
その後行 445-1155（`class ProceduralQuestGenerator` 全体）をコピー。

**ステップ 49** — 検証。
```powershell
cd E:\narou4; python -c "import naRou.quest_generation.generator as g; print(hasattr(g,'ProceduralQuestGenerator')); print('OK 49')"
```

### 3-D. manager.py（ProceduralQuestManager + 補助関数）

**ステップ 50** — `naRou/quest_generation/manager.py` を作成。
```python
from __future__ import annotations
import logging
from typing import TYPE_CHECKING, Any
from .models import GeneratedQuest
from .generator import ProceduralQuestGenerator
if TYPE_CHECKING:
    from naRou.ecs.entity import Entity
    from naRou.engine.engine import Engine
```
その後行 1155-1177（`def _norm_target`, `def _target_matches`）をコピー。

**ステップ 51** — 行 1178-1352（`class ProceduralQuestManager`）を `manager.py` にコピー。

**ステップ 52** — 検証。
```powershell
cd E:\narou4; python -c "import naRou.quest_generation.manager as m; print(hasattr(m,'ProceduralQuestManager')); print('OK 52')"
```

### 3-E. パッケージ公開 + シム化

**ステップ 53** — `naRou/quest_generation/__init__.py` を書き換え：
```python
"""Quest generation package (split from procedural_quest_generator.py)."""
from .models import *
from .registry import *
from .generator import *
from .manager import *
from .registry import QuestGenerationRegistry
from .generator import ProceduralQuestGenerator
from .manager import ProceduralQuestManager

REGISTRY = QuestGenerationRegistry()
GENERATOR = ProceduralQuestGenerator(REGISTRY)
PROCEDURAL_QUEST_GENERATOR = GENERATOR  # 後方互換エイリアス（潜在バグ修正）
```

**ステップ 54** — 検証。
```powershell
cd E:\narou4; python -c "from naRou.quest_generation import REGISTRY, GENERATOR, PROCEDURAL_QUEST_GENERATOR, ProceduralQuestGenerator, GeneratedQuest, ProceduralQuestManager; print('OK 54')"
```

**ステップ 55** — ルート `naRou/procedural_quest_generator.py` を転送シムに上書き（git履歴は残る）：
```python
"""Forwarding shim for naRou.quest_generation.

Split into naRou/quest_generation/{models,registry,generator,manager}.py.
"""
from naRou.quest_generation import *  # noqa: F401,F403
from naRou.quest_generation import REGISTRY, GENERATOR, PROCEDURAL_QUEST_GENERATOR  # noqa: F401
```

**ステップ 56** — 検証（旧名でも全シンボル取得可能）。
```powershell
cd E:\narou4; python -c "from naRou.procedural_quest_generator import REGISTRY, GENERATOR, PROCEDURAL_QUEST_GENERATOR, ProceduralQuestGenerator, GeneratedQuest, ProceduralQuestManager; print('OK 56')"
```

**ステップ 57** — importer スモーク。
```powershell
cd E:\narou4; python -c "import naRou.engine.engine, naRou.emergency_quest_injector, naRou.ui.journal_ui, naRou.packages.social.package; print('OK 57')"
```

---

## フェーズ4: 検証・クリーンアップ・再利用（ステップ 58-72）

**ステップ 58** — メソッド数パリティ確認（移動でロジックを落としていないか）。
```powershell
cd E:\narou4; python -c "
import naRou.systems as s, naRou.quest_generation.generator as g, naRou.quest_generation.manager as m
print('CombatSystem methods:', len([x for x in dir(s.CombatSystem) if not x.startswith('__')]))
print('ProceduralQuestGenerator methods:', len([x for x in dir(g.ProceduralQuestGenerator) if not x.startswith('__')]))
print('ProceduralQuestManager methods:', len([x for x in dir(m.ProceduralQuestManager) if not x.startswith('__')]))
"
```

**ステップ 59** — テストスイート再実行しステップ3のベースラインと比較。
```powershell
cd E:\narou4; pytest -q 2>&1 | Tee-Object -Variable after
```
（合格数が減っていないことを確認）

**ステップ 60** — ゲーム起動スモーク（利用可能なら）。
```powershell
cd E:\narou4; python -c "from naRou.engine.engine import Engine; print('Engine import OK')"
```

**ステップ 61** — 残存参照の確認：`systems_core` や旧パスを直接参照していないか grep。
```powershell
cd E:\narou4; Select-String -Path naRou -Pattern 'systems_core|systems\.CombatSystem|\.combat_system' -Recurse
```
（問題なければ空）

**ステップ 62** — 不要な `__pycache__` を再削除。
```powershell
cd E:\narou4; Remove-Item -Recurse -Force naRou/__pycache__/procedural_quest_generator* naRou/quest_generation/__pycache__ 2>$null; echo done
```

**ステップ 63** — 新レイアウトを `AGENTS.md`（なければ `README.md`）に追記：
「`naRou/systems/` は責務別サブモジュールに分割済み。巨大クラスは `naRou/systems/<責務>.py` へ。
`naRou/procedural_quest_generator.py` は `naRou/quest_generation/` への転送シム。」

**ステップ 64** — `CHANGELOG.md` に refactor エントリを追加（日付・対象・効果）。

**ステップ 65** — lint/typecheck を実行（設定されていれば）。
```powershell
cd E:\narou4; ruff check naRou/systems naRou/quest_generation 2>&1 | Select-Object -First 30
```

**ステップ 66** — 全 importer ファイルの最終 import テスト（ステップ4のリストを網羅）。
```powershell
cd E:\narou4; python -c "
import naRou.data_manager, naRou.entity_renderer, naRou.core.world_state_manager, naRou.game_state, naRou.interfaces, naRou.player_actions, naRou.engine.engine, naRou.emergency_quest_injector, naRou.ui.journal_ui, naRou.packages.social.package, naRou.packages.gameplay.package, naRou.packages.character.package
print('OK all importers')
"
```

**ステップ 67** — diff レビュー（ロジック欠落がないか目視）。
```powershell
cd E:\narou4; git status --short; git diff --stat
```

**ステップ 68** — （ユーザーが求めた場合のみ）コミット。
```powershell
cd E:\narou4; git add -A; git commit -m "refactor: split systems_core.py and procedural_quest_generator.py into responsibility-based modules"
```

---

## 付録: 同じパターンを他の巨大ファイルへ適用する手順（再利用）

以下の要領で、他の 15KB+ ファイル（例: `engine.py` 109KB, `skill_eater_*` 各 60-80KB,
`ecs/entity.py` 59KB, `web_server.py` 47KB など）も同様に分割できる。

1. クラス/責務ごとに `naRou/<domain>/<責務>.py` サブパッケージを作成。
2. 各クラスをサブモジュールへコピー（import は絶対→相対に調整）。
3. `<domain>/__init__.py` で `from .<責務> import *` を列挙。
4. 元ファイルを `from naRou.<domain> import *` の転送シムに置き換え（後方互換）。
5. 各ステップで `python -c "import <module>"` 検証。

注意: `engine.py`(2664行) のような極大ファイルは、本計画の「1クラス=1ステップ」を
20-30 クラス分繰り返すだけで同手順で分割可能。低性能LLM向けには「1ファイルあたり 1-72 ステップ」
のブロックを独立Issueとして発行することを推奨。
