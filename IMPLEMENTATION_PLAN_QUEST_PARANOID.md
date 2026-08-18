# 偏執的クエストシステム実装計画書
## 9大機能 × 36ステップ（推奨順序：1→3→2→6→4→5→7→8→9）

---

## フェーズ1: 条件分岐ツリー（CQCT） - Steps 1-4
**基盤エンジン：全機能の前提**

| Step | 内容 | ファイル | 成果物 |
|------|------|----------|--------|
| 1 | 条件ノードAST定義（And/Or/Not/Xor/Leaf） | `quest_condition_ast.py` | データクラス群 |
| 2 | パーサー（DSL文字列 → AST） | `quest_condition_parser.py` | `parse_condition(str) -> ConditionNode` |
| 3 | 評価エンジン（プレイヤー/ワールド状態 → bool） | `quest_condition_evaluator.py` | `evaluate(node, context) -> bool` |
| 4 | 既存 `QuestObjective` への統合・YAMLスキーマ拡張 | `main_quest_system.py`, `data/main_quests.yaml` | `condition_tree` フィールド対応 |

---

## フェーズ2: NPC記憶・噂・評判三層伝播 - Steps 5-8
**社会シミュレーション基盤**

| Step | 内容 | ファイル | 成果物 |
|------|------|----------|--------|
| 5 | NPC記憶ストア（クエスト結果・目撃・タイムスタンプ） | `npc_memory_system.py` | `NPCMemoryManager` |
| 6 | 噂伝播エンジン（距離減衰・親密度・派閥フィルタ） | `rumor_propagation_system.py` | `RumorEngine` |
| 7 | 評判閾値によるクエスト解放/敵対トリガー | `reputation_gate_system.py` | `ReputationGate` |
| 8 | `relationship_system.py` / `faction_war_system.py` 統合 | 既存ファイル修正 | 双方向連携API |

---

## フェーズ3: 5軸スケジューラ（時間・天候・季節・月齢・フェーズ） - Steps 9-12
**時間制御基盤**

| Step | 内容 | ファイル | 成果物 |
|------|------|----------|--------|
| 9 | スケジュール定義スキーマ（YAML） | `data/quest_schedules.yaml` | 定義ファイル |
| 10 | スケジューラエンジン（現在状態と照合→利用可否） | `quest_scheduler.py` | `QuestScheduler` |
| 11 | 待機/睡眠コマンドへのフック（時間経過で再評価） | `input_handler.py`, `turn_manager.py` | 自動再チェック |
| 12 | `world_event_system.py` 連携（祭り/蝕/流星群専用ウィンドウ） | 既存連携 | 動的スケジュール注入 |

---

## フェーズ4: マルチエンド分岐ナラティブDAG - Steps 13-17
**物語分岐基盤**

| Step | 内容 | ファイル | 成果物 |
|------|------|----------|--------|
| 13 | ナラティブノード/エッジ定義（DAG） | `quest_narrative_dag.py` | `NarrativeNode`, `NarrativeEdge` |
| 14 | 選択肢→分岐→サブ目的→報酬/次クエスト のYAMLスキーマ | `data/quest_narratives.yaml` | 定義ファイル |
| 15 | DAG実行エンジン（現在ノード管理・選択適用・フラグ更新） | `narrative_executor.py` | `NarrativeExecutor` |
| 16 | `story_choices.yaml` / `story_endings.yaml` 統合 | 既存連携 | フラグ自動同期 |
| 17 | メインクエストシステムへの組み込み | `main_quest_system.py` | `narrative_dag_id` フィールド対応 |

---

## フェーズ5: プロシージャルダンジョン相互生成 - Steps 18-21
**空間・クエスト統合**

| Step | 内容 | ファイル | 成果物 |
|------|------|----------|--------|
| 18 | クエスト→ダンジョン要求仕様DSL（部屋/トラップ/敵/ボス座標） | `quest_dungeon_spec.py` | `DungeonSpec` |
| 19 | `procedural_dungeon_generator.py` 拡張（仕様充足モード） | 既存拡張 | `generate_from_spec(spec)` |
| 20 | 生成結果フィードバック（実階層数・ボス座標→クエスト目的更新） | 双方向連携 | 完全一致保証 |
| 21 | ダンジョン探索クエスト生成パイプライン統合 | `procedural_quest_generator.py` | `source_type="dungeon_synced"` |

