# [巨大ファイル分割] 計画書 (実行前設計 — コードは本計画書の作成時点で1行も変更していない)

**Date:** 2026-10-14
**Status:** 計画のみ (実装は未着手)。本書は案5 (重複モジュール統合) のスコープ裁定「5巨塔の機械的分割は書面計画のみ」に基づく設計文書である。
**範囲:** 以下の5ファイルの構造実測 (AST)、分割候補、推奨順序、回帰防止テスト戦略。

| ファイル | 実測行数 | サイズ | 分割候補数 | 直接 import 元 | 専用テスト |
|---|---|---|---|---|---|
| skill_eater_facility_actions.py | 2,178 | 76KB | **6** | 3 | 45 tests |
| skill_eater_black_market.py | 2,097 | 86KB | **6** | 2 (テストのみ) | 12+3 tests |
| skill_eater_base_defense.py | 1,599 | 57KB | **4** | 4 | 50+48+2+9 tests |
| skill_eater_territory_system.py | 1,533 | 66KB | **5** | 3 (engine/save含む) | **0 tests** |
| ui_fx_systems.py | 1,254 | 47KB | **5** | **25** | 159 tests |

> 注: ui_fx_systems.py は作業指示時 57KB だったが、並行作業で F811 重複 `DynamicLighting` (旧 :188〜:267) が削除済みのため現時点 1,254行/47KB (定義は :997〜:1171 の1つのみ)。以降の実測値は 2026-10-14 時点の working tree。

---

## 0. PR #8 の教訓の繰り込み (本計画の鉄則)

PR #8 (3fbfb44, split-large-files) は **`naRou/` 物理ディレクトリに 498ファイルを移動**し、次の二重名前空間事故を生んだ:

- `from naRou.ecs.components.components import HuskComponent` のような二重名前空間 import が発生し、ルート直下の `ecs/` へのフォールバック挙動と衝突した。
- 統合時に 498ファイルの物理移動は丸ごと廃棄 (`git merge -s ours`) された — つまり「物理ディレクトリ分割」はこのリポジトリで一度失敗して捨てられた前科がある。
- 既知の再帰ハザード: pyproject `[tool.setuptools.package-dir]` の `naRou = "."` 構成では `build/lib/naRou` が再帰的にネストし得る。

そこで本計画では以下を**鉄則**とする:

1. **物理ディレクトリを新設しない。** 分割先はすべてリポジトリルート直下のフラットモジュール (`xxx_yyy.py`)。`naRou/` 配下への配置は絶対にしない。
2. **旧 import パスを完全互換に保つ。** 呼び出し側 (`engine/engine.py`, `save_system.py` 等) は**1行も変更しない**。旧モジュールを「トランク (facade)」として残し、そこから新モジュールを再エクスポートする (`from xxx_yyy import Foo` + `__all__`)。
3. **サブパッケージ化 (ディレクトリ + `__init__.py`) をしない限り pyproject.toml は無変更でよい。** 逆に言えば、サブパッケージを作ったら `[tool.setuptools] packages` への追加が必須 — 2026-10-14 に実在しない `naRou.systems` 1行の残置で `pip install -e .` が即死した実害あり (`package directory './systems' does not exist`、同日 `naRou.systems` 行削除で修復)。**ルートフラット分割を推奨する最大の理由はここ。**
4. **1ファイル分割 = 1ユニット。** green→green で個別リバート可能な単位にし、オーケストレーターが pathspec コミットする (エージェントは git commit/checkout/stash/push 禁止 — 本キャンペーンの確立済み規律)。
5. ruff の `F401` は pyproject `[tool.ruff.lint]` で ignore 済み (かつ `__init__.py` は per-file-ignores あり) のため、再エクスポートによる unused import は lint 障害にならない。

---

## 1. 共通分割パターンと回帰防止テスト戦略

### 1.1 標準手順 (各ファイル共通、テンプレ)

