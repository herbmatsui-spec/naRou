# SkillEaterSecretAccess - 隠しエリア・秘密通路・鍵システム 実装計画 (72ステップ)

## 概要
World A（スキル喰い）における秘密検知・隠し扉・鍵アイテム・アクセス条件・報酬・音響演出を実装する。
既存の `world_layer.py` `world_map_manager.py` `map_engine.py` `skill_eater_system.py` と統合する。

---

## フェーズ1: データ定義・定数追加 (Steps 1-12)

### Step 1: 定数追加 - 隠しタイル・検知タイプ
**ファイル:** `constants.py`
- `TILE_HIDDEN_DOOR = "H"` 隠し扉（未検知時は壁に見える）
- `TILE_FALSE_WALL = "F"` 偽の壁（検知で通過可能に）
- `TILE_SECRET_FLOOR = "U"` 床下通路入り口
- `TILE_VENT = "V"` 換気ダクト入り口
- `PERCEPTION_CHECK_BASE = 15` 基礎判定値
- `PERCEPTION_SKILL_BONUS = 5` スキルLvごとのボーナス

### Step 2: 定数追加 - 鍵アイテムタイプ
**ファイル:** `constants.py`
```python
KEY_TYPE_KEYCARD = "keycard"       # Keycard_LevelN (N=1-5)
KEY_TYPE_BIOMETRIC = "biometric"   # Biometric_Key (指紋/網膜/遺伝子)
KEY_TYPE_DECRYPTION = "decryption" # Decryption_Module (暗号解除)
KEY_TYPE_PHYSICAL = "physical"     # Physical_Key (物理鍵)
KEY_CONSUMABLE = True  # 消費型
KEY_PERMANENT = False  # 永続型
```

### Step 3: 定数追加 - アクセス条件フラグ
**ファイル:** `constants.py`
```python
ACCESS_FACTION_REP = "faction_rep"       # 派閥評判閾値
ACCESS_SKILL_REQUIRED = "skill_required" # 特定スキル保有
ACCESS_QUEST_FLAG = "quest_flag"         # クエストフラグ
ACCESS_TIME_WINDOW = "time_window"       # 時間帯 (hour_start, hour_end)
ACCESS_SACRIFICE = "sacrifice"           # 犠牲 (hp_cost, skill_cost, item_cost)
```

### Step 4: 定数追加 - 報酬タイプ
**ファイル:** `constants.py`
```python
REWARD_FORBIDDEN_SKILL = "forbidden_skill"    # 禁忌スキル
REWARD_CONCEPT_CRYSTAL = "concept_crystal"    # コンセプト結晶
REWARD_LORE = "lore"                          # 設定資料(ロア)
REWARD_SHORTCUT = "shortcut"                  # ショートカット
REWARD_HIDDEN_MERCHANT = "hidden_merchant"    # 隠し商人
```

### Step 5: 定数追加 - 音響・エモート
**ファイル:** `constants.py`
```python
SFX_SECRET_WALL_SLIDE = "secret_wall_slide.ogg"
SFX_KEYCARD_BEEP = "keycard_beep.ogg"
SFX_VENT_CRAWL = "vent_crawl.ogg"
SFX_ANCIENT_MECHANISM = "ancient_mechanism.ogg"
EMOTE_EYE = "emote_eye.png"
EMOTE_KEY = "emote_key.png"
```

### Step 6: audio_config.yaml にSE追加
**ファイル:** `data/audio_config.yaml`
```yaml
se:
  secret_wall_slide: 'secret_wall_slide.ogg'
  keycard_beep: 'keycard_beep.ogg'
  vent_crawl: 'vent_crawl.ogg'
  ancient_mechanism: 'ancient_mechanism.ogg'
  perception_success: 'handleSmallLeather.ogg'
  perception_fail: 'creak2.ogg'
```

