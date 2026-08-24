# メインクエスト非線形化・並行進行対応 実装計画書

## 1. 概要

### 目的
`MainQuest` に `prerequisite_quest_ids: list[str]` と `is_parallel: bool` を追加し、複数クエストの同時進行・分岐合流を可能にする。ワールドフェーズ移行条件も「全必須クエスト完了」から「特定クエスト完了 or 条件式」へ拡張する。

### 現状の問題
- `main_quests.yaml` は `next_quest_id` で単一の線形チェーン（prologue → awakening → exploration → confrontation）
- 並行クエスト（サイドストーリー、派閥クエスト等）がメインラインに組み込めない
- ワールドフェーズ移行が `next_quest_id` 連鎖の副作用としてのみ発生し、条件ベースで制御できない

### 移行後のメリット
- 複数の前提クエスト完了後に解放されるクエストが定義可能
- `is_parallel=true` で複数クエスト同時進行可能
- ワールドフェーズ移行条件を DSL で柔軟に記述可能
- 既存の CQCT (condition_dsl) と統一された条件システムで管理

---

## 2. データ構造変更

### 2.1 MainQuest フィールド追加

| フィールド名 | 型 | デフォルト | 説明 |
|------------|-----|----------|------|
| `prerequisite_quest_ids` | `list[str]` | `[]` | 解放に必要な前提クエストIDリスト（全て完了で解放） |
| `is_parallel` | `bool` | `False` | `True` の場合、他のクエストと同時進行可能 |
| `phase_unlock_condition` | `str` | `""` | ワールドフェーズ移行条件（DSL）。空なら `rewards.world_phase` 使用 |

### 2.2 既存フィールドの役割変更

| フィールド | 現状 | 移行後 |
|-----------|------|--------|
| `required_phase` | 必須（フェーズ名） | 任意。`unlock_condition` または `prerequisite_quest_ids` で代替可能 |
| `next_quest_id` | 単一ID | 非推奨。`next_quest_ids: list[str]` に移行予定（互換性維持） |
| `rewards.world_phase` | 完了時のフェーズ移行 | `phase_unlock_condition` で制御。互換性のため残す |

---

## 3. YAML 設計ガイドライン

### 3.1 基本構造

```yaml
main_quests:
  - quest_id: "prologue_01"
    title: "運命の始まり"
    required_phase: "BEGINNING"
    prerequisite_quest_ids: []  # 新規: 前提クエストなし
    is_parallel: false
    objectives: [...]
    rewards:
      gold: 100
    next_quest_id: "awakening_01"  # 互換性維持
    next_quest_ids: ["awakening_01", "side_story_01"]  # 新規: 複数次クエスト
    phase_unlock_condition: ""  # 新規: フェーズ移行条件DSL
    narrative_dag_id: "prologue_branching"

  - quest_id: "awakening_01"
    title: "目覚めの試練"
    required_phase: "AWAKENING"
    prerequisite_quest_ids: ["prologue_01"]  # 新規: prologue_01 完了必須
    is_parallel: false
    objectives: [...]
    rewards:
      gold: 1000
    next_quest_ids: ["exploration_01", "faction_intro_01"]
    phase_unlock_condition: "(completed awakening_01)"  # 新規
```

### 3.2 並行クエスト例

```yaml
  - quest_id: "faction_intro_01"
    title: "派閥への招待"
    required_phase: "AWAKENING"
    prerequisite_quest_ids: ["prologue_01"]
    is_parallel: true  # 並行進行可能
    objectives: [...]
    rewards:
      gold: 500
    next_quest_ids: ["faction_kingdom_01", "faction_church_01", "faction_shadow_01"]
    phase_unlock_condition: ""
```

### 3.3 分岐合流例

```yaml
  - quest_id: "confrontation_01"
    title: "最終決戦"
    required_phase: "CONFRONTATION"
    prerequisite_quest_ids: ["exploration_01", "faction_kingdom_02"]  # 両方必須
    is_parallel: false
    objectives: [...]
    rewards:
      gold: 10000
    next_quest_ids: ["ending_a", "ending_b", "ending_c"]
    phase_unlock_condition: "(and (completed exploration_01) (or (completed faction_kingdom_02) (completed faction_church_02) (completed faction_shadow_02)))"
```

