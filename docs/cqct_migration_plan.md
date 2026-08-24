# CQCT 完全移行 実装計画書

## 1. 概要

### 目的
`QuestObjective` の旧式フィールド（`target_type`, `target_id`, `required_count`, `current_count`）を非推奨化し、全ての目的を **CQCT (Quest Condition AST)** の DSL (`condition_dsl`) 記述に統一する。

### 現状の問題
- 旧式（カウントベース）と CQCT（条件ツリー）が混在し、保守コストが高い
- `update_progress()` で両経路を処理しておりバグの温床
- 新規クエスト追加時にどちらを使うか迷う

### 移行後のメリット
- 単一の評価パス（`condition_tree.evaluate(context)`）で統一
- 複合条件（AND/OR/NOT/XOR、比較演算子、述語）が自然に表現可能
- 既存のパーサー・評価器をそのまま活用可能

---

## 2. 移行対象

### 2.1 データファイル
| ファイル | 現状 | 移行後 |
|---------|------|--------|
| `data/main_quests.yaml` | 4クエスト、5目的中1目的のみDSL | 全目的を `condition_dsl` に統一 |

### 2.2 コードファイル
| ファイル | 変更箇所 |
|---------|---------|
| `naRou/systems/main_quest_system.py` | `QuestObjective`, `MainQuestSystem.update_progress`, `_create_default_quests`, シリアライズ |

---

## 3. DSL 設計ガイドライン

### 3.1 キー命名規則（EvaluationContext.resolve 対応）

| カテゴリ | キー例 | 説明 |
|---------|-------|------|
| キルカウント | `player.kill_counts.goblin` | モンスター討伐数 |
| 採取カウント | `player.collect_counts.herb` | アイテム採取数 |
| 訪問フラグ | `player.visited_locations.village_elder` | 場所訪問済み（真偽値） |
| ストーリ変数 | `flags.slew_guardian` | フラグ（`flags.` プレフィックス） |
| プレイヤー基本 | `player.level`, `player.gold`, `player.job` | レベル、ゴールド、職業 |
| スキル | `player.skills.fire_mastery.level` | スキルレベル |
| インベントリ | `player.inventory.sword` | アイテム所持（`has`演算子で判定） |

### 3.2 目的タイプ別 DSL 変換パターン

| 旧式タイプ | DSL 変換例 |
|-----------|-----------|
| `target_type: "kill", target_id: "goblin", required_count: 5` | `(>= player.kill_counts.goblin 5)` |
| `target_type: "visit", target_id: "village_elder", required_count: 1` | `(has player.visited_locations.village_elder)` |
| `target_type: "collect", target_id: "world_fragment", required_count: 3` | `(>= player.collect_counts.world_fragment 3)` |
| `target_type: "variable", target_id: "prove_resolve", required_count: 1` | 既存DSLをそのまま使用 |

### 3.3 既存クエストの変換マッピング

#### prologue_01
- `talk_elder` (visit, village_elder, 1) → `(has player.visited_locations.village_elder)`

#### awakening_01
- `kill_guardian` (kill, ancient_guardian, 1) → `(>= player.kill_counts.ancient_guardian 1)`
- `collect_fragment` (collect, world_fragment, 1) → `(>= player.collect_counts.world_fragment 1)`

#### exploration_01
- `collect_fragments_more` (collect, world_fragment, 3) → `(>= player.collect_counts.world_fragment 3)`
- `prove_resolve` (variable, prove_resolve, 1) → 既存DSL `(or (>= player.level 5) (has flags.slew_guardian))` を維持

---

## 4. 実装手順

### Phase 1: データ移行（main_quests.yaml）
1. 全 `objectives` から `target_type`, `target_id`, `required_count` を削除
2. 全 `objectives` に `condition_dsl` を追加（上記変換マッピングに従う）
3. `auto_evaluate: true` を明示（デフォルト値だが明示推奨）

### Phase 2: QuestObjective クラス改修
1. **削除フィールド**: `target_type`, `target_id`, `required_count`, `current_count`
2. **保持フィールド**: `objective_id`, `description`, `condition_tree`, `condition_dsl`, `auto_evaluate`, `is_completed`, `narrative_dag_id`, `narrative_started`
3. **削除メソッド**: `update()` （旧式カウント更新）
4. **変更メソッド**: 
   - `evaluate()` → `condition_tree` 必須化（Noneならエラー）
   - `to_dict()` / `from_dict()` → 旧式フィールド除外
   - `build_condition_tree()` → `condition_dsl` 必須チェック追加

### Phase 3: MainQuestSystem.update_progress 改修
1. 旧式分岐（`elif obj.target_type == event_type:`）を削除
2. 全目的を `obj.evaluate(context)` で統一評価
3. 進捗ログ: `is_completed` 変化時のみ「達成！」、それ以外は進捗表示なし（DSLでは中間進捗が概念的に存在しないため）

### Phase 4: デフォルトクエスト更新
1. `_create_default_quests()` の `QuestObjective` 生成を DSL 版に書き換え

### Phase 5: テスト・検証
1. 既存テスト通過確認
2. 手動動作確認: 各クエストの目的が正しく評価されること

---

## 5. 互換性・リスク対策

| リスク | 対策 |
|-------|------|
| 既存セーブデータの `current_count` が読めなくなる | `from_dict()` で `current_count` を無視（`is_completed` のみ復元） |
| 条件ツリー構築失敗時のクラッシュ | `build_condition_tree()` で例外をキャッチしログ出力、フォールバックなし（設計上必須） |
| パフォーマンス（毎フレーム評価） | `auto_evaluate` で制御、必要時のみ評価。キャッシュ（`EvaluationContext._property_cache`）活用 |

---

## 6. 完了基準

- [ ] `main_quests.yaml` 全目的が `condition_dsl` のみで定義されている
- [ ] `QuestObjective` に旧式フィールドが存在しない
- [ ] `update_progress()` が CQCT のみで動作する
- [ ] 既存テスト（`test_quest_paranoid_condition_tree.py` 等）が全て通る
- [ ] 手動プレイで全メインクエストが正常進行する

---

## 7. スケジュール見積

| Phase | 工数目安 |
|-------|---------|
| Phase 1 | 0.5h |
| Phase 2 | 1.0h |
| Phase 3 | 0.5h |
| Phase 4 | 0.3h |
| Phase 5 | 0.5h |
| **合計** | **約 2.8h** |