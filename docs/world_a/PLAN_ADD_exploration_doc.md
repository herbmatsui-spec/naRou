# 実装計画書：追加課題 — 探索システムの設計本文への追記

- **計画ID**: PLAN-ADD-EXPLORATION
- **対象**: 実装から見えた追加課題（PLAN-06 トレーサビリティで検出）
- **作成日**: 2026-08-20
- **スコープ**: 実装済・テスト済だが `DESIGN_A_SKILL_EATER.md` に記載のない「探索システム」を設計本文へ追記する（本計画書は計画のみ／実装は別ステップ）

---

## 1. 背景と問題

`skill_eater_exploration_system.py` は実装・テスト済だが、設計ドキュメントに一切記載がない。
- PLAN-06 トレーサビリティで「⚠ 実装あり／設計未記載（ギャップ）」として検出。
- 探索はAの世界の基本ループ（フィールド移動→敵発見→喰らい）を支えるコア機能であり、設計欠落は大きい。

**実装調査（コード観察）**:
- データ構造: `DungeonRoom`（room_id/name/description/has_treasure/has_trap/enemies）、`ExplorationResult`（action_type/current_room_id/played_sounds/presentation_events）。
- 初期部屋: `slum_alley`（スラムの裏路地）, `underground_market`（地下闇市場通り）, `midas_tower_entrance`（ミダスタワー正面玄関）, `vault_chamber`（バベルの金庫室・宝箱あり）。
- アクション種別: `STEP`, `MOVE_ROOM`, `OPEN_DOOR`, `LOOT_CHEST`, `ESCAPE`, `TRAP`。
- 演出・音響: 足音（footstep00〜09 ランダム）、扉・トラップ・宝箱の Emote/Audio 演出（`presentation_system` / `audio_system` 連携）。
- 開始地点: `slum_alley`（§4.1 序盤「スラム街」と整合）。

---

## 2. 目標

`DESIGN_A_SKILL_EATER.md` に探索システムの設計を追加し、実装↔設計のギャップを解消する。PLAN-02 の「正規設計書」方針に従い、A固有の詳細仕様として DESIGN_A に記載する。

---

## 3. 実装手順（案）

### Step 1 — DESIGN_A へのセクション追加
- `## 3. 独自メカニクス設計` 内に **`### 3.2 探索システム（ダンジョン探索・移動・環境音）`** を追加（§3.1 の直後）。
- 記載内容:
  - 概要: ダンジョン部屋の移動・足音・扉・トラップ・宝箱からなるフィールド探索ループ。
  - データ構造: `DungeonRoom`, `ExplorationResult`（上記調査より）。
  - 主要アクション: STEP/MOVE_ROOM/OPEN_DOOR/LOOT_CHEST/ESCAPE/TRAP。
  - 演出・音響連携: Emote/Foley（`presentation_system`, `audio_system`）との統合。
  - 初期部屋一覧（4部屋）と §4.1 序盤（スラム街）との整合注記。

### Step 2 — §2 マッピングへの反映（任意）
- §2 の基底システムマッピングに「探索＝プロシージャルダンジョン（`procedural_dungeon_generator.py` 等の流用）」を `### 2.8` として追記。既存 §2.1〜2.6 は TBD だが、探索は**実装済**として肯定行に格上げ。

### Step 3 — トレーサビリティ更新
- `TRACEABILITY_06_tests.md` の探索行を「⚠ 実装あり/設計未記載」から「✅ Covered（設計記載済）」へ格上げし、対応設計セクション（§3.2）を明記。

### Step 4 — 検証
- DESIGN_A に §3.2（探索）が存在し、コードの構造（DungeonRoom/ExplorationResult/4部屋/6アクション）と整合していること。
- TRACEABILITY の探索行ステータスが更新されていること。

---

## 4. 受け入れ基準

1. `DESIGN_A_SKILL_EATER.md` に探索システムのセクション（§3.2）が追加されている。
2. 記載内容が実装（`skill_eater_exploration_system.py`）と整合している。
3. `TRACEABILITY_06_tests.md` の探索行ステータスが「設計記載済」に更新されている。

---

## 5. 影響範囲・リスク

- **影響**: 設計ドキュメント（`DESIGN_A_SKILL_EATER.md`, `TRACEABILITY_06_tests.md`）のみ。コード変更なし。
- **リスク**: 低。コード観察に基づく忠実な記述にとどめる。数値・部屋名は実装と一致させる。
- **注意**: 本計画書は「計画の作成」まで。実際の DESIGN_A への追記は別ステップで実施。
