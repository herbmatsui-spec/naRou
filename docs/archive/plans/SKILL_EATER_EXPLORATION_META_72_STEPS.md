# SkillEaterExplorationMeta Implementation Plan
## 探索メタプログレッション・アセンション連動システム 72ステップ実装計画

---

## 概要
既存システム（探索・アセンションボード・バウンティ・概念結晶・転生）を連携させ、探索経験値・ランク・アセンションノード解放・バウンティ対象追加・概念結晶ドロップ・ニューゲーム+引継ぎを統合する。

**対象システム:**
- `skill_eater_exploration_system.py` - 探索システム
- `skill_eater_dungeon_floor_manager.py` - フロア管理
- `skill_eater_ascension_board.py` - アセンションボード
- `skill_eater_bounty_system.py` - バウンティ
- `skill_eater_concept_crystal.py` - 概念結晶
- `meta_progression_system.py` - メタプログレッション
- `reincarnation_system.py` - 転生システム
- `skill_eater_audio_system.py` / `skill_eater_presentation_system.py` - 音響・演出

---

## フェーズ1: 探索経験値・ランキングシステム (Steps 1-12)

### Step 1: ExplorationRank データクラス追加
**ファイル:** `skill_eater_exploration_system.py`
- `ExplorationRank` クラスを `@dataclass` で定義
- フィールド: `rank: int`, `total_exp: int`, `max_depth_reached: int`, `rooms_visited: int`, `first_visit_bonuses: int`, `secret_rooms_found: int`, `floors_cleared: int`
- `EXP_PER_RANK = 1000` 定数定義
- `calculate_rank_from_exp(exp)` 静的メソッド追加

### Step 2: ExplorationState へのランキング統合
**ファイル:** `skill_eater_exploration_system.py`
- `SkillEaterExplorationSystem` クラスに `exploration_rank: ExplorationRank` フィールド追加
- `__init__` で初期化 (`rank=1, total_exp=0, ...`)
- `visited_rooms: set[str]`, `visited_floors: set[int]` セット追加（初見判定用）

### Step 3: 初見ボーナス判定ロジック
**ファイル:** `skill_eater_exploration_system.py`
- `_is_first_visit(room_id: str) -> bool` メソッド追加
- `_is_first_floor(floor_depth: int) -> bool` メソッド追加
- `_is_secret_room(room: DungeonRoom) -> bool` メソッド追加（`room.name` に "秘密" または "隠し" 含む判定）

### Step 4: 探索経験値計算式実装
**ファイル:** `skill_eater_exploration_system.py`
- `_calculate_exploration_exp(depth: int, room_count: int, is_first_visit: bool, is_first_floor: bool, is_secret: bool) -> int` メソッド追加
- 計算式: `base = depth * room_count * 10` + `first_visit_bonus = 500 if is_first_visit else 0` + `first_floor_bonus = 1000 if is_first_floor else 0` + `secret_bonus = 2000 if is_secret else 0`

### Step 5: 経験値付与・ランクアップ処理
**ファイル:** `skill_eater_exploration_system.py`
- `add_exploration_exp(exp: int) -> tuple[int, bool]` メソッド追加（獲得経験値, ランクアップしたか）
- 経験値加算 → `total_exp` 更新 → 新ランク計算 → ランクアップ時 `True` 返却
- ランクアップ時: `exploration_rank.rank` 更新、称号取得フラグ立てる

### Step 6: ランクアップ演出・音声連動
**ファイル:** `skill_eater_exploration_system.py`
- `_play_rank_up_fanfare()` メソッド追加
- `presentation.add_event(emote_file="emote_crown.png", audio_file="rank_up_fanfare.ogg", message=f"探索ランク {new_rank} に昇格！")`
- `audio.play_sound("rank_up_fanfare.ogg")`

### Step 7: move_to_room に経験値付与統合
**ファイル:** `skill_eater_exploration_system.py`
- `move_to_room()` 内で `_is_first_visit()` 判定
- `_calculate_exploration_exp()` 呼び出し
- `add_exploration_exp()` 呼び出し
- ランクアップ時は fanfare 再生

