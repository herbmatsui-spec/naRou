# SkillEaterWorldClock - 72段階実装計画

## 概要
ターン制システムに「時間帯」「NPCスケジュール」「施設稼働」「プレイヤー行動消費」「音響」を統合する世界時計システム。

**時間帯サイクル**: DAWN(0-6) / DAY(6-18) / DUSK(18-22) / NIGHT(22-24) — 4フェーズ  
**NPCスケジュール**: ブローカー夜のみ / 検査官昼襲撃 / 闘技場開催時間 / 移動商人ルート  
**施設稼働**: 研究室夜ボーナス / 工房昼効率 / 医療ベイ24h  
**プレイヤー行動**: explore(2h) craft(3h) sleep(6h→全回復) wait(1h)  
**音響**: clock_tower_bell.ogg / shift_change_announcement.ogg / night_ambience.ogg / dawn_ambience.ogg

---

## Phase 1: コア時計システム (Steps 1-12)

### Step 1: TimePhase Enum作成
- ファイル: `naRou/time_system.py` (新規)
- Enum `TimePhase` 定義: `DAWN=0`, `DAY=1`, `DUSK=2`, `NIGHT=3`
- 各フェーズの開始時間・終了時間を属性として保持

### Step 2: WorldClock クラス骨格作成
- ファイル: `naRou/time_system.py`
- クラス `WorldClock` 定義
- フィールド: `current_hour: int`, `current_minute: int`, `current_day: int`, `ticks_per_hour: int = 100`
- メソッド: `advance(hours: int)`, `get_phase() -> TimePhase`, `to_string() -> str`

### Step 3: 時間経過ロジック実装
- `advance(hours)` で hour/minute/day 更新
- 24時で日付変更、`NEW_DAY` イベント発行 (既存 `event_bus` 利用)
- 月末・年末処理 (既存 `TimeSystem` 互換)

### Step 4: 既存 TimeSystem との統合
- `turn_manager.py` の `TimeSystem` を継承または委譲
- `pass_ticks()` 内で `WorldClock.advance()` 呼び出し
- 互換性維持: 既存 `year/month/day/hour/minute` プロパティ維持

### Step 5: フェーズ遷移イベント発行
- フェーズ変化時に `PHASE_CHANGED` イベント発行 (`old_phase`, `new_phase`)
- `event_bus.publish("PHASE_CHANGED", {"old": old, "new": new})`

### Step 6: セーブ/ロード対応
- `to_dict()` / `from_dict(cls, data)` 実装
- 保存項目: hour, minute, day, month, year, ticks

### Step 7: シングルトンアクセス用関数
- `get_world_clock() -> WorldClock` グローバル関数
- エンジン初期化時にインスタンス生成

### Step 8: 設定ファイル対応
- `data/time_config.yaml` 作成
- フェーズ定義、ティック/時間比率、音響ファイルパスを外部化

### Step 9: 設定読み込み実装
- `WorldClock.load_config(path)` クラスメソッド
- YAML パース、デフォルト値フォールバック

### Step 10: デバッグ用コマンド追加
- `debug.py` に `cmd_time` 追加
- 現在時刻表示、強制時間経過、フェーズ強制変更

### Step 11: 単体テスト作成
- `tests/test_world_clock.py` 作成
- フェーズ判定、時間経過、日付変更、セーブ/ロードテスト

### Step 12: 統合テスト・動作確認
- 既存ターンシステムと併用で時間が正しく進むか確認
- `NEW_DAY` イベントが正しく発火するか確認

---

## Phase 2: NPCスケジュールシステム (Steps 13-28)

### Step 13: NPCSchedule データクラス定義
- ファイル: `naRou/npc_schedule.py` (新規)
- `@dataclass NPCSchedule`: `npc_id`, `name`, `active_phases: list[TimePhase]`, `location: str`, `conditions: dict`

### Step 14: スケジュールレジストリ作成
- クラス `NPCScheduleRegistry` (シングルトン)
- メソッド: `register(schedule)`, `get_active_npcs(phase) -> list`, `get_npc_schedule(npc_id)`

### Step 15: デフォルトNPCスケジュール定義 (YAML)
- `data/npc_schedules.yaml` 作成
- ブローカー: `active_phases: [NIGHT]`, `location: "back_alley"`
- 検査官: `active_phases: [DAY]`, `location: "inspection_office"`, `raid_chance: 0.3`
- 闘技場受付: `active_phases: [DUSK, NIGHT]`, `location: "arena"`
- 移動商人: ルート定義 (location を時間帯で切替)

### Step 16: YAML読み込み実装
- `NPCScheduleRegistry.load_from_yaml(path)` 実装
- `TimePhase` 文字列→Enum変換

