# SkillEaterTerritoryControl 実装計画 (72 Steps)

## 概要
派閥テリトリー・勢力図システムを段階的に実装する。既存の `skill_eater_economy_system.py` の `FactionState` を拡張し、区画マップ・アクション・動的イベント・音響を統合する。

---

## Phase 1: データ構造定義 (Steps 1-12)

### Step 1: District データクラス作成
- ファイル: `skill_eater_territory_system.py` 新規作成
- 内容: `District(id, name, controlling_faction, stability, resource_output, defense_level, hidden_dungeon_entrance, exclusive_shop_unlocked)`
- 型ヒント・デフォルト値・docstring 完備

### Step 2: TerritoryAction Enum 定義
- Enum: `PATROL, RAID, PROPAGANDA, SABOTAGE, NEGOTIATE_CEASEFIRE`
- 各アクションの基本コスト・クールダウン・成功率基礎値を属性として持たせる

### Step 3: FactionState 拡張 (既存修正)
- `skill_eater_economy_system.py` の `FactionState` に追加:
  - `controlled_districts: list[str]` (区画IDリスト)
  - `territory_income_per_turn: int` (ターン収入)
  - `morale: int` (0-100, 士気)
  - `is_at_war: bool` (戦争状態)
  - `war_target: str | None` (敵対派閥ID)

### Step 4: TerritoryState 管理クラス作成
- シングルトン `TerritoryState` クラス
- `districts: dict[str, District]`
- `faction_relations: dict[tuple[str, str], int]` (派閥間関係値 -100 to 100)
- `turn_counter: int`
- `active_events: list[DynamicEvent]`

### Step 5: 初期区画データ YAML 定義
- ファイル: `data/territory_districts.yaml`
- 10-15区画を定義 (名前、初期支配派閥、資源出力、防御レベル、隠しダンジョン有無)
- 例: `industrial_zone`, `slums`, `corporate_district`, `underground_market`, `research_facility`

### Step 6: YAML ロード機能実装
- `TerritoryState.load_from_yaml(path)` 静的メソッド
- 既存の `SkillEaterRegistry.load_from_yaml()` パターンを踏襲
- エラーハンドリング・バリデーション込み

### Step 7: 支配派閥取得・判定メソッド
- `get_controlling_faction(district_id) -> str | None`
- `is_controlled_by(district_id, faction_id) -> bool`
- `get_districts_by_faction(faction_id) -> list[District]`

### Step 8: 安定度・資源出力計算
- `calculate_stability(district) -> int` (0-100)
  - 基礎安定度 + 派閥士気補正 - 隣国敵対度補正
- `calculate_resource_output(district) -> int`
  - 基礎出力 × 安定度/100 × 派閥ボーナス

### Step 9: ターン収入計算・配分
- `calculate_turn_income(faction_id) -> int`
- 全支配区画の `resource_output` 合計
- `FactionState.territory_income_per_turn` に反映

### Step 10: 安全移動判定
- `is_safe_passage(district_id, faction_id) -> bool`
- 支配下区画 + 停戦中派閥区画 + 中立区画 = 安全
- 敵対派閥区画 = 危険 (遭遇率アップ)

### Step 11: 専用ショップ・隠しダンジョン解放条件
- `check_exclusive_shop_unlock(district_id, faction_id) -> bool`
  - 支配継続ターン数 ≥ 10 かつ 安定度 ≥ 70
- `check_hidden_dungeon_reveal(district_id, faction_id) -> bool`
  - 支配継続ターン数 ≥ 20 かつ 安定度 ≥ 80 かつ `hidden_dungeon_entrance == True`

### Step 12: データ永続化・シリアライズ
- `to_dict()` / `from_dict()` 実装
- 既存セーブシステム (`save_game`, `load_game`) との統合準備

---

## Phase 2: アクションシステム実装 (Steps 13-28)

### Step 13: パトロール `patrol()` 基本実装
- 対象: 自派閥支配区画
- 効果: 安定度 +5、資源出力 +5%、クールダウン 1ターン
- コスト: アクションポイント 1、アルド 100
- 戻り値: `(success: bool, message: str, stability_change: int)`