### Step 8: フロア移動時の初見フロアボーナス
**ファイル:** `skill_eater_dungeon_floor_manager.py`
- `_perform_transition()` 内で `_is_first_floor()` 判定
- 初見フロア到達時に探索経験値付与（フロア深度 × 100 + 1000ボーナス）
- `SkillEaterExplorationSystem.get_instance()` 経由で呼び出し

### Step 9: 秘密部屋発見ボーナス
**ファイル:** `skill_eater_exploration_system.py`
- `discover_secret_room(room_id: str) -> ExplorationResult` メソッド追加
- 秘密部屋判定 → 経験値付与（2000ボーナス） → `secret_rooms_found` インクリメント
- `emote_crystal.png` + `crystal_resonance.ogg` 演出

### Step 10: フロアクリア時ボーナス
**ファイル:** `skill_eater_dungeon_floor_manager.py`
- `clear_current_floor()` 内で探索経験値付与
- ボーナス: `depth * 200` + `floors_cleared * 100`
- `floors_cleared` カウンターインクリメント

### Step 11: 探索ランクUI表示用データ取得
**ファイル:** `skill_eater_exploration_system.py`
- `get_exploration_rank_info() -> dict` メソッド追加
- 戻り値: rank, total_exp, next_rank_exp, max_depth, rooms_visited, secrets_found, floors_cleared

### Step 12: セーブ/ロード対応（探索ランキング永続化）
**ファイル:** `skill_eater_exploration_system.py`
- `to_dict()` / `from_dict(data)` メソッド追加
- `exploration_rank`, `visited_rooms`, `visited_floors` をシリアライズ
- `migration_pipeline.py` への登録は不要（既存の仕組みで自動対応）

---

## フェーズ2: アセンションボード連動ノード解放 (Steps 13-24)

### Step 13: AscensionBoard に探索連動ノード定義追加
**ファイル:** `skill_eater_ascension_board.py`
- `EXPLORATION_NODES: dict[str, dict]` クラス定数追加
- ノード定義例:
  - `"deep_delver"`: 深層到達（深度50/100/150/200で段階解放）
  - `"full_clearer"`: 全区画制覇（全フロアクリア）
  - `"secret_finder"`: 秘密部屋全発見（全秘密部屋数）
  - `"speed_runner"`: 速攻クリア（一定ターン以内）
  - `"hazard_master"`: ハザード制御（ハザードレベル0維持）

### Step 14: ノード解放条件チェックメソッド
**ファイル:** `skill_eater_ascension_board.py`
- `_check_exploration_node_conditions(exploration_rank: ExplorationRank, dungeon_manager: SkillEaterDungeonFloorManager) -> list[str]` メソッド追加
- 戻り値: 新たに解放されたノードIDリスト
- 各ノードの条件を評価し、未解放かつ条件満たすものを返す

### Step 15: ノード解放実行メソッド
**ファイル:** `skill_eater_ascension_board.py`
- `unlock_exploration_node(node_id: str, exploration_rank: ExplorationRank) -> dict` メソッド追加
- ノードを `nodes[node_id]["equipped_core"] = "EXPLORATION_UNLOCK"` としてマーク
- `_recalculate_synergies()` 呼び出し
- 解放時のパッシブバフ付与（例: 深層到達で全属性耐性+10%等）

### Step 16: 探索連動ノード用パッシブバフ定義
**ファイル:** `skill_eater_ascension_board.py`
- `EXPLORATION_NODE_BUFFS: dict[str, dict[str, float]]` 追加
- 例:
  - `deep_delver`: `{"all_resistance": 10, "max_hp_bonus": 50}`
  - `full_clearer`: `{"item_find_rate": 25, "gold_gain": 20}`
  - `secret_finder`: `{"crit_rate": 15, "secret_detection": 50}`
  - `speed_runner`: `{"speed": 10, "turn_time_reduction": 15}`
  - `hazard_master`: `{"hazard_resistance": 100, "mp_cost_reduction": 20}`

### Step 17: ノード解放時の演出・音声
**ファイル:** `skill_eater_ascension_board.py`
- `_play_node_unlock_fanfare(node_id: str)` メソッド追加
- `presentation.add_event(emote_file="emote_crown.png", audio_file="ascension_node_unlock.ogg", message=f"アセンションノード『{node_name}』解放！")`

