# 統合作業の残タスクと実装計画

## 現状のサマリ
- **feature/design-v2-impl ブランチ**: 230 passed / 1 skipped / xfail 0
- **origin/main との競合**: 解消済み（ours 戦略でマージ済み、feature/design-v2-impl ブランチに確保済み）
- **残存問題**:
  1. `test_crafting_system.py` - `CraftingSystem` クラスが存在しない
  2. `test_elemental_status_effects.py` - `STATUS_BURN` 等の定数欠如
  3. `test_reward_manager_integration.py` 等の一部テストが失敗

---

## Agent A: Constants + CraftingEngine ポート (Task T6)

### 担当範囲
1. **constants.py** - 不足定数の追加 (additive only)
2. **crafting_engine.py** 新規作成 - origin/main の CraftingSystem 移植
3. **test_crafting_system.py** - import 修正
3. **test_elemental_status_effects.py** - import 修正

### 作業手順

#### Step 1: constants.py に定数追加 (additive only)
```bash
# origin/main:naRou/constants.py から以下を抽出・追加
# - STATUS_BURN, STATUS_FREEZE 等 (line ~307-420)
# - FOOD_TAG_* 系 (line ~135)
# - CRAFT_SUCCESS_BASE, CRAFT_SUCCESS_SKILL_BONUS, CRAFT_CRIT_CHANCE (line ~150-152)
# - CRAFT_CRIT_CHANCE, CRAFT_SUCCESS_BASE, CRAFT_SUCCESS_SKILL_BONUS
# 元の関数/クラスを削除・変更せず、末尾に追記のみ
```

#### Step 2: crafting_engine.py 作成
```bash
# origin/main:naRou/systems/crafting_system.py (311行) をコピー
# ファイル名: crafting_engine.py (root 配置)
# import パスを現行レイアウトに合わせて書き換え:
# - from naRou.systems.item_generator → from item_generator
# - from naRou.systems.item_system → from item_system
# - from naRou.constants → from constants
# - from naRou.systems.item_system → from item_system
# - from data.generated.item.recipe → from data.generated.item.recipe
# - from naRou.ecs.entity → from ecs.entity
# - from naRou.constants → from constants
```

#### Step 3: テスト import 修正
```bash
# tests/test_crafting_system.py
# from crafting_system import CraftingSystem
# → from crafting_engine import CraftingSystem

# tests/test_elemental_status_effects.py
# from constants import STATUS_BURN, STATUS_FREEZE 等
# → from constants import STATUS_BURN, STATUS_FREEZE 等
# (constants.py に定数追加後、import 可能になる)
```

#### 実行確認
```bash
python3 -m pytest tests/test_crafting_system.py tests/test_elemental_status_effects.py -q --tb=short
python3 -m pytest tests/test_data_integrity.py tests/test_reachability.py -q --tb=no
ruff check --fix --unsafe-fixes crafting_engine.py constants.py tests/test_crafting_system.py tests/test_elemental_status_effects.py
```

---

## Agent B: 報酬/インベントリテスト トリアージ (Task T7)

### 担当範囲
4つのテストファイルのトリアージ:
1. `test_reward_manager_integration.py` - 報酬システム
2. `test_inventory_filter_sort_lock.py` - インベントリフィルタ/ソート/ロック
3. `test_pet_personality_system.py` - ペット性格システム
4. `test_item_enchantments_quality.py` - アイテム鑑定/品質

### 作業手順 (各ファイル個別判断)

#### 判断基準
| 判断 | 基準 | アクション |
|------|------|------------|
| **Port (additive)** | 不足機能が小さく、既存実装を壊さず追加可能 | root ファイルに追加実装 + テスト修正 |
| **Quarantine** | 既存実装の大幅書き換え必要 / 既存テストを壊すリスク | `tests/pending_remote_adaptation/` へ移動 + README 記録 |

### チェック対象ファイル
| ファイル | 期待される問題 | 推奨判断 |
|----------|---------------|----------|
| test_reward_manager_integration.py | RewardManager 機能不足? | Port (additive 可能性高) |
| test_inventory_filter_sort_lock.py | Inventory.filter/sort/lock メソッド不足 | Port (additive 可能性高) |
| test_pet_personality_system.py | PetPersonalitySystem クラス不足? | Quarantine (大幅実装必要) |
| test_item_enchantments_quality.py | ItemEnchantmentInstance 不足? | Port (additive 可能性) |

### 実行手順
```bash
# 1. 各テストを個別実行して失敗理由特定
python3 -m pytest tests/test_reward_manager_integration.py -v --tb=short -p no:cacheprovider 2>&1 | head -30
python3 -m pytest tests/test_inventory_filter_sort_lock.py -v --tb=short 2>&1 | head -30
python3 -m pytest tests/test_pet_personality_system.py -v --tb=short 2>&1 | head -30
python3 -m pytest tests/test_item_enchantments_quality.py -v --tb=short 2>&1 | head -30

# 2. 判断・実装
# Port の場合: root ファイルに機能追加、テスト import 修正
# Quarantine の場合: tests/pending_remote_adaptation/ へ移動 + README 記録

# 3. コア正常性確認
python3 -m pytest tests/test_economy.py tests/test_affix_system.py tests/test_identification.py -q --tb=no
ruff check --fix --unsafe-fixes <変更ファイル>
```

---

## 実行順序
1. **Agent A 先行** (Constants + CraftingEngine - 他の基盤)
2. **Agent B 並行** (テストトリアージ - 並列可能)
3. **統合確認**: 全コアスイート 230 passed 維持
3. **ルーフ修正**: 全ファイル ruff clean
4. **最終コミット**: 統合完了コミット

---

## 残存既知問題 (報告書記録済み - 解決不要)
- `test_enemy_intent_formation.py` 2件 - 旧仕様固定テスト (真実性設計と矛盾)
- インベントリ容量制限 (Step 63.1 skip)

---

## 次のアクション

Agent A: `python3 -m pytest tests/test_crafting_system.py tests/test_elemental_status_effects.py -v --tb=short` で失敗確認 → 実装開始

Agent B: 4テストファイルを個別実行 → 判断 → 実装/隔離