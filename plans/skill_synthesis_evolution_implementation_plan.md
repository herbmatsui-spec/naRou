# スキル合成・進化システム 詳細実装計画書

## Step 1: data/skill_fusion.yaml 基本構造作成
- ファイル `data/skill_fusion.yaml` を作成し、基本的なYAML構造を定義
- スキル融合のトップレベルキー `fusion_recipes:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_fusion.yaml', encoding='utf-8')); print('OK' if data and 'fusion_recipes' in data else 'ERROR')"

## Step 2: data/skill_fusion.yaml 基本融合レシピ追加
- `data/skill_fusion.yaml` に「ファイアボール融合」の基本構造を追加
- name, description, inputs, output, requirements, success_rate, failure_penalty
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_fusion.yaml', encoding='utf-8')); r=data.get('fusion_recipes',{}).get('fireball_fusion'); print(f'Recipe exists: {r is not None}'); print(f'Name: {r.get(\"name\") if r else \"Missing\"}')"

## Step 3: data/skill_evolution.yaml 基本構造作成
- ファイル `data/skill_evolution.yaml` を作成し、基本的なYAML構造を定義
- スキル進化のトップレベルキー `evolution_chains:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_evolution.yaml', encoding='utf-8')); print('OK' if data and 'evolution_chains' in data else 'ERROR')"

