# ダンジョン・ワールド自動生成ストーリーテラー 詳細提案書

## 概要
プレイヤーの行動、選択、世界状態に基づいてプロシージャルにダンジョンシナリオとストーリーを生成するシステム。選択肢分岐、世界状態の永続化、メタストーリープログレスを実現し、毎回異なる物語体験を提供する。

## 1. プロシージャルダンジョンシナリオ生成システム
### データ構造（`data/procedural_scenarios.yaml`）
```yaml
scenario_templates:
  goblin_invasion:
    id: goblin_invasion
    name: "ゴブリンの侵略"
    description: "ゴブリン族が近隣の村を襲撃している"
    chapters:
      - id: discovery
        name: "異変の発見"
        type: exploration
        objectives:
          - {type: "visit_location", target: "abandoned_farm", count: 1}
          - {type: "defeat_enemy", target: "goblin_scout", count: 3}
        choices:
          - id: investigate_farmhouse
            description: "農家を詳しく調べる"
            consequence: {type: "unlock_chapter", target: "survivor_testimony"}
          - id: chase_scouts
            description: "ゴブリン偵察隊を追跡する"
            consequence: {type: "unlock_chapter", target: "ambush_preparation"}
      - id: survivor_testimony
        name: "生存者の証言"
        type: dialogue
        objectives:
          - {type: "talk_to_npc", target: "farm_survivor"}
        rewards:
          - {type: "information", key: "goblin_weak_to_fire"}
          - {type: "item", id: "holy_water", count: 1}
      - id: ambush_preparation
        name: "伏兵の準備"
        type: preparation
        objectives:
          - {type: "gather_item", target: "oil", count: 5}
          - {type: "gather_item", target: "rope", count: 3}
        choices:
          - id: set_trap
            description: "罠を仕掛ける"
            consequence: {type: "modify_battle", modifier: "trap_damage", value: 50}
          - id: direct_assault
            description: "直接突撃する"
            consequence: {type: "modify_battle", modifier: "enemy_alert", value: 30}
    variables:
      - {name: "goblin_leader_present", type: "boolean", default: false}
      - {name: "villager_morale", type: "integer", min: 0, max: 100, default: 50}
```

### 実装箇所
- `storyteller_system.py` - メインストーリーテラーエンジン
- `data/procedural_scenarios.yaml` - シナリオテンプレート定義
- `entity.py` - ストーリー状態追跡フィールド追加
- `game.py` - ストーリーイベントトリガー統合

## 2. 選択肢分岐・結果永続化システム
### データ構造（`data/story_choices.yaml`）
```yaml
choice_consequences:
  farm_survivor_saved:
    id: farm_survivor_saved
    description: "農家の生存者を救出した"
    immediate_effects:
      - {type: "gain_item", item: "emergency_ration", count: 3}
      - {type: "modify_reputation", faction: "villagers", value: 15}
    long_term_effects:
      - {type: "unlock_quest", quest_id: "revenge_against_goblins"}
      - {type: "permanent_bonus", stat: "luck", value: 2}
      - {type: "future_encounter", npc: "grateful_villager", chance: 0.3}
    world_state_changes:
      - {type: "variable_set", name: "villager_morale", value: 80}
      - {type: "location_unlock", location: "hidden_village"}
  goblin_chief_captured:
    id: goblin_chief_captured
    description: "ゴブリンの酋長を捕虜にした"
    immediate_effects:
      - {type: "gain_gold", amount: 500}
      - {type: "gain_item", item: "goblin_chief_trophy"}
    long_term_effects:
      - {type: "unlock_dialogue", npc: "goblin_chief", topic: "tribe_secrets"}
      - {type: "faction_change", faction: "goblins", value: -25}
    world_state_changes:
      - {type: "variable_set", name: "goblin_leader_present", value: false}
      - {type: "event_trigger", event: "goblin_retaliation", delay: 3} # 3日後に報復
```