### Step 18: 探索システムからアセンションボードへの通知
**ファイル:** `skill_eater_exploration_system.py`
- `_check_and_unlock_ascension_nodes()` メソッド追加
- `AscensionBoard.get_instance()` 取得 → `_check_exploration_node_conditions()` 呼び出し
- 解放されたノード分 `_play_node_unlock_fanfare()` 実行

### Step 19: 部屋移動時のノードチェック
**ファイル:** `skill_eater_exploration_system.py`
- `move_to_room()` 末尾で `_check_and_unlock_ascension_nodes()` 呼び出し

### Step 20: フロアクリア時のノードチェック
**ファイル:** `skill_eater_dungeon_floor_manager.py`
- `clear_current_floor()` 末尾で `_check_and_unlock_ascension_nodes()` 呼び出し

### Step 21: 秘密部屋発見時のノードチェック
**ファイル:** `skill_eater_exploration_system.py`
- `discover_secret_room()` 末尾で `_check_and_unlock_ascension_nodes()` 呼び出し

### Step 22: アセンションボード状態取得API拡張
**ファイル:** `skill_eater_ascension_board.py`
- `get_exploration_node_status() -> dict` メソッド追加
- 各探索連動ノードの: 解放済みか、進捗率、残り条件 を返却

### Step 23: 深層到達ノードの段階的解放実装
**ファイル:** `skill_eater_ascension_board.py`
- `deep_delver` を段階的（Lv1:深度50, Lv2:深度100, Lv3:深度150, Lv4:深度200）に対応
- `_check_exploration_node_conditions()` で深度に応じたレベル判定
- `nodes["deep_delver"]["level"]` で現在レベル管理

### Step 24: アセンションボード連動テスト追加
**ファイル:** `test_skill_eater_phase3.py` または新規テストファイル
- 深度50到達でノード解放確認
- 全フロアクリアでノード解放確認
- 秘密部屋全発見でノード解放確認
- パッシブバフ適用確認

---

## フェーズ3: バウンティシステム連動・深層敵対象化 (Steps 25-36)

### Step 25: MidasBountyManager に深層敵対象追加
**ファイル:** `skill_eater_bounty_system.py`
- `DEEP_DUNGEON_TARGETS: dict[str, dict]` クラス定数追加
- 対象例:
  - `"abyss_warden"`: 深層の守護者（深度100+、ユニークスキル「虚無の障壁」）
  - `"void_stalker"`: 虚空の追跡者（深度150+、ユニークスキル「次元断絶」）
  - `"babel_architect"`: バベルの設計者（深度200、ユニークスキル「創世の権能」）
  - `"shadow_broker_01"` 〜 `"shadow_broker_05"`: 闇市場指名手配犯（ランダム深度出現）

### Step 26: バウンティ対象の動的生成メソッド
**ファイル:** `skill_eater_bounty_system.py`
- `generate_deep_dungeon_bounties(current_depth: int, dungeon_manager: SkillEaterDungeonFloorManager) -> list[dict]` メソッド追加
- 現在深度に応じて出現可能なバウンティ対象をフィルタリング
- 各フロアのボス部屋・秘密部屋・隠しエリアに配置判定

### Step 27: バウンティ敵のフロア配置連動
**ファイル:** `skill_eater_dungeon_floor_manager.py`
- `_generate_floor()` 内でバウンティ敵配置判定
- `MidasBountyManager.generate_deep_dungeon_bounties()` 呼び出し
- 該当する敵を `boss_room.enemies` または特殊部屋の `enemies` に追加

### Step 28: バウンティ敵討伐時の特別報酬
**ファイル:** `skill_eater_bounty_system.py`
- `eliminate_deep_target(target_id: str, player: CharacterState) -> dict` メソッド追加
- 通常の幹部討伐より高報酬: アルド大量 + 概念結晶シャード + 固有スキル
- `ConceptCrystallizer` 連携で概念結晶生成トリガー

### Step 29: 隠しボス（シークレットボス）実装
**ファイル:** `skill_eater_bounty_system.py`
- `SECRET_BOSSES: dict[str, dict]` 追加
- 出現条件: 特定フロアの全秘密部屋発見、特定アイテム所持、特定派閥評価等
- `check_secret_boss_spawn(floor_depth: int, exploration_rank: ExplorationRank) -> str | None` メソッド追加