### Step 17: 移動商人ルートシステム
- `MerchantRoute` クラス: `stops: list[tuple[TimePhase, str]]` (フェーズ, 場所)
- `get_current_location(phase) -> str` 実装

### Step 18: NPC出現判定ロジック
- `WorldClock.get_active_npcs() -> list[str]` 実装
- 現在フェーズでアクティブなNPC IDリスト返却

### Step 19: 検査官襲撃イベント統合
- DAY フェーズ時に確率で `INSPECTOR_RAID` イベント発行
- `event_bus.publish("INSPECTOR_RAID", {"intensity": 1-3})`

### Step 20: 闘技場開催スケジュール
- DUSK/NIGHT 開催時 `ARENA_OPEN` イベント
- 開催中のみ闘技場コマンド有効化フラグ管理

### Step 21: NPCスケジュールUI表示
- `ui_event_panel.py` に現在出現中NPC一覧表示追加
- 時刻表示横に「出現中: ブローカー, 闘技場受付」等表示

### Step 22: NPCスケジュールセーブ/ロード
- 動的スケジュール変更(イベントによる一時変更)対応
- `to_dict()` / `from_dict()` 実装

### Step 23: 条件付き出現対応
- `conditions` に `faction_reputation`, `player_level`, `quest_flag` 等指定可能
- `check_conditions(player) -> bool` 実装

### Step 24: テスト・動作確認
- 各時間帯で正しいNPCが出現するか確認
- 移動商人が正しい場所にいるか確認
- 検査官襲撃が発火するか確認

---

## Phase 3: 施設稼働システム (Steps 29-40)

### Step 29: FacilityType Enum定義
- ファイル: `naRou/facility_system.py` (新規)
- Enum `FacilityType`: `LAB`, `WORKSHOP`, `MEDICAL_BAY`, `ARENA`, `SHOP`, `GUILD`

### Step 30: FacilitySchedule データクラス
- `@dataclass FacilitySchedule`: `facility_id`, `type`, `base_efficiency: float`, `phase_modifiers: dict[TimePhase, float]`, `is_24h: bool`

### Step 31: 施設レジストリ作成
- クラス `FacilityRegistry` (シングルトン)
- 登録・取得・現在効率計算メソッド

### Step 32: デフォルト施設定義 (YAML)
- `data/facility_schedules.yaml` 作成
- 研究室: `base_efficiency: 1.0`, `phase_modifiers: {NIGHT: 1.5, DAWN: 1.2}`
- 工房: `base_efficiency: 1.0`, `phase_modifiers: {DAY: 1.3, DUSK: 1.1}`
- 医療ベイ: `is_24h: true`, `phase_modifiers: {}` (常時1.0)
- 闘技場: `active_phases: [DUSK, NIGHT]`
- 店/ギルド: 通常営業時間

### Step 33: 現在効率取得メソッド
- `FacilityRegistry.get_efficiency(facility_id, phase) -> float`
- 24h施設は常に `base_efficiency` 返却
- 非アクティブフェーズは `0.0` 返却

### Step 34: クラフト/研究時間計算への適用
- `skill_eater_economy_system.py` のクラフト時間に効率乗算
- `effective_time = base_time / efficiency`

### Step 35: 探索報酬・遭遇率への適用
- 夜間探索: 遭遇率上昇、レアドロップ率上昇
- 昼間探索: 安全、経験値ボーナス

### Step 36: 医療ベイ24h効果
- 睡眠以外の回復手段(薬、治療)に常時効果
- `MEDICAL_BAY` 使用時 `heal_amount *= efficiency`

### Step 37: 施設UI表示
- 施設メニューに「現在の効率: 130% (昼ボーナス)」等表示
- 次フェーズでの効率変化予告表示

### Step 38: 施設スケジュールセーブ/ロード
- 動的変更(アップグレード、イベントによる一時変更)対応

### Step 39: テスト・動作確認
- 各施設が時間帯で正しい効率を返すか確認
- クラフト時間が効率で変わるか確認
- 医療ベイが常時利用可能か確認

### Step 40: バランス調整用定数外部化
- `data/balance_standards.yaml` に効率係数追加
- 後から数値調整可能に

---

## Phase 4: プレイヤー行動時間消費 (Steps 41-52)

### Step 41: ActionType Enum定義
- ファイル: `naRou/player_actions.py` (新規)
- Enum `ActionType`: `EXPLORE`, `CRAFT`, `SLEEP`, `WAIT`, `TRAVEL`, `TRAIN`, `SHOP`, `TALK`

### Step 42: ActionCost データクラス
- `@dataclass ActionCost`: `action_type`, `base_hours: float`, `stamina_cost: int`, `mp_cost: int`