### Step 7: 隠しエリア定義YAML作成
**ファイル:** `data/secret_areas.yaml` (新規作成)
```yaml
secret_areas:
  - id: "secret_lab_01"
    name: "廃棄実験室"
    layer: "underground:ruins:15:material"
    type: "hidden_door"
    position: [45, 23]
    detection_difficulty: 20
    access_conditions:
      - type: "faction_rep"
        faction: "resistance"
        min_rep: 30
      - type: "skill_required"
        skill_id: "rar_utility_003"
    key_required:
      type: "keycard"
      level: 2
      consumable: false
    rewards:
      - type: "forbidden_skill"
        skill_id: "eat_forbidden_001"
      - type: "lore"
        text: "ミダス社の非人道実験記録"
    audio:
      detect: "perception_success"
      unlock: "secret_wall_slide"
      enter: "ancient_mechanism"
    emotes:
      detect: "emote_eye.png"
      unlock: "emote_key.png"
```

### Step 8: 鍵アイテム定義YAML作成
**ファイル:** `data/key_items.yaml` (新規作成)
```yaml
key_items:
  - id: "keycard_lv1"
    name: "セキュリティキーカード Lv.1"
    type: "keycard"
    level: 1
    consumable: false
    description: "下層施設の扉を開ける汎用カード"
  - id: "keycard_lv2"
    name: "セキュリティキーカード Lv.2"
    type: "keycard"
    level: 2
    consumable: false
  - id: "keycard_lv3"
    name: "セキュリティキーカード Lv.3"
    type: "keycard"
    level: 3
    consumable: false
  - id: "biometric_fingerprint"
    name: "生体認証キー:指紋"
    type: "biometric"
    subtype: "fingerprint"
    consumable: true
  - id: "biometric_retina"
    name: "生体認証キー:網膜"
    type: "biometric"
    subtype: "retina"
    consumable: true
  - id: "decryption_module_basic"
    name: "暗号解除モジュール・基礎"
    type: "decryption"
    level: 1
    consumable: true
  - id: "physical_key_ancient"
    name: "古代の物理鍵"
    type: "physical"
    consumable: false
```

### Step 9: SecretArea データクラス作成
**ファイル:** `secret_area_system.py` (新規作成)
```python
@dataclass
class SecretArea:
    id: str
    name: str
    layer_key: str          # "zone:biome:depth:dimension"
    secret_type: str        # hidden_door, false_wall, secret_floor, vent
    position: tuple[int, int]
    detection_difficulty: int
    access_conditions: list[dict]
    key_required: dict | None
    rewards: list[dict]
    audio: dict
    emotes: dict
    is_discovered: bool = False
    is_unlocked: bool = False
```

### Step 10: KeyItem データクラス作成
**ファイル:** `secret_area_system.py` (同ファイル内)
```python
@dataclass
class KeyItem:
    id: str
    name: str
    key_type: str           # keycard, biometric, decryption, physical
    level: int = 1
    subtype: str = ""
    consumable: bool = False
    description: str = ""
```

### Step 11: SecretAreaRegistry シングルトン作成
**ファイル:** `secret_area_system.py` (同ファイル内)
- `load_from_yaml()` - secret_areas.yaml, key_items.yaml 読み込み
- `get_secret_area(area_id)` - 単体取得
- `get_areas_in_layer(layer_key)` - 指定層の全シークレット取得
- `get_key_item(key_id)` - 鍵アイテム取得

### Step 12: プレイヤー状態に秘密発見・鍵所持を追加
**ファイル:** `skill_eater_system.py` - `CharacterState` クラス拡張
```python
discovered_secrets: set[str] = field(default_factory=set)  # 発見済みシークレットID
unlocked_secrets: set[str] = field(default_factory=set)    # 解放済みシークレットID
owned_keys: dict[str, int] = field(default_factory=dict)   # key_id -> count
```

---

## フェーズ2: 検知システム実装 (Steps 13-24)

