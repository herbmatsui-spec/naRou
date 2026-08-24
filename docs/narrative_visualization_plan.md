# ナラティブ分岐の永続的影響可視化 実装計画書

## 1. 概要

### 目的
- `NarrativeState.history` に選択肢テキスト・分岐理由・主要報酬を記録し、後から「どの分岐を選んだか」を確認可能にする
- ジャーナルUIで「運命の分岐点」タイムライン表示を追加
- `StoryEnding.unlock_conditions` を DSL 対応にし、複数エンディングの解放条件をクエスト完了時以外（好感度/派閥/カルマ等）でも判定可能にする

### 現状の問題
- `NarrativeState.history` はノードIDのみ記録（`list[str]`）
- 選択肢テキスト・理由・報酬が失われ、後から振り返り不可
- ジャーナルUIにナラティブ分岐履歴の表示がない
- `StoryEnding.unlock_conditions` は簡易文字列マッチングのみ（`has_flag:`、`karma_good_N` 等）で DSL 非対応

### 改善後のメリット
- プレイヤーが自分の選択の歴史を「運命の分岐点」として振り返り可能
- 選択の結果（報酬・フラグ・長期効果）が明確に記録される
- エンディング解放条件が CQCT DSL で統一的に記述可能（`(and (>= player.faction_rep.kingdom 50) (has flags.spared_cubs))` 等）

---

## 2. データ構造変更

### 2.1 NarrativeState.history の拡張

**現状**: `history: list[str]` （ノードIDのみ）

**改善**: `history: list[HistoryEntry]` （リッチな履歴エントリ）

```python
@dataclass
class HistoryEntry:
    """ナラティブ履歴エントリ"""
    node_id: str                    # ノードID
    node_title: str                 # ノードタイトル
    node_type: str                  # ノードタイプ (START/CHOICE/EVENT/END 等)
    timestamp: str                  # ISO8601形式タイムスタンプ
    # 選択肢の場合のみ
    choice_text: str = ""           # 選択したテキスト
    choice_reason: str = ""         # 分岐理由（条件式や説明）
    # 結果
    immediate_rewards: dict = field(default_factory=dict)      # 即時報酬
    long_term_effects: dict = field(default_factory=dict)      # 長期効果
    flags_set: list[str] = field(default_factory=list)         # 設定されたフラグ
    flags_cleared: list[str] = field(default_factory=list)     # クリアされたフラグ
    # 到達時のコンテキストスナップショット（任意）
    karma_at_choice: int = 0
    faction_rep_snapshot: dict = field(default_factory=dict)
```

### 2.2 StoryEnding.unlock_conditions の DSL 対応

**現状**: 簡易文字列リスト（`["has_flag:spared_cubs", "karma_good_50"]`）

**改善**: DSL 文字列リスト（`["(has flags.spared_cubs_resolved)", "(>= player.karma 50)"]`）

既存の `_check_condition()` を CQCT パーサー・評価器に置き換え。

---

## 3. YAML データ設計

### 3.1 story_endings.yaml (DSL対応版)

```yaml
story_endings:
  goblin_peace_bringer:
    id: "goblin_peace_bringer"
    name: "ゴブリンの和平使者"
    description: "武力による殲滅ではなく対話と共存を選び..."
    unlock_conditions:
      - "(has flags.spared_cubs_resolved)"
      - "(>= player.karma 50)"
      - "(or (>= player.faction_rep.kingdom 30) (>= player.faction_rep.church 30))"
    ending_scene: "scene_peace_banquet"
    rewards:
      title: "peace_envoy"
      gold: 50000
      item: "pendant_of_unity"

  ruthless_slayer_conqueror:
    id: "ruthless_slayer_conqueror"
    name: "冷徹なる殲滅覇者"
    description: "一片の慈悲も無く全ての脅威を滅ぼし尽くし..."
    unlock_conditions:
      - "(has flags.ruthless_extermination_resolved)"
      - "(>= player.kill_counts.total 500)"
      - "(<= player.karma -50)"
    ending_scene: "scene_iron_reign"
    rewards:
      title: "absolute_conqueror"
      gold: 100000
      item: "crown_of_domination"

  # 新規: 派閥別エンディング
  kingdom_loyalist:
    id: "kingdom_loyalist"
    name: "王国の忠臣"
    unlock_conditions:
      - "(has flags.faction_kingdom)"
      - "(>= player.faction_rep.kingdom_garde 100)"
      - "(completed confrontation_01)"
```

---

## 4. 実装手順

### Phase 1: データ構造拡張 (`narrative_executor.py`)

