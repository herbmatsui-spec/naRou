# ダンジョン・ワールド自動生成ストーリーテラー 詳細実装計画書

## Step 1: data/procedural_scenarios.yaml 基本構造作成
- ファイル `data/procedural_scenarios.yaml` を作成し、基本的なYAML構造を定義
- シナリオテンプレートのトップレベルキー `scenario_templates:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/procedural_scenarios.yaml', encoding='utf-8')); print('OK' if data and 'scenario_templates' in data else 'ERROR')"

## Step 2: data/procedural_scenarios.yaml ゴブリン侵略シナリオ追加
- `data/procedural_scenarios.yaml` に「ゴブリンの侵略」シナリオの基本構造を追加
- id, name, description, chapters 配列を定義
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/procedural_scenarios.yaml', encoding='utf-8')); t=data.get('scenario_templates',{}).get('goblin_invasion'); print(f'Scenario exists: {t is not None}'); print(f'Chapters count: {len(t.get(\"chapters\",[])) if t else 0}')"

## Step 3: data/story_choices.yaml 基本構造作成
- ファイル `data/story_choices.yaml` を作成し、基本的なYAML構造を定義
- 選択肢結果のトップレベルキー `choice_consequences:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/story_choices.yaml', encoding='utf-8')); print('OK' if data and 'choice_consequences' in data else 'ERROR')"