### 実装箇所
- `choice_system.py` - 選択肢管理と結果適用
- `data/story_choices.yaml` - 選択肢結果定義
- `entity.py` - 選択履歴とワールド状態フィールド
- `save_system.py` - 選択結果の永続化

## 3. 世界状態永続化・メタプログレスシステム
### データ構造（`data/world_state.yaml`）
```yaml
world_state_template:
  version: "1.0"
  last_updated: null
  persistent_variables:
    goblin_leader_present: false
    villager_morale: 50
    ancient_seal_strength: 100
    dragon_sightings: 0
    temple_discovered: false
  location_states:
    vermin_town:
      prosperity: 75
      danger_level: 20
      special_events_available: []
      npcs:
        - {id: "innkeeper", mood: "neutral", quests_offered: []}
    abandoned_castle:
      explored_areas: []
      traps_disarmed: 0
      secrets_found: 0
      guardian_defeated: false
  faction_relations:
    villagers:
      reputation: 0
      trade_availability: "normal"
      military_support: 0
    mages_guild:
      reputation: 0
      spell_discount: 0
      rare_ingredients: []
  global_events:
    active: []
    completed:
      - {id: "harvest_festival_2024", completion_date: "2024-09-15"}
    upcoming:
      - {id: "blood_moon", predicted_date: "2024-10-31", probability: 0.1}
  player_legacy:
    titles_earned: []
    major_achievements: []
    failed_attempts: []
```

### 実装箇所
- `world_state_system.py` - ワールド状態管理
- `data/world_state.yaml` - ワールド状態テンプレート
- `entity.py` - プレイヤーレガシーフィールド
- `save_system.py` - ワールド状態のセーブ/ロード
- `game.py` - ワールド状態更新トリガー

## 4. ダンジョン生成アルゴリズム統合システム
### データ構造（`data/dungeon_themes.yaml`）
```yaml
dungeon_themes:
  goblin_cave:
    theme_id: goblin_cave
    name: "ゴブリンの洞窟"
    base_layout: "natural_cave"
    difficulty_modifier: 0.8
    enemy_pools:
      common: ["goblin", "goblin_archer", "cave_rat"]
      uncommon: ["goblin_champion", " cave_troll"]
      rare: ["goblin_shaman", "stone_golem"]
    environmental_hazards:
      - {type: "slime", damage: 5, frequency: 0.1}
      - {type: "falling_rocks", damage: 15, frequency: 0.05}
    special_rooms:
      - {type: "throne_room", guardian: "goblin_chief", loot_table: "goblin_treasure"}
      - {type: "egg_chamber", special_effect: "spawn_goblin_lings"}
    story_hooks:
      - {condition: "goblin_leader_present == true", bonus_xp: 200}
      - {condition: "villager_morale < 30", extra_encounters: 2}
  ancient_temple:
    theme_id: ancient_temple
    name: "古代の神殿"
    base_layout: "symmetrical_temple"
    difficulty_modifier: 1.2
    enemy_pools:
      common: ["animated_statue", "temple_guard"]
      uncommon: ["cursed_priest", "stone_sentinel"]
      rare: ["temple_avatar", "ancient_dragon_spirit"]
    environmental_hazards:
      - {type: "darts_trap", damage: 25, frequency: 0.15}
      - {type: "poison_gas", damage: 8, frequency: 0.1}
    special_rooms:
      - {type: "inner_sanctum", puzzle_required: true, reward: "divine_blessing"}
      - {type: "library", special_effect: "random_spell_discovery"}
    story_hooks:
      - {condition: "temple_discovered == true", unlock_secret_boss: true}
      - {condition: "ancient_seal_strength < 50", spawn_evil_entities: 3}
```