1. **事前緑確認:** 対象の影響テスト群を分割前に回し、既知失敗 (後述の既知債務) と区別できる baseline を取る。
2. **抽出:** クラス/関数群を新フラットモジュールへ移す。移動は「カット&ペースト + import 追加」のみ。**ロジックの書き換え・リネーム・docstring 改変を一切しない** (diff が移動だけだと機械的に検証できる状態を保つ)。
3. **トランク再エクスポート:** 旧モジュール末尾 (または旧定義位置) に `from 新モジュール import A, B, C` と `__all__` を置き、`from skill_eater_xxx import Foo` の契約を維持。
4. **緑確認:** 影響テスト群 + `python3 -m pytest tests/test_entrypoint.py tests/test_narou_package_init.py` (packaging 契約)。
5. **wheel 検証:** `pip wheel . --no-deps -w /tmp/narou_wheel_test` — pyproject 触っていなくても分割後に回す (鉄則3の事故予防。実測: このコマンドで 2026-10-14 の破損再現→修復確認済み)。
6. **ruff:** `ruff check <旧モジュール> <新モジュール>` で新規違反ゼロを確認。

### 1.2 回帰防止テストの選定基準と既知債務

- フルスイートは 2,812 tests ≈15分。分割ステップごとにフルは回さず、**影響テスト群 (下記ファイル別表) + コア15ファイル (≈35秒)** で担保し、1ファイルの分割完了時にフルを1回回す。
- 既知債務 15 件 (balance_snapshot ×2, enemy_intent_formation ×3, stability win_rate, meta_intervention `KeyError: 'expel'`, latency フレーキー等) は分割と無関係のため、失敗リストの**差分ゼロ**を判定基準にする。
- テストが新モジュールの実体を直接 import していないか (テストが旧パス経由のまま壊れないか) は再エクスポートで自動的に解決される。テスト側の書き換えは原則不要 — する場合は別ステップに分ける。

### 1.3 使用する検証コマンド (実績あり)

```bash
python3 -m pytest tests/test_skill_eater_facility_actions.py -q          # 例: ファイル別影響テスト
python3 -m pytest tests/test_entrypoint.py tests/test_narou_package_init.py -q
pip wheel . --no-deps -w /tmp/narou_wheel_test                          # packaging 契約 (実測で破損再現可能)
python3 -m pytest tests/ -x -q -m "not integration"                     # 完了時のフル (≈15分)
```

---

## 2. skill_eater_facility_actions.py — 分割候補 6 単位 (推奨順序: 1番目 / 最もリスク低)

**根拠:** 実体は「モジュールレベル関数の束」。`execute_*` 関数 16 本が互いにほぼ独立しており、クラス状態を持たないため切り出しが最も機械的。import 元 3 件 (`skill_eater_economy_system.py`, `demo_facility_actions.py`, `tests/test_skill_eater_facility_actions.py`) はトランク再エクスポートで保護される。

### 実測構造 (AST)

- dataclass 3 個: `MercenaryContract` (:27-32), `FacilityAction` (:36-51), `FacilityActionResult` (:55-66)
- `FacilityActionRegistry` :69-347 (279行, 12メソッド — `_register_*` で action を登録するテーブル)
- **モジュールレベル関数 20 本** (うち `execute_*` が 15 本) :350-1929 (合計 ≈1,550行 — ファイルの約7割がここ)
- `SkillEaterFacilitySystem` :1936-2177 (242行, 11メソッド — `execute_action` ファサード)

### 分割候補