---

## フェーズ6: ビルド連動専用目的生成 - Steps 22-24
**キャラビルド×クエスト融合**

| Step | 内容 | ファイル | 成果物 |
|------|------|----------|--------|
| 22 | プレイヤービルド解析（職業/スキル/覚醒/継承/特化） | `build_analyzer.py` | `BuildProfile` |
| 23 | ビルド特化目的テンプレートライブラリ | `data/build_objectives.yaml` | 定義ファイル |
| 24 | プロシージャル生成時のビルド適応注入 | `procedural_quest_generator.py` | `archetype="build_tailored"` |

---

## フェーズ7: 考古学・コーデックス・メタ進行三位一体 - Steps 25-28
**メタゲーム統合**

| Step | 内容 | ファイル | 成果物 |
|------|------|----------|--------|
| 25 | クエスト完了→記憶断片ドロップテーブル | `quest_fragment_rewards.py` | `FragmentDropTable` |
| 26 | `truth_codex` 解読進行との自動連携 | `archaeology_system.py` 連携 | 解読ゲージ上昇 |
| 27 | セット完了ボーナス（真実の一片・NG+引継ぎフラグ） | `meta_progression_system.py` 連携 | `TruthPiece` 付与 |
| 28 | 考古学サイト発掘クエストの動的生成 | `procedural_quest_generator.py` | `archetype="excavation"` |

---

## フェーズ8: ペット同行クエスト - Steps 29-31
**ペットシステム統合**

| Step | 内容 | ファイル | 成果物 |
|------|------|----------|--------|
| 29 | 同行ペットプロファイル解析（種族/契約/融合/進化歴） | `pet_quest_analyzer.py` | `PetProfile` |
| 30 | ペット固有目的テンプレート・進化触媒連動 | `data/pet_quests.yaml` | 定義ファイル |
| 31 | クエスト生成・完了時のペット成長フック | `pet_evolution_system.py`, `pet_fusion_system.py` 連携 | 専用スキル/進化解放 |

---

## フェーズ9: リアルタイムワールドシミュレーション連動 - Steps 32-36
**生きた世界への完全統合**

| Step | 内容 | ファイル | 成果物 |
|------|------|----------|--------|
| 32 | ワールドイベント監視バス（戦争/疫病/彗星/継承） | `world_event_hooks.py` | `EventMonitor` |
| 33 | 緊急クエスト自動注入（イベント発生中のみ有効） | `emergency_quest_injector.py` | 動的ボード更新 |
| 34 | 派閥戦争専用クエストテンプレート（前線/補給/スパイ） | `data/faction_war_quests.yaml` | 定義ファイル |
| 35 | 未完了時の機会喪失記録・NPC会話/エンディング反映 | `missed_opportunity_system.py` | `MissedOpportunity` |
| 36 | 全システム統合テスト・バランス調整・ドキュメント化 | 全ファイル | 完成版 |

---

## 依存関係DAG
```
1→2→3→4
    ↓
5→6→7→8
    ↓
9→10→11→12
    ↓
13→14→15→16→17
    ↓
18→19→20→21
    ↓
22→23→24
    ↓
25→26→27→28
    ↓
29→30→31
    ↓
32→33→34→35→36
```

---

## 実装ルール
1. **1ステップ = 1コミット単位**（テスト通過まで）
2. **既存ファイル破壊禁止**（拡張のみ・インターフェース維持）
3. **YAMLデータ駆動**（ハードコード排除）
4. **型ヒント必須**（mypy strict pass）
5. **各ステップ完了時に `pytest tests/` 緑確認**

---

## 予想工数
- Steps 1-4:  2-3日（核心エンジン）
- Steps 5-8:  2-3日（社会シム）
- Steps 9-12: 1-2日（スケジューラ）
- Steps 13-17: 2-3日（ナラティブDAG）
- Steps 18-21: 2-3日（ダンジョン統合）
- Steps 22-24: 1-2日（ビルド連動）
- Steps 25-28: 1-2日（メタ統合）
- Steps 29-31: 1-2日（ペット統合）
- Steps 32-36: 1-2日（ワールド連動）
- **合計: 13-22日**