### Step 30: 闇市場指名手配犯のランダム出現
**ファイル:** `skill_eater_bounty_system.py`
- `roll_shadow_broker_encounter(current_depth: int) -> dict | None` メソッド追加
- 深度に応じた出現率（深度×0.5%）
- 出現時: 戦闘 → 勝利で高額アルド + 情報アイテム

### Step 31: バウンティ情報収集の探索連動
**ファイル:** `skill_eater_exploration_system.py`
- `gather_bounty_intel(target_id: str) -> ExplorationResult` メソッド追加
- 情報収集コスト: アルド または 探索経験値消費
- 成功で弱点情報取得 → バウンティ戦闘有利に

### Step 32: 罠設置の探索連動（事前準備）
**ファイル:** `skill_eater_exploration_system.py`
- `set_bounty_trap(target_id: str, trap_type: str) -> ExplorationResult` メソッド追加
- 罠タイプ: `EMP`, `SEALING_WARD`, `GRAVITY_WELL`, `CONCEPT_DAMPENER`
- 成功でバウンティ戦闘時デバフ付与（HP-30%, ATK-20%等）

### Step 33: バウンティ戦闘突入フロー
**ファイル:** `skill_eater_exploration_system.py`
- `initiate_bounty_combat(target_id: str) -> ExplorationResult` メソッド追加
- 情報収集・罠設置状況を `MidasBountyManager.initiate_combat()` に渡す
- 戦闘結果に応じて `eliminate_deep_target()` または `eliminate_executive()` 呼び出し

### Step 34: バウンティ討伐時の概念結晶ドロップ連動
**ファイル:** `skill_eater_bounty_system.py`
- `eliminate_deep_target()` 内で概念結晶生成判定
- `ConceptCrystallizer.crystallize_skills()` 呼び出し（バウンティ固有スキル3つを合成）
- 生成された概念結晶をプレイヤーに付与

### Step 35: バウンティUI表示用データ取得
**ファイル:** `skill_eater_bounty_system.py`
- `get_available_bounties(current_depth: int) -> list[dict]` メソッド追加
- 現在深度で挑戦可能なバウンティ一覧（難易度、報酬、出現条件含む）

### Step 36: バウンティ連動テスト追加
**ファイル:** `test_skill_eater_phase2.py` 
- 深層バウンティ生成確認
- 隠しボス出現条件確認
- 闇市場指名手配犯遭遇確認
- 概念結晶ドロップ確認

---

## フェーズ4: 概念結晶ドロップシステム拡張 (Steps 37-48)

### Step 37: ConceptCrystallizer にドロップテーブル追加
**ファイル:** `skill_eater_concept_crystal.py`
- `DROP_TABLES: dict[str, dict]` クラス定数追加
- カテゴリ:
  - `"first_floor_boss"`: 初見フロアボス討伐
  - `"secret_area"`: 秘密エリアクリア
  - `"faction_boss"`: 派閥ボス討伐
  - `"deep_bounty"`: 深層バウンティ討伐

### Step 38: ドロップ判定メソッド
**ファイル:** `skill_eater_concept_crystal.py`
- `roll_concept_crystal_drop(category: str, depth: int, exploration_rank: ExplorationRank) -> dict | None` メソッド追加
- 基礎ドロップ率 + 深度ボーナス + ランクボーナス + 初見補正
- 成功時: カテゴリに応じた概念結晶生成

### Step 39: 初見フロアボス討伐ドロップ
**ファイル:** `skill_eater_dungeon_floor_manager.py`
- `clear_current_floor()` でボス討伐判定
- 初見フロアかつボス討伐時 → `roll_concept_crystal_drop("first_floor_boss", ...)`
- ドロップ時: `emote_crystal.png` + `crystal_resonance.ogg` 演出

### Step 40: 秘密エリアクリアドロップ
**ファイル:** `skill_eater_exploration_system.py`
- `discover_secret_room()` 完了時（敵全討伐等）でドロップ判定
- `roll_concept_crystal_drop("secret_area", ...)`
- 秘密部屋ごとに1回のみドロップ判定

