# Agent A 実装指示書: Constants + CraftingEngine ポート (Step 69)

## 現状
- branch: feature/design-v2-impl
- tests/test_crafting_system.py: `ImportError: cannot import name 'CraftingSystem' from 'crafting_system'`
- tests/test_elemental_status_effects.py: `STATUS_BURN` 等の定数不足
- 既存 crafting_system.py は空実装のみ (CraftingSystem クラスなし)

## 作業手順

### Step 1: constants.py に定数追加 (additive only)
```bash
# origin/main:naRou/constants.py から以下を抽出・追加:
# - STATUS_BURN, STATUS_FREEZE, STATUS_POISON, STATUS_PARALYSIS, STATUS_BLIND, STATUS_CONFUSION, STATUS_SLEEP, STATUS_SILENCE, STATUS_FEAR, STATUS_STUN (lines ~307-420)
# - FOOD_TAG_MEAT, FOOD_TAG_VEGETABLE, FOOD_TAG_FRUIT, FOOD_TAG_SEAFOOD, FOOD_TAG_GRAIN, FOOD_TAG_SEASONING, FOOD_TAG_MEDICINE (line ~135)
# - CRAFT_SUCCESS_BASE=70, CRAFT_SUCCESS_SKILL_BONUS=2, CRAFT_CRIT_CHANCE=0.05 (lines ~150-152)
```
- 元の関数/クラスを削除・変更せず、末尾に追記のみ
- バナー: `# --- Elemental status effects, food tags, craft constants (PR #8 integration) ---`

### Step 2: crafting_engine.py 作成 (repo root, NEW FILE)
- origin/main:naRou/systems/crafting_system.py (311行) をコピー
- import パスを現行レイアウトに合わせて書き換え:
  - from naRou.systems.item_generator → from item_generator
  - from naRou.systems.item_system → from item_system
  - from naRou.constants → from constants
  - from naRou.systems.item_system → from item_system
  - from data.generated.item.recipe → from data.generated.item.recipe
  - from naRou.ecs.entity → from ecs.entity
  - from naRou.constants → from constants
  - from naRou.systems.item_generator → from item_generator
  - from naRou.data_manager → from data_manager
- 保存先: crafting_engine.py (repo root)

### Step 3: テスト import 修正
- tests/test_crafting_system.py: `from crafting_system import CraftingSystem` → `from crafting_engine import CraftingSystem`
- tests/test_elemental_status_effects.py: `from constants import STATUS_BURN, STATUS_FREEZE, ...` (constants.py 更新後動作)

### 検証
```bash
python3 -m pytest tests/test_crafting_system.py tests/test_elemental_status_effects.py -q --tb=short
python3 -m pytest tests/test_data_integrity.py tests/test_reachability.py -q --tb=no
ruff check --fix --unsafe-fixes crafting_engine.py constants.py tests/test_crafting_system.py tests/test_elemental_status_effects.py
```

## 禁止事項
- 既存の crafting_system.py を変更しない
- 既存の crafting_system.py を削除しない
- 既存の関数/クラスを削除・変更しない
- 既存の constants.py の既存定義を変更しない
- reward_manager.py, item_system.py, tests/test_reward_manager_integration.py, tests/test_inventory_filter_sort_lock.py, tests/test_pet_personality_system.py, tests/test_item_enchantments_quality.py は触らない

## 報告事項
- 変更ファイル、テスト結果、未解決問題