### 実装箇所
- `procedural_dungeon_generator.py` - プロシージャルダンジョン生成
- `data/dungeon_themes.yaml` - ダンジョンテーマ定義
- `map_engine.py` - 生成されたダンジョンの統合
- `storyteller_system.py` - ストーリーに基づくダンジョンテーマ選択

## 5. キャラクター関係・記憶システム
### データ構造（`data/character_relations.yaml`）
```yaml
relationship_templates:
  saved_villager:
    id: saved_villager
    name: "助けた村人"
    relationship_type: "gratitude"
    decay_rate: 0.01  # 日ごとの減少率
    interaction_effects:
      - {action: "talk", mood_change: 5, trust_change: 3}
      - {action: "help", mood_change: 10, trust_change: 8}
      - {action: "ignore", mood_change: -5, trust_change: -3}
    benefits_at_levels:
      - {level: 10, benefit: "free_healing_at_inn"}
      - {level: 25, benefit: "villager_militia_support"}
      - {level: 50, benefit: "hidden_knowledge_sharing"}
    memory_triggers:
      - {condition: "player_in_town", dialogue: "また来てくれたんだね！"}
      - {condition: "player_low_health", action: "offer_shelter"}
  former_enemy:
    id: former_enemy
    name: "かつての敵"
    relationship_type: "rivalry"
    decay_rate: 0.02
    interaction_effects:
      - {action: "defeat_in_battle", mood_change: -15, trust_change: -10}
      - {action: "spare_life", mood_change: 5, trust_change: 15}
      - {action: "exchange_gifts", mood_change: 10, trust_change: 10}
    benefits_at_levels:
      - {level: 20, benefit: "rivalry_bonus_damage"}
      - {level: 40, benefit: "duel_invitation"}
      - {level: 60, benefit: "reluctant_alliance_option"}
```

### 実装箇所
- `relationship_system.py` - キャラクター関係管理
- `data/character_relations.yaml` - 関係テンプレート定義
- `npc_behavior.yaml` - NPC動作への関係影響統合
- `entity.py` - キャラクター関係追跡フィールド
- `talk_to_neighbor()` - 関係に基づく会話結果変更

## 6. 動的世界イベントシステム
### データ構造（`data/world_events.yaml`）
```yaml
world_events:
  blood_moon:
    id: blood_moon
    name: "血の月"
    description: "月に赤い光が差し、怪物の活動が活発になる"
    trigger_conditions:
      - {type: "date_match", pattern: "***-10-31"}  # 毎年10月31日
      - {type: "variable_check", name: "ancient_seal_strength", max: 30}
    duration: 3  # 日数
    effects:
      - {type: "enemy_spawn_rate", multiplier: 2.0}
      - {type: "special_enemy_spawn", entity: "blood_werewolf", chance: 0.1}
      - {type: "magic_modifier", school: "necromancy", value: 50}
      - {type: "shop_price_modifier", item_type: "holy_items", value: -30}
    story_triggers:
      - {type: "unlock_chapter", scenario: "werewolf_hunt", condition: "first_blood_moon"}
      - {type: "grant_temporary_title", title: "moonstalker", duration: 7}
  harvest_festival:
    id: harvest_festival
    name: "収穫祭"
    description: "豊作を祝う村の祭り"
    trigger_conditions:
      - {type: "date_match", pattern: "***-09-15"}
      - {type: "variable_check", name: "villager_morale", min: 60}
    duration: 1  # 日数
    effects:
      - {type: "shop_price_modifier", item_type: "food", value: -50}
      - {type: "special_shop_item", item: "festival_special_dish"}
      - {type: "experience_bonus", value: 0.1}  # 10%増加
      - {type: "unique_quest_available", quest_id: "festival_champion"}
    story_triggers:
      - {type: "relationship_boost", target: "all_villagers", value: 10}
      - {type: "unlock_achievement", achievement: "festival_participant"}
```

