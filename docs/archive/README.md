# docs/archive/ — 設計文書アーカイブ

2026-10-13 に「改善案8: 設計文書の整理」の一環として、リポジトリルートおよび `plans/` から
**2026-08-23 付けで完結済み・陳腐化した計画書・報告書** を退避したものです。

- 移動方法: すべて `git mv` による履歴保持付き移動。
- 裁定基準: ファイル先頭を読み、「完了報告」「完了済み計画」「日付付きスナップショット分析」「後続計画に置き換えられた計画」をアーカイブ対象とした。
- 現役の文書 (README.md / TODO.md / CHANGELOG.md / MANUAL.md / API.md / ARCHITECTURE.md / ASSETS.md /
  `DETAILED_IMPLEMENTATION_PLAN_TEST_FIXES_AND_COVERAGE.md` / `NAROU_9_WORLDS_DESIGN.md` /
  `MULTIVERSE_GAME_DESIGN.md` / `README_TERRITORY.md`、および `plans/` の 2026-10 月文書) は移動していない。

## ルートから移動 (27本)

| ファイル | 移動理由 |
| --- | --- |
| 2D_GAME_COMPARISON.md | 2026-08 時点のWebクライアント批判分析スナップショット。行番号引用が現行コードと乖離 |
| ARCHAEOLOGY_IMPLEMENTATION_SUMMARY.md | 考古学メタゲーム Step 36 の完了報告 |
| ARCHAEOLOGY_IMPROVEMENT_PLAN.md | 検証に基づく3改善の計画。実装済みで tests/test_archaeology_metagame.py が改善を検証 |
| COMMERCIAL_EVALUATION_REPORT.md | 2026-08-19 付の商用化評価スナップショット。GAME_DESIGN_V2 で現状認識が更新済み |
| COMMERCIAL_SUCCESS_PROPOSALS.md | 上記評価を前提とした2026-08-19 付の商業化9提案 |
| DETAILED_IMPLEMENTATION_PLAN_1_36.md | タイルセット/アセットパイプライン計画 (Step 1-36)。完了 |
| DETAILED_IMPLEMENTATION_PLAN_review_fixes.md | feature/webgl-postprocess のレビュー指摘修正計画。完了 |
| IMPLEMENTATION_COMPLETE.md | 垂直ワールド拡張の完了レポート |
| IMPLEMENTATION_FINAL_NOTE.md | 垂直ワールド拡張の完了メモ |
| IMPLEMENTATION_META_PLAN.md | グラフィック強化72ステップ計画書の作成用メタ計画 |
| IMPLEMENTATION_PLAN.md | 「失敗テスト修正」12ステップ計画 (397/429 時点)。完了 |
| IMPLEMENTATION_PLAN_24_STEPS.md | コードレビュー対応24ステップ計画。完了 |
| IMPLEMENTATION_PLAN_DETAILED.md | 偏執的グラフィック強化 9フェーズ×72ステップ計画 |
| IMPLEMENTATION_PLAN_POSTPROCESS.md | ライティング/ポストプロセス/パーティクル実装計画。完了 |
| IMPLEMENTATION_PLAN_QUEST_PARANOID.md | 偏執的クエストシステム 9機能×36ステップ計画。完了 (サマリーは下記) |
| META_PLAN_FOR_DETAILED_PLAN.md | タイルセット詳細計画書の作成プロセス定義 |
| META_PLAN_archaeology.md | 考古学詳細計画書の作成プロセス定義 |
| PHASE1_META_PLAN.md | Webクライアント Phase 1 計画書の作成用メタ計画 |
| PLAN_ACCESSIBILITY_72.md | アクセシビリティ72ステップ実装計画 |
| QUEST_SYSTEM_IMPLEMENTATION_SUMMARY.md | 偏執的クエストシステム実装サマリー (完了) |
| REFACTOR_PLAN.md | リファクタリング72ステップ計画。完了 (ARCHITECTURE.md の「Key refactors」が成果) |
| STEP_01_COMPLETED.md | クエスト条件分岐ツリー (CQCT) Step 1 の完了記録 |
| VERIFICATION_AND_IMPROVEMENTS.md | タイルシステム検証結果と改善提案。対応済み |
| VERTICAL_WORLD_IMPLEMENTATION_PLAN.md | 垂直ワールド拡張計画。完了 |
| VERTICAL_WORLD_IMPLEMENTATION_SUMMARY.md | 垂直ワールド拡張完了サマリー |
| design_audit.md | demos スタイル監査 (Step 1) 完了記録。docs/VISUAL_UNIFICATION.md から言及あり |
| test_report.md | テストレポート生成設定の雛形。実利用なし |

