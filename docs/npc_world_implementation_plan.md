# NPC・世界反応システム 実装計画（低性能LLM向け 72ステップ）

対象: `naRou/`（Elona系ローグライク）。現在は `player` + `pet` のみ。
本計画は 4 大機能を 72 の小ステップに分割する。各ステップは **1ファイル・1責務・小テスト付き** で、弱いLLMでも順に実装・検証できる。

前提とする既存資産（そのまま再利用）:
- YAML読込パターン: `yaml.safe_load(open(path, encoding="utf-8"))`
- シングルトン + Kernel登録: `packages/world_a/package.py` の `setup()` パターン
- 演出エンジン: `SkillEaterPresentationSystem.get_instance().add_event(emote_file=, audio_file=, message=, duration_ms=)`
- NPC記憶: `npc_memory_system.GLOBAL_MEMORY_REGISTRY`（噂ネットワークの土台）
- 関係性: `relationship_system.py` + `data/character_relations.yaml`
- スケジュール: `data/quest_schedules.yaml` の `schedule_templates`（朝/市/夜）
- 因果: `karma.yaml` / `story_choices.yaml` / `world_state.yaml` / `data/world_state.yaml`

---

## フェーズ0: 基盤（データスキーマとローダー） — ステップ 1〜9

### Step 1 — NPCデータスキーマ雛形を作る
- ファイル: `data/npcs.yaml`（新規）
- 内容: 1体だけ定義（市場の商人 `merchant_lina`）。name, char, color, archetype, schedule_id, relation_template, speech_style を持つ最小YAML。
- 確認: `python -c "import yaml;yaml.safe_load(open('data/npcs.yaml',encoding='utf-8'))"` が通る。

### Step 2 — NPCローダー `npc_loader.py` を作る
- ファイル: `npc_loader.py`（新規）
- 内容: `load_npcs(path) -> dict[str, dict]` を1関数だけ実装。safe_loadして `raw["npcs"]` を返す。
- 確認: `load_npcs("data/npcs.yaml")` が dict を返す。

### Step 3 — テスト `test_npc_loader.py` を作る
- ファイル: `tests/test_npc_loader.py`
- 内容: ダミーYAML文字列を `tmp_path` に書き、`load_npcs` が件数を正しく返すことを assert。
- 確認: `python -m pytest tests/test_npc_loader.py -q` が通る。

### Step 4 — NPC実体クラス `NPCActor` を作る
- ファイル: `npc_actor.py`（新規）
- 内容: `@dataclass` に `id,name,char,color,archetype,schedule_id,relation_template,speech_style,current_location` を持つだけ。
- 確認: クラスが import できる。

### Step 5 — スケジュール定義を `data/npc_schedules.yaml` に抽出
- ファイル: `data/npc_schedules.yaml`（新規）
- 内容: `quest_schedules.yaml` の `schedule_templates` を参照し、`daily_dawn/market`, `daily_noon/market`, `daily_dusk/tavern`, `daily_midnight/tavern` の4枠をNPC用に定義（time_windows のみ）。
- 確認: safe_load で4枠読める。

### Step 6 — `npc_schedule.py` で「今の時間帯→場所」を解決
- ファイル: `npc_schedule.py`（新規）
- 内容: `def location_for_time(schedule:dict, hour:int) -> str` を実装。hour で window を判定し場所キーを返す（該当なしは `"home"`）。
- 確認: 朝6時→`market`、夜23時→`tavern` を返す単体テスト。

### Step 7 — 口調（speech_style）のバリエーションデータ
- ファイル: `data/npc_speech.yaml`（新規）
- 内容: `polite/rough/childlike/solemn` の4スタイル。各スタイルに `greeting:`, `farewell:`, `rumor_hint:` の定型文テンプレ（{name} 埋め込み）。
- 確認: safe_load で読める。

### Step 8 — `npc_speech.py` で定型文を取得
- ファイル: `npc_speech.py`（新規）
- 内容: `get_line(style, kind, name="") -> str` を実装。テンプレの `{name}` を置換。
- 確認: `get_line("rough","greeting","リナ")` が名前入り文字列を返すテスト。

### Step 9 — フェーズ0 統合テスト
- ファイル: `tests/test_npc_foundation.py`
- 内容: npcs.yaml をロード→NPCActor化→朝のlocation解決→口調文生成、までの一連をassert。
- 確認: `pytest` 該当ファイル緑。