### Step 14: 襲撃 `raid()` 基本実装
- 対象: 敵対派閥支配区画
- 効果: 敵安定度 -15、自派閥影響力 +50、戦争状態移行判定
- コスト: アクションポイント 3、アルド 500、部隊消耗リスク
- 成功率: `(自攻撃力 - 敵防御力 + 50) / 100` クランプ 0.1-0.9

### Step 15: プロパガンダ `propaganda()` 基本実装
- 対象: 中立区画 または 敵支配区画 (隣接必須)
- 効果: 対象区画の支配派閥ロイヤリティ低下、中立なら自派閥寄りに
- コスト: アクションポイント 2、アルド 300
- 成功率: 派閥評判 × 0.5 + 隣接自派閥区画数 × 10

### Step 16: 破壊工作 `sabotage()` 基本実装
- 対象: 敵支配区画
- 効果: 区画の `resource_output` 半減 (3ターン)、`defense_level` -1
- コスト: アクションポイント 3、アルド 800、発覚リスク (評判 -20)
- 成功率: 30% 基礎 + スキル補正

### Step 17: 停戦交渉 `negotiate_ceasefire()` 基本実装
- 対象: 戦争状態の敵派閥
- 効果: 停戦成立で `is_at_war = False`、相互評判 +10、区画返還オプション
- コスト: アクションポイント 2、アルド 2000 (賠償金オプション)
- 成功率: 双方士気・戦況・第三勢力圧力で算出

### Step 18: アクション共通基盤クラス
- `TerritoryActionBase` 抽象基底クラス
- `execute(actor_faction, target_district, **kwargs) -> ActionResult`
- `can_execute(actor_faction, target_district) -> tuple[bool, str]`
- 共通: コスト支払い、クールダウン管理、ログ記録

### Step 19: ActionResult データクラス
- `success: bool`
- `message: str`
- `effects: dict[str, Any]` (stability_change, income_change, reputation_change 等)
- `audio_cue: str | None` (再生するSE名)
- `emote_cue: str | None` (表示するエモート画像)

### Step 20: パトロール詳細実装・テスト
- 実行時: `emote_stars.png` + `chop.ogg` (建設音イメージ)
- 連続パトロールボーナス: 3ターン連続で安定度ボーナス 2倍

### Step 21: 襲撃詳細実装・テスト
- 成功時: `emote_exclamations.png` + `doorOpen_2.ogg` + `handleCoins.ogg`
- 失敗時: `emote_cross.png` + `metalClick.ogg`
- 戦争勃発トリガー: 襲撃成功時 30% で `declare_war()`

### Step 22: プロパガンダ詳細実装・テスト
- 成功時: `emote_speech.png` (新規) + `bookOpen.ogg`
- 中立区画獲得時: 派閥評判 +5、区画 `controlling_faction` 変更
- 失敗時: 逆効果 (敵派閥評判 +5)

### Step 23: 破壊工作詳細実装・テスト
- 成功時: `emote_alert.png` + `knifeSlice.ogg` + `creak.ogg`
- 発覚時: `emote_cross.png` + `metalLatch.ogg`、実行派閥評判 -20、熱レベル +15
- 効果持続: `SabotageEffect` クラスでターン管理

### Step 24: 停戦交渉詳細実装・テスト
- 成功時: `emote_heart.png` (新規) + `negotiation_chime.ogg` (新規音声)
- 条件提示 UI: 賠償金、区画返還、相互不可侵期間
- 破棄時: `declare_war()` 自動発動、評判 -30

### Step 25: アクション実行統合インターフェース
- `TerritoryController.execute_action(faction_id, action_type, district_id, **kwargs)`
- プレイヤー派閥・NPC派閥双方から呼び出し可能
- ターン終了時のクールダウンデクリメント処理

### Step 26: NPC派閥 AI 行動決定
- `NPCFactionAI.decide_action(territory_state) -> (action_type, district_id)`
- 戦略: 拡張主義 / 防衛 / 経済 / バランス
- 簡易評価関数: 期待値 = 成功率 × 効果 - コスト - リスク

### Step 27: アクション履歴・ログ
- `action_history: list[ActionLog]` (派閥、アクション、対象、結果、ターン)
- 最大 100 件保持、古い順に削除
- UI 表示用 `get_recent_actions(limit=10)`