| # | 新モジュール (ルート直下) | 移動対象 (実測行位置) | 推定行数 |
|---|---|---|---|
| 2.1 | `facility_actions_data.py` | `MercenaryContract` / `FacilityAction` / `FacilityActionResult` / `calculate_success_rate` / `can_afford_action` / `get_available_servants` / `get_hostile_factions` / `apply_raid_bonus` | ≈70 |
| 2.2 | `facility_actions_crafting.py` | `execute_craft_implant` (:373) / `execute_repair_gear` (:463) / `execute_install_cybernetic` (:550) / `execute_analyze_skill_crystal` (:663) / `execute_reverse_engineer_tech` (:763) / `execute_develop_countermeasure` (:876) | ≈580 |
| 2.3 | `facility_actions_medical.py` | `execute_treat_toxicity` (:971) / `execute_memory_wipe` (:1181) / `execute_augment_servant` (:1062) | ≈320 |
| 2.4 | `facility_actions_military.py` | `execute_dispatch_squad` (:1298) / `execute_plan_raid` (:1407) / `execute_negotiate_truce` (:1500) / `execute_gather_intel` (:1608) / `execute_hire_mercenary` (:1707) | ≈530 |
| 2.5 | `facility_actions_economy.py` | `execute_launder_aldo` (:1810) | ≈105 |
| 2.6 | トランク (旧名維持) | `FacilityActionRegistry` + `SkillEaterFacilitySystem` + 上記 5 モジュールの再エクスポート | ≈530 |

実施順は 2.1 → 2.2 → 2.5 → 2.3 → 2.4 (小さい候補から着手して手順を確定してから大きいもの)。

**回帰テスト:** `tests/test_skill_eater_facility_actions.py` (45 tests: `TestFacilityActions`, `TestMercenaryContract`)。

---

## 3. skill_eater_black_market.py — 分割候補 6 単位 (推奨順序: 2番目)

**根拠:** import 元がテスト 2 件のみ (`tests/test_skill_eater_black_market.py`, `tests/test_skill_eater_masterpiece_phase3.py`) でゲーム本体からの結合ゼロ。ただし `BlackMarketNetwork` が singleton (`__new__` + `get_instance`/`reset_instance`) の巨大クラス (1,886行, 76メソッド) なのが主リスク。

### 実測構造 (AST)

- 列挙 3 個: `DistrictType` / `ContrabandType` / `Rarity`、dataclass 4 個: `BlackMarketLocation` / `SmuggleRoute` / `ContrabandItem` / `MarketPriceSnapshot` (:20-100, 合計 ≈65行)
- `BlackMarketNetwork` :103-1988 (singleton, 76メソッド) — メソッド群は下表の通り機能ごとに綺麗にブロック化されている
- `MarketTrends` :1996-2012, `calculate_skill_market_value` / `sell_skill_to_black_market` (:2015-2059), `CyberDoctorSurgery` :2062-2096

### `BlackMarketNetwork` の機能ブロック (実測メソッド分類)

| ブロック | メソッド数 | 代表メソッド (行位置) |
|---|---|---|
| 初期化/singleton | 6 | `__new__`(:106), `__init__`(:111), `_initialize_locations`(:146), `_initialize_routes`(:208), `_initialize_contraband`(:274, 135L) |
| 価格/需給 | 10 | `calculate_dynamic_price`(:410), `update_demand_supply`(:446), `process_illegal_possession_heat`(:1482), `check_price_surges`(:1754) |
| ロケーション | 14 | `check_location_unlock`(:490), `travel_to_location`(:580), `generate_location_event`(:616), `update_mobile_caravan_position`(:512), `format_location_for_ui`(:703) |
| 密輸ルート | 11 | `establish_smuggle_route`(:906), `process_smuggle_routes_turn_end`(:984, 110L), `activate_emergency_evacuation`(:1202), `generate_smuggle_report`(:1234) |
| 取引 | 8 | `buy_from_black_market`(:1276), `sell_to_black_market`(:1350), `buy_contraband`(:1782), `sell_contraband`(:1797), `cancel_trade`(:1505) |
| 演出 (audio/emote) | 17 | `_get_audio_path`(:1545)〜`play_location_upgrade_effect`(:1744) — 完全に自己完結した play_* 群 ≈200行 |
| 永続化/統合 | 10 | `to_dict`(:762, 72L), `from_dict`(:836, 69L), `process_turn_end`(:1850), `check_inspector_raid_integration`(:1906) |

### 分割候補