### Step 41: 派閥ボス討伐ドロップ
**ファイル:** `skill_eater_economy_system.py` または `skill_eater_bounty_system.py`
- 派閥ボス（ミダス幹部、レジスタンス首領、銀行総裁、ブローカー親分）討伐時
- `roll_concept_crystal_drop("faction_boss", ...)`
- 派閥ごとに異なる概念結晶カテゴリ（火/氷/闇/金等）

### Step 42: 概念結晶ドロップ演出統一
**ファイル:** `skill_eater_concept_crystal.py`
- `_play_crystal_drop_effect(category: str)` メソッド追加
- `presentation.add_event(emote_file="emote_crystal.png", audio_file="crystal_resonance.ogg", message=f"概念結晶《{crystal_name}》を獲得！")`

### Step 43: 概念結晶の自動合成オプション
**ファイル:** `skill_eater_concept_crystal.py`
- `auto_crystallize_if_possible(player: CharacterState) -> list[dict]` メソッド追加
- 所持スキルから同カテゴリ3つ揃っていれば自動合成提案
- `presentation` で確認プロンプト表示

### Step 44: 探索ランクによるドロップ率補正
**ファイル:** `skill_eater_concept_crystal.py`
- `roll_concept_crystal_drop()` で `exploration_rank.rank` 参照
- ランク毎に +5% ドロップ率上昇（上限 +50%）

### Step 45: 概念結晶ドロップ履歴管理
**ファイル:** `skill_eater_concept_crystal.py`
- `drop_history: list[dict]` フィールド追加
- `{timestamp, category, depth, crystal_name, exploration_rank}` 記録
- `get_drop_history() -> list[dict]` メソッド追加

### Step 46: ドロップ率表示（デバッグ/UI用）
**ファイル:** `skill_eater_concept_crystal.py`
- `get_drop_rates(depth: int, exploration_rank: ExplorationRank) -> dict` メソッド追加
- 各カテゴリの現在ドロップ率を返却

### Step 47: 概念結晶連動テスト追加
**ファイル:** `test_skill_eater_phase4.py`
- 初見ボスドロップ確認
- 秘密エリアドロップ確認
- 派閥ボスドロップ確認
- ランク補正確認

### Step 48: ドロップ音声ファイル存在確認・フォールバック
**ファイル:** `skill_eater_audio_system.py` / 設定確認
- `crystal_resonance.ogg`, `rank_up_fanfare.ogg`, `ascension_node_unlock.ogg` 存在確認
- 不在時は既存音声で代替（`victory.ogg`, `fanfare.ogg` 等）

---

## フェーズ5: ニューゲーム+引継ぎシステム (Steps 49-60)

### Step 49: NewGamePlusData データクラス定義
**ファイル:** `reincarnation_system.py` または新規 `new_game_plus.py`
- `@dataclass NewGamePlusData` 定義
- フィールド: `max_depth_reached`, `total_secrets_found`, `faction_reputations`, `base_tier`, `exploration_rank`, `ascension_nodes_unlocked`, `concept_crystals_owned`, `completed_bounties`

### Step 50: 引継ぎデータ収集メソッド
**ファイル:** `reincarnation_system.py`
- `ReincarnationManager.collect_new_game_plus_data(player, engine) -> NewGamePlusData` メソッド追加
- 各システムからデータ収集:
  - `max_dungeon_depth` (TitleComponent)
  - `exploration_rank` (ExplorationSystem)
  - `secrets_found` (ExplorationSystem)
  - `faction_reputations` (EconomySystem)
  - `base_facilities` levels (EconomySystem)
  - `ascension_board` nodes (AscensionBoard)
  - `concept_crystals` (ConceptCrystallizer / 所持スキルからフィルタ)
  - `defeated_bounties` (BountyManager)