### Step 28: アクション統合テスト
- 全アクションの組み合わせテスト
- エッジケース: 資金不足、クールダウン中、区画不存在、同盟派閥への襲撃等

---

## Phase 3: ターン処理・収入・効果適用 (Steps 29-38)

### Step 29: ターン開始処理フック
- `TerritoryState.on_turn_start(turn_number)`
- 既存 `TurnManager` / `TimeSystem` との連携 (EventBus `NEW_DAY` 等)

### Step 30: ターン収入自動配分
- 全派閥の `calculate_turn_income()` 実行
- `FactionState.influence_points` に加算
- プレイヤー派閥の場合: 通知メッセージ表示

### Step 31: 区画安定度自然変動
- 全区画に対し毎ターン処理:
  - 支配派閥士気 > 50: +1
  - 支配派閥士気 < 30: -2
  - 隣接敵対区画数 × -1
  - 破壊工作中: -5/ターン
- クランプ 0-100

### Step 32: 区画自動失陥判定
- 安定度 ≤ 0 になった区画:
  - `controlling_faction = "neutral"`
  - 隣接最強派閥が自動獲得判定 (影響力比較)
  - イベント発火: `territory_lost`

### Step 33: 専用ショップ解放チェック・適用
- 全支配区画で `check_exclusive_shop_unlock()` 実行
- 解放時: `exclusive_shop_unlocked = True`
- 通知: `emote_stars.png` + `handleCoins2.ogg` + メッセージ

### Step 34: 隠しダンジョン入口発見チェック
- 全支配区画で `check_hidden_dungeon_reveal()` 実行
- 発見時: `hidden_dungeon_entrance = True` (プレイヤーのみ可視化)
- 通知: `emote_exclamations.png` + `territory_capture_fanfare.ogg` (新規)

### Step 35: 破壊工作効果ターン経過処理
- `SabotageEffect.remaining_turns` デクリメント
- 0 到達で効果解除、`resource_output` 復元、`defense_level` 復元
- 解除通知: `emote_stars.png` + `chop.ogg`

### Step 36: 停戦期間カウントダウン
- `CeasefireAgreement.remaining_turns` デクリメント
- 0 到達で自動破棄 → 戦争状態復帰オプション
- 破棄通知: `emote_alert.png` + `metalLatch.ogg`

### Step 37: 派閥士気更新
- 全派閥毎ターン:
  - 支配区画数 × +1
  - 戦争中: -2/ターン
  - 収入 > 支出: +2
  - 収入 < 支出: -3
- クランプ 0-100

### Step 38: ターン終了処理・統計記録
- `TerritoryState.on_turn_end()`
- ターン統計記録: 収入、区画変動、アクション実行数
- `turn_counter` インクリメント

---

## Phase 4: 動的イベントシステム (Steps 39-54)

### Step 39: DynamicEvent データクラス
- `id, name, description, trigger_condition, duration, effects, faction_scope`
- `event_type: EventType` (FACTION_WAR, BETRAYAL, THIRD_PARTY, MIDAS_RAID)
- `is_active: bool`, `remaining_turns: int`

### Step 40: イベントトリガー判定エンジン
- `check_event_triggers(territory_state) -> list[DynamicEvent]`
- 条件例:
  - 派閥戦争: 2大派閥影響力差 < 20% かつ 隣接区画数 ≥ 3
  - 裏切り: 派閥士気 < 20 かつ 支配区画数 ≥ 3
  - 第三勢力: 中立区画数 ≥ 5 かつ 全派閥影響力合計 < 閾値
  - ミダス一斉検挙: `heat_level ≥ 80` かつ 違法区画支配数 ≥ 2

### Step 41: 派閥戦争イベント実装
- 発動: `declare_war(attacker, defender)` 両方向 `is_at_war = True`
- 効果: 双方 `moral -10`、襲撃成功率 +20%、プロパガンダ無効化
- 期間: 10-30ターン (ランダム)
- 終了条件: 一方降伏 / 全面停戦 / 第三勢力介入

### Step 42: 裏切りイベント実装
- 発動: 低士気派閥の区画 1-2個が「反乱派閥」として独立
- 新派閥生成: `rebel_<parent_id>_<turn>`
- 元派閥: 影響力 -300、評判 -15
- 反乱派閥: 中立関係、区画継承、独自AI