### Step 13: perception_check() 関数実装
**ファイル:** `secret_area_system.py`
```python
def perception_check(player: CharacterState, base_difficulty: int, 
                     skill_bonus: int = 0) -> tuple[bool, int]:
    """知覚判定: 成功なら (True, margin), 失敗なら (False, 0)"""
    perception = player.attributes.perception if hasattr(player, 'attributes') else 10
    analysis = player.analysis_level
    roll = random.randint(1, 100)
    target = base_difficulty + skill_bonus
    effective = perception * 2 + analysis * 3
    success = (roll + effective) >= target
    margin = (roll + effective) - target if success else 0
    return success, margin
```

### Step 14: check_secret_detection() - 周囲の隠し要素検知
**ファイル:** `secret_area_system.py`
- プレイヤー周囲3マス以内のシークレットエリアを取得
- 未発見のものに対して perception_check() 実行
- 成功時: `discovered_secrets` に追加、イベント発行、音響・エモート再生

### Step 15: 検知種別ごとの処理分岐
**ファイル:** `secret_area_system.py`
- `hidden_door`: 壁タイルを `TILE_HIDDEN_DOOR` に変更、通行可能フラグ付与
- `false_wall`: 壁タイルを `TILE_FALSE_WALL` に変更、通行可能フラグ付与
- `secret_floor`: 床タイルを `TILE_SECRET_FLOOR` に変更、下層接続フラグ付与
- `vent`: 床タイルを `TILE_VENT` に変更、クロール移動フラグ付与

### Step 16: GameMap に隠しタイル状態追加
**ファイル:** `map_engine.py` - `GameMap` クラス
```python
self.hidden_tiles: dict[tuple[int, int], dict] = {}  # pos -> {original_tile, secret_type, area_id}
```

### Step 17: 隠しタイルの描画・判定処理追加
**ファイル:** `map_engine.py`
- `is_walkable()` で `TILE_HIDDEN_DOOR`, `TILE_FALSE_WALL` を通行可能に（発見済み時のみ）
- `get_tile_display()` 等で未発見時は壁として描画

### Step 18: 自動検知トリガー - ターン経過時
**ファイル:** `packages/gameplay/package.py` - `GameplayLoop.advance_world()`
- プレイヤー移動時・ターン終了時に `check_secret_detection()` 呼び出し

### Step 19: 手動サーチコマンド実装
**ファイル:** `game.py` または入力処理
- `s` キーで周囲サーチ実行（エネルギー消費なし or 少量消費）
- `perception_check()` 強制実行、ボーナス付与

### Step 20: スキルによる検知ボーナス付与
**ファイル:** `secret_area_system.py`
- スキル `detection_mastery`, `trap_finder`, `secret_sense` 等をチェック
- 保有スキルに応じて `skill_bonus` 加算

### Step 21: 検知失敗時のペナルティ・クールダウン
**ファイル:** `secret_area_system.py`
- 連続失敗時: 難易度上昇（一時的）、またはクールダウン（10ターン）
- `CharacterState` に `last_search_turn`, `failed_search_count` 追加

### Step 22: イベントバス連携 - 検知イベント発行
**ファイル:** `secret_area_system.py`
```python
event_bus.publish("secret_detected", {
    "area_id": area.id,
    "position": area.position,
    "secret_type": area.secret_type,
    "margin": margin
})
```

### Step 23: 音響・エモート再生 - 検知成功時
**ファイル:** `secret_area_system.py` - `SkillEaterPresentationSystem` 連携
- `area.audio["detect"]` 再生
- `area.emotes["detect"]` 表示

### Step 24: ユニットテスト - 検知システム
**ファイル:** `tests/test_secret_access.py` (新規作成)
- `test_perception_check_success()`
- `test_perception_check_failure()`
- `test_check_secret_detection_nearby()`
- `test_secret_type_tile_changes()`

---

## フェーズ3: 鍵システム・解除処理 (Steps 25-36)