## Step 4: data/skill_evolution.yaml 剣の熟達進化チェーン追加
- `data/skill_evolution.yaml` に「剣の熟達進化」チェーンを追加
- stages 配列と各ステージの構造（id, name, unlock_condition, bonuses）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_evolution.yaml', encoding='utf-8')); c=data.get('evolution_chains',{}).get('sword_mastery'); print(f'Chain exists: {c is not None}'); print(f'Stages count: {len(c.get(\"stages\",[])) if c else 0}')"

## Step 5: data/skill_awakening.yaml 基本構造作成
- ファイル `data/skill_awakening.yaml` を作成し、基本的なYAML構造を定義
- 覚醒スキルのトップレベルキー `awakenings:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_awakening.yaml', encoding='utf-8')); print('OK' if data and 'awakenings' in data else 'ERROR')"

## Step 6: data/skill_awakening.yaml 竜殺しの覚醒追加
- `data/skill_awakening.yaml` に「竜殺しの覚醒」を追加
- base_skill, requirements, awakened_skill, visual_effect, passive_effects
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_awakening.yaml', encoding='utf-8')); a=data.get('awakenings',{}).get('dragon_slaying_awakening'); print(f'Awakening exists: {a is not None}'); print(f'Base skill: {a.get(\"base_skill\") if a else \"Missing\"}')"

## Step 7: data/skill_transfer.yaml 基本構造作成
- ファイル `data/skill_transfer.yaml` を作成し、基本的なYAML構造を定義
- スキル特性転移のトップレベルキー `transfer_traits:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_transfer.yaml', encoding='utf-8')); print('OK' if data and 'transfer_traits' in data else 'ERROR')"

## Step 8: data/skill_transfer.yaml クリティカル強化転移追加
- `data/skill_transfer.yaml` に「クリティカル強化転移」を追加
- name, description, source_traits, target_skills, transfer_ratio, cost, irreversible
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_transfer.yaml', encoding='utf-8')); t=data.get('transfer_traits',{}).get('critical_boost'); print(f'Trait exists: {t is not None}'); print(f'Transfer ratio: {t.get(\"transfer_ratio\") if t else \"Missing\"}')"

## Step 9: data/skill_resonance.yaml 基本構造作成
- ファイル `data/skill_resonance.yaml` を作成し、基本的なYAML構造を定義
- スキル共鳴のトップレベルキー `resonance_sets:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_resonance.yaml', encoding='utf-8')); print('OK' if data and 'resonance_sets' in data else 'ERROR')"

## Step 10: data/skill_resonance.yaml 炎の騎士セット追加
- `data/skill_resonance.yaml` に「炎の騎士セット」を追加
- name, description, required_skills, min_count, resonance_effects, visual_effect
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_resonance.yaml', encoding='utf-8')); r=data.get('resonance_sets',{}).get('flame_knight_set'); print(f'Resonance set exists: {r is not None}'); print(f'Required skills: {r.get(\"required_skills\") if r else \"Missing\"}')"

## Step 11: data/skill_inheritance.yaml 基本構造作成
- ファイル `data/skill_inheritance.yaml` を作成し、基本的なYAML構造を定義
- スキル継承のトップレベルキー `inheritance_rules:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_inheritance.yaml', encoding='utf-8')); print('OK' if data and 'inheritance_rules' in data else 'ERROR')"

## Step 12: data/skill_inheritance.yaml 血統スキル継承追加
- `data/skill_inheritance.yaml` に「血統スキル継承」を追加
- name, description, inheritance_type, eligible_skills, inheritance_rate, level_bonus, requirements
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_inheritance.yaml', encoding='utf-8')); i=data.get('inheritance_rules',{}).get('bloodline_skills'); print(f'Inheritance rule exists: {i is not None}'); print(f'Eligible skills: {i.get(\"eligible_skills\") if i else \"Missing\"}')"

## Step 13: data/skill_specialization.yaml 基本構造作成
- ファイル `data/skill_specialization.yaml` を作成し、基本的なYAML構造を定義
- スキル専門化のトップレベルキー `specialization_paths:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_specialization.yaml', encoding='utf-8')); print('OK' if data and 'specialization_paths' in data else 'ERROR')"

## Step 14: data/skill_specialization.yaml ファイアボール専門化パス追加
- `data/skill_specialization.yaml` に「ファイアボール専門化パス」を追加
- name, description, base_skill, branches 配列
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_specialization.yaml', encoding='utf-8')); s=data.get('specialization_paths',{}).get('fireball_specialization'); print(f'Specialization path exists: {s is not None}'); print(f'Base skill: {s.get(\"base_skill\") if s else \"Missing\"}')"

## Step 15: data/skill_fusion_chains.yaml 基本構造作成
- ファイル `data/skill_fusion_chains.yaml` を作成し、基本的なYAML構造を定義
- スキル融合連鎖のトップレベルキー `fusion_chains:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_fusion_chains.yaml', encoding='utf-8')); print('OK' if data and 'fusion_chains' in data else 'ERROR')"

## Step 16: data/skill_fusion_chains.yaml 究極竜殺し融合連鎖追加
- `data/skill_fusion_chains.yaml` に「究極竜殺し融合連鎖」を追加
- name, description, stages 配列（各ステージの構造）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_fusion_chains.yaml', encoding='utf-8')); f=data.get('fusion_chains',{}).get('ultimate_dragon_slayer'); print(f'Fusion chain exists: {f is not None}'); print(f'Stages count: {len(f.get(\"stages\",[])) if f else 0}')"

## Step 17: data/skill_archive.yaml 基本構造作成
- ファイル `data/skill_archive.yaml` を作成し、基本的なYAML構造を定義
- スキルアーカイブのトップレベルキー `archive_categories:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_archive.yaml', encoding='utf-8')); print('OK' if data and 'archive_categories' in data else 'ERROR')"

## Step 18: data/skill_archive.yaml 元素魔法アーカイブ追加
- `data/skill_archive.yaml` に「元素魔法アーカイブ」を追加
- name, description, skills, completion_rewards, archive_entries
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_archive.yaml', encoding='utf-8')); a=data.get('archive_categories',{}).get('elemental_spells'); print(f'Archive category exists: {a is not None}'); print(f'Skills: {a.get(\"skills\") if a else \"Missing\"}')"

## Step 19: entity.py スキル合成・進化関連フィールド追加準備
- `entity.py` の Entity クラスにスキル合成・進化関連フィールドのプレースホルダーコメントを追加
- フィールド追加の場所を示すコメント: `# TODO: Skill synthesis/evolution fields will be added here`
- 検証: `grep -n "TODO: Skill synthesis/evolution fields" entity.py`

## Step 20: entity.py スキル融合素材フィールド追加
- `entity.py` の Entity クラスに `skill_fusion_materials: Dict[str, int] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'skill_fusion_materials'))"`

## Step 21: entity.py スキル進化状態フィールド追加
- `entity.py` の Entity クラスに `skill_evolution: Dict[str, str] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'skill_evolution'))"`

## Step 22: entity.py 覚醒スキルフィールド追加
- `entity.py` の Entity クラスに `awakened_skills: List[str] = field(default_factory=list)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'awakened_skills'))"`

## Step 23: entity.py スキル特性フィールド追加
- `entity.py` の Entity クラスに `skill_traits: Dict[str, Dict[str, float]] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'skill_traits'))"`

## Step 24: entity.py 装備スキルフィールド追加
- `entity.py` の Entity クラスに `equipped_skills: List[str] = field(default_factory=list)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'equipped_skills'))"`

## Step 25: entity.py 継承可能スキルフィールド追加
- `entity.py` の Entity クラスに `inheritable_skills: List[str] = field(default_factory=list)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'inheritable_skills'))"`

## Step 26: entity.py スキル専門化フィールド追加
- `entity.py` の Entity クラスに `skill_specialization: Dict[str, str] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'skill_specialization'))"`

## Step 27: entity.py 融合連鎖進捗フィールド追加
- `entity.py` の Entity クラスに `fusion_chain_progress: Dict[str, int] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'fusion_chain_progress'))"`

## Step 28: entity.py スキルアーカイブ進捗フィールド追加
- `entity.py` の Entity クラスに `skill_archive_progress: Dict[str, bool] = field(default_factory=dict)` フィールドを追加
- 検証: `python -c "from entity import Entity; e = Entity(); print(hasattr(e, 'skill_archive_progress'))"`

## Step 29: skill_fusion_system.py 新規ファイル作成
- 空のファイル `skill_fusion_system.py` を作成
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la skill_fusion_system.py`

## Step 30: skill_fusion_system.py SkillFusionData クラス定義
- `skill_fusion_system.py` に `@dataclass` デコレータ付きの `SkillFusionData` クラスを定義
- フィールド: id, name, description, inputs, output, requirements, success_rate, failure_penalty
- 検証: `python -c "from skill_fusion_system import SkillFusionData; print('SkillFusionData class exists')`

## Step 31: skill_fusion_system.py SkillFusionRegistry クラス作成
- `skill_fusion_system.py` に `SkillFusionRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all()` メソッドで全スキル融合データの取得
- 検証: `python -c "from skill_fusion_system import REGISTRY; REGISTRY.load(); print('Registry loaded')`

## Step 32: skill_fusion_system.py SkillFusionRegistry.load() 実装
- `SkillFusionRegistry.load()` メソッドを実装
- `data/skill_fusion.yaml` からYAMLを読み込み、SkillFusionData オブジェクトに変換
- エラーハンドリング（ファイルが存在しない場合のデフォルト融合レシピ作成）
- 検証: `python -c "from skill_fusion_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all())} fusion recipes')`

## Step 33: skill_fusion_system.py SkillFusionManager クラス作成
- `skill_fusion_system.py` に `SkillFusionManager` クラスを作成
- `can_fuse()` メソッドのスタブ実装
- `fuse_skills()` メソッドのスタブ実装
- 検証: `python -c "from skill_fusion_system import SkillFusionManager; m = SkillFusionManager(); print('Manager created')`

## Step 34: skill_fusion_system.py 融合可能チェックロジック
- `SkillFusionManager.can_fuse()` メソッドを実装
- 素材チェック、レベルチェック、スキルレベルチェック
- 検証: `python -c "from skill_fusion_system import SkillFusionManager; m = SkillFusionManager(); print('can_fuse method exists')`

## Step 35: skill_fusion_system.py スキル融合実行ロジック
- `SkillFusionManager.fuse_skills()` メソッドを実装
- 素材消費、新スキル付与、失敗時のペナルティ適用
- 検証: `python -c "from skill_fusion_system import SkillFusionManager; m = SkillFusionManager(); print('fuse_skills method exists')`

## Step 36: skill_evolution_system.py 新規ファイル作成
- 空のファイル `skill_evolution_system.py` を作成
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la skill_evolution_system.py`

## Step 37: skill_evolution_system.py SkillEvolutionData クラス定義
- `skill_evolution_system.py` に `@dataclass` デコレータ付きの `SkillEvolutionData` クラスを定義
- フィールド: id, name, description, stages
- 検証: `python -c "from skill_evolution_system import SkillEvolutionData; print('SkillEvolutionData class exists')`

## Step 38: skill_evolution_system.py SkillEvolutionRegistry クラス作成
- `skill_evolution_system.py` に `SkillEvolutionRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all()` メソッドで全スキル進化データの取得
- 検証: `python -c "from skill_evolution_system import REGISTRY; REGISTRY.load(); print('Registry loaded')`

## Step 39: skill_evolution_system.py SkillEvolutionRegistry.load() 実装
- `SkillEvolutionRegistry.load()` メソッドを実装
- `data/skill_evolution.yaml` からYAMLを読み込み、SkillEvolutionData オブジェクトに変換
- エラーハンドリング
- 検証: `python -c "from skill_evolution_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all())} evolution chains')`

## Step 40: skill_evolution_system.py SkillEvolutionManager クラス作成
- `skill_evolution_system.py` に `SkillEvolutionManager` クラスを作成
- `check_evolution()` メソッドのスタブ実装
- `evolve_skill()` メソッドのスタブ実装
- 検証: `python -c "from skill_evolution_system import SkillEvolutionManager; m = SkillEvolutionManager(); print('Manager created')`

## Step 41: skill_evolution_system.py 進化条件チェックロジック
- `SkillEvolutionManager.check_evolution()` メソッドを実装
- スキルレベルチェック、前段階進化チェック
- 検証: `python -c "from skill_evolution_system import SkillEvolutionManager; m = SkillEvolutionManager(); print('check_evolution method exists')`

## Step 42: skill_evolution_system.py スキル進化実行ロジック
- `SkillEvolutionManager.evolve_skill()` メソッドを実装
- 進化段階更新、ボーナス適用
- 検証: `python -c "from skill_evolution_system import SkillEvolutionManager; m = SkillEvolutionManager(); print('evolve_skill method exists')`

## Step 43: skill_awakening_system.py 新規ファイル作成
- 空のファイル `skill_awakening_system.py` を作成
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la skill_awakening_system.py`

## Step 44: skill_awakening_system.py SkillAwakeningData クラス定義
- `skill_awakening_system.py` に `@dataclass` デコレータ付きの `SkillAwakeningData` クラスを定義
- フィールド: id, name, description, base_skill, requirements, awakened_skill, visual_effect, passive_effects
- 検証: `python -c "from skill_awakening_system import SkillAwakeningData; print('SkillAwakeningData class exists')`

## Step 45: skill_awakening_system.py SkillAwakeningRegistry クラス作成
- `skill_awakening_system.py` に `SkillAwakeningRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all()` メソッドで全覚醒スキルデータの取得
- 検証: `python -c "from skill_awakening_system import REGISTRY; REGISTRY.load(); print('Registry loaded')`

## Step 46: skill_awakening_system.py SkillAwakeningRegistry.load() 実装
- `SkillAwakeningRegistry.load()` メソッドを実装
- `data/skill_awakening.yaml` からYAMLを読み込み、SkillAwakeningData オブジェクトに変換
- エラーハンドリング
- 検証: `python -c "from skill_awakening_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all())} awakenings')`

## Step 47: skill_awakening_system.py SkillAwakeningManager クラス作成
- `skill_awakening_system.py` に `SkillAwakeningManager` クラスを作成
- `can_awaken()` メソッドのスタブ実装
- `awaken_skill()` メソッドのスタブ実装
- 検証: `python -c "from skill_awakening_system import SkillAwakeningManager; m = SkillAwakeningManager(); print('Manager created')`

## Step 48: skill_awakening_system.py 覚醒可能チェックロジック
- `SkillAwakeningManager.can_awaken()` メソッドを実装
- スキルレベルチェック、特定アイテム所持チェック、カウントチェック
- 検証: `python -c "from skill_awakening_system import SkillAwakeningManager; m = SkillAwakeningManager(); print('can_awaken method exists')`

## Step 49: skill_awakening_system.py 覚醒スキル実行ロジック
- `SkillAwakeningManager.awaken_skill()` メソッドを実装
- 基本スキルから覚醒スキルへの変換、視覚効果適用
- 検証: `python -c "from skill_awakening_system import SkillAwakeningManager; m = SkillAwakeningManager(); print('awaken_skill method exists')`

## Step 50: skill_transfer_system.py 新規ファイル作成
- 空のファイル `skill_transfer_system.py` を作成
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la skill_transfer_system.py`

## Step 51: skill_transfer_system.py SkillTransferData クラス定義
- `skill_transfer_system.py` に `@dataclass` デコレータ付きの `SkillTransferData` クラスを定義
- フィールド: id, name, description, source_traits, target_skills, transfer_ratio, cost, irreversible
- 検証: `python -c "from skill_transfer_system import SkillTransferData; print('SkillTransferData class exists')`

## Step 52: skill_transfer_system.py SkillTransferRegistry クラス作成
- `skill_transfer_system.py` に `SkillTransferRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all()` メソッドで全スキル特性転移データの取得
- 検証: `python -c "from skill_transfer_system import REGISTRY; REGISTRY.load(); print('Registry loaded')`

## Step 53: skill_transfer_system.py SkillTransferRegistry.load() 実装
- `SkillTransferRegistry.load()` メソッドを実装
- `data/skill_transfer.yaml` からYAMLを読み込み、SkillTransferData オブジェクトに変換
- エラーハンドリング
- 検証: `python -c "from skill_transfer_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all())} transfer traits')`

## Step 54: skill_transfer_system.py SkillTransferManager クラス作成
- `skill_transfer_system.py` に `SkillTransferManager` クラスを作成
- `can_transfer()` メソッドのスタブ実装
- `transfer_trait()` メソッドのスタブ実装
- 検証: `python -c "from skill_transfer_system import SkillTransferManager; m = SkillTransferManager(); print('Manager created')`

## Step 55: skill_transfer_system.py 特性転移可能チェックロジック
- `SkillTransferManager.can_transfer()` メソッドを実装
- スキルポイントチェック、素材チェック、対象スキル習得チェック
- 検証: `python -c "from skill_transfer_system import SkillTransferManager; m = SkillTransferManager(); print('can_transfer method exists')`

## Step 56: skill_transfer_system.py 特性転移実行ロジック
- `SkillTransferManager.transfer_trait()` メソッドを実装
- 特性値の転移、元スキルの弱体化、コスト消費
- 検証: `python -c "from skill_transfer_system import SkillTransferManager; m = SkillTransferManager(); print('transfer_trait method exists')`

## Step 57: skill_resonance_system.py 新規ファイル作成
- 空のファイル `skill_resonance_system.py` を作成
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la skill_resonance_system.py`

## Step 58: skill_resonance_system.py SkillResonanceData クラス定義
- `skill_resonance_system.py` に `@dataclass` デコレータ付きの `SkillResonanceData` クラスを定義
- フィールド: id, name, description, required_skills, min_count, resonance_effects, visual_effect
- 検証: `python -c "from skill_resonance_system import SkillResonanceData; print('SkillResonanceData class exists')`

## Step 59: skill_resonance_system.py SkillResonanceRegistry クラス作成
- `skill_resonance_system.py` に `SkillResonanceRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all()` メソッドで全スキル共鳴データの取得
- 検証: `python -c "from skill_resonance_system import REGISTRY; REGISTRY.load(); print('Registry loaded')`

## Step 60: skill_resonance_system.py SkillResonanceRegistry.load() 実装
- `SkillResonanceRegistry.load()` メソッドを実装
- `data/skill_resonance.yaml` からYAMLを読み込み、SkillResonanceData オブジェクトに変換
- エラーハンドリング
- 検証: `python -c "from skill_resonance_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all())} resonance sets')`

## Step 61: skill_resonance_system.py SkillResonanceManager クラス作成
- `skill_resonance_system.py` に `SkillResonanceManager` クラスを作成
- `check_resonance()` メソッドのスタブ実装
- `apply_resonance_effects()` メソッドのスタブ実装
- `remove_resonance_effects()` メソッドのスタブ実装
- 検証: `python -c "from skill_resonance_system import SkillResonanceManager; m = SkillResonanceManager(); print('Manager created')`

## Step 62: skill_resonance_system.py 共鳴条件チェックロジック
- `SkillResonanceManager.check_resonance()` メソッドを実装
- 装備スキルセットチェック、必要数チェック
- 検証: `python -c "from skill_resonance_system import SkillResonanceManager; m = SkillResonanceManager(); print('check_resonance method exists')`

## Step 63: skill_resonance_system.py 共鳴効果適用ロジック
- `SkillResonanceManager.apply_resonance_effects()` メソッドを実装
- バフ適用、視覚効果トリガー
- 検証: `python -c "from skill_resonance_system import SkillResonanceManager; m = SkillResonanceManager(); print('apply_resonance_effects method exists')`

## Step 64: skill_resonance_system.py 共鳴効果解除ロジック
- `SkillResonanceManager.remove_resonance_effects()` メソッドを実装
- バフ解除、視覚効果停止
- 検証: `python -c "from skill_resonance_system import SkillResonanceManager; m = SkillResonanceManager(); print('remove_resonance_effects method exists')`

## Step 65: skill_inheritance_system.py 新規ファイル作成
- 空のファイル `skill_inheritance_system.py` を作成
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la skill_inheritance_system.py`

## Step 66: skill_inheritance_system.py SkillInheritanceData クラス定義
- `skill_inheritance_system.py` に `@dataclass` デコレータ付きの `SkillInheritanceData` クラスを定義
- フィールド: id, name, description, inheritance_type, eligible_skills, inheritance_rate, level_bonus, requirements
- 検証: `python -c "from skill_inheritance_system import SkillInheritanceData; print('SkillInheritanceData class exists')`

## Step 67: skill_inheritance_system.py SkillInheritanceRegistry クラス作成
- `skill_inheritance_system.py` に `SkillInheritanceRegistry` クラスをシングルトンパターンで作成
- `__new__` メソッドでシングルトン実装
- `all()` メソッドで全スキル継承データの取得
- 検証: `python -c "from skill_inheritance_system import REGISTRY; REGISTRY.load(); print('Registry loaded')`

## Step 68: skill_inheritance_system.py SkillInheritanceRegistry.load() 実装
- `SkillInheritanceRegistry.load()` メソッドを実装
- `data/skill_inheritance.yaml` からYAMLを読み込み、SkillInheritanceData オブジェクトに変換
- エラーハンドリング
- 検証: `python -c "from skill_inheritance_system import REGISTRY; REGISTRY.load(); print(f'Loaded {len(REGISTRY.all())} inheritance rules')`

## Step 69: skill_inheritance_system.py SkillInheritanceManager クラス作成
- `skill_inheritance_system.py` に `SkillInheritanceManager` クラスを作成
- `get_inheritable_skills()` メソッドのスタブ実装
- `inherit_skill()` メソッドのスタブ実装
- 検証: `python -c "from skill_inheritance_system import SkillInheritanceManager; m = SkillInheritanceManager(); print('Manager created')`

## Step 70: skill_specialization_system.py 新規ファイル作成
- 空のファイル `skill_specialization_system.py` を作成
- 基本的なファイルヘッダーとコメントを追加
- 検証: `ls -la skill_specialization_system.py`

## Step 71: skill_specialization_system.py SkillSpecializationData クラス定義
- `skill_specialization_system.py` に `@dataclass` デコレータ付きの `SkillSpecializationData` クラスを定義
- フィールド: id, name, description, base_skill, branches
- 検証: `python -c "from skill_specialization_system import SkillSpecializationData; print('SkillSpecializationData class exists')`

## Step 72: game.py スキル合成・進化システム統合
- `game.py` の Engine クラスに 各種マネージャーへの参照を追加
  - `skill_fusion_manager: SkillFusionManager`
  - `skill_evolution_manager: SkillEvolutionManager`
  - `skill_awakening_manager: SkillAwakeningManager`
  - `skill_transfer_manager: SkillTransferManager`
  - `skill_resonance_manager: SkillResonanceManager`
  - `skill_inheritance_manager: SkillInheritanceManager`
  - `skill_specialization_manager: SkillSpecializationManager`
- `__init__` メソッドで初期化
- `_on_kill()` メソッドで スキル経験値更新時の 進化チェック追加
- `advance_world()` メソッドで 定期的な共鳴チェック追加
- スキル使用関連メソッドで 融合素材追跡・専門化進捗更新追加
- 検証: `python -c "from game import Engine; e = Engine(); print(f'Fusion manager: {hasattr(e, \"skill_fusion_manager\")}'); print(f'Evolution manager: {hasattr(e, \"skill_evolution_manager\")}')"

この実装計画書は、スキル合成・進化システムを72の小さなステップに分割しています。
各ステップは具体的なファイル変更、コード追加、および検証コマンドを含んでおり、
低性能なLLMでも段階的に実装を進めることができます。
