# 実装済みチュートリアルガイド一覧

## 追加分（スキル喰い / Aの世界 専用）

| ID | トリガー条件 | アクション | タイトル | 概要 |
|----|-------------|-----------|---------|------|
| `skill_eater_enter` | `switch_world_skill_eater` | `scan_enemy` | 禁忌の世界へようこそ | 世界遷移直後に発火。基本システム説明 |
| `skill_eater_first_scan` | `first_scan` | `scan_enemy` | 深度解析の使い方 | Xキー初回押下時。解析の使い方・成功率UP条件 |
| `skill_eater_first_devour` | `first_devour_attempt` | `devour_enemy` | 喰らいの実践 | Vキー初回押下時。捕食手順・失敗リスク・毒性確認方法 |
| `skill_eater_toxicity_warning` | `toxicity_above_40` | `rest_safehouse` | 生体拒絶反応の警告 | 毒性40%到達時。デバフ説明・セーフハウス休息案内 |
| `skill_eater_first_synthesis` | `first_synthesis_open` | `synthesize_skill` | キメラ合成炉の解放 | Shift+T初回押下時。合成条件・キメラスキル例・失敗リスク |

## 既存ガイド（参考）

| ID | トリガー条件 | タイトル |
|----|-------------|---------|
| `welcome_start` | `game_start` | 冒険の始まり |
| `first_hunger` | `hunger_hungry` | 空腹への対処 |
| `first_low_hp` | `hp_below_50` | 生命の危機 |
| `first_depth_10` | `reach_depth_10` | 深層ダンジョンへの到達 |
| `first_reincarnation` | `reincarnate_ready` | 輪廻転生と継承 |
| `first_skill_fusion` | `open_menu_fusion` | スキル合成の極意 |
| `world_clock_intro` | `first_time_check` | 世界時計と時間帯 |
| `world_clock_actions` | `first_action` | 行動と時間消費 |
| `world_clock_npcs` | `first_npc_check` | NPCスケジュール |

## トリガー発火箇所（実装側での呼び出し必要）

以下のトリガー条件は、ゲームコード側で `engine.check_tutorial_triggers("条件名")` を呼ぶ必要があります：

- `switch_world_skill_eater` - ワールド切替時（`Engine.switch_world()` 内）
- `first_scan` - `Engine.execute_scan()` 成功時
- `first_devour_attempt` - `Engine.execute_devour()` 呼び出し時
- `toxicity_above_40` - 毒性管理システムで40%到達検知時
- `first_synthesis_open` - 合成メニュー（Shift+T）初回オープン時

## テスト確認済み

- `TutorialManager` で全14件読み込み成功
- `tests/test_ux_enhancements.py::test_tutorial_manager_loading_and_triggers` PASS
- `tests/test_ux_enhancements.py::test_engine_tutorial_and_notification_flow` PASS