---

## フェーズ1: NPCアクターと行動スケジュール — ステップ 10〜26

### Step 10 — `NPCManager` 雛形
- ファイル: `npc_manager.py`
- 内容: `class NPCManager` に `__init__(self)` だけ。内部 `self.actors: dict[str,NPCActor]={}`。
- 確認: import可。

### Step 11 — NPCの一括生成
- `npc_manager.py` に `spawn_from_data(self, npcs:dict)` を追加。各定義から `NPCActor` を作り `actors` に格納。
- 確認: 1体登録されるテスト。

### Step 12 — 時間帯ごとの所在地更新メソッド
- `update_locations(self, hour:int, schedules:dict)` を追加。各actorの `current_location` を `location_for_time` で更新。
- 確認: 朝は market、夜は tavern に変わるテスト。

### Step 13 — 複数NPCを npcs.yaml に追加
- `data/npcs.yaml` に `market_vendor`, `tavern_keeper`, `guard_bran` の3体を追加（異なる schedule_id/style）。
- 確認: ロードで4体になる。

### Step 14 — 場所（location）の座標マップ
- ファイル: `data/npc_locations.yaml`（新規）。`market:[x,y]`,`tavern:[x,y]`,`home:[x,y]` を定義。
- 確認: safe_load可。

### Step 15 — `npc_manager.place_in_town(map)`
- `npc_manager.py` にメソッド追加。各actorを `current_location` に応じた座標に配置（townマップ上のEntityを生成して返す）。
- 確認: market のNPCが market座標にいるテスト。

### Step 16 — game_state へNPCリストを追加
- `game_state.py` の `GameStateData` に `npcs: list = field(default_factory=list)` を追加。
- 確認: 既存テストが壊れないこと。

### Step 17 — ワールド初期化でNPCを生成
- `core/world_state_manager.py` の `initialize_world_state` 内で `NPCManager` を呼び、state_data.npcs に配置結果を入れる。
- 確認: 初期化後に npcs が空でない。

### Step 18 — 昼夜（hour）の状態変数を追加
- `game_state.py` に `hour:int=8` を追加。`world_state.yaml` 的には不要だが進行用。
- 確認: import可。

### Step 19 — turn 経過で hour を進めるフック
- `game.py` のターン進行部（既存ループ）に `state_data.hour = (state_data.hour + 1) % 24` を1箇所追加（コメント付き）。
- 確認: ターン経過で hour が変わるテスト（game.py の既存ユニットがあれば）。

### Step 20 — NPCの移動更新をターンに組み込む
- `game.py` の `_npc_ai` またはターンループで `npc_manager.update_locations(hour, schedules)` と `place_in_town` を呼ぶ（NPC用の軽量更新）。
- 確認: 夜になると tavern のNPC座標に移動する。

### Step 21 — NPC描画（char/color）をマップ表示へ
- 既存のマップ描画ルーチン（rendering）で `state_data.npcs` を `entities` 同様に描画する最小修正。
- 確認: マップ上にNPCが見える（視覚 or テストで座標一致）。

### Step 22 — 外見バリエーションデータ
- `data/npcs.yaml` 各NPCに `appearance: "赤いマントの小柄な女性"` 等の記述を追加。
- 確認: ロードで appearance を読める。

### Step 23 — 名前バリエーション（姓名プール）
- `data/npc_names.yaml`（新規）に first/last プールを定義。`npc_loader` で `name_variants` を使いランダム命名の補助関数 `random_name()` を追加。
- 確認: `random_name()` がプール内から返るテスト。

### Step 24 — スケジュール例外（祭り等）の適用
- `npc_schedule.py` に `override_location(schedule, date_key, default)` を追加。`quest_schedules.yaml` の `schedule_overrides` を参照し無効日は home にする。
- 確認: 指定日は market に行かないテスト。

### Step 25 — NPCとの隣接検出
- `game.py` でプレイヤー隣接にNPCがいるか判定する `adjacent_npc(state)` ヘルパを追加。
- 確認: 隣にNPCがいればそのactorを返すテスト。

### Step 26 — フェーズ1 統合テスト
- `tests/test_npc_schedule_integration.py`: 朝/昼/夜でNPCの座標が正しく遷移することを確認。
- 確認: pytest 緑。

---

## フェーズ2: 対話・噂・関係性ツリー — ステップ 27〜44