### Step 43: 第三勢力介入イベント実装
- 新派閥 `third_party_<name>` 出現 (例: `mercenary_guild`, `ancient_order`)
- ランダム中立区画 2-3個を即時支配
- 既存全派閥と中立スタート、高戦力・高資源
- 目的: 全区画制圧 / 特定派閥殲滅 / 資源独占

### Step 44: ミダス一斉検挙イベント実装
- 条件: `heat_level ≥ 80` (既存システム連携)
- 効果: 違法スキル保有区画・闇市場区画を強制中立化
- プレイヤー: 違法スキル没収、アルド没収 50%、熱レベルリセット
- NPC派閥: 違法区画失陥、影響力 -500、評判 -30
- 音声: `emote_alert.png` + `metalLatch.ogg` 連続 + `riot_crowd.ogg` (新規)

### Step 45: イベント適用・解除システム
- `apply_event(event)` / `remove_event(event)`
- 効果適用: 派閥ステータス変更、区画属性変更、グローバル修正値
- 重複防止: 同種イベント多重発動ブロック

### Step 46: イベント進行・ターン経過
- `update_events(territory_state)` 毎ターン呼出
- `remaining_turns` デクリメント、0 で自動解除
- 期間中効果: ターン毎の追加効果 (士気低下、資源減産等)

### Step 47: イベント連鎖・派生
- 派閥戦争終了 → 勝者に「覇権」バフ (収入 +20% 10ターン)
- 裏切り → 元派閥が「粛清」イベント発動可能に
- 第三勢力撃退 → 全派閥に「団結」バフ (評判 +10)
- ミダス検挙生存 → 「地下抵抗」バフ (違法スキル入手率 UP)

### Step 48: イベント通知・演出統合
- 発生時: `PresentationSystem.add_event()` 連携
- 専用音声・エモート:
  - 派閥戦争: `territory_capture_fanfare.ogg` + `emote_exclamations.png`
  - 裏切り: `riot_crowd.ogg` + `emote_alert.png`
  - 第三勢力: `doorOpen_2.ogg` + `emote_exclamations.png`
  - ミダス検挙: `metalLatch.ogg` 連続 + `riot_crowd.ogg`

### Step 49: イベント履歴・ログ
- `event_history: list[EventLog]`
- 発生ターン、終了ターン、結果、主要数値変化
- UI: 「年表」「戦史」タブで閲覧可能

### Step 50: プレイヤー選択肢イベント
- 特定イベントでプレイヤーに選択肢提示:
  - 派閥戦争: 介入 / 観戦 / 仲裁
  - 裏切り: 鎮圧支援 / 反乱容認 / 第三勢力利用
- 選択結果で派閥関係・報酬・後続イベント分岐

### Step 51: イベントバランス調整パラメータ
- YAML 化: `data/dynamic_events.yaml`
- 発生確率、期間、効果量、クールダウンを外部設定
- 難易度スケーリング (ゲーム進行度連動)

### Step 52: イベントデバッグ・強制発火コマンド
- 開発用: `trigger_event(event_id)` コマンド
- テスト用シナリオプリセット

### Step 53: イベント統合テスト
- 全イベントタイプの発生・進行・終了フロー
- 同時多発・連鎖・競合ケース
- セーブロード整合性

### Step 54: イベントパフォーマンス最適化
- トリガー判定のキャッシュ・インデックス化
- 不要区画・派閥のスキップ
- ターン処理時間 < 5ms 目標

---

## Phase 5: 音響・演出統合 (Steps 55-62)

### Step 55: 領土獲得ファンファーレ実装
- 音声ファイル: `assets/audio/territory_capture_fanfare.ogg` 配置
- `SkillEaterAudioSystem` に登録・キャッシュ
- 再生トリガー: 区画新規支配、隠しダンジョン発見、派閥戦争勝利

### Step 56: 暴動群衆音実装
- 音声ファイル: `assets/audio/riot_crowd.ogg` 配置
- ループ再生対応 (イベント期間中継続)
- 再生トリガー: 裏切りイベント、ミダス検挙、安定度暴落区画

### Step 57: 交渉チャイム実装
- 音声ファイル: `assets/audio/negotiation_chime.ogg` 配置
- 短い効果音 (1-2秒)
- 再生トリガー: 停戦交渉成功、同盟締結、外交メッセージ受信