### 実装箇所
- `world_event_system.py` - ワールドイベント管理
- `data/world_events.yaml` - ワールドイベント定義
- `game.py` - 日付チェックとイベントトリガー
- `systems.py` - イベント効果の適用（戦闘、商価格など）
- `ui_fx_systems.py` - イベントの視覚・音響効果

## 7. 記憶・フラッシュバックシステム
### データ構造（`data/memory_fragments.yaml`）
```yaml
memory_fragments:
  goblin_child_screams:
    id: goblin_child_screams
    name: "ゴブリン子どもの悲鳴"
    description: "過去に目撃したゴブリンの襲撃の記憶の断片"
    trigger_conditions:
      - {type: "location_visit", location: "goblin_cave"}
      - {type: "variable_check", name: "villager_morale", max: 40}
    unlock_requirement:
      - {type: "experience_threshold", value: 1000}
      - {type: "flag_check", flag: "witnessed_goblin_atrocity"}
    effects:
      - {type: "temporary_stat_change", stat: "willpower", value: -10, duration: 5}  # ターン数
      - {type: "vision_effect", effect: "flashback_screams"}
      - {type: "dialogue_unlock", npc: "traumatized_villager", topic: "past_trauma"}
    resolution_paths:
      - {type: "psychotherapy", cost: 500, willpower_recovery: 20}
      - {type: "confrontation", location: "goblin_chief", willpower_recovery: 30}
      - {type: "time_healing", days: 7, willpower_recovery: 15}
  ancestral_voice:
    id: ancestral_voice
    name: "先祖の声"
    description: "血統から受け継がれた古代の知恵の断片"
    trigger_conditions:
      - {type: "skill_check", skill: "ancient_lore", min: 15}
      - {type: "location_type", type: "ancient_ruins"}
    unlock_requirement:
      - {type: "inheritance_check", bloodline: "noble"}
      - {type: "item_possessed", item: "family_heirloom"}
    effects:
      - {type: "skill_temporary_boost", skill: "ancient_lore", value: 25, duration: 10}
      - {type: "reveal_hidden_door", location_bonus: true}
      - {type: "grant_temporary_title", title: "heir_of_ancients", duration: 1}
    resolution_paths:
      - {type: "meditation", location: "sacred_grove", wisdom_gain: 5}
      - {type: "study_artifact", item: "ancient_tablet", wisdom_gain: 10}
```

### 実装箇所
- `memory_system.py` - 記憶フラグメント管理
- `data/memory_fragments.yaml` - 記憶フラグメント定義
- `entity.py` - 記憶状態とトラッキングフィールド
- `render_system.py` - フラッシュバックの視覚効果
- `game.py` - 記憶トリガーチェック（特定行動時）