---

## 4. 条件 DSL 拡張

### 4.1 新規演算子・関数

| 演算子/関数 | 構文 | 説明 |
|------------|------|------|
| `completed` | `(completed quest_id)` | 指定クエストが COMPLETED 状態か判定 |
| `active` | `(active quest_id)` | 指定クエストが ACTIVE 状態か判定 |
| `available` | `(available quest_id)` | 指定クエストが AVAILABLE 状態か判定 |
| `phase` | `(phase "PHASE_NAME")` | 現在のワールドフェーズ判定（既存互換） |

### 4.2 EvaluationContext への追加実装

`EvaluationContext.resolve()` で以下のキーを解決：
- `quest.status.prologue_01` → "COMPLETED"/"ACTIVE"/"LOCKED" 等
- `quest.completed.prologue_01` → true/false
- `world_state.phase` → 現在のフェーズ名

---

## 5. 実装手順

### Phase 1: データモデル拡張
1. `MainQuest` に `prerequisite_quest_ids`, `is_parallel`, `phase_unlock_condition`, `next_quest_ids` 追加
2. `to_dict()` / `from_dict()` 更新
3. `build_condition_trees()` で `phase_unlock_condition` パース追加

### Phase 2: 解放判定ロジック更新
1. `MainQuest.check_unlock()` を拡張：
   - `unlock_condition` (CQCT) 最優先
   - 次に `prerequisite_quest_ids` 全完了チェック
   - フォールバック: `required_phase` チェック
2. `QuestStatus` 参照用ヘルパー追加

### Phase 3: アクティブ化ロジック更新
1. `_try_activate_next_quest()` → `_try_activate_available_quests()` に拡張
2. `is_parallel=true` のクエストは同時に ACTIVE にできる
3. 単一 `active_quest_id` → `active_quest_ids: set[str]` に変更

### Phase 4: 完了処理・フェーズ移行更新
1. `_complete_quest()` で `next_quest_ids` 全てを AVAILABLE に
2. `phase_unlock_condition` 評価 → 満たす場合 `world_phase` 移行
3. 従来の `rewards.world_phase` はフォールバックとして維持

### Phase 5: データ移行
1. `main_quests.yaml` を新形式に書き換え
2. 既存線形チェーンを `prerequisite_quest_ids` 形式に変換
3. サンプル並行クエスト追加

### Phase 6: テスト・検証
1. 既存テスト通過確認
2. 並行クエスト同時進行テスト
3. 分岐合流テスト
4. フェーズ移行条件テスト

---

## 6. 互換性・リスク対策

| リスク | 対策 |
|-------|------|
| 既存セーブデータの `active_quest_id` 単一値 | ロード時に `active_quest_ids = {active_quest_id}` に変換 |
| `next_quest_id` 単一フィールド参照箇所 | `next_quest_ids` が空なら `next_quest_id` を参照する互換ロジック |
| `required_phase` 必須前提のコード | `check_unlock()` でフォールバック維持 |
| パフォーマンス（複数クエスト評価） | `auto_evaluate` で制御、必要時のみ評価 |

---

## 7. 完了基準

- [ ] `MainQuest` に新フィールドが追加され、YAML で読み書きできる
- [ ] `prerequisite_quest_ids` による前提クエスト判定が動作する
- [ ] `is_parallel=true` で複数クエスト同時 ACTIVE 可能
- [ ] `next_quest_ids` で複数次クエスト指定可能
- [ ] `phase_unlock_condition` でフェーズ移行制御可能
- [ ] 既存線形クエストが新形式で正常動作する
- [ ] 既存テスト（`test_quest_paranoid_condition_tree.py` 等）が全て通る

---

## 8. スケジュール見積

| Phase | 工数目安 |
|-------|---------|
| Phase 1 | 1.0h |
| Phase 2 | 0.8h |
| Phase 3 | 0.8h |
| Phase 4 | 0.5h |
| Phase 5 | 0.5h |
| Phase 6 | 0.5h |
| **合計** | **約 4.1h** |