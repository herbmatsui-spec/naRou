# テスト↔設計 トレーサビリティ表 — PLAN-06 成果物

> 設計要件（`DESIGN_A_SKILL_EATER.md` §2/§3.1/§4/§5、README 4大システム）と `tests/test_skill_eater_*.py` の対応。
> カバレッジ凡例: ✅ Covered（自動テストあり）／⚠ Partial（実装ありだが設計未記載・または間接のみ）／❌ TBD（自動テストなし）

## マッピング表

| 設計要素（出典） | 内容 | 対応テスト | カバレッジ |
|---|---|---|---|
| §3.1 解析 (analysis) | スキル構造可視化・Lvスケーリング | `test_skill_eater_phase1.py`::test_analysis_system_basic / _high_level, test_skills_loaded | ✅ |
| §3.1 喰らい 成功/失敗 | Devour 成功フロー・失敗バックラッシュ | `test_skill_eater_phase2.py`::test_devour_success_flow / test_devour_failure_backlash / test_basic_attack_and_passive | ✅ |
| §3.1 合成（静的/動的）+ §2.4 動的ツリー | 静的レシピ・プロシージャル合成・動的ツリー生成 | `test_skill_eater_phase3.py`::test_static_synthesis / test_procedural_synthesis / test_dynamic_tree_generation | ✅ |
| README システム4 Husk従属 | Husk捕獲/移植・従属タレット回復/自壊 | `test_skill_eater_phase4_5.py`::test_husk_capture_and_skill_transplant / test_servant_turret_healing_and_crumble, `full`::improvement_2 | ✅(実装) / ⚠ 設計本文(§2.5除く)に詳細未記載 |
| README システム2 経済/闇市場/監査 | 純資産/階級・闇市場売買・拠点拡張・監査レイド | `test_skill_eater_phase4_5.py`::test_economy_net_worth_and_tier / test_black_market_sale_and_facility_upgrade, `full`::improvement_1 | ✅ |
| README システム3 ROOTハック/世界法則上書き | 世界法則のリアルタイム書き換え・暗号/ハック | `test_skill_eater_phase6_7_8.py`::test_global_rule_override_root_access, `full`::improvement_6 / improvement_9 | ✅ |
| §2.6 輪廻転生 / README システム3 | スキル継承・動的輪廻 | `test_skill_eater_phase6_7_8.py`::test_reincarnation_inheritance, `full`::improvement_7 | ✅ |
| 終盤 meta counter / 真エンド | 銀行防衛・metaカウンター戦略 | `test_skill_eater_phase6_7_8.py`::test_meta_counter_boss_mechanic, `full`::improvement_5 | ✅ |
| README システム1 喰らいシナジー/消化不良 | 胃袋内属性連鎖・消化不良 | `full`::improvement_3 (devour_synergy_and_indigestion) | ✅ |
| メモリ容量/廃棄 (SkillDef.memory_usage) | スキル記憶容量管理 | `full`::improvement_4 (memory_capacity_and_discard) | ✅ |
| 中毒/精神侵食 (Sanity) | ハック代償の中毒蓄積 | `full`::improvement_8 (addiction_buildup) | ✅ |
| 探索システム (skill_eater_exploration_system.py) | 探索・移動・環境音 | `presentation`::test_exploration_presentation_events, `audio`::test_exploration_audio | ✅ Covered（設計記載済：§3.2） |
| 演出 (Presentation) | 全システムの Emote/Foley 演出 | `test_skill_eater_presentation_integration.py`（core/戦闘/喰らい/合成/経済/従属/探索/meta/トグル） | ✅ |
| 音響 (Audio) | 全システムの SE | `test_skill_eater_audio_integration.py`（同上＋ミュート） | ✅ |
| §4 進行フェーズ（序/中/終/輪廻後） | レベルデザイン・シナリオ進行 | （間接のみ：各メカニクス単体テストでカバー） | ⚠ 進行シナリオの自動テストなし |
| §5 UI/UX（スキャナーUI/星図UI） | 解析オーバーレイ・星図UI | （なし） | ❌ 手動/未 |

## サマリ
- コアメカニクス（解析/喰らい/合成/ROOT/輪廻/経済/Husk/探索）は自動テストで網羅されている。
- **設計記載済みの実装**: 探索システム（§3.2 に追記済・§2.8 マッピング追加済）→ ギャップ解消。
- **自動テスト不在**: §4 進行シナリオ、§5 UI/UX → 統合テストまたは手動検証が必要。