## 8. 複数エンディング・ストーリー結末システム
### データ構造（`data/story_endings.yaml`）
```yaml
story_endings:
  goblin_peace_bringer:
    id: goblin_peace_bringer
    name: "ゴブリンの和平使者"
    description: "暴力ではなく対話を選び、ゴブリンとの共存を築いた"
    unlock_conditions:
      - {type: "flag_check", flag: "goblin_dialogue_attempted"}
      - {type: "variable_check", name: "goblin_faction_relation", min: 50}
      - {type: "choice_count", choice_type: "peaceful", min: 5}
    ending_scene:
      - {type: "dialogue", npc: "goblin_elder", line: "我々の子供たちが一緒に遊べる日が来るとは..."}
      - {type: "cutscene", scene: "joint_village_festival"}
      - {type: "permanent_world_change", location: "goblin_village", add: "trade_outpost"}
    rewards:
      - {type: "title", id: "peace_bringer"}
      - {type: "permanent_bonus", stat: "charisma", value: 5}
      - {type: "unlock_skill", skill: "diplomatic_immunity"}
      - {type: "legacy_effect", effect: "future_goblin_allies"}
  dragon_slayer_legend:
    id: dragon_slayer_legend
    name: "伝説の竜殺し"
    description: "古代の悪竜を討伐し、王国の救世主となった"
    unlock_conditions:
      - {type: "flag_check", flag: "ancient_dragon_defeated"}
      - {type: "variable_check", name: "dragon_slaying_equipment", min: 3}
      - {type: "achievement_check", achievement: "dragon_slayer"}
    ending_scene:
      - {type: "cutscene", scene: "dragon_defeat_cinematics"}
      - {type: "dialogue", npc: "king", line: "王国はお前のおかげで救われた"}
      - {type: "permanent_world_change", location: "dragon_valley", add: "dragon_slayer_monument"}
    rewards:
      - {type: "title", id: "dragon_slayer_legend"}
      - {type: "permanent_bonus", stat: "attack", value: 10}
      - {type: "unlock_skill", skill: "dragon_slaying_mastery"}
      - {type: "legacy_effect", effect: "dragon_hunt_quests_available"}
  forgotten_wanderer:
    id: forgotten_wanderer
    name: "忘れられた彷徨い人"
    description: "誰にも覚えられず、静かに消えていった冒険者"
    unlock_conditions:
      - {type: "variable_check", name: "player_isolation", min: 80}
      - {type: "flag_check", flag: "no_meaningful_connections"}
      - {type: "turn_count", max: 5000}  # 比較的早期エンディング
    ending_scene:
      - {type: "monologue", text: "風が静かに私の名前を呼んでいる..."}
      - {type: "fade_to_black", duration: 5}
    rewards:
      - {type: "title", id: "forgotten_one"}
      - {type: "permanent_bonus", stat: "stealth", value: 15}
      - {type: "legacy_effect", effect: "hidden_path_discovery_bonus"}
```

### 実装箇所
- `ending_system.py` - エンディング条件判定と実行
- `data/story_endings.yaml` - エンディング定義
- `entity.py` - エンディング条件追跡フィールド
- `game.py` - エンディングチェック（ゲームオーバー時、特定マイルストーン時）
- `render_system.py` - エンディングカットシーン表示

## 9. ストーリーテラーUI・フィードバックシステム
### データ構造（`data/story_ui.yaml`）
```yaml
ui_elements:
  story_notification:
    id: story_notification
    name: "ストーリー通知"
    display_priority: "high"
    duration: 5  # 秒数
    animation: "fade_in_out"
    sound_effect: "story_chime"
    visual_elements:
      - {type: "icon", name: "scroll", color: "gold"}
      - {type: "text", style: "bold", color: "white"}
  choice_prompt:
    id: choice_prompt
    name: "選択肢プロンプト"
    display_priority: "highest"
    duration: null  # プレイヤー入力待ち
    animation: "pulse"
    sound_effect: "choice_tick"
    layout:
      - {type: "question", position: "top"}
      - {type: "options", position: "center", max_width: 40}
      - {type: "hint", position: "bottom", color: "gray"}
  world_state_display:
    id: world_state_display
    name: "ワールド状態表示"
    display_priority: "low"
    duration: null  # 常時表示可能
    animation: "none"
    layout:
      - {type: "section", title: "世界の状態"}
      - {type: "variable", name: "villager_morale", format: "bar", label: "村人の士気"}
      - {type: "variable", name: "goblin_threat", format: "icon_text", label: "ゴブリンの脅威"}
      - {type: "section", title: "最近の出来事"}
      - {type: "event_list", max_items: 5}
```

### 実装箇所
- `story_ui.py` - ストーリーUI管理と表示
- `data/story_ui.yaml` - UI要素定義
- `render_system.py` - ストーリー要素の描画統合
- `input_handler.py` - ストーリー選択肢の入力処理
- `game.py` - ストーリーUIトリガー（特定キー、イベント時）