### Step 25: 鍵アイテムインベントリ管理
**ファイル:** `skill_eater_system.py` - `CharacterState`
- `add_key(key_id: str, count: int = 1)` 
- `remove_key(key_id: str, count: int = 1)`
- `has_key(key_id: str) -> bool`
- `get_key_count(key_id: str) -> int`

### Step 26: 鍵アイテムドロップ・入手処理
**ファイル:** `packages/gameplay/package.py` - `_spawn_dungeon()` 等
- モンスタードロップ、宝箱、クエスト報酬で鍵アイテム配置
- `Keycard_LevelN` は深度に応じたレベルで出現

### Step 27: try_unlock_secret() - 解除試行メイン関数
**ファイル:** `secret_area_system.py`
```python
def try_unlock_secret(player: CharacterState, area: SecretArea) -> tuple[bool, str]:
    # 1. 発見済みチェック
    # 2. アクセス条件チェック (派閥/スキル/クエスト/時間/犠牲)
    # 3. 鍵要件チェック (キーカードレベル/生体/暗号/物理)
    # 4. 消費型ならキー消費
    # 5. 解除成功: unlocked_secrets 追加、タイル変更、音響・エモート
```

### Step 28: アクセス条件 - 派閥評判チェック
**ファイル:** `secret_area_system.py`
```python
def check_faction_rep(player: CharacterState, condition: dict) -> bool:
    faction_id = condition["faction"]
    min_rep = condition["min_rep"]
    return player.faction_reputation.get(faction_id, 0) >= min_rep
```

### Step 29: アクセス条件 - 特定スキル保有チェック
**ファイル:** `secret_area_system.py`
```python
def check_skill_required(player: CharacterState, condition: dict) -> bool:
    skill_id = condition["skill_id"]
    return player.has_skill(skill_id)
```

### Step 30: アクセス条件 - クエストフラグチェック
**ファイル:** `secret_area_system.py`
```python
def check_quest_flag(player: CharacterState, condition: dict) -> bool:
    flag = condition["quest_flag"]
    return player.story_variables.get(flag, False)
```

### Step 31: アクセス条件 - 時間帯チェック
**ファイル:** `secret_area_system.py`
```python
def check_time_window(condition: dict) -> bool:
    current_hour = get_current_game_hour()  # 既存の時間システムから取得
    start = condition["hour_start"]
    end = condition["hour_end"]
    return start <= current_hour < end
```

### Step 32: アクセス条件 - 犠牲チェック・実行
**ファイル:** `secret_area_system.py`
```python
def check_and_pay_sacrifice(player: CharacterState, condition: dict) -> tuple[bool, str]:
    # hp_cost, skill_cost (skill_id), item_cost (item_id, count)
    # 確認ダイアログ表示 → 実行
```

### Step 33: 鍵要件 - キーカードレベルチェック
**ファイル:** `secret_area_system.py`
```python
def check_keycard(player: CharacterState, key_req: dict) -> bool:
    required_level = key_req["level"]
    for key_id, count in player.owned_keys.items():
        key_def = registry.get_key_item(key_id)
        if key_def and key_def.key_type == "keycard" and key_def.level >= required_level:
            return True
    return False
```

### Step 34: 鍵要件 - 生体認証キー チェック
**ファイル:** `secret_area_system.py`
```python
def check_biometric(player: CharacterState, key_req: dict) -> tuple[bool, str]:
    subtype = key_req.get("subtype", "fingerprint")
    key_id = f"biometric_{subtype}"
    if player.owned_keys.get(key_id, 0) > 0:
        return True, key_id
    return False, ""
```

### Step 35: 鍵要件 - 暗号解除モジュール / 物理鍵 チェック
**ファイル:** `secret_area_system.py`
- `decryption`: レベル比較
- `physical`: 特定ID完全一致

### Step 36: 解除成功時の処理・音響・エモート
**ファイル:** `secret_area_system.py`
- `area.is_unlocked = True`
- タイルを恒久的に通行可能に変更 (`TILE_FLOOR` 等)
- `area.audio["unlock"]` (`secret_wall_slide.ogg` 等) 再生
- `area.emotes["unlock"]` (`emote_key.png`) 表示
- イベント `secret_unlocked` 発行