### Step 51: 引継ぎボーナス計算式
**ファイル:** `reincarnation_system.py`
- `_calculate_ng_plus_bonuses(data: NewGamePlusData) -> dict[str, Any]` メソッド追加
- ボーナス内容:
  - 最大深度ボーナス: `depth // 10` → 初期ステータス上昇
  - 秘密発見数: `count * 2` → 初期アイテム発見率上昇
  - 派閥関係: 友好度に応じて初期評価・ショップ割引
  - アジトティア: 施設レベル合計 → 初期施設レベル
  - 探索ランク: ランク × 100 → 初期探索経験値
  - アセンション解放数: ノード数 × 5% → 永続ダメージボーナス
  - 概念結晶所持数: 個数 × 10 → 初期MP上昇

### Step 52: 転生実行時の引継ぎ適用
**ファイル:** `reincarnation_system.py`
- `reincarnate()` 内で `collect_new_game_plus_data()` 呼び出し
- `_calculate_ng_plus_bonuses()` でボーナス計算
- プレイヤー初期ステータス・所持品・施設に適用

### Step 53: 引継ぎ演出・音声
**ファイル:** `reincarnation_system.py`
- 転生完了時に `rank_up_fanfare.ogg` + `emote_crown.png` で「輪廻の記憶継承」演出
- 引継ぎボーナス詳細をメッセージ表示

### Step 54: New Game+ 専用メニュー/UIフック
**ファイル:** `game.py` または UIシステム
- タイトル画面/ゲーム開始時に「輪廻転生（ニューゲーム+）」選択肢追加
- 引継ぎ内容プレビュー表示

### Step 55: 複数周目での難易度スケーリング
**ファイル:** `reincarnation_system.py` / `meta_progression_system.py`
- `reincarnation_count` に応じた敵強化・報酬増加
- `CycleModifierData` を活用（既存システムと統合）

### Step 56: メタプログレッション連動（永続ボーナス）
**ファイル:** `meta_progression_system.py`
- `MetaProgressionManager.recalculate_and_apply_bonuses()` でNG+ボーナスも合算
- `permanent_bonuses` に NG+ 由来ボーナスをマージ

### Step 57: 引継ぎデータのセーブ/ロード
**ファイル:** `reincarnation_system.py`
- `NewGamePlusData.to_dict()` / `from_dict()` 実装
- セーブデータに `ng_plus_data` キーで保存

### Step 58: 周回プレイ時の初期化処理
**ファイル:** `game.py` / `engine.py`
- 新規ゲーム開始時、NG+データ存在なら自動適用
- `ReincarnationManager.apply_ng_plus_bonuses(player, ng_plus_data)` 呼び出し

### Step 59: 引継ぎ上限・バランス調整パラメータ
**ファイル:** `reincarnation_system.py` 定数または設定ファイル
- `MAX_NG_PLUS_BONUS_CAP = 50` 等の上限定数
- 各ボーナスの係数を外部設定可能に

### Step 60: NG+ 統合テスト
**ファイル:** 統合テスト
- 1周目クリア → 2周目開始でボーナス適用確認
- 深度・秘密・派閥・アジト・ランク・アセンション・結晶・バウンティ全項目確認
- 複数周（3周目以降）での累積確認

---

## フェーズ6: 音響・演出リソース統合 (Steps 61-66)

### Step 61: 必要音声ファイルリストアップ・配置確認
**ファイル/ディレクトリ:** `assets/audio/`
- 必要ファイル: `rank_up_fanfare.ogg`, `ascension_node_unlock.ogg`, `crystal_resonance.ogg`
- 既存: `victory.ogg`, `fanfare.ogg`, `warning.ogg`, `alarm.ogg` 等で代替可能
- 不足分は Kenney Foley Sound Effects 等から取得・配置

### Step 62: 必要エモート画像ファイル確認
**ファイル/ディレクトリ:** `assets/emote/pixel/style1/`
- 必要ファイル: `emote_crown.png`, `emote_crystal.png`
- 既存: `emote_star.png`, `emote_heart.png`, `emote_exclamation.png` 等で代替可能

### Step 63: 音声・エモート欠損時のフォールバック実装
**ファイル:** `skill_eater_presentation_system.py`
- `add_event()` 内でファイル存在チェック
- 不在時: 代替ファイル指定または演出スキップ（ログのみ）

### Step 64: 音響ボリューム別再生制御
**ファイル:** `skill_eater_audio_system.py`
- `play_sound()` で効果音/環境音/BGM の音量カテゴリ別制御
- 設定: `sfx_volume`, `bgm_volume`, `ui_volume`