## 実装優先度マトリクス
| システムコンポーネント | 優先度 | 難易度 | 説明 |
|----------------------|--------|--------|------|
| 1. プロシージャルダンジョンシナリオ生成システム | 高 | 中 | コアゲームプレイに直結 |
| 2. 選択肢分岐・結果永続化システム | 高 | 中 | プレイヤーの選択意味を与える |
| 3. 世界状態永続化・メタプログレスシステム | 高 | 低 | セーブデータの拡張 |
| 4. ダンジョン生成アルゴリズム統合システム | 高 | 中 | 既存ダンジョンシステムとの連携 |
| 5. キャラクター関係・記憶システム | 中 | 中 | NPCインタラクションの深化 |
| 6. 動的世界イベントシステム | 中 | 低 | 世界に生き生き感を与える |
| 7. 記憶・フラッシュバックシステム | 中 | 高 | 複雑なトリガー条件管理 |
| 8. 複数エンディング・ストーリー結末システム | 中 | 中 | リプレイ価値の向上 |
| 9. ストーリーテラーUI・フィードバックシステム | 低 | 低 | プレゼンテーション層 |

## entity.py への追加フィールド
```python
# ストーリー・ワールド状態関連フィールド (Steps 1-9)
story_flags: Dict[str, bool] = field(default_factory=dict)  # ストーリーイベントフラグ
story_variables: Dict[str, Any] = field(default_factory=dict)  # ストーリー変数
story_choices_made: List[str] = field(default_factory=list)  # 行った選択の履歴
world_state_version: str = "1.0"  # ワールド状態のバージョン
player_legacy: Dict[str, Any] = field(default_factory=dict)  # プレイヤーレガシー
character_relationships: Dict[str, Dict[str, int]] = field(
    default_factory=dict
)  # NPC関係値
memory_fragments: List[str] = field(default_factory=list)  # 解放された記憶フラグメント
active_world_events: List[str] = field(
    default_factory=list
)  # 現在アクティブなワールドイベント
completed_storylines: List[str] = field(
    default_factory=list
)  # 完了したストーリーライン
available_storylines: List[str] = field(
    default_factory=list
)  # 利用可能なストーリーライン
story_notifications: List[Dict[str, Any]] = field(
    default_factory=list
)  # 表示中のストーリー通知
current_choice_prompt: Optional[Dict[str, Any]] = field(
    default=None
)  # 現在表示中の選択肢
ending_progress: Dict[str, int] = field(
    default_factory=dict
)  # 各エンディングへの進行度
```

## 統合フロー
1. ゲーム開始時に `WorldStateSystem` が初期状態をロードまたは生成
2. プレイヤーの行動（移動、戦闘、会話など）が `StorytellerSystem` に通知される
3. `StorytellerSystem` が現在のワールド状態、フラグ、変数に基づいて適切なストーリーイベントをトリガー判定
4. トリガーされたイベントに基づいて：
   - 選択肢が提示される場合：`ChoiceSystem` が選択肢UIを表示し、プレイヤー入力を待つ
   - 自動的に発生するイベントの場合：即座に効果が適用される
5. 選択またはイベントの結果が：
   - ワールド状態変数を更新
   - ストーリーフラグを設定/解除
   - キャラクター関係値を変更
   - アイテム/経験値/ゴールドを付与
   - 新しいダンジョンテーマやクエストをアンロック
6. 一定時間間隔で `WorldEventSystem` が日付や条件をチェックし、ワールドイベントをトリガー
7. ゲームセーブ時にすべてのストーリー関連データが永続化
8. ゲームロード時にストーリー状態が完全に復元され、継続が可能

## 次のステップ
提案されたシステムの実装を開始するには、以下のファイルから順に作成していくことを推奨：
1. `data/procedural_scenarios.yaml` - 基本シナリオテンプレート
2. `data/story_choices.yaml` - 選択肢結果定義
3. `data/world_state.yaml` - ワールド状態テンプレート
4. `entity.py` にストーリー関連フィールドを追加
5. `storyteller_system.py` メインファイルを作成