### Step 43: デフォルト行動コスト定義 (YAML)
- `data/action_costs.yaml` 作成
- explore: 2h, stamina 10
- craft: 3h, stamina 15, mp 5
- sleep: 6h, 全回復
- wait: 1h
- travel: 距離依存 (後で実装)

### Step 44: PlayerActionManager クラス作成
- クラス `PlayerActionManager`
- メソッド: `can_perform(action_type, player) -> bool`, `perform(action_type, player, **kwargs) -> tuple[bool, str, float]` (成功, メッセージ, 消費時間)

### Step 45: 探索アクション実装
- `perform(ActionType.EXPLORE, player)` 
- 2h経過、`WorldClock.advance(2)`
- ダンジョン/フィールド移動処理連携

### Step 46: クラフトアクション実装
- `perform(ActionType.CRAFT, player, recipe_id)`
- 施設効率適用: `actual_hours = 3.0 / facility_efficiency`
- 時間経過、アイテム生成、スキル経験値付与

### Step 47: 睡眠アクション実装
- `perform(ActionType.SLEEP, player)`
- 6h経過 (次の DAWN まで調整オプション)
- HP/MP/Stamina 全回復、空腹・眠気リセット
- `SurvivalSystem.sleep()` 連携

### Step 48: 待機アクション実装
- `perform(ActionType.WAIT, player, hours=1)`
- 指定時間経過、スタミナ微回復
- 次フェーズまで待機オプション

### Step 47: 行動前確認・キャンセル機能
- `can_perform()` でスタミナ/MP/時間帯制限チェック
- 夜間探索警告、施設未営業時クラフト不可等

### Step 48: UI統合 - 行動メニュー
- `ui_event_panel.py` に行動選択メニュー追加
- 消費時間・コスト・効果プレビュー表示
- 実行確認ダイアログ

### Step 49: ターン終了時自動処理
- プレイヤー行動後の `WorldClock.advance(hours)` 自動呼出
- イベント発生チェック (NPC出現、襲撃等)

### Step 50: 時間経過ログ表示
- メッセージログに「2時間経過した (現在: 昼 10:00)」等表示
- フェーズ変更時は強調表示

### Step 51: セーブ/ロード対応
- 消費時間累計、最後に実行したアクション等保存

### Step 52: テスト・動作確認
- 各アクションで正しく時間経過するか
- 睡眠で全回復・日付変更するか
- 施設効率がクラフト時間に反映されるか

---

## Phase 5: 音響システム統合 (Steps 53-64)

### Step 53: 音響ファイル配置確認
- `audio/Audio/clock_tower_bell.ogg` (時報鐘)
- `audio/Audio/shift_change_announcement.ogg` (シフト変更アナウンス)
- `audio/Audio/night_ambience.ogg` (夜環境音ループ)
- `audio/Audio/dawn_ambience.ogg` (朝環境音ループ)
- 不足分はプレースホルダ作成

### Step 54: AudioConfig に時計音響追加
- `data/audio_config.yaml` に `world_clock` セクション追加
- 時報: 毎正時、フェーズ境界
- 環境音: フェーズ別ループ

### Step 55: WorldClockAudioManager クラス作成
- ファイル: `naRou/audio/world_clock_audio.py` (新規)
- クラス `WorldClockAudioManager`
- BGMPlayer と動的音響の併用設計

### Step 56: 時報鐘再生実装
- `play_hour_bell(hour)` - 時間分の鐘を鳴らす (3時なら3回)
- `play_phase_bell(phase)` - フェーズ境界で特殊音
- DAWN: 明るい音、NIGHT: 重い音

### Step 57: シフト変更アナウンス実装
- フェーズ遷移時に `shift_change_announcement.ogg` 再生
- テキスト表示連携: 「夜勤シフトに切り替わります」

### Step 58: 環境音ループ制御
- `start_ambience(phase)` / `stop_ambience()`
- DAWN: `dawn_ambience.ogg`、NIGHT: `night_ambience.ogg`
- DAY/DUSK: 既存環境音 (town_day, town_night) 継続
- クロスフェード切替 (1秒)

### Step 59: WorldClock へのフック統合
- `WorldClock.on_phase_changed` コールバック登録
- フェーズ変更時に音響マネージャー通知

### Step 60: 時間経過時の時報
- `WorldClock.advance()` 内で正時通過チェック
- 通過した正時分 `play_hour_bell()` 呼出

### Step 61: 音量・有効/無効設定
- `feature_flags` または設定ファイルで ON/OFF
- マスターボリューム、環境音ボリューム別個調整

### Step 62: セーブ/ロード時の音響状態復元
- 現在再生中の環境音を保存、ロード時に再開