## plans/ から移動 (65本)

### スキル喰い・世界構築キャンペーン (完了)

| ファイル | 移動理由 |
| --- | --- |
| SKILL_EATER_BASE_DEFENSE_IMPLEMENTATION_72_STEPS.md | 拠点防衛72ステップ計画。実装済み (skill_eater_base_defense) |
| SKILL_EATER_BLACK_MARKET_NETWORK_72_STEPS.md | 闇市場ネットワーク72ステップ計画。実装済み |
| SKILL_EATER_DUNGEON_FLOOR_MANAGER_72_STEPS.md | ダンジョン階層管理72ステップ計画。実装済み |
| SKILL_EATER_EXPLORATION_META_72_STEPS.md | 探索メタ72ステップ計画。実装済み (skill_eater_exploration_system) |
| SKILL_EATER_FACILITY_ACTIONS_72_STEPS.md | 拠点施設アクション72ステップ計画。実装済み |
| SKILL_EATER_SECRET_ACCESS_72_STEPS.md | 隠しアクセス72ステップ計画。実装済み (docs/SKILL_EATER_SECRET_ACCESS_IMPLEMENTATION.md) |
| SKILL_EATER_TERRITORY_CONTROL_72_STEPS.md | テリトリー制圧72ステップ計画。実装済み (README_TERRITORY.md が現行dev文書) |
| WORLD_CLOCK_72_STEPS.md | 世界時計72ステップ計画。実装済み |
| main_quest_world_state_design.md | 「運命運の導き」メインクエスト&ワールドステート設計書 (旧期) |

### Canvas / グラフィック / デモ系 (完了)

| ファイル | 移動理由 |
| --- | --- |
| CANVAS_REFACTOR_72_STEPS.md | HTML5 Canvas 2D 統合72ステップ計画。完了 |
| canvas_refactor_plan.md | 同スコープの先行詳細計画 (上記72ステップ版に収束) |
| gemini_graphics_enhancement_plan_japanese.md | Gemini 画像生成拡張計画 |
| gemini_90pct_labor_reduction_plan.md | Gemini 画像生成工数削減計画 |
| gameplay_demo_24_scenes_implementation_plan_japanese.md | デモ24シーン実装計画。demos/ 実装済み |
| playthrough_3videos_plan.md | プレイ動画3分割制作計画 |
| visual_reward_test_plan.md | 視覚報酬検証計画。検証済み |
| ui_ux_design_system_implementation_plan.md | UI/UXデザインシステム実装計画 |
| ui_ux_visual_upgrade_plan_japanese.md | UI/UXビジュアルupgrade計画 |
| AUTONOMOUS_AI_SUBAGENT_72_STEPS.md | 自律プレイAI (AutoPlayer) 72ステップ計画 |
| IMPLEMENTATION_PLAN_TINY_ROGUE_ENRICHMENT_1_72.md | Tiny Rogue 拡充72ステップ計画。完了 |
| META_PLAN_TINY_ROGUE_ENRICHMENT.md | 同計画のメタ計画 |

### クエスト / ストーリー系 (完了)

| ファイル | 移動理由 |
| --- | --- |
| procedural_quest_generation_proposal.md | プロシージャルクエスト生成提案 |
| procedural_quest_generation_meta_plan.md | 同メタ計画 |
| procedural_quest_generation_implementation_plan.md | 同実装計画。完了 |
| procedural_quest_enhancement_meta_plan.md | クエスト拡張メタ計画 |
| procedural_quest_enhancement_implementation_plan.md | クエスト拡張実装計画。完了 |
| dungeon_world_storyteller_proposal.md | 語り部システム提案。実装済み (storyteller) |
| dungeon_world_storyteller_implementation_plan.md | 同実装計画。完了 |
| hub_town_implementation_plan.md | ハブタウン実装計画 |
| narou_elements_proposal.md | Elona×なろう要素統合提案 |
| elona_enhancement_plan.md | Elona ゲーム性向上9提案 |

### システム実装計画 (完了)