## Step 4: data/story_choices.yaml 農家の生存者救出結果追加
- `data/story_choices.yaml` に「農家の生存者を救出した」選択肢結果を追加
- id, description, immediate_effects, long_term_effects, world_state_changes を定義
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/story_choices.yaml', encoding='utf-8')); c=data.get('choice_consequences',{}).get('farm_survivor_saved'); print(f'Consequence exists: {c is not None}'); print(f'Immediate effects: {len(c.get(\"immediate_effects\",[])) if c else 0}')"

## Step 5: data/world_state.yaml 基本構造作成
- ファイル `data/world_state.yaml` を作成し、基本的なYAML構造を定義
- ワールド状態のトップレベルキー `world_state_template:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/world_state.yaml', encoding='utf-8')); print('OK' if data and 'world_state_template' in data else 'ERROR')"

## Step 6: data/world_state.yaml 基本ワールド状態テンプレート追加
- `data/world_state.yaml` に基本ワールド状態テンプレートを追加
- version, last_updated, persistent_variables, location_states, faction_relations, global_events, player_legacy を定義
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/world_state.yaml', encoding='utf-8')); t=data.get('world_state_template'); print(f'Template exists: {t is not None}'); print(f'Variables keys: {list(t.get(\"persistent_variables\",{}).keys()) if t else []}')"

## Step 7: data/dungeon_themes.yaml 基本構造作成
- ファイル `data/dungeon_themes.yaml` を作成し、基本的なYAML構造を定義
- ダンジョンテーマのトップレベルキー `dungeon_themes:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/dungeon_themes.yaml', encoding='utf-8')); print('OK' if data and 'dungeon_themes' in data else 'ERROR')"

## Step 8: data/dungeon_themes.yaml ゴブリンの洞窟テーマ追加
- `data/dungeon_themes.yaml` に「ゴブリンの洞窟」ダンジョンテーマを追加
- theme_id, name, base_layout, difficulty_modifier, enemy_pools, environmental_hazards, special_rooms, story_hooks を定義
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/dungeon_themes.yaml', encoding='utf-8')); t=data.get('dungeon_themes',{}).get('goblin_cave'); print(f'Theme exists: {t is not None}'); print(f'Enemy pools: {list(t.get(\"enemy_pools\",{}).keys()) if t else []}')"

## Step 9: data/character_relations.yaml 基本構造作成
- ファイル `data/character_relations.yaml` を作成し、基本的なYAML構造を定義
- 関係テンプレートのトップレベルキー `relationship_templates:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/character_relations.yaml', encoding='utf-8')); print('OK' if data and 'relationship_templates' in data else 'ERROR')"

## Step 10: data/character_relations.yaml 助けた村人関係追加
- `data/character_relations.yaml` に「助けた村人」関係テンプレートを追加
- id, name, relationship_type, decay_rate, interaction_effects, benefits_at_levels, memory_triggers を定義
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/character_relations.yaml', encoding='utf-8')); r=data.get('relationship_templates',{}).get('saved_villager'); print(f'Relationship exists: {r is not None}'); print(f'Interaction effects: {len(r.get(\"interaction_effects\",[])) if r else 0}')"

## Step 11: data/world_events.yaml 基本構造作成
- ファイル `data/world_events.yaml` を作成し、基本的なYAML構造を定義
- ワールドイベントのトップレベルキー `world_events:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/world_events.yaml', encoding='utf-8')); print('OK' if data and 'world_events' in data else 'ERROR')"

## Step 12: data/world_events.yaml 血の月イベント追加
- `data/world_events.yaml` に「血の月」ワールドイベントを追加
- id, name, description, trigger_conditions, duration, effects, story_triggers を定義
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/world_events.yaml', encoding='utf-8')); e=data.get('world_events',{}).get('blood_moon'); print(f'Event exists: {e is not None}'); print(f'Duration: {e.get(\"duration\") if e else \"Missing\"}')"

## Step 13: data/memory_fragments.yaml 基本構造作成
- ファイル `data/memory_fragments.yaml` を作成し、基本的なYAML構造を定義
- 記憶フラグメントのトップレベルキー `memory_fragments:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/memory_fragments.yaml', encoding='utf-8')); print('OK' if data and 'memory_fragments' in data else 'ERROR')"

## Step 14: data/memory_fragments.yaml ゴブリン子どもの悲鳴フラグメント追加
- `data/memory_fragments.yaml` に「ゴブリン子どもの悲鳴」記憶フラグメントを追加
- id, name, description, trigger_conditions, unlock_requirement, effects, resolution_paths を定義
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/memory_fragments.yaml', encoding='utf-8')); m=data.get('memory_fragments',{}).get('goblin_child_screams'); print(f'Fragment exists: {m is not None}'); print(f'Trigger conditions: {len(m.get(\"trigger_conditions\",[])) if m else 0}')"

## Step 15: data/story_endings.yaml 基本構造作成
- ファイル `data/story_endings.yaml` を作成し、基本的なYAML構造を定義
- ストーリーエンディングのトップレベルキー `story_endings:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/story_endings.yaml', encoding='utf-8')); print('OK' if data and 'story_endings' in data else 'ERROR')"

## Step 16: data/story_endings.yaml ゴブリンの和平使者エンディング追加
- `data/story_endings.yaml` に「ゴブリンの和平使者」エンディングを追加
- id, name, description, unlock_conditions, ending_scene, rewards を定義
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/story_endings.yaml', encoding='utf-8')); en=data.get('story_endings',{}).get('goblin_peace_bringer'); print(f'Ending exists: {en is not None}'); print(f'Unlock conditions: {len(en.get(\"unlock_conditions\",[])) if en else 0}')"

## Step 17: data/story_ui.yaml 基本構造作成
- ファイル `data/story_ui.yaml` を作成し、基本的なYAML構造を定義
- UI要素のトップレベルキー `ui_elements:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/story_ui.yaml', encoding='utf-8')); print('OK' if data and 'ui_elements' in data else 'ERROR')"

## Step 18: data/story_ui.yaml ストーリー通知UI要素追加
- `data/story_ui.yaml` に「ストーリー通知」UI要素を追加
- id, name, display_priority, duration, animation, sound_effect, visual_elements を定義
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/story_ui.yaml', encoding='utf-8')); u=data.get('ui_elements',{}).get('story_notification'); print(f'UI element exists: {u is not None}'); print(f'Display priority: {u.get(\"display_priority\") if u else \"Missing\"}')"

## Step 19: entity.py ストーリー関連フィールド追加準備
- `entity.py` の Entity クラスにストーリー関連フィールドのプレースホルダーコメントを追加
- フィールド追加の場所を示すコメント: `# TODO: Story/world state fields will be added here`
- 検証: `grep -n "TODO: Story/world state fields" entity.py`

## Step 20: entity.py story_flags フィールド追加
- `entity.py` の Entity クラスに `story_flags: Dict[str, bool] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'story_flags'))"`

## Step 21: entity.py story_variables フィールド追加
- `entity.py` の Entity クラスに `story_variables: Dict[str, Any] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'story_variables'))"`

## Step 22: entity.py story_choices_made フィールド追加
- `entity.py` の Entity クラスに `story_choices_made: List[str] = field(default_factory=list)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'story_choices_made'))"`

## Step 23: entity.py world_state_version フィールド追加
- `entity.py` の Entity クラスに `world_state_version: str = "1.0"` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'world_state_version'))"`

## Step 24: entity.py player_legacy フィールド追加
- `entity.py` の Entity クラスに `player_legacy: Dict[str, Any] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'player_legacy'))"`

## Step 25: entity.py character_relationships フィールド追加
- `entity.py` の Entity クラスに `character_relationships: Dict[str, Dict[str, int]] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'character_relationships'))"`

## Step 26: entity.py memory_fragments フィールド追加
- `entity.py` の Entity クラスに `memory_fragments: List[str] = field(default_factory=list)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'memory_fragments'))"`

## Step 27: entity.py active_world_events フィールド追加
- `entity.py` の Entity クラスに `active_world_events: List[str] = field(default_factory=list)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'active_world_events'))"`

## Step 28: entity.py completed_storylines フィールド追加
- `entity.py` の Entity クラスに `completed_storylines: List[str] = field(default_factory=list)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'completed_storylines'))"`

## Step 29: entity.py available_storylines フィールド追加
- `entity.py` の Entity クラスに `available_storylines: List[str] = field(default_factory=list)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'available_storylines'))"`

## Step 30: entity.py story_notifications フィールド追加
- `entity.py` の Entity クラスに `story_notifications: List[Dict[str, Any]] = field(default_factory=list)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'story_notifications'))"`

## Step 31: entity.py current_choice_prompt フィールド追加
- `entity.py` の Entity クラスに `current_choice_prompt: Optional[Dict[str, Any]] = field(default=None)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'current_choice_prompt'))"`

## Step 32: entity.py ending_progress フィールド追加
- `entity.py` の Entity クラスに `ending_progress: Dict[str, int] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'ending_progress'))"`

## Step 33: storyteller_system.py 新規ファイル作成
- 空のファイル `storyteller_system.py` を作成
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la storyteller_system.py`

## Step 34: storyteller_system.py StoryScenarioData クラス定義
- `storyteller_system.py` に `@dataclass` デコレータ付きの `StoryScenarioData` クラスを定義
- フィールド: id, name, description, chapters
- 検証: `python -c "from storyteller_system import StoryScenarioData; print('StoryScenarioData class exists')`

## Step 35: storyteller_system.py StoryChapterData クラス定義
- `storyteller_system.py` に `@dataclass` デコレータ付きの `StoryChapterData` クラスを定義
- フィールド: id, name, type, objectives, choices
- 検証: `python -c "from storyteller_system import StoryChapterData; print('StoryChapterData class exists')`

## Step 36: storyteller_system.py StoryChoiceData クラス定義
- `storyteller_system.py` に `@dataclass` デコレータ付きの `StoryChoiceData` クラスを定義
- フィールド: id, description, consequence
- 検証: `python -c "from storyteller_system import StoryChoiceData; print('StoryChoiceData class exists')`

## Step 37: storyteller_system.py ChoiceConsequenceData クラス定義
- `storyteller_system.py` に `@dataclass` デコレータ付きの `ChoiceConsequenceData` クラスを定義
- フィールド: id, description, immediate_effects, long_term_effects, world_state_changes
- 検証: `python -c "from storyteller_system import ChoiceConsequenceData; print('ChoiceConsequenceData class exists')`

## Step 38: storyteller_system.py StorytellerRegistry クラス作成
- `storyteller_system.py` に `StorytellerRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all_scenarios()` メソッドで全シナリオテンプレートの取得
- 検証: `python -c "from storyteller_system import REGISTRY; REGISTRY.load(); print('Registry loaded')`

## Step 39: storyteller_system.py StorytellerRegistry.load() 実装
- `StorytellerRegistry.load()` メソッドを実装
- `data/procedural_scenarios.yaml` からYAMLを読み込み、StoryScenarioData オブジェクトに変換
- エラーハンドリング（ファイルが存在しない場合のデフォルトシナリオ作成）
- 検証: `python -c "from storyteller_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all_scenarios())} scenarios')`

## Step 40: storyteller_system.py StorytellerManager クラス作成
- `storyteller_system.py` に `StorytellerManager` クラスを作成
- `check_scenario_triggers()` メソッドのスタブ実装
- `activate_scenario()` メソッドのスタブ実装
- `process_choice()` メソッドのスタブ実装
- 検証: `python -c "from storyteller_system import StorytellerManager; m = StorytellerManager(); print('Manager created')`

## Step 41: choice_system.py 新規ファイル作成
- 空のファイル `choice_system.py` を作成
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la choice_system.py`

## Step 42: choice_system.py ChoiceConsequenceData クラス定義（再定義）
- `choice_system.py` に `@dataclass` デコレータ付きの `ChoiceConsequenceData` クラスを定義
- フィールド: id, description, immediate_effects, long_term_effects, world_state_changes
- 検証: `python -c "from choice_system import ChoiceConsequenceData; print('ChoiceConsequenceData class exists')`

## Step 43: choice_system.py ChoiceRegistry クラス作成
- `choice_system.py` に `ChoiceRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all_consequences()` メソッドで全選択肢結果の取得
- 検証: `python -c "from choice_system import REGISTRY; REGISTRY.load(); print('Registry loaded')`

## Step 44: choice_system.py ChoiceRegistry.load() 実装
- `ChoiceRegistry.load()` メソッドを実装
- `data/story_choices.yaml` からYAMLを読み込み、ChoiceConsequenceData オブジェクトに変換
- エラーハンドリング
- 検証: `python -c "from choice_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all_consequences())} consequences')`

## Step 45: choice_system.py ChoiceManager クラス作成
- `choice_system.py` に `ChoiceManager` クラスを作成
- `get_consequence()` メソッドのスタブ実装
- `apply_consequence()` メソッドのスタブ実装
- 検証: `python -c "from choice_system import ChoiceManager; m = ChoiceManager(); print('Manager created')`

## Step 46: choice_system.py 選択肢結果適用ロジック
- `ChoiceManager.apply_consequence()` メソッドを実装
- 即時効果の適用（アイテム付与、経験値増加など）
- 長期効果の適用（クエストアンロック、永続ボーナスなど）
- ワールド状態変更の適用
- 検証: `python -c "from choice_system import ChoiceManager; m = ChoiceManager(); print('apply_consequence method exists')`

## Step 47: world_state_system.py 新規ファイル作成
- 空のファイル `world_state_system.py` を作成
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la world_state_system.py`

## Step 48: world_state_system.py WorldStateTemplate クラス定義
- `world_state_system.py` に `@dataclass` デコレータ付きの `WorldStateTemplate` クラスを定義
- フィールド: version, last_updated, persistent_variables, location_states, faction_relations, global_events, player_legacy
- 検証: `python -c "from world_state_system import WorldStateTemplate; print('WorldStateTemplate class exists')`

## Step 49: world_state_system.py WorldStateRegistry クラス作成
- `world_state_system.py` に `WorldStateRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `get_template()` メソッドでワールド状態テンプレートの取得
- `create_from_template()` メソッドでテンプレートからインスタンス作成
- 検証: `python -c "from world_state_system import REGISTRY; REGISTRY.load(); print('Registry loaded')`

## Step 50: world_state_system.py WorldStateRegistry.load() 実装
- `WorldStateRegistry.load()` メソッドを実装
- `data/world_state.yaml` からYAMLを読み込み、WorldStateTemplate オブジェクトに変換
- エラーハンドリング
- 検証: `python -c "from world_state_system import REGISTRY; REGISTRY.load(); print(f'Loaded template version: {REGISTRY.get_template().version}')"

## Step 51: world_state_system.py WorldStateManager クラス作成
- `world_state_system.py` に `WorldStateManager` クラスを作成
- `get_variable()` メソッドのスタブ実装
- `set_variable()` メソッドのスタブ実装
- `update_location_state()` メソッドのスタブ実装
- `update_faction_relation()` メソッドのスタブ実装
- 検証: `python -c "from world_state_system import WorldStateManager; m = WorldStateManager(); print('Manager created')`

## Step 52: world_state_system.py ワールド状態変数取得ロジック
- `WorldStateManager.get_variable()` メソッドを実装
- 永続変数の取得、デフォルト値の処理
- 検証: `python -c "from world_state_system import WorldStateManager; m = WorldStateManager(); print('get_variable method exists')`

## Step 53: world_state_system.py ワールド状態変数更新ロジック
- `WorldStateManager.set_variable()` メソッドを実装
- 永続変数の更新、バリデーション、変更イベントのトリガー
- 検証: `python -c "from world_state_system import WorldStateManager; m = WorldStateManager(); print('set_variable method exists')`

## Step 54: procedural_dungeon_generator.py 新規ファイル作成
- 空のファイル `procedural_dungeon_generator.py` を作成
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la procedural_dungeon_generator.py`

## Step 55: procedural_dungeon_generator.py DungeonThemeData クラス定義
- `procedural_dungeon_generator.py` に `@dataclass` デコレータ付きの `DungeonThemeData` クラスを定義
- フィールド: theme_id, name, base_layout, difficulty_modifier, enemy_pools, environmental_hazards, special_rooms, story_hooks
- 検証: `python -c "from procedural_dungeon_generator import DungeonThemeData; print('DungeonThemeData class exists')`

## Step 56: procedural_dungeon_generator.py DungeonThemeRegistry クラス作成
- `procedural_dungeon_generator.py` に `DungeonThemeRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all_themes()` メソッドで全ダンジョンテーマの取得
- 検証: `python -c "from procedural_dungeon_generator import REGISTRY; REGISTRY.load(); print('Registry loaded')`

## Step 57: procedural_dungeon_generator.py DungeonThemeRegistry.load() 実装
- `DungeonThemeRegistry.load()` メソッドを実装
- `data/dungeon_themes.yaml` からYAMLを読み込み、DungeonThemeData オブジェクトに変換
- エラーハンドリング
- 検証: `python -c "from procedural_dungeon_generator import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all_themes())} themes')`

## Step 58: procedural_dungeon_generator.py ProceduralDungeonGenerator クラス作成
- `procedural_dungeon_generator.py` に `ProceduralDungeonGenerator` クラスを作成
- `generate_dungeon()` メソッドのスタブ実装
- `select_theme_by_story()` メソッドのスタブ実装（ストーリー状態に基づくテーマ選択）
- 検証: `python -c "from procedural_dungeon_generator import ProceduralDungeonGenerator; g = ProceduralDungeonGenerator(); print('Generator created')`

## Step 59: procedural_dungeon_generator.py ダンジョンテーマ選択ロジック
- `ProceduralDungeonGenerator.select_theme_by_story()` メソッドを実装
- ストーリー変数とフラグに基づくテーマ選択ロジック
- デフォルトテーマへのフォールバック
- 検証: `python -c "from procedural_dungeon_generator import ProceduralDungeonGenerator; g = ProceduralDungeonGenerator(); print('select_theme_by_story method exists')`

## Step 60: relationship_system.py 新規ファイル作成
- 空のファイル `relationship_system.py` を作成
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la relationship_system.py`

## Step 61: relationship_system.py RelationshipTemplateData クラス定義
- `relationship_system.py` に `@dataclass` デコレータ付きの `RelationshipTemplateData` クラスを定義
- フィールド: id, name, relationship_type, decay_rate, interaction_effects, benefits_at_levels, memory_triggers
- 検証: `python -c "from relationship_system import RelationshipTemplateData; print('RelationshipTemplateData class exists')`

## Step 62: relationship_system.py RelationshipRegistry クラス作成
- `relationship_system.py` に `RelationshipRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all_templates()` メソッドで全関係テンプレートの取得
- 検証: `python -c "from relationship_system import REGISTRY; REGISTRY.load(); print('Registry loaded')`

## Step 63: relationship_system.py RelationshipRegistry.load() 実装
- `RelationshipRegistry.load()` メソッドを実装
- `data/character_relations.yaml` からYAMLを読み込み、RelationshipTemplateData オブジェクトに変換
- エラーハンドリング
- 検証: `python -c "from relationship_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all_templates())} templates')`

## Step 64: relationship_system.py RelationshipManager クラス作成
- `relationship_system.py` に `RelationshipManager` クラスを作成
- `get_relationship_level()` メソッドのスタブ実装
- `update_relationship()` メソッドのスタブ実装
- `get_relationship_benefits()` メソッドのスタブ実装
- 検証: `python -c "from relationship_system import RelationshipManager; m = RelationshipManager(); print('Manager created')`

## Step 65: relationship_system.py 関係レベル計算ロジック
- `RelationshipManager.get_relationship_level()` メソッドを実装
- 基本レベル計算、時間経過による減衰適用
- 検証: `python -c "from relationship_system import RelationshipManager; m = RelationshipManager(); print('get_relationship_level method exists')`

## Step 66: relationship_system.py 関係更新ロジック
- `RelationshipManager.update_relationship()` メソッドを実装
- インタラクションタイプに基づく気分の変化、信頼度の変化適用
- 検証: `python -c "from relationship_system import RelationshipManager; m = RelationshipManager(); print('update_relationship method exists')`

## Step 67: world_event_system.py 新規ファイル作成
- 空のファイル `world_event_system.py` を作成
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la world_event_system.py`

## Step 68: world_event_system.py WorldEventData クラス定義
- `world_event_system.py` に `@dataclass` デコレータ付きの `WorldEventData` クラスを定義
- フィールド: id, name, description, trigger_conditions, duration, effects, story_triggers
- 検証: `python -c "from world_event_system import WorldEventData; print('WorldEventData class exists')`

## Step 69: world_event_system.py WorldEventRegistry クラス作成
- `world_event_system.py` に `WorldEventRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all_events()` メソッドで全ワールドイベントの取得
- 検証: `python -c "from world_event_system import REGISTRY; REGISTRY.load(); print('Registry loaded')`

## Step 70: world_event_system.py WorldEventRegistry.load() 実装
- `WorldEventRegistry.load()` メソッドを実装
- `data/world_events.yaml` からYAMLを読み込み、WorldEventData オブジェクトに変換
- エラーハンドリング
- 検証: `python -c "from world_event_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all_events())} events')`

## Step 71: world_event_system.py WorldEventManager クラス作成
- `world_event_system.py` に `WorldEventManager` クラスを作成
- `check_event_triggers()` メソッドのスタブ実装
- `trigger_event()` メソッドのスタブ実装
- `update_active_events()` メソッドのスタブ実装
- 検証: `python -c "from world_event_system import WorldEventManager; m = WorldEventManager(); print('Manager created')`

## Step 72: game.py ストーリーシステム統合
- `game.py` の Engine クラスに 各種マネージャーへの参照を追加
  - `storyteller_manager: StorytellerManager`
  - `choice_manager: ChoiceManager`
  - `world_state_manager: WorldStateManager`
  - `procedural_dungeon_generator: ProceduralDungeonGenerator`
  - `relationship_manager: RelationshipManager`
  - `world_event_manager: WorldEventManager`
- `__init__` メソッドで初期化
- `_on_kill()` メソッドで ストーリー変数更新チェック追加
- `advance_world()` メソッドで ワールドイベントチェックとストーリーシナリオトリガーチェック追加
- `talk_to_neighbor()` メソッドで キャラクター関係更新追加
- `render_all()` メソッドで ストーリー通知と選択肢プロンプト表示追加
- 検証: `python -c "from game import Engine; e = Engine(); print(f'Storyteller manager: {hasattr(e, \"storyteller_manager\")}'); print(f'World state manager: {hasattr(e, \"world_state_manager\")}'); print(f'Choice manager: {hasattr(e, \"choice_manager\")}')"

この実装計画書は、ダンジョン・ワールド自動生成ストーリーテラーを72の小さなステップに分割しています。
各ステップは具体的なファイル変更、コード追加、および検証コマンドを含んでおり、
低性能なLLMでも段階的に実装を進めることができます。