### Step 65: 演出イベントの優先度制御
**ファイル:** `skill_eater_presentation_system.py`
- `PresentationEvent` に `priority: int` フィールド追加
- 同時発生時: 高優先度（ランクアップ、ノード解放、結晶ドロップ）を優先表示

### Step 66: 演出テスト・動作確認
**ファイル:** 手動確認 / 既存テスト拡張
- 全音声・エモート正常再生確認
- 同時発生時の優先度動作確認
- ミュート設定時の挙動確認

---

## フェーズ7: 統合・バランス調整・最終確認 (Steps 67-72)

### Step 67: 探索経験値バランス調整
- 実プレイ想定での経験値曲線シミュレーション
- 深度1-99でのランクカーブ確認
- 必要に応じて `EXP_PER_RANK` や係数調整

### Step 68: アセンションノード解放条件バランス調整
- 深層到達: 深度50/100/150/200 が適切か
- 全区画制覇: 99フロア全クリアは現実的か（主要フロアのみ等に緩和検討）
- 秘密部屋全発見: 総数と発見率のバランス

### Step 69: バウンティ報酬・難易度バランス調整
- 深層バウンティの報酬がリスクに見合うか
- 概念結晶ドロップ率の適正化
- 隠しボス出現率の調整

### Step 70: 概念結晶ドロップ率・効果バランス調整
- カテゴリ別ドロップ率の適正化
- 概念結晶の性能がゲームバランスを崩さないか
- 自動合成の利便性確認

### Step 71: ニューゲーム+ボーナス上限・累積バランス確認
- 10周目等でのステータスインフレ抑制確認
- 上限値・減衰曲線の妥当性確認
- 初回プレイヤーと周回プレイヤーの格差緩和

### Step 72: 総合統合テスト・ドキュメント更新
- 全機能連動テスト（探索→経験値→ランクアップ→アセンション解放→バウンティ出現→結晶ドロップ→転生→引継ぎ→2周目）
- エッジケース（セーブ/ロード、中断復帰、エラー耐性）
- `README.md` / 実装ドキュメント更新
- 変更履歴・既知の問題まとめ

---

## 実装順序の依存関係まとめ

```
Phase 1 (Steps 1-12): 基盤 - 独立実装可能
    ↓
Phase 2 (Steps 13-24): Phase1完了後 - AscensionBoard拡張
    ↓
Phase 3 (Steps 25-36): Phase1完了後 - BountySystem拡張（並行可）
    ↓
Phase 4 (Steps 37-48): Phase1,3完了後 - CrystalSystem拡張
    ↓
Phase 5 (Steps 49-60): Phase1-4完了後 - Reincarnation統合
    ↓
Phase 6 (Steps 61-66): 並行可能 - リソース配置
    ↓
Phase 7 (Steps 67-72): 全完了後 - 調整・テスト
```

---

## 実装時の注意事項

1. **シングルトンパターン踏襲**: 既存システム（`get_instance()`）に合わせる
2. **演出システム連携**: `presentation.add_event()` + `audio.play_sound()` の組み合わせ必須
3. **循環インポート回避**: `TYPE_CHECKING` で型ヒントのみインポート、実行時は遅延インポート
4. **エラーハンドリング**: `try/except` で音声再生失敗等を吸収（既存パターン踏襲）
5. **モックモード対応**: `is_mock_only=True` 時は全演出スキップ
6. **セーブ互換**: 新フィールド追加時はデフォルト値設定で後方互換維持
7. **テストファースト**: 各ステップ完了時に該当テスト実行・パス確認

---

## 推奨実装コマンド例

```bash
# Step 1-3 実装後
python -m pytest tests/test_skill_eater_exploration_rank.py -v

# Phase 1 完了後
python -m pytest tests/test_skill_eater_exploration_meta_phase1.py -v

# 統合テスト
python -m pytest tests/test_skill_eater_exploration_meta_integration.py -v
```

---

*作成日: 2026-08-22*
*対象: naRou Roguelike - Skill Eater World A*
*想定実装期間: 72ステップ × 約30分/ステップ = 約36時間*