| ファイル | 移動理由 |
| --- | --- |
| achievement_trophy_system_proposal.md | 実績・トロフィー提案 |
| achievement_trophy_system_implementation_plan.md | 同実装計画。完了 |
| reincarnation_system_proposal.md | 転生システム提案。実装済み |
| reincarnation_system_implementation_plan.md | 同実装計画。完了 |
| reincarnation_memory_metagoal_implementation_plan.md | 転生記憶メタゴール実装計画。完了 |
| pet_contract_evolution_fusion_proposal.md | ペット契約/進化/融合提案。実装済み |
| pet_contract_evolution_fusion_implementation_plan.md | 同実装計画。完了 |
| skill_synthesis_evolution_proposal.md | スキル合成進化提案。実装済み |
| skill_synthesis_evolution_implementation_plan.md | 同実装計画。完了 |
| skill_tree_job_system_proposal.md | スキルツリー/ジョブ提案。実装済み |
| skill_tree_job_system_implementation_plan.md | 同実装計画 |
| skill_tree_job_system_implementation_plan_japanese.md | 同実装計画 (日本語版・内容重複) |
| title_system_implementation_plan.md | 称号システム実装計画。実装済み |
| guild_faction_ranking_proposal.md | ギルド派閥ランキング提案 |
| guild_faction_ranking_implementation_plan.md | 同実装計画 |
| journal_ui_implementation_plan.md | ジャーナルUI実装計画。実装済み (journal_ui) |
| help_tooltip_implementation_plan.md | ヘルプツールチップ実装計画 |
| internationalization_implementation_plan_japanese.md | i18n実装計画。実装済み (data/text/*.yaml, tests/test_i18n.py) |
| ci_cd_pipeline_implementation_plan_japanese.md | CI/CD パイプライン計画。実装済み (.github/workflows/ci.yml) |
| asset_build_pipeline_implementation_plan_japanese.md | アセットビルドパイプライン計画 |
| performance_validation_optimization_implementation_plan_japanese.md | 性能検証・最適化実装計画 |
| phase1_ux_enhancement_detail.md | UX向上 Phase 1 詳細計画 |
| phase2_stability_detail.md | 安定化 Phase 2 詳細計画 |
| phase3_architecture_detail.md | アーキテクチャ Phase 3 詳細計画 |
| phase4_immersion_detail.md | 没入感 Phase 4 詳細計画 |
| remaining_tasks_implementation_plan.md | 旧期の残タスク実装計画 |
| implementation_plan_enhancement_proposals.md | 拡張提案の実装計画 |
| implementation_quality_enhancement_proposals.md | 品質向上提案 |
| quality_enhancement_roadmap.md | 品質向上ロードマップ (後続の GAME_DESIGN_V2 に役割を譲る) |
| IMPLEMENTATION_PLAN_REVIEW_FIXES_72.md | レビュー指摘修正72ステップ計画。完了 |
| DETAILED_IMPLEMENTATION_PLAN_SEASONAL_LIVE_CONTENT_PIPELINE_1_36.md | 季節イベント配信パイプライン計画。完了 (tests/test_seasonal_events.py) |
| META_PLAN_for_SEASONAL_LIVE_CONTENT_PIPELINE.md | 同メタ計画 |
| commercial_release_detailed_plan.md | 商用リリース詳細計画 (2026-08、未実施・棚上げ) |
| commercial_infrastructure_proposal1_implementation_plan_japanese.md | 商用インフラ提案1実装計画 (同上) |

## 残した文書と理由

- **ルート `ARCHAEOLOGY_COMMUNITY_PROPOSALS.md` / `DETAILED_IMPLEMENTATION_PLAN_archaeology.md`**:
  内容は2026-08 の完了分だが、`tests/test_archaeology_metagame.py` がルート直下の存在を
  assert しているため移動不可 (tests/ は本作業のスコープ外)。
- **ルート `NAROU_9_WORLDS_DESIGN.md` / `MULTIVERSE_GAME_DESIGN.md`**:
  `docs/world_a/INDEX.md`・`docs/world_a/DESIGN_A_SKILL_EATER.md` が現役の設計階層として
  正規性ルール付きで参照しているため現役。
- **ルート `README_TERRITORY.md`**: 現行システム `skill_eater_territory_system.py` の開発者向け文書。
- **ルート `DETAILED_IMPLEMENTATION_PLAN_TEST_FIXES_AND_COVERAGE.md`**: 2026-10-12 付の現行作業計画。
- **`plans/` の 2026-10 月文書 14本** (GAME_DESIGN_V2 一式、PLAN_P1〜P3、AUDIT_2026-10-06、
  MAIN_INTEGRATION_PLAN、REMAINING_IMPLEMENTATION_PLAN、AGENT_A/B_INSTRUCTIONS、
  DEBUG_SUMMARY_2026-10-05、CODE_REVIEW_2026-10-08/): README 参照 2本
  (`GAME_DESIGN_V2_RESULT.md` / `GAME_DESIGN_V2_PHASE2_REPORT.md`) を含む現役文書。