### Step 27 — 対話ツリースキーマ
- `data/npc_dialogue_trees.yaml`（新規）。NPCごとに `nodes:{id:{text,choices:[{label,next,unlock_rumor,effect}]}}` と `start` を持つ。
- 確認: safe_load可。

### Step 28 — `dialogue_tree.py` でノード解決
- `dialogue_tree.py`（新規）。`get_node(tree, node_id)` と `start_node(tree)` だけ。
- 確認: start ノードを取得するテスト。

### Step 29 — 既存 `dialogue_system.py` を拡張（最小）
- `DialogueManager.get_dialogue` の前に `if npc actor present: return treeベース` の分岐を1つ追加（後段で実装するため、まずはフラグだけ）。
- 確認: 既存テスト維持。

### Step 30 — 噂ネットワークスキーマ
- `data/rumors.yaml`（新規）。`rumors:{id:{about_npc, text, unlock_from:[npc_id], requires_relation:{template,min_level}}}`。
- 確認: safe_load可。

### Step 31 — `rumor_network.py` ローダ
- `rumor_network.py`（新規）。`load_rumors(path)->dict` と `rumors_unlocked_by(npc_id)` を実装。
- 確認: `merchant_lina` が特定噂をアンロックするテスト。

### Step 32 — プレイヤーが「聞いた噂」を保持
- `game_state.py` に `known_rumors: set = field(default_factory=set)` を追加。
- 確認: import可。

### Step 33 — 対話で噂をアンロック
- `dialogue_tree.py` または `dialogue_system.py` で choice に `unlock_rumor` があれば `state.known_rumors.add(id)` する最小処理を追加。
- 確認: 選択後に known_rumors に追加されるテスト。

### Step 34 — アンロック条件（関係性）のチェック
- `rumor_network.py` に `is_unlockable(rumor, relation_mgr)` を追加。`requires_relation` を `relationship_system.RelationshipManager` で判定。
- 確認: 好感度不足なら False を返すテスト。

### Step 35 — 関係性テンプレートのマルチタイプ対応
- `relationship_system.py` の `load` を拡張し、`character_relations.yaml` の `relationship_types`（配列）と `initial_levels` を `RelationshipTemplateData` に取り込む（現状は単一 `relationship_type` のみ）。
- 確認: `saved_villager` が `favorability/friendship` の2軸を持つテスト。

### Step 36 — 関係性マネージャに「軸別レベル」を追加
- `RelationshipManager` に `levels: dict[str,float]` を追加し、`apply_interaction(action)` で `interaction_effects` の effect を軸別に加算（clamp -100..100）。
- 確認: talk で favorability+5 になるテスト。

### Step 37 — NPC↔プレイヤー関係のインスタンス化
- `npc_manager.py` で各NPCに対し `RelationshipManager` を1つ生成し `relation_template` で初期化して保持。
- 確認: 生成時に初期レベルが入るテスト。

### Step 38 — 対話選択が関係性に反映
- `dialogue_system.py` の choice 処理で `effect: talk/gift/help` を `relation_mgr.apply_interaction` に渡す。
- 確認: gift 選択で favorability が上がるテスト。

### Step 39 — 噂が「別NPCの文脈」を提示
- 対話UI（既存 `managers/context_menu_builder.py` のNPC分岐）で、known_rumors にある `about_npc` の噂文を選択肢・表示に混ぜる最小修正。
- 確認: 噂テキストが取得できるテスト。

### Step 40 — NPC記憶への噂伝播
- `npc_memory_system.GLOBAL_MEMORY_REGISTRY` を使い、噂アンロック時に「誰から聞いたか」を記憶に残す1メソッド `record_rumor(state, from_npc, rumor_id)` を追加。
- 確認: 記憶に rumor タイプが残るテスト。

### Step 41 — 関係性ツリーの「深層ノード」
- `npc_dialogue_trees.yaml` に、特定関係レベル（例: favorability>=60）でのみ `next` 遷移する `req_relation` 付きノードを2つ追加。
- 確認: レベル不足なら深層に進まないテスト（`dialogue_tree` に `can_enter(node, relation_mgr)` を追加）。

### Step 42 — クエスト提示の接続
- 対話ノードに `offer_quest: quest_id` を追加。`quest_scheduler.py` の既存仕組みで受注可能にする最小フック。
- 確認: 特定ノード到達でクエストが state.quests に追加されるテスト。

