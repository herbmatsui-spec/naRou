# Agent B 実装指示書: 報酬/インベントリ/ペット/鑑定テストのトリアージと移植/隔離

## 現状
- branch: feature/design-v2-impl
- 4つのテストファイルが失敗中 (Agent Aの作業完了後に検証済み)

## 対象テストファイル
1. `tests/test_reward_manager_integration.py` - 報酬システム
2. `tests/test_inventory_filter_sort_lock.py` - インベントリフィルタ/ソート/ロック
3. `tests/test_pet_personality_system.py` - ペット性格システム
4. `tests/test_item_enchantments_quality.py` - アイテム鑑定/品質

## 作業手順 (各ファイル個別判断)

### 判断基準
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

#### 1. 各テストを個別実行して失敗理由特定
```bash
python3 -m pytest tests/test_reward_manager_integration.py -v --tb=short -p no:cacheprovider 2>&1 | head -30
python3 -m pytest tests/test_inventory_filter_sort_lock.py -v --tb=short 2>&1 | head -30
python3 -m pytest tests/test_pet_personality_system.py -v --tb=short 2>&1 | head -30
python3 -m pytest tests/test_item_enchantments_quality.py -v --tb=short 2>&1 | head -30
```

#### 2. 判断・実装
- Port の場合: root ファイルに機能追加、テスト import 修正
- Quarantine の場合: tests/pending_remote_adaptation/ へ移動 + README 記録

#### 3. コア正常性確認
```bash
python3 -m pytest tests/test_economy.py tests/test_affix_system.py tests/test_identification.py -q --tb=no
ruff check --fix --unsafe-fixes <変更ファイル>
```

## 禁止事項
- 既存の reward_manager.py, item_system.py を大幅書き換えない
- tests/test_economy.py, tests/test_affix_system.py, tests/test_identification.py を壊さない
- 既存の tests/test_item_enchantments_quality.py は触らない

## 報告事項
- 各ファイルの判断 (Port/Quarantine)
- 変更ファイル、テスト結果、未解決問題