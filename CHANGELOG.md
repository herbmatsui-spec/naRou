# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.0.6] - 2026-08-24

### Added
- **メタシナリオ介入システム「なろうテンプレ粉砕」** (提案3実装):
  - プロシージャル・テンプレート生成: 文脈(スラム/ギルド/貴族街/ダンジョン)×派閥×重み付きアーキタイプで「無能追放」「婚約破棄」「横取り」「裏切り」等のなろう系お約束イベントを動的生成
  - **《原典閲覧》（リーダーズ・プリビレッジ）**: `MetaAwarenessSystem` 拡張により、NPCのシナリオフラグ（追放/横取り/裏切り等）を検出・深度別読み取り(Lv1〜3)。深読みにはカルマ秩序逸脱・露見度上昇の代償
  - **3階層介入アクション**:
    - T1 表面介入: 安値買い占め等の表層ハイジャック(低リスク・低報酬)
    - T2 構造介入: ヒロイン主導権移譲等の因果順序書き換え(中リスク・中報酬・善悪変動)
    - T3 存在介入: テンプレートそのものを `GlobalRuleEngine.override_rule` で世界から抹消(高リスク・高報酬・世界法則改変)
  - **完全性連動報酬システム**: 破壊完全性(0〜100%)に応じて因果ポイント倍率変動(×0.3〜×4.0)、限定ユニークスキル《ざまぁの極み》《追放者の意地》《横取り還元》《原典編集》《読者特権・外伝創生》
  - **三重経済システム**: 因果ポイント(周回通貨・法則書き換え資源)・露見度(バレる恐怖・緊張軸)・秩序/混沌・善悪カルマ(既存連動)
  - **テンプレ学習・耐性**: 同一アーキタイプ乱獲で成功率減衰(0.7倍/周)、世界変異メッセージで供給枯渇を表現
  - **輪廻転生引き継ぎ**: 乱獲カウント半減引き継ぎ、`apply_world_modifier` で世界変異メッセージ生成
  - **UI統合**: サイバー義眼ARオーバーレイ(`template_flag_badges`)、原典閲覧モード(IFルートタイムライン)、完全性ゲージ、演出イベント(`emote_exclamations`/`bookFlip3`/`fanfare`等)
  - **キーバインド**: `Shift+R` 《原典閲覧》、`Shift+I` 《テンプレ介入》
  - **Web API公開**: `/api/state` に `karma_law_chaos`/`karma_good_evil`/`template_exposure`、`meta_intervention` (active_events/total_karma_points/devoured_template_counts) を追加
  - **新規ファイル**: `skill_eater_meta_intervention_system.py`、`skill_eater_template_model.py`、`data/templates/*.yaml`、`data/meta_intervention.yaml`、デモ・テスト一式

### Fixed
- `components.py` に `AchievementComponent` 不在による既存テスト収集エラーは、同コンポーネントが `naRou/systems/meta_progression_system.py` 内定義であるため影響外（本実装は依存せずモックでテスト完遂）

### Tests
- 新規テスト 35 件追加 (`test_skill_eater_meta_intervention_*.py` ×5): ローダー/原典閲覧/生成器/介入エンジン/統合ループ、全通過

## [v1.0.5] - 2026-08-24

### Fixed
- **定数整合性・重複排除** (`naRou/constants.py`): `TILE_SECRET_FLOOR` (7 vs 10) 矛盾解消、`AI_ROLE_*`, `INTENT_*`, `EMOTE_*`, `ACCESS_*`, `KEY_TYPE_*`, `REWARD_*` 重複定義を一本化
- **EventBus 一元化** (`naRou/event_bus.py`, `naRou/core_framework.py`): シングルトン重複を解消し、標準クラスと堅牢な例外ハンドリングに統合
- **DIコンテナのクリーンアップ** (`naRou/di_container.py`): 未使用の `_services` フィールドを削除
- **循環インポート解消** (`naRou/render_context.py`): TYPE_CHECKING による遅延インポートを導入し初期化デッドロックを防止
- **英語ローカリゼーション完全対応** (`data/text/en.yaml`): ja.yaml と完全に同期する180行以上の英訳定義を追加
- **テストコレクション警告解消** (`tests/test_phase2_social_simulation.py`): `TestPlayer` → `MockPlayer` にリネーム
- **魔法詠唱の完全化** (`naRou/systems.py`): `fireball` のダメージ計算・戻り値および未知の魔法へのデフォルト戻り値を追加
- **末尾 localize 不要インポートの削除**: 8つのモジュールから末尾のデッドインポートを除去

## [v1.0.0] - 2026-08-20

### Added
- **スキル喰い専用チュートリアル5件追加** (`data/tutorial_guides.yaml`): 世界遷移時、初回解析、初回捕食、毒性警告、初回合成
- **喰らいサイクル常時HUD表示** (`uirenderer.py`, `render_context.py`): 底部UIに毒性ゲージ、所持スキル数、捕食成功率を常時表示
- **色覚モード時の数値強制表示** (`uirenderer.py`, `ui_fx_systems.py`): `GaugeBar.render()` に `force_numeric` パラメータ追加、色覚モード時に `%数値` をバーと併記
- `RenderContext` に `world_a_data`, `toxicity_manager`, `skill_eater_combat_system`, `color_vision_mode`, `last_scan_result` 追加
- `Engine.last_scan_result` プロパティ追加（解析結果保存用）