| # | 新モジュール (ルート直下) | 移動対象 | 方式 |
|---|---|---|---|
| 3.1 | `black_market_data.py` | 列挙 3 + dataclass 4 + `MarketTrends` + `CyberDoctorSurgery` + `calculate_skill_market_value` / `sell_skill_to_black_market` | クラス移動 (独立で最容易) |
| 3.2 | `black_market_presentation.py` | play_* 17 メソッド群 | **Mixin 化** (`class BlackMarketPresentationMixin`) — audio/emote は他ブロックから呼ばれるだけで逆依存が薄い |
| 3.3 | `black_market_smuggling.py` | 密輸ルート 11 メソッド | Mixin 化 |
| 3.4 | `black_market_trading.py` | 価格/需給 10 + 取引 8 メソッド | Mixin 化 |
| 3.5 | `black_market_locations.py` | ロケーション 14 メソッド | Mixin 化 |
| 3.6 | トランク (旧名維持) | singleton 核心 (`__new__`/`__init__`/`get_instance`/`reset_instance`) + `to_dict`/`from_dict` + `class BlackMarketNetwork(PresentationMixin, SmugglingMixin, TradingMixin, LocationsMixin)` の組立 + 再エクスポート | 残置 |

**Mixin の注意点 (鉄則5の補足):** Mixin 分割は「1クラスの状態を跨ぐメソッド」が多い場合に mypy/可読性を損なう。3.2 (演出) が最も安全で、3.4/3.5 は `_record_price_snapshot` → `to_dict` 等のブロック間呼び出しがあるため、Mixin のメソッドは `self._xxx` 参照のままで良い (mixin 間で状態を共有する前提を docstring に明記)。疑問が残る候補は**切り出さずトランクに残す**判断をしてよい (候補数は上限であり必達リストではない)。

**回帰テスト:** `tests/test_skill_eater_black_market.py` (12 tests: `test_step61_dynamic_price_calculation` 〜 `test_step72_final_validation` — singleton・価格・密輸・演出・バランスを網羅), `tests/test_skill_eater_masterpiece_phase3.py` (3 tests)。

---

## 4. skill_eater_base_defense.py — 分割候補 4 単位 (推奨順序: 3番目)

**根拠:** テストが最も厚い (50 + 48 + 2 + 9 = 109 tests) ので回帰網は充分。リスクは襲撃フェーズステートマシン (`RaidPhase`: WARNING → BREACH → AFTERMATH) を跨ぐメソッド群が `self.raid_state` 等の共有状態に密に触れること。

### 実測構造 (AST)

- enum 4 個: `RaidPhase` / `RaidTriggerType` / `DefenseFacilityType` / `EnemyType` (:24-57)
- dataclass 5 個: `DefenseFacility` (:89-224, 136行・11メソッド), `RaidTrigger`, `DamageReport`, `RaidEnemy`, `Subordinate` (:228-302)
- `BaseDefenseManager` :305-1598 (**1,294行, 41メソッド**)

### `BaseDefenseManager` の機能ブロック (実測メソッド分類)

| ブロック | メソッド数 | 代表メソッド (行位置) |
|---|---|---|
| 施設建設/管理 | 9 | `can_build_facility`(:458), `build_facility`(:491), `upgrade_facility`(:519), `repair_facility`(:553), `load_facilities_from_yaml`(:1495), `_update_synergy_bonuses`(:442) |
| 警戒度/トリガー | 5 | `increase_heat`(:618), `increase_alert`(:1554), `check_raid_triggers`(:648), `trigger_meta_quest_raid`(:1296) |
| 袭撃フェーズ機械 | 11 | `start_raid_warning_phase`(:665), `_generate_raid_enemies`(:693, 58L), `process_breach_phase`(:803), `_facility_attack_enemies`(:853, 89L), `_enemy_attack_facilities`(:943, 93L), `process_raid_wave`(:1584), `resolve_raid_outcome`(:1514) |
| 事後処理 (AFTERMATH) | 8 | `start_aftermath_phase`(:1041, 74L), `process_aftermath_phase`(:1158), `_apply_subordinate_injuries`(:1134), `get_aftermath_report`(:1220) |
| ターン/UI/永続化 | 8 | `process_turn`(:1262), `get_defense_ui_state`(:1303), `balance_test`(:1357), `to_dict`(:1405), `from_dict`(:1440) |