---

## フェーズ4: 秘密通路・特殊移動実装 (Steps 37-48)

### Step 37: 床下通路 (secret_floor) 移動処理
**ファイル:** `secret_area_system.py`
- `TILE_SECRET_FLOOR` 上で `<` キー (下り) 押下時
- 対象層の `WorldLayer` 取得、接続先座標へワープ
- `SFX_ANCIENT_MECHANISM` 再生

### Step 38: 換気ダクト (vent) クロール移動
**ファイル:** `secret_area_system.py`
- `TILE_VENT` 上で方向キー入力時
- 連続した `TILE_VENT` を自動探索、出口まで移動
- 移動中 `SFX_VENT_CRAWL` ループ再生
- スタミナ消費、中断可能

### Step 39: 隠し扉 (hidden_door) 開閉アニメーション
**ファイル:** `map_engine.py` - `GameMap.update_animations()`
- 隠し扉タイルにアニメーション追加
- `secret_wall_slide.ogg` に同期して開閉

### Step 40: 偽の壁 (false_wall) 通過判定
**ファイル:** `map_engine.py` - `is_walkable()`
- 発見済みかつ解除済みの `TILE_FALSE_WALL` は通行可能
- 通過時わずかな抵抗（エネルギー+100等）

### Step 41: 秘密エリア間の接続マップ管理
**ファイル:** `secret_area_system.py`
```python
@dataclass
class SecretConnection:
    from_area: str
    to_area: str
    connection_type: str  # tunnel, vent, teleport
    one_way: bool = False
```

### Step 42: WorldMapManager 連携 - 層間秘密移動
**ファイル:** `world_map_manager.py` - `get_adjacent_layers()` 拡張
- 秘密通路による層間移動を隣接層として追加
- `SecretConnection` 参照

### Step 43: 秘密商人 (hidden_merchant) 出現処理
**ファイル:** `secret_area_system.py`
- 報酬タイプ `hidden_merchant` の場合
- 解除時に NPC 生成、特殊ショップ開放
- `SkillEaterEconomySystem` と連携

### Step 44: ショートカット (shortcut) 登録
**ファイル:** `secret_area_system.py`
- 報酬タイプ `shortcut` の場合
- `WorldMapManager` に高速移動ポイント登録
- マップUIにショートカットアイコン表示

### Step 45: 禁忌スキル (forbidden_skill) 付与
**ファイル:** `secret_area_system.py`
- 報酬タイプ `forbidden_skill` の場合
- `CharacterState.add_skill()` で付与（メモリ容量チェック）
- `is_illegal=True` フラグ付き

### Step 46: コンセプト結晶 (concept_crystal) 付与
**ファイル:** `secret_area_system.py`
- 報酬タイプ `concept_crystal` の場合
- アイテムとしてインベントリに追加
- 合成・進化素材として使用可能

### Step 47: ロア (lore) 取得・閲覧システム
**ファイル:** `secret_area_system.py`
- 報酬タイプ `lore` の場合
- `CharacterState.discovered_lore: list[str]` に追加
- メニューから閲覧可能

### Step 48: 秘密通路移動時のイベント発行
**ファイル:** `secret_area_system.py`
```python
event_bus.publish("secret_passage_used", {
    "from_pos": (x, y),
    "to_pos": (nx, ny),
    "passage_type": "vent|floor|tunnel",
    "area_id": area.id
})
```

---

## フェーズ5: マップ生成時の秘密配置 (Steps 49-60)

### Step 49: ダンジョン生成フック - 秘密エリア配置
**ファイル:** `map_engine.py` - `GameMap.generate_dungeon()`
- 部屋生成後、`SecretAreaRegistry.get_areas_in_layer()` で該当層のシークレット取得
- 指定座標またはランダム適合位置に配置