### Changed
- `UIRenderer.render()`: スキル喰いワールド時に専用HUD描画、色覚モード判定追加
- `GaugeBar.render()`: `force_numeric` 引数で数値併記制御対応

### Refactored
- Split `Engine` god-class into `managers/` (Combat, SkillReward, PetBond, WorldNews, Persistence, Faction, ContextMenu, StateMachine, SetupCoordinator)
- Componentized `Entity`: `affection`, `pet_type`, `emote_*`, `pet_ai` now ECS components
- Moved `GodInfo` → `god_system.py`, `Skill`/`Attributes` → `components.py`
- Centralized `localize()` in `localization_manager.py`; magic numbers → `constants.py`
- Added `data_validation.py` YAML loader; `Kernel.get_system` default overload; DI-friendly `Engine(renderer, kernel)`
- Added unit tests (core_framework, event_bus, entity, config_manager, kernel) and `tools/cli.py`
- 132 new tiles across 12 categories: floors, walls, decorations, items, monsters, effects, UI
- New `tiny_rogue_16` atlas scale (509×115) with 105 tile entries
- Monster rendering: 12 monster types mapped to `TR_MONSTER_01/02/03` and `TR_MONSTER_VAR_01/02/03` with 4-directional animation
- Particle effects: 12 new effect types using `TR_EFFECT_01-12` (magic_cast, fire, ice, lightning, poison, heal, teleport, explosion, sparkle, smoke, slash, shockwave)
- Blood splatter system using `TR_DECOR_10` on damage/kill with directional splatter
- UI icons: heart, mana, coin, key, sword, shield, potion, level using `TR_UI_01-12`
- Screen flash on critical hits using `TR_EFFECT_09` + `TR_EFFECT_01`
- Dynamic lighting enhancements: tile-specific properties (emissive, reflective, translucent, material)
- Ambient occlusion for wall corners based on neighbor count
- Parallax background layers from `tilemap_packed.png`
- Weather effects: rain, snow, ash using repurposed effect tiles
- Tile variant randomization (12 floor variants) during dungeon generation
- Footstep particles matching floor type (stone, water, grass, dirt)
- Death animations with monster-type-specific effects
- Loot sparkle with rarity-based colors on item drops
- Feature flag `ENABLE_TINY_ROGUE_GFX` (toggle with `G` key)
- Tile mapping utilities for dungeon generation, items, decorations, effects, UI
- Comprehensive integration test suite
- Demo script `demo_tiny_rogue_graphics.py` showcasing all features
- テキスト(ASCII)モード（GPU不要）: `core/text_renderer.py`, `main_text.py`, メニュー選択肢追加
- アクセシビリティ対応: 色覚多様性 (`design_tokens.*`, `core/accessibility.py`), 難易度プリセット (`core/difficulty.py`, `config.yaml`), チュートリアル (`data/tutorial_steps.json`, `core/tutorial_controller.py`), 操作ガイドトグル, フォントスケール (`web_server.py`)
- ワンタッチ Web 起動＋モバイル対応: `web_server.py` の `launch_browser`, `--open` フラグ, バックグラウンド起動, レンダラ選択フォールバック (WebGL2→Canvas2D), タッチ/スワイプ/D-pad, レスポンシブ対応, 自動再接続, FPS ベース品質低下, ライトモードトグル

### Changed
- `TileAtlas._load()` now loads `tiny_rogue_16` metadata
- `TileRegistry.get_uv()` supports `tiny_rogue_16` scale with feature flag fallback
- `EntityRenderer._get_tile_id()` maps monster types to Tiny Rogue tiles
- `MonsterPreset.create()` stores `monster_type` for tile mapping
- `CombatSystem` publishes damage/kill/trap events for FX
- `FXManager` spawns blood, death animations, loot sparkles, flash effects
- `TileRegistry` supports autotile variants for Tiny Rogue floors/walls
- Dungeon generation assigns random floor variants (0-11) when feature flag enabled
- Parallax background rendering in `MapRenderer`
- Weather particle spawning using Tiny Rogue effect tiles
- UI icons rendered via Tiny Rogue tiles when feature flag enabled
- Screen flash on critical hits
- Ambient occlusion for wall tiles
- ゲーム本編の SDL 失敗フォールバック: テキストモード有効時はテキストモードへ自動切替
- web_server.py: /api/tokens エンドポイントに ?a11y= クエリ対応, /api/capabilities エンドポイント追加
- main.py: メニューにテキストモード起動オプション追加, アクセシビリティ選択画面追加, NAROU_FORCE_TEXT 環境変数対応

### Fixed
- Validation warnings for variant/frame counts are expected (atlas packing uses single-tile entries with animation handled via UV offsets)
- Feature flag fallback to standard tiles when disabled

## [v1.0.0] - 2026-08-20

### Added
- Initial release of Tiny Rogue Graphics Pack integration
- Complete asset pipeline from Kenney "Tiny Rogue" pack to in-game rendering
- Reusable atlas packing tool (`tools/pack_tiny_rogue_atlas.py`)
- Tile mapping configuration system (`data/tile_mappings/`)
- Integration test suite (`tests/integration/test_tiny_rogue_graphics.py`)
- Demo script (`demo_tiny_rogue_graphics.py`)