### Step 63: テスト・動作確認
- フェーズ遷移で正しい音が鳴るか
- 時報が正しく鳴るか
- 環境音がループ・クロスフェードするか

### Step 64: パフォーマンス確認
- 音声再生によるラグ・メモリリークなし確認
- 低スペック環境での動作確認

---

## Phase 6: 統合・UI・仕上げ (Steps 65-72)

### Step 65: 時計表示UI統合
- 画面常時表示: 「Year 517 Month 8 Day 15 昼 10:30」
- フェーズアイコン表示 (太陽/月/星等)
- 次フェーズまでの残り時間表示

### Step 66: 時間帯別ビジュアルエフェクト
- `visual_fx_system.py` 連携
- DAWN: 朝霧、DAY: 明るい、DUSK: 夕焼け、NIGHT: 暗闇+ライト
- パレット切替 (既存 `palette_unifier.py` 活用)

### Step 67: チュートリアル・ヘルプ追加
- `tutorial_guides.yaml` に世界時計説明追加
- 初回プレイ時にポップアップ表示

### Step 68: 設定メニュー統合
- オプション画面に「世界時計設定」追加
- 時間経過速度、音響ON/OFF、通知設定

### Step 69: 既存システムとの整合性確認
- `SurvivalSystem.pass_turn()` との整合 (空腹/眠気は実時間ベースへ)
- `EventScheduler` 季節イベントとの整合
- `WorldStateManager` フェーズとの整合

### Step 70: 総合テストシナリオ実行
- 1週間(ゲーム内)プレイシミュレーション
- NPC出現、施設効率、行動消費、音響すべて確認
- セーブ/ロード後の状態復元確認

### Step 71: ドキュメント更新
- `README.md` または `docs/WORLD_CLOCK.md` 作成
- 仕様書、設定方法、拡張ガイド

### Step 72: 最終調整・リリース準備
- バランス調整 (時間消費量、効率係数)
- バグ修正、リファクタリング
- 変更履歴記録 (CHANGELOG.md)

---

## ファイル構成まとめ

### 新規作成ファイル
```
naRou/time_system.py          # WorldClock, TimePhase
naRou/npc_schedule.py         # NPCSchedule, Registry
naRou/facility_system.py      # FacilityType, Schedule, Registry
naRou/player_actions.py       # ActionType, Cost, Manager
naRou/audio/world_clock_audio.py  # WorldClockAudioManager
data/time_config.yaml         # 時計設定
data/npc_schedules.yaml       # NPCスケジュール
data/facility_schedules.yaml  # 施設稼働
data/action_costs.yaml        # 行動コスト
```

### 修正対象既存ファイル
```
naRou/turn_manager.py         # TimeSystem統合
naRou/systems.py              # SurvivalSystem.sleep() 連携
naRou/skill_eater_economy.py  # クラフト時間効率適用
naRou/ui_event_panel.py       # 時計/NPC/施設/行動UI
naRou/debug.py                # デバッグコマンド
naRou/audio/dynamic_audio.py  # 環境音制御拡張
data/audio_config.yaml        # 音響設定追加
tests/test_world_clock.py     # テスト
```

---

## 依存関係グラフ

```
TimePhase (Step 1)
    ↓
WorldClock (Steps 2-7) ← TimeSystem統合 (Step 4)
    ↓
NPCScheduleRegistry (Steps 13-17) ← WorldClock.get_phase()
    ↓
FacilityRegistry (Steps 29-33) ← WorldClock.get_phase()
    ↓
PlayerActionManager (Steps 44-49) ← WorldClock.advance(), FacilityRegistry.get_efficiency()
    ↓
WorldClockAudioManager (Steps 55-60) ← WorldClock.on_phase_changed, advance()
    ↓
UI統合 (Steps 21, 37, 48, 65) ← すべてのシステム
```

---

## 実装順序のポイント

1. **Phase 1 完了まで他 Phase 開始不可** (コア時計が基盤)
2. **Phase 2, 3 は並行可能** (NPC/施設は独立)
3. **Phase 4 は Phase 1, 3 完了後** (施設効率参照)
4. **Phase 5 は Phase 1 完了後開始可能** (フェーズ変更フックのみ必要)
5. **Phase 6 はすべて完了後** (統合・仕上げ)

---

## 低性能LLM向け実装指針

- 各 Step は **単一ファイル・単一機能** に限定
- 既存コードパターン踏襲: `Registry` シングルトン、`dataclass`、`YAML` 設定、`event_bus` イベント
- 型ヒント必須、docstring 必須
- 1 Step = 1 コミット推奨
- テストは各 Phase 末尾で実行
- 不明点は `question` ツールで確認せず、既存コードから推測して実装