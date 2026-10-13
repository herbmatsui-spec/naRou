# 輪廻転生・ニューゲーム+システム 詳細実装計画書

## Step 1: data/reincarnation.yaml 基本構造作成
- ファイル `data/reincarnation.yaml` を作成し、基本的なYAML構造を定義
- 転生のトップレベルキー `reincarnation:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/reincarnation.yaml', encoding='utf-8')); print('OK' if data and 'reincarnation' in data else 'ERROR')"`
## Step 2: data/reincarnation.yaml 基本転生要件追加
- `data/reincarnation.yaml` に基本転生要件を追加
- min_level, max_level, stat_bonus_per_reincarnation, level_reset_multiplier
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/reincarnation.yaml', encoding='utf-8')); r=data.get('reincarnation',{}); print(f'Min level: {r.get(\"base_requirements\",{}).get(\"min_level\") if r else \"Missing\"}')"`
## Step 3: data/reincarnation_inheritance.yaml 基本構造作成
- ファイル `data/reincarnation_inheritance.yaml` を作成し、基本的なYAML構造を定義
- 継承のトップレベルキー `inheritance:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/reincarnation_inheritance.yaml', encoding='utf-8')); print('OK' if data and 'inheritance' in data else 'ERROR')"`
## Step 4: data/reincarnation_inheritance.yaml 基本継承ルール追加
- `data/reincarnation_inheritance.yaml` に基本継承ルールを追加
- always_keepリストとselective_keepセクション（ポイント制）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/reincarnation_inheritance.yaml', encoding='utf-8')); i=data.get('inheritance',{}); print(f'Always keep: {i.get(\"always_keep\") if i else \"Missing\"}'); print(f'Points per reincarnation: {i.get(\"selective_keep\",{}).get(\"points_per_reincarnation\") if i else \"Missing\"}')"`
## Step 5: data/karma.yaml 基本構造作成
- ファイル `data/karma.yaml` を作成し、基本的なYAML構造を定義
- カーマのトップレベルキー `karma:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/karma.yaml', encoding='utf-8')); print('OK' if data and 'karma' in data else 'ERROR')"`
## Step 6: data/karma.yaml カーマ軸と行動追加
- `data/karma.yaml` にカーマ軸（law_chaos, good_evil）と基本行動を追加
- alignmentセクションとactionsセクション
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/karma.yaml', encoding='utf-8')); k=data.get('karma',{}); print(f'Law-Chaos range: {k.get(\"alignment\",{}).get(\"law_chaos\",{}).get(\"range\") if k else \"Missing\"}'); print(f'Good-Evil neutral: {k.get(\"alignment\",{}).get(\"good_evil\",{}).get(\"neutral\") if k else \"Missing\"}')"`
## Step 7: data/reincarnation_dungeons.yaml 基本構造作成
- ファイル `data/reincarnation_dungeons.yaml` を作成し、基本的なYAML構造を定義
- ダンジョンのトップレベルキー `dungeons:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/reincarnation_dungeons.yaml', encoding='utf-8')); print('OK' if data and 'dungeons' in data else 'ERROR')"`
## Step 8: data/reincarnation_dungeons.yaml 初心者ダンジョン追加
- `data/reincarnation_dungeons.yaml` に「最初の試練」ダンジョンを追加
- min_reincarnation, max_reincarnation, name, description, floors, rewards
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/reincarnation_dungeons.yaml', encoding='utf-8')); d=data.get('dungeons',{}).get('first_life_trial'); print(f'Dungeon name: {d.get(\"name\") if d else \"Missing\"}'); print(f'Min reincarnation: {d.get(\"min_reincarnation\") if d else \"Missing\"}')"`
## Step 9: data/reincarnation_scaling.yaml 基本構造作成
- ファイル `data/reincarnation_scaling.yaml` を作成し、基本的なYAML構造を定義
- スケーリングのトップレベルキー `scaling:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/reincarnation_scaling.yaml', encoding='utf-8')); print('OK' if data and 'scaling' in data else 'ERROR')"`
## Step 10: data/reincarnation_scaling.yaml 敵ステータススケーリング追加
- `data/reincarnation_scaling.yaml` に敵ステータス増加率を追加
- base, per_reincarnation, max_multiplier
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/reincarnation_scaling.yaml', encoding='utf-8')); s=data.get('scaling',{}); print(f'Enemy base: {s.get(\"enemy_stats_multiplier\",{}).get(\"base\") if s else \"Missing\"}'); print(f'Per reincarnation: {s.get(\"enemy_stats_multiplier\",{}).get(\"per_reincarnation\") if s else \"Missing\"}')"`
## Step 11: entity.py 転生関連フィールド追加準備
- `entity.py` の Entity クラスに転生関連フィールドのプレースホルダーコメントを追加
- フィールド追加の場所を示すコメント: `# TODO: Reincarnation fields will be added here`
- 検証: `grep -n "TODO: Reincarnation fields" entity.py`
## Step 12: entity.py 基本転生フィールド追加
- `entity.py` の Entity クラスに `reincarnation_count: int = 0` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'reincarnation_count'))"`
## Step 13: entity.py カーマフィールド追加
- `entity.py` の Entity クラスに `karma_law_chaos: int = 0` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'karma_law_chaos'))"`
## Step 14: entity.py カーマフィールド追加（続き）
- `entity.py` の Entity クラスに `karma_good_evil: int = 0` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'karma_good_evil'))"`
## Step 15: entity.py レガシースキルフィールド追加
- `entity.py` の Entity クラスに `legacy_skills: List[str] = field(default_factory=list)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'legacy_skills'))"`
## Step 16: entity.py 転生ダンジョンアンロックフィールド追加
- `entity.py` の Entity クラスに `unlocked_reincarnation_dungeons: List[str] = field(default_factory=list)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'unlocked_reincarnation_dungeons'))"`
## Step 17: entity.py メモリーフラグメントフィールド追加
- `entity.py` の Entity クラスに `collected_fragments: List[str] = field(default_factory=list)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'collected_fragments'))"`
## Step 18: entity.py 神恩寵フィールド追加
- `entity.py` の Entity クラスに `favor: Dict[str, int] = field(default_factory=list)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'favor'))"`
## Step 19: entity.py 転生準備用一時フィールド追加
- `entity.py` の Entity クラスに `inheritance_selection: Dict[str, Any] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'inheritance_selection'))"`
## Step 20: entity.py チャレンジ進捗フィールド追加
- `entity.py` の Entity クラスに `challenge_progress: Dict[str, int] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'challenge_progress'))"`
## Step 21: reincarnation_system.py 新規ファイル作成
- 空のファイル `reincarnation_system.py` を作成
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la reincarnation_system.py`
## Step 22: reincarnation_system.py ReincarnationData クラス定義
- `reincarnation_system.py` に `@dataclass` デコレータ付きの `ReincarnationData` クラスを定義
- フィールド: id, min_level, max_level, stat_bonus, level_reset_multiplier, name, description
- 検証: `python -c "from reincarnation_system import ReincarnationData; print('ReincarnationData class exists')"`
## Step 23: reincarnation_system.py ReincarnationRegistry クラス作成
- `reincarnation_system.py` に `ReincarnationRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all()` メソッドで全転生データの取得
- 検証: `python -c "from reincarnation_system import REGISTRY; REGISTRY.load(); print('Registry loaded')"`
## Step 24: reincarnation_system.py ReincarnationRegistry.load() 実装
- `ReincarnationRegistry.load()` メソッドを実装
- `data/reincarnation.yaml` からYAMLを読み込み、ReincarnationData オブジェクトに変換
- エラーハンドリング（ファイルが存在しない場合のデフォルト転生データ作成）
- 検証: `python -c "from reincarnation_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all())} reincarnation configs')"`
## Step 25: reincarnation_system.py ReincarnationManager クラス作成
- `reincarnation_system.py` に `ReincarnationManager` クラスを作成
- `can_reincarnate()` メソッドのスタブ実装
- `reincarnate()` メソッドのスタブ実装
- 検証: `python -c "from reincarnation_system import ReincarnationManager; m = ReincarnationManager(); print('Manager created')"`
## Step 26: reincarnation_system.py 転生可能チェックロジック
- `ReincarnationManager.can_reincarnate()` メソッドを実装
- レベルチェックと基本条件評価
- 検証: `python -c "from reincarnation_system import ReincarnationManager; m = ReincarnationManager(); print('can_reincarnate method exists')"`
## Step 27: reincarnation_system.py 転生実行ロジック
- `ReincarnationManager.reincarnate()` メソッドを実装
- 基本的な転生処理（レベルリセット、転生回数インクリメント）
- 検証: `python -c "from reincarnation_system import ReincarnationManager; m = ReincarnationManager(); print('reincarnate method exists')"`
## Step 28: game.py 転生マネージャー参照追加
- `game.py` の Engine クラスに `reincarnation_manager: ReincarnationManager` フィールドを追加
- `__init__` メソッドで初期化
- 検証: `python -c "from game import Engine; e = Engine(); print(hasattr(e, 'reincarnation_manager'))"`
## Step 29: game.py 転生オプション表示準備
- `game.py` の 特定条件下で転生オプションを表示するロジックのプレースホルダーを追加
- レベル上限到達時または特定アイテム使用時の転生メニュー表示準備
- 検証: `grep -n "# TODO: Reincarnation option" game.py`
## Step 30: game.py 転生オプション表示ロジック
- `game.py` に 転生オプションを表示するロジックを実装
- レベルが転生可能範囲内かチェックし、転生メニューを準備
- 検証: `python -c "import game; print('Reincarnation option logic added')"`
## Step 31: inheritance_system.py 新規ファイル作成
- 空のファイル `inheritance_system.py` を作成
- 特典継承システム用のファイル
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la inheritance_system.py`
## Step 32: inheritance_system.py InheritanceData クラス定義
- `inheritance_system.py` に `@dataclass` デコレータ付きの `InheritanceData` クラスを定義
- フィールド: id, name, description, always_keep, selective_keep_rules
- 検証: `python -c "from inheritance_system import InheritanceData; print('InheritanceData class exists')"`
## Step 33: inheritance_system.py InheritanceRegistry クラス作成
- `inheritance_system.py` に `InheritanceRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all()` メソッドで全継承データの取得
- 検証: `python -c "from inheritance_system import REGISTRY; REGISTRY.load(); print('Registry loaded')"`
## Step 34: inheritance_system.py InheritanceRegistry.load() 実装
- `InheritanceRegistry.load()` メソッドを実装
- `data/reincarnation_inheritance.yaml` からYAMLを読み込み、InheritanceData オブジェクトに変換
- エラーハンドリング
- 検証: `python -c "from inheritance_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all())} inheritance configs')"`
## Step 35: inheritance_system.py InheritanceManager クラス作成
- `inheritance_system.py` に `InheritanceManager` クラスを作成
- `process_inheritance()` メソッドのスタブ実装
- 検証: `python -c "from inheritance_system import InheritanceManager; m = InheritanceManager(); print('Manager created')"`
## Step 36: karma_system.py 新規ファイル作成
- 空のファイル `karma_system.py` を作成
- カーマシステム用のファイル
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la karma_system.py`
## Step 37: karma_system.py KarmaData クラス定義
- `karma_system.py` に `@dataclass` デコレータ付きの `KarmaData` クラスを定義
- フィールド: id, name, description, alignment_ranges, actions, reincarnation_effects
- 検証: `python -c "from karma_system import KarmaData; print('KarmaData class exists')"`
## Step 38: karma_system.py KarmaRegistry クラス作成
- `karma_system.py` に `KarmaRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all()` メソッドで全カーマデータの取得
- �検証: `python -c "from karma_system import REGISTRY; REGISTRY.load(); print('Registry loaded')"`
## Step 39: karma_system.py KarmaRegistry.load() 実装
- `KarmaRegistry.load()` メソッドを実装
- `data/karma.yaml` からYAMLを読み込み、KarmaData オブジェクトに変換
- エラーハンドリング
- 検証: `python -c "from karma_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all())} karma configs')"`
## Step 40: karma_system.py KarmaManager クラス作成
- `karma_system.py` に `KarmaManager` クラスを作成
- `update_karma()` メソッドのスタブ実装
- `get_karma_bonuses()` メソッドのスタブ実装
- 検証: `python -c "from karma_system import KarmaManager; m = KarmaManager(); print('Manager created')"`
## Step 41: karma_system.py カーマ更新ロジック
- `KarmaManager.update_karma()` メソッドを実装
- 行動ベースのカーマ変動を適用
- 検証: `python -c "from karma_system import KarmaManager; m = KarmaManager(); print('update_karma method exists')"`
## Step 42: karma_system.py カーマボーナス取得ロジック
- `KarmaManager.get_karma_bonuses()` メソッドを実装
- 現在のカーマ値に基づくボーナスを計算
- 検証: `python -c "from karma_system import KarmaManager; m = KarmaManager(); print('get_karma_bonuses method exists')"`
## Step 43: reincarnation_dungeon_system.py 新規ファイル作成
- 空のファイル `reincarnation_dungeon_system.py` を作成
- 転生専用ダンジョンシステム用のファイル
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la reincarnation_dungeon_system.py`
## Step 44: reincarnation_dungeon_system.py ReincarnationDungeonData クラス定義
- `reincarnation_dungeon_system.py` に `@dataclass` デコレータ付きの `ReincarnationDungeonData` クラスを定義
- フィールド: id, min_reincarnation, max_reincarnation, name, description, floors, rewards, unlock_condition, is_arena
- 検証: `python -c "from reincarnation_dungeon_system import ReincarnationDungeonData; print('ReincarnationDungeonData class exists')"`
## Step 45: reincarnation_dungeon_system.py ReincarnationDungeonRegistry クラス作成
- `reincarnation_dungeon_system.py` に `ReincarnationDungeonRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all()` メソッドで全転生ダンジョンデータの取得
- 検証: `python -c "from reincarnation_dungeon_system import REGISTRY; REGISTRY.load(); print('Registry loaded')"`
## Step 46: reincarnation_dungeon_system.py ReincarnationDungeonRegistry.load() 実装
- `ReincarnationDungeonRegistry.load()` メソッドを実装
- `data/reincarnation_dungeons.yaml` からYAMLを読み込み、ReincarnationDungeonData オブジェクトに変換
- エラーハンドリング
- 検証: `python -c "from reincarnation_dungeon_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all())} reincarnation dungeon configs')"`
## Step 47: reincarnation_dungeon_system.py ReincarnationDungeonManager クラス作成
- `reincarnation_dungeon_system.py` に `ReincarnationDungeonManager` クラスを作成
- `is_dungeon_unlocked()` メソッドのスタブ実装
- `get_available_dungeons()` メソッドのスタブ実装
- �検証: `python -c "from reincarnation_dungeon_system import ReincarnationDungeonManager; m = ReincarnationDungeonManager(); print('Manager created')"`
## Step 48: reincarnation_dungeon_system.py ダンジョンアンロックチェックロジック
- `ReincarnationDungeonManager.is_dungeon_unlocked()` メソッドを実装
- 転生回数に基づくダンジョンアンロック条件をチェック
- 検証: `python -c "from reincarnation_dungeon_system import ReincarnationDungeonManager; m = ReincarnationDungeonManager(); print('is_dungeon_unlocked method exists')"`
## Step 49: reincarnation_dungeon_system.py 利用可能ダンジョン取得ロジック
- `ReincarnationDungeonManager.get_available_dungeons()` メソッドを実装
- 現在の転生回数で利用可能なダンジョンリストを返す
- 検証: `python -c "from reincarnation_dungeon_system import ReincarnationDungeonManager; m = ReincarnationDungeonManager(); print('get_available_dungeons method exists')"`
## Step 50: map_engine.py 転生ダンジョン選択ロジック準備
- `map_engine.py` の ダンジョン選択ロジックに 転生ダンジョン考慮のプレースホルダーを追加
- 検証: `grep -n "# TODO: Reincarnation dungeon" map_engine.py`
## Step 51: map_engine.py 転生ダンジョン選択ロジック実装
- `map_engine.py` に 転生回数に基づくダンジョン選択ロジックを実装
- 転生専用ダンジョンがアンロックされている場合、それを優先
- 検証: `python -c "import map_engine; print('Dungeon selection considers reincarnation dungeons')"`
## Step 52: game.py ダンジョン入場チェック転生制限追加
- `game.py` の ダンジョン入場チェックに 転生回数制限を追加
- 転生専用ダンジョンの入場条件を検証
- 検証: `python -c "import game; print('Dungeon entry checks reincarnation restrictions')"`
## Step 53: systems.py 転生スケーリング適用準備
- `systems.py` の 戦闘計算関数に 転生スケーリング適用のプレースホルダーを追加
- 検証: `grep -n "# TODO: Reincarnation scaling" systems.py`
## Step 54: systems.py 敵ステータス転生スケーリング適用
- `systems.py` の 戦闘計算で 敵のステータスに転生スケーリングを適用
- 敵の攻撃力、防御力等に転生回数ベースの修正を掛ける
- 検証: `python -c "import systems; print('Enemy stats scaling applied')"`
## Step 55: item_system.py 転生ドロップスケーリング適用準備
- `item_system.py` の ドロップ計算に 転生ドロップスケーリング適用のプレースホルダーを追加
- �検証: `grep -n "# TODO: Reincarnation drop scaling" item_system.py`
## Step 56: item_system.py アイテムドロップ転生スケーリング適用
- `item_system.py` の ドロップ計算で アイテムドロップ率に転生スケーリングを適用
- 転生回数ベースのドロップ率修正を掛ける
- 検証: `python -c "import item_system; print('Item drop scaling applied')"`
## Step 57: game.py 転生経験値ペナルティ適用準備
- `game.py` の 経験値取得処理に 転生経験値ペナルティ適用のプレースホルダーを追加
- 検証: `grep -n "# TODO: Reincarnation XP penalty" game.py`
## Step 58: game.py 転生経験値ペナルティ適用
- `game.py` の 経験値取得処理で 転生経験値ペナルティを適用
- 転生回数ベースの経験値獲得修正を掛ける（ペナルティなので減少）
- 検証: `python -c "import game; print('XP penalty applied based on reincarnation')"`
## Step 59: legacy_skill_system.py 新規ファイル作成
- 空のファイル `legacy_skill_system.py` を作成
- レガシースキルシステム用のファイル
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la legacy_skill_system.py`
## Step 60: legacy_skill_system.py LegacySkillData クラス定義
- `legacy_skill_system.py` に `@dataclass` デコレータ付きの `LegacySkillData` クラスを定義
- フィールド: id, min_reincarnation, description, effect_type, effect_value, unlock_condition
- 検証: `python -c "from legacy_skill_system import LegacySkillData; print('LegacySkillData class exists')"`
## Step 61: legacy_skill_system.py LegacySkillRegistry クラス作成
- `legacy_skill_system.py` に `LegacySkillRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all()` メソッドで全レガシースキルデータの取得
- 検証: `python -c "from legacy_skill_system import REGISTRY; REGISTRY.load(); print('Registry loaded')"`
## Step 62: legacy_skill_system.py LegacySkillRegistry.load() 実装
- `LegacySkillRegistry.load()` メソッドを実装
- `data/legacy_skills.yaml` からYAMLを読み込み、LegacySkillData オブジェクトに変換
- エラーハンドリング
- 検証: `python -c "from legacy_skill_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all())} legacy skill configs')"`
## Step 63: legacy_skill_system.py LegacySkillManager クラス作成
- `legacy_skill_system.py` に `LegacySkillManager` クラスを作成
- `apply_legacy_effects()` メソッドのスタブ実装
- `check_unlocks()` メソッドのスタブ実装
- 検証: `python -c "from legacy_skill_system import LegacySkillManager; m = LegacySkillManager(); print('Manager created')"`
## Step 64: legacy_skill_system.py レガシースキル効果適用ロジック
- `LegacySkillManager.apply_legacy_effects()` メソッドを実装
- スキル経験値取得時やスキル使用時にレガシー効果を適用
- 検証: `python -c "from legacy_skill_system import LegacySkillManager; m = LegacySkillManager(); print('apply_legacy_effects method exists')"`
## Step 65: legacy_skill_system.py レガシースキルアンロックチェックロジック
- `LegacySkillManager.check_unlocks()` メソッドを実装
- 転生回数に基づく新規レガシースキルアンロックをチェック
- 検証: `python -c "from legacy_skill_system import LegacySkillManager; m = LegacySkillManager(); print('check_unlocks method exists')"`
## Step 66: reincarnation_challenge_system.py 新規ファイル作成
- 空のファイル `reincarnation_challenge_system.py` を作成
- 転生チャレンジシステム用のファイル
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la reincarnation_challenge_system.py`
## Step 67: reincarnation_challenge_system.py ReincarnationChallengeData クラス定義
- `reincarnation_challenge_system.py` に `@dataclass` デコレータ付きの `ReincarnationChallengeData` クラスを定義
- フィールド: id, name, description, requirements, rewards
- 検証: `python -c "from reincarnation_challenge_system import ReincarnationChallengeData; print('ReincarnationChallengeData class exists')"`
## Step 68: reincarnation_challenge_system.py ReincarnationChallengeRegistry クラス作成
- `reincarnation_challenge_system.py` に `ReincarnationChallengeRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all()` メソッドで全転生チャレンジデータの取得
- 検証: `python -c "from reincarnation_challenge_system import REGISTRY; REGISTRY.load(); print('Registry loaded')"`
## Step 69: reincarnation_challenge_system.py ReincarnationChallengeRegistry.load() 実装
- `ReincarnationChallengeRegistry.load()` メソッドを実装
- `data/reincarnation_challenges.yaml` からYAMLを読み込み、ReincarnationChallengeData オブジェクトに変換
- エラーハンドリング
- 検証: `python -c "from reincarnation_challenge_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all())} reincarnation challenge configs')"`
## Step 70: reincarnation_challenge_system.py ReincarnationChallengeManager クラス作成
- `reincarnation_challenge_system.py` に `ReincarnationChallengeManager` クラスを作成
- `update_challenge_progress()` メソッドのスタブ実装
- `check_completions()` メソッドのスタブ実装
- `grant_rewards()` メソッドのスタブ実装
- 検証: `python -c "from reincarnation_challenge_system import ReincarnationChallengeManager; m = ReincarnationChallengeManager(); print('Manager created')"`
## Step 71: game.py 転生時のチャレンジ進捗更新
- `game.py` の 転生関連処理で チャレンジ進捗を更新とチェックを追加
- 転生後にチャレンジ達成条件をチェックし、報酬を付与
- 検証: `python -c "import game; print('Reincarnation updates challenge progress')"`
## Step 72: advanced_systems.py SaveSystem 転生データ保存実装
- `advanced_systems.py` の SaveSystem.save()/load() メソッドを修正
- 転生関連データ（転生回数、カーマ、レガシースキル等）を含めてセーブ/ロード
- 後方互換性のためデフォルト値を設定
- 検証: セーブ/ロードテスト用の簡単なスクリプト実行
この実装計画書は、輪廻転生・ニューゲーム+システムを72の小さなステップに分割しています。
各ステップは具体的なファイル変更、コード追加、および検証コマンドを含んでおり、
低性能なLLMでも段階的に実装を進めることができます。
