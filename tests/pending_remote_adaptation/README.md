# 遠隔機能テストの未適応分 (PR #8 統合 2026-10-10)

origin/main (8/24) 由来の機能テストのうち、当リポジトリの現行 Entity 内部
(シリアライズ形式・MetaAwarenessSystem internals) と未適合のため一時退避。

| テスト | 依存 | 適応に必要な作業 |
|---|---|---|
| test_husk_serialization.py | Entity.to_dict の components dict 形式 | HuskInventoryComponent の保存経路を実装後に復帰 |
| test_skill_eater_meta_intervention_awareness.py | 遠隔版 MetaAwarenessSystem 内部 (reading_depth / exploit_windows) | 遠隔の awareness 機能を移植するか、現行 meta_awareness_system.py への適合 |

対応する実装 (動作確認済み) はリポジトリに同梱済み:
- skill_eater/skill_eater_husk_forge.py 系 (PuppetForgeSystem)
- skill_eater/skill_eater_meta_intervention_system.py (InterventionEngine)
- karma_system.py (露見度 exposure 対応版)
- ecs/components/components.py (HuskComponent / HuskInventoryComponent / PuppetUnitComponent)