### Step 50: 隠し扉配置ロジック
**ファイル:** `map_engine.py`
- 部屋と部屋、部屋と通路の境界壁に配置
- 両側から検知可能な位置を優先

### Step 51: 偽の壁配置ロジック
**ファイル:** `map_engine.py`
- デッドエンドの壁、宝箱裏の壁等に配置
- 視覚的ヒント（微妙なテクスチャ差分）を `micro_details` に記録

### Step 52: 床下通路・換気ダクト配置ロジック
**ファイル:** `map_engine.py`
- 部屋の隅、通路の曲がり角等に配置
- 対応する下層/隣室の入り口とペアで配置

### Step 53: テーマ別秘密密度設定
**ファイル:** `data/dungeon_themes.yaml` 拡張
```yaml
gimmicks:
  - "secret_doors:0.3"      # 30%の部屋に隠し扉
  - "false_walls:0.2"
  - "secret_floors:0.1"
  - "vents:0.15"
```

### Step 54: generate_dungeon() で gimmicks 参照
**ファイル:** `map_engine.py`
- `world_layer.theme_data.get("gimmicks", [])` 解析
- 確率に基づき秘密要素配置

### Step 55: 秘密エリア位置の重複回避
**ファイル:** `map_engine.py`
- 同一座標に複数の秘密要素が重ならないようチェック
- 階段・重要NPC・ボス部屋周辺は除外

### Step 56: 手動配置用エディタ機能（デバッグ用）
**ファイル:** `secret_area_system.py`
- `place_secret_area_manual(layer, pos, area_id)` 
- デバッグコマンド / チートコマンドで使用

### Step 57: 秘密エリアのシード固定化
**ファイル:** `map_engine.py`
- ダンジョンシードから決定論的に配置位置を決める
- 再訪問時同一位置に存在保証

### Step 58: ミニマップ・探索済みフラグへの反映
**ファイル:** `map_engine.py`
- 発見済み秘密エリアはミニマップに特別アイコン表示
- `explored` 配列とは別管理

### Step 59: ロックされた秘密エリアのヒント表示
**ファイル:** `secret_area_system.py`
- 発見済みだが未解除の場合、調べるとヒント表示
- 「キーカードLv.2が必要」「レジスタンス評判30以上」等

### Step 60: ユニットテスト - マップ生成・配置
**ファイル:** `tests/test_secret_access.py` 追加
- `test_secret_area_placement_in_dungeon()`
- `test_secret_density_by_theme()`
- `test_no_overlap_with_stairs()`

---

## フェーズ6: 統合・UI・ゲームループ連携 (Steps 61-72)

### Step 61: メインメニューに「秘密の記録」追加
**ファイル:** `game.py` または UI システム
- 発見済み/解放済みシークレット一覧
- 入手報酬履歴、ロア閲覧

### Step 62: キーアイテム専用インベントリタブ
**ファイル:** `item_system.py` / UI
- 「鍵・認証」カテゴリ追加
- 所持キーカードレベル一覧、生体キー残り回数表示

### Step 63: 探索コマンド (sキー) UI統合
**ファイル:** `game.py` - 入力処理
- ヘルプテキストに「[s] 検索」追加
- 検知実行時のメッセージログ出力

### Step 64: 秘密扉解除プロンプトUI
**ファイル:** `game.py` - インタラクション処理
- 隠し扉前で決定キー押下時
- 条件不足時: 不足内容表示
- 条件満たし: 確認プロンプト → 解除実行

### Step 65: 音響システム統合 - 3D位置音響
**ファイル:** `sound_manager.py` / `skill_eater_audio_system.py`
- `play_sound_at_position(sfx, x, y)` 実装
- プレイヤーからの距離で音量減衰

### Step 66: エモート表示システム統合
**ファイル:** `skill_eater_presentation_system.py`
- `add_event(emote_file, audio_file, message, position)` 
- プレイヤー頭上 or 秘密エリア位置に表示