1. **`HistoryEntry` データクラス追加**
   - 上記フィールド定義
   - `to_dict()` / `from_dict()` 実装

2. **`NarrativeState.history` 型変更**
   - `list[str]` → `list[HistoryEntry]`
   - 既存セーブ互換: `from_dict()` で旧形式（文字列リスト）を検出し自動変換

3. **`NarrativeState.to_dict()` / `from_dict()` 更新**

### Phase 2: 履歴記録ロジック実装

1. **`make_choice()` での履歴エントリ作成**
   - 選択前のノード情報、選択肢テキスト、条件式を取得
   - `apply_choice_consequence()` 実行後の報酬・効果を取得
   - `HistoryEntry` 作成し `state.history` に追加

2. **自動遷移（AUTO/CONDITION_TRUE）も履歴に記録**
   - `_execute_transition()` / `_apply_auto_transitions()` でイベントノード通過時も記録

3. **タイムスタンプ生成**
   - `datetime.now().isoformat()` またはゲーム内時間（WorldStateManager経由）

### Phase 3: エンディング解放条件 DSL 対応

1. **`check_ending_unlock()` 書き換え**
   - 旧 `_check_condition()` を削除
   - `parse_condition()` + `evaluate()` で DSL 評価
   - `EvaluationContext` にクエストシステム・プレイヤー状態を渡す

2. **`StoryEnding` クラス拡張（任意）**
   - `unlock_conditions: list[str]` のまま維持（中身がDSLに）

### Phase 4: ジャーナルUI 追加 (`journal_ui.py`)

1. **新セクション「【運命の分岐点】」追加**
   - アクティブなナラティブ状態取得
   - `state.history` から `HistoryEntry` を読み取り表示

2. **表示フォーマット**
   ```
   【運命の分岐点】
   ▶ 14:32 [選択] 「引き受ける」 (prologue_accept)
        理由: 村の長の依頼を受諾
        結果: 金+100, フラグ[accepted_elder_request]
   ▶ 15:10 [選択] 「正面から戦う」 (awakening_fight)
        理由: 剣を抜き守護者に挑む
        結果: 金+500, 断片+1, 名声+20
   ▶ 16:45 [完了] ナラティブ「prologue_branching」終了
        エンディング: 「覚醒への道」解放
   ```

3. **ナビゲーション対応**
   - ↑/↓ で履歴エントリ選択
   - Enter で詳細表示（モーダル）

### Phase 5: データファイル更新

1. `story_endings.yaml` を DSL 形式に書き換え
2. 既存条件のマッピング:
   - `has_flag:xxx` → `(has flags.xxx)`
   - `karma_good_N` → `(>= player.karma N)`
   - `karma_evil_N` → `(<= player.karma -N)`
   - `kill_counts_total_N` → `(>= player.kill_counts.total N)`

### Phase 6: テスト・検証

1. 既存セーブデータのロード互換性確認
2. ナラティブ実行 → 選択 → 履歴記録 → ジャーナル表示の一連フロー
3. エンディング解放条件の DSL 評価テスト
4. 並行ナラティブ（複数DAG）での履歴分離確認

---

## 5. 互換性・リスク対策

| リスク | 対策 |
|-------|------|
| 既存セーブの `history: list[str]` 読み込み失敗 | `from_dict()` で型判定し自動変換（ノードIDのみのエントリとして復元） |
| `EvaluationContext` への依存追加 | 既存の `_get_evaluator()` パターンで遅延インポート、循環参照回避 |
| パフォーマンス（履歴肥大化） | 上限（例: 100エントリ）で古いものを削除、または重要選択のみ記録 |
| 並行ナラティブの履歴混在 | `NarrativeState` 単位で分離（既存仕様のまま） |

---

## 6. 完了基準

- [ ] `NarrativeState.history` が `HistoryEntry` リストになっている
- [ ] 選択時に choice_text, 条件, 報酬, フラグ変化が記録される
- [ ] ジャーナルUIに「運命の分岐点」セクションが表示される
- [ ] `StoryEnding.unlock_conditions` が DSL で評価される
- [ ] 既存セーブデータがロード可能（自動変換含む）
- [ ] 既存テスト（`test_phase4_narrative_dag.py` 等）が全て通る

---

## 7. スケジュール見積

| Phase | 工数目安 |
|-------|---------|
| Phase 1 | 0.8h |
| Phase 2 | 1.0h |
| Phase 3 | 0.8h |
| Phase 4 | 1.0h |
| Phase 5 | 0.3h |
| Phase 6 | 0.5h |
| **合計** | **約 4.4h** |