### Step 58: アクション別音響マッピング拡張
- `TERRITORY_ACTION_AUDIO_MAP` 辞書追加:
  - PATROL: `chop.ogg`
  - RAID: `doorOpen_2.ogg` + `handleCoins.ogg`
  - PROPAGANDA: `bookOpen.ogg`
  - SABOTAGE: `knifeSlice.ogg` + `creak.ogg`
  - NEGOTIATE: `negotiation_chime.ogg`

### Step 59: エモート画像追加・マッピング
- 新規エモート画像配置: `assets/emote/pixel/style1/`
  - `emote_speech.png` (プロパガンダ)
  - `emote_heart.png` (停戦・同盟)
  - `emote_flag.png` (領土獲得・戦争)
- `TERRITORY_ACTION_EMOTE_MAP` 辞書追加

### Step 60: 空間音響対応 (オプション)
- `dynamic_audio.play_positional_sound()` 連携
- 区画座標 (マップ上) からリスナー (プレイヤー位置) への距離減衰
- 大規模イベント (戦争、暴動) は広範囲再生

### Step 61: 演出キュー統合・優先度制御
- 同時発生イベントの音声重複防止
- 優先度: システム > イベント > アクション > 環境
- 同一フレーム複数再生時: 最優先のみ / ミックス / キューイング選択可

### Step 62: 音響設定・ミュート連携
- 既存 `SkillEaterAudioSystem.set_mute()` `set_volume()` 対応
- テリトリー専用音量スライダー (環境音・イベント音・アクション音別)
- 設定保存・ロード

---

## Phase 6: UI・可視化・統合 (Steps 63-72)

### Step 63: 勢力図マップ描画基盤
- `TerritoryMapRenderer` クラス
- 既存 `WorldMapManager` / `UIRenderer` と統合
- 区画境界・支配色・安定度バー・資源アイコン描画

### Step 64: 派閥色・アイコン定義
- 各派閥固有色 (RGB) とアイコン (16x16px)
- ミダス: 赤系 / レジスタンス: 青系 / 銀行: 金系 / ブローカー: 紫系 / 中立: 灰色
- 新規派閥 (反乱、第三勢力) 動的生成

### Step 65: 区画詳細ツールチップ
- ホバー/クリックで詳細表示:
  - 名前、支配派閥、安定度、資源出力/ターン、防御レベル
  - 専用ショップ・隠しダンジョン状態
  - 実行可能アクション一覧・コスト・成功率

### Step 66: アクション実行UIパネル
- 派閥コマンドメニューに「テリトリー」タブ追加
- 区画選択 → アクション選択 → 確認ダイアログ
- 成功率・予測効果・コスト表示
- 実行ボタン押下で `TerritoryController.execute_action()`

### Step 67: ターン収入・統計サマリーUI
- ターン終了時/メニュー開時表示:
  - 派閥別: 支配区画数、総収入、士気、戦争状態
  - プレイヤー: 収入内訳、次ターン予測
  - グラフ: 過去20ターンの区画数・収入推移

### Step 68: イベント通知ログUI
- 画面端/サイドバーにイベント発生通知スタック
- クリックで詳細モーダル表示
- 選択肢イベント時: 選択ボタン表示
- 既存 `UIEventPanel` 拡張

### Step 69: 世界地図・ミニマップ連携
- `WorldMapManager` の層・区画データと同期
- ミニマップに派閥色オーバーレイ表示
- 区画クリックで詳細・アクションパネル開閉

### Step 70: セーブ/ロード完全対応
- `TerritoryState.to_dict()` / `from_dict()` 完成
- 既存 `save_game.py` `load_game.py` に統合
- バージョニング・マイグレーション対応

### Step 71: 総合バランス調整・プレイテスト
- 全アクション・イベントのコスト/効果/確率調整
- 序盤・中盤・終盤のペース確認
- 難易度別パラメータセット作成

### Step 72: ドキュメント・引き継ぎ
- `README_TERRITORY.md` 作成 (アーキテクチャ、API、拡張方法)
- 既存システムとの依存関係図
- 既知の制限・今後の拡張案
- 開発者向けデバッグコマンド一覧