### Step 67: セーブ/ロード対応
**ファイル:** `save_system.py` / `game.py`
- `discovered_secrets`, `unlocked_secrets`, `owned_keys` をセーブデータに含める
- `SecretArea.is_discovered`, `is_unlocked` も永続化

### Step 68: 難易度連動 - 秘密難易度調整
**ファイル:** `core/difficulty.py` / `secret_area_system.py`
- `DifficultyManager.secret_detection_modifier()`
- Easy: -5, Normal: 0, Hard: +5, Lunatic: +10

### Step 69: 転生引き継ぎ - 秘密発見知識
**ファイル:** `reincarnation_system.py` / `skill_eater_system.py`
- 再生時、発見済みシークレットの一部引き継ぎオプション
- 「記憶の欠片」アイテムで全復元可能

### Step 70: 実績・称号連携
**ファイル:** `achievement_system.py`
- 「最初の発見」「全隠し扉解放」「キーコレクター」等実績追加
- 称号「秘密の探求者」「鍵主」等

### Step 71: 総合テスト・バランス調整
**ファイル:** `tests/test_secret_access_integration.py` (新規)
- E2Eテスト: ダンジョン生成→検知→解除→報酬取得の一連流れ
- 各難易度での検知成功率測定
- 鍵アイテム入手バランス確認

### Step 72: ドキュメント更新・完了
**ファイル:** `README.md` / `docs/secret_access.md` (新規)
- システム概要、仕様書、モッダー向けガイド作成
- 実装完了マーク付与

---

## 実装順序の推奨

| 優先度 | ステップ範囲 | 内容 |
|--------|-------------|------|
| **高** | 1-12 | データ基盤・定数・YAML・レジストリ |
| **高** | 13-24 | 検知システム核心 |
| **高** | 25-36 | 鍵・解除システム核心 |
| **中** | 37-48 | 特殊移動・報酬処理 |
| **中** | 49-60 | マップ生成統合 |
| **低** | 61-72 | UI・セーブ・実績・ドキュメント |

---

## 依存関係マップ

```
Step 1-6 (定数) 
    ↓
Step 7-8 (YAMLデータ)
    ↓
Step 9-11 (レジストリ・データクラス) ← Step 12 (プレイヤー状態拡張)
    ↓
Step 13 (perception_check) 
    ↓
Step 14-17 (検知・マップ連携)
    ↓
Step 18-23 (トリガー・音響・テスト)
    ↓
Step 25-26 (キーインベントリ・ドロップ)
    ↓
Step 27 (try_unlock_secret メイン)
    ↓
Step 28-35 (各種条件チェック)
    ↓
Step 36 (解除成功処理)
    ↓
Step 37-48 (特殊移動・報酬)
    ↓
Step 49-60 (マップ生成統合)
    ↓
Step 61-72 (UI・セーブ・実績・完了)
```

---

## 注意事項・低性能LLM向けTips

1. **各ステップは独立してテスト可能** - 1つ完了したら動作確認してから次へ
2. **既存コードのパターンを踏襲** - `SkillEaterRegistry`, `WorldStateManager` 等のシングルトンパターン使用
3. **イベントバス活用** - 疎結合でシステム間連携 (`event_bus.publish/subscribe`)
4. **YAMLデータ駆動** - ハードコード避け、データ定義で拡張可能に
5. **音響・エモートは `SkillEaterPresentationSystem` 経由** - 統一インターフェース使用
6. **型ヒント必須** - `from __future__ import annotations` + `TYPE_CHECKING` で循環回避
7. **デフォルト値・フォールバック徹底** - `get(key, default)` パターンで堅牢化

---

## 完了基準

- [ ] 全72ステップ実装完了
- [ ] `tests/test_secret_access.py` 全パス
- [ ] `tests/test_secret_access_integration.py` 全パス
- [ ] 手動プレイテスト: 隠し扉発見→キーカード使用→報酬取得の一連流れ動作
- [ ] セーブ/ロードで秘密状態維持確認
- [ ] 難易度別バランス確認