### Step 43 — 世界の文脈（lore）テキスト
- `data/npc_lore.yaml`（新規）に、噂/対話で解放される世界背景文を定義。`dialogue_system` から参照。
- 確認: lore id で本文取得テスト。

### Step 44 — フェーズ2 統合テスト
- `tests/test_dialogue_rumor_integration.py`: 商人と話→噂アンロック→関係上昇→深層ノード開放→クエスト提示、を通しでassert。
- 確認: pytest 緑。

---

## フェーズ3: 意味のあるモンスター生態 — ステップ 45〜59

### Step 45 — monsters.yaml に生態フィールドを追加
- 各モンスターに `territory: floor_range`(既存min/max_floorで可)、`pack: {size:int, role:"alpha/subordinate"}`、`day_behavior`/`night_behavior` を追加（まず slime のみ）。
- 確認: safe_load可。

### Step 46 — `monster_ecology.py` ローダ
- `monster_ecology.py`（新規）。`load_ecology(monsters:dict)->dict` で生態フィールドを正規化（省略時はデフォルト）。
- 確認: slime が ecology を持つテスト。

### Step 47 — テリトリー判定
- `in_territory(monster_id, floor)->bool` を追加。floor が範囲外なら出現抑制の判定用。
- 確認: floor外で False を返すテスト。

### Step 48 — 昼夜行動の解決
- `behavior_for_time(monster_id, hour)->str` を追加。`night_behavior` 優先、なければ day。
- 確認: 夜は night_behavior を返すテスト。

### Step 49 — 群れ（pack）生成
- `spawn_pack(monster_id, rng)->list[str]` を追加。sizeに応じ alpha+subordinate のリストを返す（既存 spawn に差し込む形）。
- 確認: size=3 なら3体分のIDリストを返すテスト。

### Step 50 — 出現フィルタへの組み込み
- 既存モンスター生成部（spawn）で `in_territory` をチェックし、テリトリー外は別種/非生成にする最小修正。
- 確認: 範囲外floorで該当モンスターが出ないテスト。

### Step 51 — 昼夜で行動AIを切替
- `ai_system.py` の処理で `behavior_for_time` 結果に応じ `aggressive↔coward` 等を上書きする1分岐。
- 確認: 夜の coward が別挙動になるテスト。

### Step 52 — 「気配」演出のトリガ
- `monster_ecology.py` に `presence_event(monster_id, behavior)->PresentationEvent風` を追加。`SkillEaterPresentationSystem.get_instance().add_event(...)` を呼ぶ。
- 確認: add_event が呼ばれる（mock）テスト。

### Step 53 — エンカウント前の気配演出を spawn に差込
- モンスター出現直前に `presence_event` を発行。emote/audio は `assets/emote/...` の既存パスを想定（存在しなくてもmessageだけ再生）。
- 確認: 出現時に演出イベントが1件以上キューに入るテスト。

### Step 54 — 気配の強さ（テリトリー接近度）
- `presence_intensity(monster_id, player_floor, player_pos, monster_territory)` を追加。近いほど強いメッセージ。
- 確認: 近接ほど高intensity を返すテスト。

### Step 55 — 群れの連動AI（alpha依存）
- `ai_system.py` に `alpha_id` 参照を1つ追加。subordinate は alpha が倒されると `flee/coward` に切替。
- 確認: alpha 死亡で subordinate が flee フラグになるテスト。

### Step 56 — 生態データを全モンスターへ拡張
- `data/monsters.yaml` の全モンスターに `pack`/`day_behavior`/`night_behavior` を埋める（コピペベース）。
- 確認: 全件 ecology 正規化できるテスト。

### Step 57 — フェーズ3 統合テスト
- `tests/test_monster_ecology_integration.py`: 夜のテリトリー外周で気配演出→出現→alpha死で群れ崩壊、をassert。
- 確認: pytest 緑。

---

## フェーズ4: プレイヤーに反応する世界（評判・因果） — ステップ 58〜72

### Step 58 — karma ローダ
- `karma_system.py` が既存。無ければ `load_karma(path)->dict` を `karma.yaml` 用に追加（actions→delta）。
- 確認: `defeat_monster` が good_evil+1 を返すテスト。

### Step 59 — 行動→karma 適用フック
- 既存の行動ポイント（モンスター討伐/寄付/盗み）で `karma_system.apply(action)` を呼び `state.survival.karma` 等へ加算する最小修正。
- 確認: 討伐で karma が変化するテスト。