### 分割候補

| # | 新モジュール (ルート直下) | 移動対象 | 方式 |
|---|---|---|---|
| 4.1 | `base_defense_data.py` | enum 4 + dataclass 5 (`DefenseFacility` 含む ≈300行) | クラス移動 (独立) |
| 4.2 | `base_defense_facilities.py` | 施設管理 9 メソッド | Mixin 化 |
| 4.3 | `base_defense_raid.py` | 襲撃フェーズ機械 11 メソッド | Mixin 化 — **フェーズ境界で切る**。WARNING+BREACH を 1 単位とし AFTERMATH とは分けない (跨ぎ呼び出し `_return_to_normal` があるため) |
| 4.4 | トランク (旧名維持) | `BaseDefenseManager` 核心 (警告度/事後処理/ターン/永続化) + Mixin 組立 + 再エクスポート | 残置 |

**回帰テスト:** `tests/test_skill_eater_base_defense.py` (50 tests: `test_step11_can_build_facility_...` 〜 `test_step68_warning_phase_transition`, fixture `defense_manager`/`built_defense_manager` は `BaseDefenseManager` を直接生成 — 再エクスポートでそのまま動く), `tests/test_audit_defense_phase0.py` (48), `tests/legacy/test_skill_eater_phase2.py` (9), `tests/test_skill_eater_masterpiece_phase4.py` (2)。

---

## 5. ui_fx_systems.py — 分割候補 5 単位 (推奨順序: 4番目)

**根拠:** import 元 **25 ファイル**で最多だが、クラスはすべて小型 (~10-175行) で相互依存が薄い。25 個の呼び出し側を一切触らずに済ませるのが設計の要 — トランクを再エクスポート専用にする。

### 実測構造 (AST: 23 クラス + 3 関数)

機能クラスタごとの内訳 (行位置は現 working tree):

| クラスタ | クラス/関数 |
|---|---|
| FX プリミティブ | `FloatingText`(:31), `Particle`(:48), `ScreenShake`(:320), `FloatingNotification`(:274), `NotificationManager`(:284) |
| UI ウィジェット | `LookCursor`(:70), `ContextAction`(:82), `ContextMenu`(:92), `MiniMapRenderer`(:107), `GaugeBar`(:187), `HelpSystem`(:351) |
| チュートリアル | `TutorialGuide`(:212), `TutorialManager`(:231) |
| ライティング/天候 | `LightSource`(:176), `DynamicLighting`(:997, 175行), `WeatherAtmosphereLayer`(:515, 147行), `ScreenFilterManager`(:664, 128行) |
| パネル/UI 表示 | `SkillTreeUI`(:417), `JobUI`(:461), `PetUI`(:507), `ItemInspectorUI`(:794, 93行), `EmotionalUI`(:889), `CinematicLogVisualizer`(:948) |
| 関数 | `play_pet_fusion_fx`(:469), `format_skill_tree_display`(:1174), `format_job_display`(:1196) |

### 分割候補

| # | 新モジュール (ルート直下) | 移動対象 | 推定行数 |
|---|---|---|---|
| 5.1 | `ui_fx_primitives.py` | FloatingText / Particle / ScreenShake / FloatingNotification / NotificationManager | ≈115 |
| 5.2 | `ui_fx_widgets.py` | LookCursor / ContextAction / ContextMenu / MiniMapRenderer / GaugeBar / HelpSystem / TutorialGuide / TutorialManager | ≈235 |
| 5.3 | `ui_fx_lighting.py` | LightSource / DynamicLighting / WeatherAtmosphereLayer / ScreenFilterManager | ≈470 |
| 5.4 | `ui_panels.py` | SkillTreeUI / JobUI / PetUI / ItemInspectorUI / EmotionalUI / CinematicLogVisualizer / format_skill_tree_display / format_job_display / play_pet_fusion_fx | ≈400 |
| 5.5 | トランク (旧名維持) | **再エクスポートのみ** (`from ui_fx_primitives import ...` 等 + `__all__`) | ≈40 |

実施順は 5.1 → 5.2 → 5.3 → 5.4。**呼び出し側 25 ファイル (`engine/engine.py`, `render_system.py`, `fx_manager.py`, `managers/context_menu_builder.py`, `core/system_initializer.py` 等は変更禁止** — トランク再エクスポートが契約)。

**回帰テスト:** `tests/test_ui_fx_systems.py` (159 tests: `TestFXManagerCore`, `TestUiFxPrimitives`, `TestVisualFxParticles`, `TestTimeOfDayFX` 等 18 クラス), `tests/test_ux_enhancements.py`, `tests/test_skill_tree_job_system_72_steps.py`, `tests/test_pet_contract_evolution_fusion_72_steps.py`, `tests/test_crafting_systems.py` (一部が ui_fx 経由)。

---

## 6. skill_eater_territory_system.py — 分割候補 5 単位 (推奨順序: **5番目 = 最後** / 最高リスク)

**根拠 (最重要):** このファイルには**専用テストが 1 本も存在しない** (AST 調査 + `grep -rln TerritoryState tests/` 実測ゼロ)。しかも `engine/engine.py` (lazy import :532/:539), `save_system.py` (:333 lazy), `skill_eater_territory_ui.py` (:11) という中枢 3 ファイルが結合し、`TerritoryState` は singleton。**分割の前に characterization test の新設が必須** — テストゼロの巨大 singleton を動かすのは PR #8 の失敗を再現する行為と同義。

### 実測構造 (AST)

- データ/列挙クラス群 :19-276 (8 個): `TerritoryActionType`, `District`(:45, 49行), `ActionResult`, `SabotageEffect`, `CeasefireAgreement`, `ActionLog`, `DynamicEventType`, `DynamicEvent`(:237, 40行) — `to_dict`/`from_dict` 持ちが中心
- `TerritoryState` :279-1102 (**824行, 54メソッド**, singleton)
- Action クラス群 :1108-1462: `TerritoryActionBase` + `PatrolAction` / `RaidAction` / `PropagandaAction` / `SabotageAction` / `NegotiateCeasefireAction`
- `TerritoryController` :1465-1532 (68行, 5メソッド)

### `TerritoryState` の機能ブロック (実測メソッド分類)

| ブロック | メソッド数 | 代表メソッド (行位置) |
|---|---|---|
| 状態参照/計算 | 13 | `calculate_stability`(:337), `calculate_resource_output`(:358), `calculate_turn_income`(:381), `is_safe_passage`(:387), `check_exclusive_shop_unlock`(:403), `check_hidden_dungeon_reveal`(:411) |
| ターン進行 | 8 | `on_turn_start`(:433), `on_turn_end`(:444), `_distribute_turn_income`(:456), `_update_stability`(:475), `_check_district_loss`(:494, 29L) |
| 動的イベント | 19 | `check_event_triggers`(:620), `_check_faction_war_trigger`(:644), `_check_betrayal_trigger`(:681), `_check_midas_raid_trigger`(:736), `_apply_faction_war`(:785)〜`_resolve_third_party`(:943), `trigger_event`(:979) |
| プレイヤー介入 | 6 | `get_player_choices`(:995), `apply_player_choice`(:1011), `_intervene_war`(:1026), `_mediate_war`(:1037), `_suppress_betrayal`(:1051) |
| sabotage/ceasefire/永続化 | 8 | `_process_sabotage_effects`(:561), `_process_ceasefire_countdown`(:584), `load_from_yaml`(:302), `to_dict`(:1076), `from_dict`(:1089) |

### 分割候補