### Step 60 — 評判（reputation）状態変数
- `game_state.py` に `reputation: dict[str,int] = field(default_factory=lambda:{"town":0})` を追加。
- 確認: import可。

### Step 61 — 評判の加算・閾値
- `reputation.py`（新規）に `add_rep(state, faction, delta)` と `rep_tier(state, faction)->str`（敵対/中立/友好的/有名）を追加。
- 確認: +30 で "友好的" を返すテスト。

### Step 62 — 評判がNPC対応を変える
- `npc_manager` の対話開始時に `rep_tier` を見て greeting 文を変える（友好なら歓迎、敵対なら拒絶）。
- 確認: 敵対評判で拒絶文が返るテスト。

### Step 63 — story_choices ローダ
- `choice_system.py` が既存。無ければ `load_choices(path)->dict` を追加。`immediate_effects`/`long_term_effects`/`world_state_changes` を構造化。
- 確認: `farm_survivor_saved` が immediate gold+1500 を持つテスト。

### Step 64 — 選択の即時適用
- 対話/イベント選択で `apply_choice(state, choice_id)` を呼び immediate_effects（gold/karma等）を適用。
- 確認: 選択で gold が増えるテスト。

### Step 65 — 長期効果の保持
- `game_state.py` に `active_long_term: list[dict] = field(default_factory=list)` を追加。apply_choice で long_term を積む。
- 確認: long_term が1件追加されるテスト。

### Step 66 — 因果の「遅延発火」キュー
- `causality.py`（新規）に `schedule_world_change(state, change:dict, delay_days:int)` と `tick_day(state)` を追加。`state.day` を進め、期限で `world_state_changes` を適用。
- 確認: delay=3 で3日後に change が適用されるテスト。

### Step 67 — world_state との接続
- `data/world_state.yaml` の `persistent_variables` を `state.world_state: dict` にロード。`apply_world_change` で該当キーを書き換え。
- 確認: `vernis_safety_index` が変わるテスト。

### Step 68 — 日付進行のフック
- `game.py` の日付更新（day インクリメント）で `causality.tick_day(state)` を呼ぶ。
- 確認: 日付経過で遅延発火が走るテスト。

### Step 69 — 噂/評判/因果の三角結合
- 高karmaで特定噂が早期アンロック、低評判でクエスト提示が拒絶される、などの組み合わせルールを `npc_manager` に1メソッド `should_offer_quest(state, npc)` として追加。
- 確認: 条件で True/False が切替わるテスト。

### Step 70 — 因果が世界の文脈に反映
- 遅延発火した `world_state_changes` を `npc_lore.yaml` の該当エントリと紐づけ、次回対話で「最近の変化」として提示。
- 確認: 変化後に lore が更新文を返すテスト。

### Step 71 — 統合: 1回の行動が数日後に世界を変える
- `tests/test_causality_e2e.py`: 農民救出選択 → 即時gold/karma → 数日待機 → town評判上昇 + world_state変化 + 商人の対応が変わる、を通しassert。
- 確認: pytest 緑。

### Step 72 — 全体統合テスト & 登録
- `packages/world_a/package.py` の `setup()` に `npc_manager`/`rumor_network`/`monster_ecology`/`causality` をシステム登録（既存パターン準拠）。
- `tests/test_npc_world_master_e2e.py` を追加: 朝市で商人と会話→噂取得→夜酒場で別NPC→関係上昇→生態モンスターの気配演出→選択の因果が数日後反映、の全結合。
- 確認: `pytest` 全体緑、既存テスト回帰なし。

---

## LLM実装のためのルール（守るべきこと）
1. 各ステップは **前ステップの出力（関数/データ）のみに依存** する。飛ばさない。
2. 新規ファイルは 1 機能・1 クラス（または数関数）に留める。巨大クラスを作らない。
3. 全ステップで `tests/test_*.py` を 1 つずつ追加し、`pytest -q` を緑にする。
4. 既存API（`SkillEaterPresentationSystem.add_event`、`GLOBAL_MEMORY_REGISTRY`、`relationship_system`、YAMLロード）は改変せず **呼び出すだけ** に留める。
5. データは必ず `yaml.safe_load(open(..., encoding="utf-8"))` で読み、存在しない場合はデフォルトを返す（堅牢性）。
6. ステップ番号はこの計画と同じ番号をコメント/テスト名に入れ、進捗を追えるようにする。