| # | 新モジュール (ルート直下) | 移動対象 | 方式 |
|---|---|---|---|
| 6.0 (**前提**) | `tests/test_skill_eater_territory_system.py` **新規** | characterization test: singleton 生成/`to_dict`↔`from_dict` 往復/`on_turn_end` の収入配分/`_check_district_loss`/イベント 4 種の発火 → apply → resolve/`apply_player_choice`。**現挙動の固定**が目的で理想値の断言をしない | テスト先行 |
| 6.1 | `territory_data.py` | データクラス群 8 個 (全部 `to_dict`/`from_dict` 付きで自己完結) | クラス移動 |
| 6.2 | `territory_actions.py` | `TerritoryActionBase` + 5 action クラス + `TerritoryController` (:1108-1532, ≈425行) — 既に綺麗に分かれたクラス群 | クラス移動 |
| 6.3 | `territory_state.py` | `TerritoryState` コア (状態参照/ターン進行/永続化) | singleton ごと移動しトランクから再エクスポート |
| 6.4 | `territory_events.py` | 動的イベント 19 + 介入 6 メソッド | Mixin 化 (6.3 の完了後) |
| 6.5 | トランク (旧名維持) | 再エクスポート (`TerritoryState`, `District`, `TerritoryController`, ... の全公開名) | 残置 |

**結合先の保護確認リスト (実測):**
- `skill_eater_territory_ui.py:11` モジュール先頭 `from skill_eater_territory_system import (...)` — トランク再エクスポートで無変更
- `engine/engine.py:532/:539` 関数内 lazy `from skill_eater_territory_system import TerritoryState` — 同上
- `save_system.py:333` 関数内 lazy `from skill_eater_territory_system import TerritoryState` (セーブ移行処理) — 同上

**回帰テスト:** 既存ゼロ → 6.0 の characterization tests (新規) + セーブ経路スモーク (`tests/test_core_systems.py:905-921` が save_system の `territory` キーを `territory_state=None` で exercise — `TerritoryState.from_dict` 実体経路は 6.0 で新規に固定する) + 案2 の永続化回帰 (`tests/test_entity_personality_persistence.py` が示す save/load 契約)。

---

## 7. 推奨順序 (リスク低 → 高) と各ステップの完了条件

| 順 | ファイル | 候補数 | リスク評価の根拠 |
|---|---|---|---|
| 1 | skill_eater_facility_actions.py | 6 | 関数の束・状態なし・テスト 45 本 |
| 2 | skill_eater_black_market.py | 6 | import 元テストのみ・singleton あり・テスト 12 本 |
| 3 | skill_eater_base_defense.py | 4 | テスト 109 本で網厚い・フェーズマシンの跨ぎあり |
| 4 | ui_fx_systems.py | 5 | import 元 25 件だが全クラス小型・facade で遮断・テスト 159 本 |
| 5 | skill_eater_territory_system.py | 5 | **テストゼロ + 中枢 3 ファイル結合 + singleton** — 6.0 (characterization tests) が完了するまで着手しない |

**各ステップの完了条件 ( Definition of Done ):**

1. 移動 diff が「移動 + import/再エクスポート」のみで、ロジック変更を含まない (`git diff --stat` と目視で確認)。
2. 対象影響テスト群が baseline と同一結果 (既知債務 15 件の差分ゼロ)。
3. `tests/test_entrypoint.py` + `tests/test_narou_package_init.py` 緑。
4. `pip wheel . --no-deps -w /tmp/narou_wheel_test` 成功。
5. `ruff check` 新規違反ゼロ。
6. 1 ファイルの全候補完了時点でフルスイート 1 回 (差分判定)。

---

## 8. 明示的にやらないこと (非目標)

- `naRou/` 配下への物理移動・新サブパッケージ作成 (PR #8 の再現になるため)。
- 呼び出し側 (engine / save_system / economy / ui 系 25+3 ファイル) の import 書き換え。
- メソッドのリネーム、docstring・ログ文言の改変、挙動調整 (案5 の重複解消スコープと混ぜない)。
- pyproject.toml の変更 (ルートフラット分割の限り不要)。`from constants import Element` が wheel で失敗する既知制約の解消も本計画の範囲外 (包む範囲を変えない方針は既に確定済み)。

