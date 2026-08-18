# スキルツリー・ジョブシステム 詳細実装計画書
低性能なLLMでも実装可能なように1～72までの小さなステップに分割

---

## 📦 フェーズ1：データ構造の構築 (Step 1-10)
**目的: スキルツリーとジョブシステムのデータ構造を構築する。**

### 1.1 data/skill_trees.yaml 基本構造作成 (Step 1)
- ファイル `data/skill_trees.yaml` を作成し、基本的なYAML構造を定義
- スキルツリーのトップレベルキー `skill_trees:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_trees.yaml')); print('OK' if data and 'skill_trees' in data else 'ERROR')"`
- ヒント: 最初は空の構造から始め、後に内容を追加

### 1.2 data/skill_trees.yaml 基本スキルツリー定義 (Step 2)
- `data/skill_trees.yaml` に「剣術」スキルツリーの基本構造を追加
- swordツリーのname, icon, tiers配列を定義（最低1つのティア）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_trees.yaml')); print('Sword tree found' if data.get('skill_trees',{}).get('sword') else 'Missing')"`
- ヒント: まずは1つのティアから始め、後で拡張

### 1.3 data/skill_trees.yaml 剣術ツリー初期ティア完成 (Step 3)
- 「剣の基礎」ティアを完成（id, name, description, cost, prerequisites, effects）
- effectsにはdamage_bonusタイプを1つ追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_trees.yaml')); tree=data.get('skill_trees',{}).get('sword',{}); print('Basic sword tier found' if tree.get('tiers') and len(tree['tiers']) > 0 else 'Missing')"`
- ヒント: YAMLのインデントに注意（2スペース推奨）

### 1.4 data/skill_trees.yaml 剣術ツリー2ティア目追加 (Step 4)
- 「剣術熟練」ティアを追加（基本剣の前提条件付き）
- damage_bonusとunlock_skill効果を含める
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_trees.yaml')); tiers=data.get('skill_trees',{}).get('sword',{}).get('tiers',[]); print(f'Tiers count: {len(tiers)}'); print('Sword mastery found' if any(t.get('id')=='sword_mastery' for t in tiers) else 'Missing')"`
- ヒント: prerequisitesリストの形式に注意

### 1.5 data/skill_trees.yaml 剣術ツリー3ティア目追加 (Step 5)
- 「剣の極意」ティアを追加（剣術熟練の前提条件付き）
- damage_bonus, crit_chance, unlock_skill効果を含める
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_trees.yaml')); tiers=data.get('skill_trees',{}).get('sword',{}).get('tiers',[]); ids=[t.get('id') for t in tiers]; print(f'Tier IDs: {ids}'); print('All three tiers present' if len([i for i in ['basic_sword','sword_mastery','sword_essence'] if i in ids])==3 else 'Missing some')"`
- ヒント: 最終的に3ティア構成になることを確認

### 1.6 data/skill_trees.yaml 魔法スキルツリー追加 (Step 6)
- 「魔法」スキルツリーを追加（name, icon, tiers構造）
- 「魔法の基礎」ティアから開始
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_trees.yaml')); print('Magic tree found' if 'magic' in data.get('skill_trees',{}) else 'Missing magic tree')"`
- ヒント: swordツリーの構造をコピーして名前を変更すると楽

### 1.7 data/skill_trees.yaml 魔法ツリー詳細定義 (Step 7)
- 魔法ツリーに「魔法の基礎」「魔法熟練」「魔法の極意」の3ティアを定義
- 適切なeffects（damage_bonusなど）とunlock_skillを含める
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_trees.yaml')); magic=data.get('skill_trees',{}).get('magic',{}); print(f'Magic tiers: {len(magic.get(\"tiers\",[]))}'); print('Magic essence found' if any(t.get('id')=='magic_essence' for t in magic.get('tiers',[])) else 'Missing')"`
- ヒント: ID命名規則に注意（一貫性を持たせる）

### 1.8 data/skill_trees.yaml 体術スキルツリー追加 (Step 8)
- 「体術」スキルツリーを追加（同様に3ティア構成）
- 「体術の基礎」「体術熟練」「体術の極意」を定義
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_trees.yaml')); trees=list(data.get('skill_trees',{}).keys()); print(f'Available trees: {trees}'); print('Has 3+ trees' if len(trees)>=3 else 'Need more trees')"`
- ヒント: これで基本の3ツリー構成（剣術、魔法、体術）が完成

### 1.9 entity.py スキルツリー進捗フィールド追加 (Step 9)
- `entity.py` のEntityクラスに `skill_tree_progress: Dict[str, List[str]] = field(default_factory=dict)` を追加
- 場所: スキルツリー関連のコメントブロック内（約593行付近）
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); cls=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='Entity'][0]; fields=[n for n in cls.body if isinstance(n,ast.AnnAssign)]; has_field=any('skill_tree_progress' in ast.dump(n) for n in fields); print('Field found' if has_field else 'Field missing')"`
- ヒント: dataclassフィールドなので、デフォルトファクトリーを正しく設定

### 1.10 entity.py スキルポイントフィールド追加 (Step 10)
- `entity.py` のEntityクラスに `skill_points: int = 0` と `total_skill_points_earned: int = 0` を追加
- 場所: skill_tree_progressの直後
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); cls=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='Entity'][0]; fields=[n.note for n in cls.body if isinstance(n,ast.AnnAssign) and hasattr(n,'target') and hasattr(n.target,'id')]; has_sp='skill_points' in fields; has_tsp='total_skill_points_earned' in fields; print(f'Skill points: {has_sp}, Total earned: {has_tsp}')"`
- ヒント: 両方とも整数型で初期値0

---

## 🏗️ フェーズ2：スキルツリーシステムの構築 (Step 11-30)
**目的: スキルツリー管理システムを構築する。**

### 2.1 skill_tree_system.py 新規ファイル作成 (Step 11)
- 新規ファイル `skill_tree_system.py` を作成
- 基本的なファイルヘッダーとモジュール docstring を追加
- 検証: `python -c "print('File exists' if open('skill_tree_system.py').readline().strip() else 'Empty or missing')"`
- ヒント: 他のシステムファイル（title_system.py等）を参考に構造を作る

### 2.2 skill_tree_system.py SkillTreeEffectクラス定義 (Step 12)
- `skill_tree_system.py` に `@dataclass` デコレータ付きの `SkillTreeEffect` クラスを定義
- フィールド: type (str), value (Union[int, float, str]), target (Optional[str])
- 検証: `python -c "from skill_tree_system import SkillTreeEffect; e=SkillTreeEffect(type='damage_bonus', value=5, target='melee'); print(f'Effect: {e.type} {e.value}')"`
- ヒント: Optional型を使うため、`from typing import Optional` をインポート

### 2.3 skill_tree_system.py SkillTreeTierクラス定義 (Step 13)
- `skill_tree_system.py` に `@dataclass` デコレータ付きの `SkillTreeTier` クラスを定義
- フィールド: id, name, description, cost (int), prerequisites (List[str]), effects (List[SkillTreeEffect])
- 検証: `python -c "from skill_tree_system import SkillTreeTier, SkillTreeEffect; t=SkillTreeTier(id='test',name='Test',desc='Test',cost=10,prerequisites=[],effects=[SkillTreeEffect('dmg',5,'melee')]); print(f'Tier: {t.name}')"`
- ヒント: デフォルトファクトリーを使う場合は注意（ここではシンプルにリストを直接定義）

### 2.4 skill_tree_system.py SkillTreeクラス定義 (Step 14)
- `skill_tree_system.py` に `@dataclass` デコレータ付きの `SkillTree` クラスを定義
- フィールド: id, name, icon, tiers (List[SkillTreeTier])
- 検証: `python -c "from skill_tree_system import SkillTree, SkillTreeTier, SkillTreeEffect; tier=SkillTreeTier('t1','Test Tier','Desc',10,[],[SkillTreeEffect('dmg',5,'melee')]); tree=SkillTree('sword','Sword','⚔',[tier]); print(f'Tree: {tree.name} tiers:{len(tree.tiers)}')"`
- ヒント: tiersフィールドにはList[SkillTreeTier]を指定

### 2.5 skill_tree_system.py SkillTreeRegistryクラス作成 (Step 15)
- `skill_tree_system.py` に `SkillTreeRegistry` クラスを作成（シングルトンパターン）
- `__new__` メソッドでインスタンスの単一化を実装
- `load()` メソッドのスタブを作成（引数: path: str = "data/skill_trees.yaml"）
- 検証: `python -c "from skill_tree_system import SkillTreeRegistry; r1=SkillTreeRegistry(); r2=SkillTreeRegistry(); print(f'Same instance: {r1 is r2}'); print('Registry created')"`
- ヒント: タイトルシステムの実装を参考にすると良い

### 2.6 skill_tree_system.py SkillTreeRegistry.load()実装 (Step 16)
- `skill_tree_system.py` の `SkillTreeRegistry.load()` メソッドを実装
- YAMLファイルを読み込み、skill_treesキーのデータをパースして内部辞書に格納
- エラーハンドリング（ファイルがない場合は空で開始）を追加
- 検証: `python -c "from skill_tree_system import SkillTreeRegistry; r=SkillTreeRegistry(); r.load(); print(f'Loaded {len(r.all())} trees')"`
- ヒント: yaml.safe_loadを使い、例外処理を忘れずに

### 2.7 skill_tree_system.py SkillTreeRegistryアクセッサー追加 (Step 17)
- `skill_tree_system.py` の `SkillTreeRegistry` に以下を追加:
  - `all()`: すべてのスキルツリーを返す辞書
  - `get(tree_id: str)`: 特定のツリーを返す（見つからなければNone）
- 検証: `python -c "from skill_tree_system import SkillTreeRegistry; r=SkillTreeRegistry(); r.load(); print(f'Tree count: {len(r.all())}'); sword=r.get('sword'); print(f'Sword tree: {sword.name if sword else \"Not found\"}')"`
- ヒント: タイトルシステムと同じパターンで実装

### 2.8 skill_tree_system.py SkillTreeManagerクラス作成 (Step 18)
- `skill_tree_system.py` に `SkillTreeManager` クラスを作成
- `__init__` で registry 参照を保持
- 主要メソッドのスタブを作成:
  - `check_prerequisites(player, tier) -> bool`
  - `learn_skill(player, tree_id, tier_id) -> bool`
  - `get_available_skills(player) -> List[Dict]`
  - `get_learned_skills(player) -> List[str]`
- 検証: `python -c "from skill_tree_system import SkillTreeManager; m=SkillTreeManager(); print('Manager created')"`
- ヒント: まずはスタブ実装で構造を作り、後で中身を埋める

### 2.9 skill_tree_system.py SkillTreeManager.check_prerequisites実装 (Step 19)
- `skill_tree_system.py` の `SkillTreeManager.check_prerequisites` を実装
- プレイヤーのskill_tree_progressを参照して、必要なスキルがすべて習得済みかチェック
- 前提条件が空リストの場合はTrueを返す
- 検証: `python -c "from skill_tree_system import SkillTreeManager, SkillTreeRegistry; r=SkillTreeRegistry(); r.load(); m=SkillTreeManager(r); from entity import Entity; p=Entity(); print(f'No prereqs: {m.check_prerequisites(p, r.get(\"sword\").tiers[0])}')"`
- ヒント: プレイヤーの進捗はDict[tree_id, List[learned_skill_id]]の形

### 2.10 skill_tree_system.py SkillTreeManager.learn_skill実装 (Step 20)
- `skill_tree_system.py` の `SkillTreeManager.learn_skill` を実装
- 前提条件チェック → スキルポイント消費チェック → 習得記録 → 効果適用
- スキルポイントが不足している場合はFalseを返す
- 習得成功時はskill_tree_progressに追加し、skill_pointsを減少
- 検証: `python -c "from skill_tree_system import SkillTreeManager, SkillTreeRegistry; r=SkillTreeRegistry(); r.load(); m=SkillTreeManager(r); from entity import Entity; p=Entity(); p.skill_points=100; result=m.learn_skill(p, 'sword', 'basic_sword'); print(f'Learn result: {result}; Remaining SP: {p.skill_points}')"`
- ヒント: 習得記録はplayer.skill_tree_progress[tree_id].append(tier_id)の形

### 2.11 skill_tree_system.py SkillTreeManager.get_available_skills実装 (Step 21)
- `skill_tree_system.py` の `SkillTreeManager.get_available_skills` を実装
- 各スキルツリーを巡回し、習得可能かつ未習得のティアをリストアップ
- 各エントリーにツリー名、ティア名、コスト、効果説明を含める
- 検証: `python -c "from skill_tree_system import SkillTreeManager, SkillTreeRegistry; r=SkillTreeRegistry(); r.load(); m=SkillTreeManager(r); from entity import Entity; p=Entity(); p.skill_points=50; avail=m.get_available_skills(p); print(f'Available skills: {len(avail)}'); [print(f'  - {s[\"tree\"]}:{s[\"tier\"]}') for s in avail[:3]]"`
- ヒント: 未習得かつ前提条件満たしているティアを対象にする

### 2.12 skill_tree_system.py SkillTreeManager.get_learned_skills実装 (Step 22)
- `skill_tree_system.py` の `SkillTreeManager.get_learned_skills` を実装
- プレイヤーのskill_tree_progressからすべての習得済みスキルIDをフラット化して返す
- 検証: `python -c "from skill_tree_system import SkillTreeManager, SkillTreeRegistry; r=SkillTreeRegistry(); r.load(); m=SkillTreeManager(r); from entity import Entity; p=Entity(); p.skill_tree_progress={'sword':['basic_sword']}; learned=m.get_learned_skills(p); print(f'Learned skills: {learned}')"`
- ヒント: 内包表記かリスト.extendを使うと簡単

---

## 🎮 フェーズ3：ゲーム統合 (Step 23-40)
**目的: スキルツリーシステムをゲームに統合する。**

### 3.1 entity.py gain_expメソッド修準備 (Step 23)
- `entity.py` の `gain_exp` メソッドを修準備（後でスキルポイント付与ロジックを追加）
- 現在の実装を確認し、経験値獲得ロジックの末尾にフックポイントを作る
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); gain_exp=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='gain_exp'][0]; print(f'gain_exp lines: {gain_exp.end_lineno-gain_exp.lineno+1}')"`
- ヒント: 後でここでスキルポイント計算ロジックを追加する

### 3.2 entity.py gain_expメソッドにスキルポイント付与追加 (Step 24)
- `entity.py` の `gain_exp` メソッドにスキルポイント付与ロジックを追加
- 基本レベルアップ時（レベルが上がったとき）にスキルポイントを付与
- 例: レベルアップごとに 5スキルポイント（バランス調整のため後で変更可能）
- 合計獲得スキルポイントも更新
- 検証: `python -c "from entity import Entity; p=Entity(); initial_sp=p.skill_points; p.gain_exp(1000); print(f'SP before: {initial_sp}, after: {p.skill_points} (earned: {p.total_skill_points_earned})')"`
- ヒント: レベルアップ判定は既存のロジックを利用（self.level < new_level）

### 3.3 game.py スキルツリーマネージャー参照追加 (Step 25)
- `game.py` のEngineクラスに `title_manager` と同様に `skill_tree_manager: SkillTreeManager` フィールドを追加
- `__init__` で初期化（SkillTreeRegistryをロード済みのインスタンスを渡す）
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); engine=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='Engine'][0]; init=[n for n in engine.body if isinstance(n,ast.FunctionDef) and n.name=='__init__'][0]; has_stm=any('skill_tree_manager' in ast.dump(n) for n in init.body); print(f'Manager field: {has_stm}')"`
- ヒント: title_managerの初期化方法を真似る

### 3.4 game.py _on_killメソッドスキルポイント追加（オプション） (Step 26)
- `game.py` の `_on_kill` メソッドに、敵を倒したときのスキルポイント付与ロジックを追加（オプション機能）
- 特殊な条件下（ボス撃破等）で追加スキルポイントを与える
- 基本的にはコメントアウトまたは設定可能にしておく
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').text); on_kill=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_on_kill'][0]; print(f'_on_kill has SP logic: {\"skill_points\" in ast.dump(on_kill)}')"`
- ヒント: まずは実装せず、後でバランス調整のためにオプションとして残す

### 3.5 game.py advance_worldメソッドスキルツリー定期チェック追加 (Step 27)
- `game.py` の `advance_world` メソッドに、一定ターンごとのスキルツリー自動習得チェックを追加
- 例: 10ターンごとにスキルポイントが十分あれば自動で習得を提案（または自動習得）
- デバッグ目的で実装し、後でUI連携に置き換える
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); advance=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='advance_world'][0]; print(f'advance_world lines: {advance.end_lineno-advance.lineno+1}')"`
- ヒント: タイトルシステムのperiodicチェックと同じパターン（self.turn_count % 10 == 0）

### 3.6 ui_fx_systems.py スキルツリーUI基礎追加 (Step 28)
- `ui_fx_systems.py` にスキルツリー表示のための基礎関数を追加
- スキルツリーのデータを受け取り、簡単なテキスト表示を返す関数
- 後でグラフィカルUIに置き換えるための足がかり
- 検証: `python -c "from ui_fx_systems import *; print('UI FX systems imported successfully')"`
- ヒント: まずはシンプルなテキスト出力関数から始める

### 3.7 game.py render_allメソッドスキルツリーUI追加 (Step 29)
- `game.py` の `render_all` メソッドに、特定キー（例: Sキー）押下時のスキルツリー表示ロジックを追加
- ゲームステートに `SHOWING_SKILL_TREE` を追加し、その状態時にスキルツリーを描画
- 基本的なテキストベースのUIから始める
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); render=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='render_all'][0]; print(f'render_all has skill tree logic: {\"skill_tree\" in ast.dump(render)}')"`
- ヒント: 既存のゲームステート処理パターンに従う


### 3.8 game.py メインループスキルツリーキー割り当て追加 (Step 30)
- `game.py` の `main` 関数のイベントループに、スキルツリー表示用のキー割り当てを追加
- Sキーが押されたらゲームステートを `SHOWING_SKILL_TREE` に変更
- ESCキーで元のゲームステートに戻る処理も合わせて実装
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); main=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='main'][0]; print(f'main has S key handling: {\"K_s\" in ast.dump(main) or \"s\" in ast.dump(main)}')"`
- ヒント: 既存のキー処理（F1ヘルプ等）と同じ場所に追加

---

## 💼 フェーズ4：ジョブシステムの構築 (Step 31-60)
**目的: ジョブシステムを構築する。**

### 4.1 data/jobs.yaml 基本構造作成 (Step 31)
- ファイル `data/jobs.yaml` を作成し、基本的なYAML構造を定義
- ジョブのトップレベルキー `jobs:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/jobs.yaml')); print('OK' if data and 'jobs' in data else 'ERROR')"`
- ヒント: skill_trees.yamlと同様のパターンで構造を作る

### 4.2 data/jobs.yaml 初期ジョブ（見習い）定義 (Step 32)
- `data/jobs.yaml` に「見習い」ジョブ（tier: 0）の基本構造を追加
- name, description, 空のstat_modifiers, equipment_restrictions, exclusive_skills, 空のunlock_conditions
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/jobs.yaml')); novice=data.get('jobs',{}).get('novice'); print(f'Novice job: {novice.name if novice else \"Missing\"}')"`
- ヒント: まずは最小限の構造から始める

### 4.3 data/jobs.yaml 戦士ジョブ定義 (Step 33)
- `data/jobs.yaml` に「戦士」ジョブ（tier: 1）を追加
- stat_modifiers (strength: 10, constitution: 5, speed: -2)
- equipment_restrictions (can_wear_heavy_armor: true, can_use_shield: true)
- exclusive_skills (リスト形式で ["shield_bash", "taunt", "whirlwind"])
- unlock_conditions (level: 10, skills: {basic_sword: 30, shield: 20}, stats: {strength: 15})
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/jobs.yaml')); warrior=data.get('jobs',{}).get('warrior'); print(f'Warrior STR mod: {warrior.stat_modifiers.get(\"strength\",0) if warrior else \"Missing\"}')"`
- ヒント: 階層構造(YAMLのネスト)に注意してインデントを合わせる

### 4.4 data/jobs.yaml 剣聖ジョブ定義 (Step 34)
- `data/jobs.yaml` に「剣聖」ジョブ（tier: 2）を追加
- 剣聖は戦士から転職可能（unlock_conditions.job: "warrior"）
- 適切なstat_modifiersとequipment_restrictionsを設定
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/jobs.yaml')); sm=data.get('jobs',{}).get('swordmaster'); print(f'Swordmaster exists: {sm is not None}'); print(f'Requires warrior job: {\"job\" in sm.unlock_conditions and sm.unlock_conditions[\"job\"]==\"warrior\" if sm else False}')"`
- ヒント: 前提ジョブ条件の形式に注意（job: "warrior"）

### 4.5 data/jobs.yaml 魔法使いジョブ定義 (Step 35)
- `data/jobs.yaml` に「魔法使い」ジョブ（tier: 1）を追加
- 戦士と同じ階層（tier: 1）だが異なる方向性
- 適切なintelligenceベースのstat_modifiersとstaff関連のequipment_restrictions
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/jobs.yaml')); mage=data.get('jobs',{}).get('mage'); print(f'Mage INT mod: {mage.stat_modifiers.get(\"intelligence\",0) if mage else \"Missing\"}')"`
- ヒント: 剣術とは異なるステータス補正を設定することで多様性を出す

### 4.6 data/jobs.yaml 大賢者ジョブ定義 (Step 36)
- `data/jobs.yaml` に「大賢者」ジョブ（tier: 2）を追加
- 魔法使いから転職可能（unlock_conditions.job: "mage"）
- 高いintelligenceとmana補正、artifact_staff使用可能
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/jobs.yaml')); arch=data.get('jobs',{}).get('archmage'); print(f'Archmage exists: {arch is not None}'); print(f'Requires mage job: {\"job\" in arch.unlock_conditions and arch.unlock_conditions[\"job\"]==\"mage\" if arch else False}')"`
- ヒント: 魔法使いジョブが先に定義されていることを確認

### 4.7 entity.py ジョブ関連フィールド追加 (Step 37)
- `entity.py` のEntityクラスにジョブ関連フィールドを追加:
  - job: str = "novice"
  - job_level: int = 1
  - job_exp: int = 0
  - previous_jobs: List[str] = field(default_factory=list)
  - mastered_jobs: List[str] = field(default_factory=list)
- 場所: ジョブ関連のコメントブロック内（約598-602行付近）
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); cls=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='Entity'][0]; fields=[n.note for n in cls.body if isinstance(n,ast.AnnAssign)]; req=['job','job_level','job_exp','previous_jobs','mastered_jobs']; found=[f for f in req if f in fields]; print(f'Job fields: {len(found)}/5 ({found})')"`
- ヒント: デフォルト値を見習い(novice)に設定することを忘れずに

### 4.8 job_system.py 新規ファイル作成 (Step 38)
- 新規ファイル `job_system.py` を作成
- 基本的なファイルヘッダーとモジュール docstring を追加
- 検証: `python -c "print('File exists' if open('job_system.py').readline().strip() else 'Empty or missing')"`
- ヒント: skill_tree_system.pyと同じパターンで構造を作る

### 4.9 job_system.py JobEffectクラス定義 (Step 39)
- `job_system.py` に `@dataclass` デコレータ付きの `JobEffect` クラスを定義（タイトルシステムのTitleEffectと同様）
- フィールド: type (str), value (Union[int, float, str]), target (Optional[str])
- 検証: `python -c "from job_system import JobEffect; e=JobEffect(type='stat_modifier', value=5, target='strength'); print(f'Job effect: {e.type} {e.value} to {e.target}')"`
- ヒント: スキルツリーのエフェクトと同様の構造で良い

### 4.10 job_system.py JobDataクラス定義 (Step 40)
- `job_system.py` に `@dataclass` デコレータ付きの `JobData` クラスを定義
- フィールド: id, name, tier, description, stat_modifiers (Dict[str, int]), equipment_restrictions (Dict[str, bool]), exclusive_skills (List[str]), unlock_conditions (Dict[str, Any])
- 検証: `python -c "from job_system import JobData; j=JobData('test','Test Job',1,'Desc',{}, {}, [], {}); print(f'Job: {j.name} tier:{j.tier}')"`
- ヒント: 辞書フィールドには適切なタイプヒントを付ける（Dict[str, int]等）

### 4.11 job_system.py JobRegistryクラス作成 (Step 41)
- `job_system.py` に `JobRegistry` クラスを作成（シングルトンパターン）
- `__new__` メソッドと `load(path: str = "data/jobs.yaml")` メソッドのスタブ
- `all()` と `get(job_id: str)` アクセッサーのスタブ
- 検証: `python -c "from job_system import JobRegistry; r=JobRegistry(); r2=JobRegistry(); print(f'Same instance: {r is r2}'); print('Job registry created')"`
- ヒント: スキルツリジストリとほぼ同じ構造

### 4.12 job_system.py JobRegistry.load()実装 (Step 42)
- `job_system.py` の `JobRegistry.load()` メソッドを実装
- YAMLファイルを読み込み、jobsキーのデータをパースして内部辞書に格納
- エラーハンドリング（ファイルがない場合は空で開始）を追加
- 検証: `python -c "from job_system import JobRegistry; r=JobRegistry(); r.load(); print(f'Loaded {len(r.all())} jobs')"`
- ヒント: 例外処理を忘れずに（FileNotFoundError等）

### 4.13 job_system.py JobManagerクラス作成 (Step 43)
- `job_system.py` に `JobManager` クラスを作成
- `__init__` で registry 参照を保持
- 主要メソッドのスタブを作成:
  - `check_unlock_conditions(player, job_data) -> bool`
  - `change_job(player, job_id) -> bool`
  - `get_available_jobs(player) -> List[JobData]`
  - `apply_job_stats(player, job_data) -> None`
- 検証: `python -c "from job_system import JobManager; m=JobManager(None); print('Job manager created')"`
- ヒント: まずはスタブで構造を作り、後で実装を埋める


### 4.14 job_system.py JobManager.check_unlock_conditions実装 (Step 44)
- `job_system.py` の `JobManager.check_unlock_conditions` を実装
- プレイヤーのレベル、スキル習得度、ステータス、現在のジョブなどを参照して解放条件をチェック
- 複数条件タイプ（level, skills, stats, job等）に対応
- 検証: `python -c "from job_system import JobManager, JobRegistry; from entity import Entity; r=JobRegistry(); r.load(); m=JobManager(r); p=Entity(); p.level=15; print(f'Can unlock novice: {m.check_unlock_conditions(p, r.get(\"novice\"))}')"`
- ヒント: 各条件タイプごとに別々のチェックロジックを書くと見やすい

### 4.15 job_system.py JobManager.change_job実装 (Step 45)
- `job_system.py` の `JobManager.change_job` を実装
- 解放条件チェック → 現在のジョブをprevious_jobsに追加 → 新しいジョブ設定 → ジョブ経験値リセット
- マスター済みジョブリストに追加（もしまだマスターしていなければ）
- 検証: `python -c "from job_system import JobManager, JobRegistry; from entity import Entity; r=JobRegistry(); r.load(); m=JobManager(r); p=Entity(); p.level=15; result=m.change_job(p, 'warrior'); print(f'Job change result: {result}; New job: {p.job}')"`
- ヒント: ジョブ変更時にステータスの再計算が必要（recalculate_statsを呼ぶ）


### 4.16 job_system.py JobManager.get_available_jobs実装 (Step 46)
- `job_system.py` の `JobManager.get_available_jobs` を実装
- すべてのジョブを巡回し、未習得かつ解放条件を満たしているものをリストアップ
- 現在のジョブとマスター済みジョブは除外する（オプション: マスター済みでも転職可能にするか設計による）
- 検証: `python -c "from job_system import JobManager, JobRegistry; from entity import Entity; r=JobRegistry(); r.load(); m=JobManager(r); p=Entity(); p.level=15; avail=m.get_available_jobs(p); print(f'Available jobs: {[j.name for j in avail]}')"`
- ヒント: 条件を満たしているがまだ習得していないジョブを対象にする

### 4.17 job_system.py JobManager.apply_job_stats実装 (Step 47)
- `job_system.py` の `JobManager.apply_job_stats` を実装
- ジョブのstat_modifiersをプレイヤーのベースステータスに適用（実際はrecalculate_statsで行うが、ここでは適用ロジックを定義）
- 現在はスタブでも良いが、後でentity.pyのrecalculate_statsで使うためのインターフェースを定義
- 検証: `python -c "from job_system import JobManager, JobRegistry; from entity import Entity; r=JobRegistry(); r.load(); m=JobManager(r); p=Entity(); warrior=r.get('warrior'); m.apply_job_stats(p, warrior); print(f'Job stats applied (check recalculate_stats)')"`
- ヒント: 実際のステータス適用はentity.py側で行うため、ここではインターフェース定義に留めても良い


### 4.18 entity.py recalculate_statsメソッドジョブ補正追加準備 (Step 48)
- `entity.py` の `recalculate_stats` メソッドを修準備（ジョブ補正適用のためのフックポイント作成）
- 現在の実装を確認し、ベースステータス計算後のジョブ補正適用ポイントを作る
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); recalc=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='recalculate_stats'][0]; print(f'recalculate_stats lines: {recalc.end_lineno-recalc.lineno+1}')"`
- ヒント: ここでジョブのstat_modifiersを加算するロジックを後で追加

### 4.19 entity.py recalculate_statsメソッドにジョブ補正適用追加 (Step 49)
- `entity.py` の `recalculate_stats` メソッドにジョブ補正適用ロジックを追加
- プレイヤーの現在のジョブを参照して、対応するJobDataを取得
- stat_modifiersをベースステータスに加算（強化は乗算、減弱は加算でマイナス値）
- 検証: `python -c "from entity import Entity; from job_system import JobRegistry; r=JobRegistry(); r.load(); p=Entity(); p.job='warrior'; p.job_level=1; base_str=p.attributes.strength; p.recalculate_stats(); new_str=p.attributes.strength; print(f'STR before: {base_str}, after: {new_str} (warrior +10)')"`
- ヒント: ジョブが見つからない場合は補正を適用しない（デフォルトnoviceは空の修正値）

### 4.20 game.py ジョブマネージャー参照追加 (Step 50)
- `game.py` のEngineクラスに `job_manager: JobManager` フィールドを追加（skill_tree_managerと同様）
- `__init__` で初期化（JobRegistryをロード済みのインスタンスを渡す）
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); engine=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='Engine'][0]; init=[n for n in engine.body if isinstance(n,ast.FunctionDef) and n.name=='__init__'][0]; has_jm=any('job_manager' in ast.dump(n) for n in init.body); print(f'Job manager field: {has_jm}')"`
- ヒント: 既存のマネージャーフィールドと同じパターンで追加

### 4.21 game.py advance_worldメソッドジョブ経験値追加 (Step 51)
- `game.py` の `advance_world` メソッドにジョブ経験値加算ロジックを追加
- 一定ターンごと（例: 1ターンにつき10ジョブ経験値）に職業経験値を増加
- 一定値（例: 100）に到達したらジョブレベルアップ
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); advance=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='advance_world'][0]; print(f'advance_world has job exp: {\"job_exp\" in ast.dump(advance)}')"`
- ヒント: ターンベースで増やすとバランス取りやすい

### 4.22 entity.py gain_expメソッドジョブ経験値ボーナス追加（オプション） (Step 52)
- `entity.py` の `gain_exp` メソッドに、通常経験値取得時にジョブ経験値ボーナスを追加（オプション）
- 例えば通常経験値の10%をジョブ経験値として加算
- これにより戦闘やクエストでもジョブレベルが上がるようになる
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); gain_exp=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='gain_exp'][0]; print(f'gain_exp has job exp bonus: {\"job_exp\" in ast.dump(gain_exp)}')"`
- ヒント: まずはスタブ実装で、後でバランス調整のための係数を設定可能にする

### 4.23 game.py render_allメソッドジョブUI追加 (Step 53)
- `game.py` の `render_all` メソッドに、特定キー（例: Jキー）押下時のジョブ表示ロジックを追加
- ゲームステートに `SHOWING_JOB` を追加し、その状態時に現在のジョブ情報・転職可能なジョブリストを表示
- 基本的なテキストベースのUIから始める
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); render=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='render_all'][0]; print(f'render_all has job UI: {\"job\" in ast.dump(render) and \"J\" in ast.dump(render)}')"`
- ヒント: スキルツリーUIと同様のパターンで実装すると一貫性が出る

### 4.24 game.py メインループジョブキー割り当て追加 (Step 54)
- `game.py` の `main` 関数のイベントループに、ジョブ表示用のキー割り当てを追加
- Jキーが押されたらゲームステートを `SHOWING_JOB` に変更
- ESCキーで元のゲームステートに戻る処理
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); main=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='main'][0]; print(f'main has J key handling: {\"K_j\" in ast.dump(main) or \"j\" in ast.dump(main)}')"`
- ヒント: キー割り当ては重複しないように注意（Sキーはスキルツリー、Jキーはジョブ）

---

## 🎯 フェーズ5：エクスクルーシブスキルシステムの構築 (Step 55-72)
**目的: エクスクルーシブスキルシステムを構築する。**

### 5.1 data/exclusive_skills.yaml 基本構造作成 (Step 55)
- ファイル `data/exclusive_skills.yaml` を作成し、基本的なYAML構造を定義
- エクスクルーシブスキルのトップレベルキー `exclusive_skills:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/exclusive_skills.yaml')); print('OK' if data and 'exclusive_skills' in data else 'ERROR')"`
- ヒント: これまでのYAMLファイルと同様のパターン

### 5.2 data/exclusive_skills.yaml シールドバッシュ定義 (Step 56)
- `data/exclusive_skills.yaml` に「シールドバッシュ」を追加（戦士専用）
- name, job: "warrior", type: "active", mp_cost, cooldown, description
- effects: ダメージ（str * 1.5 formula）とスタン効果
- inherit_chance: 0.3
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/exclusive_skills.yaml')); sb=data.get('exclusive_skills',{}).get('shield_bash'); print(f'Shield bash exists: {sb is not None}'); print(f'Warrior exclusive: {sb.job==\"warrior\" if sb else False}')"`
- ヒント: 数式形式のeffectsは後でパースするため、今は文字列として保存

### 5.3 data/exclusive_skills.yaml 居合術定義 (Step 57)
- `data/exclusive_skills.yaml` に「居合術」を追加（剣聖専用）
- 同様の構造でname, job: "swordmaster"等を設定
- 特殊効果: crit_guaranteedとignore_defenseを含める
- inherit_chance: 0.2
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/exclusive_skills.yaml')); ij=data.get('exclusive_skills',{}).get('iaijutsu'); print(f'Iaijutsu exists: {ij is not None}'); print(f'Swordmaster exclusive: {ij.job==\"swordmaster\" if ij else False}')"`
- ヒント: ジョブ名のスペルに注意（「swordmaster」かつ職業データと一致させる）

### 5.4 data/exclusive_skills.yaml メテオ定義 (Step 58)
- `data/exclusive_skills.yaml` に「メテオ」を追加（大賢者専用）
- 高いmp_costとcooldown、広範囲aoe_damage効果
- 追加効果: burn状態付与
- inherit_chance: 0.1（高レアリティスキルは低い継承確率）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/exclusive_skills.yaml')); meteor=data.get('exclusive_skills',{}).get('meteor'); print(f'Meteor exists: {meteor is not None}'); print(f'Archmage exclusive: {meteor.job==\"archmage\" if meteor else False}')"`
- ヒント: 上位の専用スキルほど継承確率を低く設定することでバランスを取る

### 5.5 skill_tree_system.py エクスクルーシブスキルマネージャー追加準備 (Step 59)
- `skill_tree_system.py` の `SkillTreeManager` クラスに、エクスクルーシブスキル関連メソッドのスタブを追加
- `check_exclusive_learnable(player, exclusive_skill_data) -> bool`
- `learn_exclusive_skill(player, skill_id) -> bool`
- `get_learned_exclusive_skills(player) -> List[str]`
- 検証: `python -c "from skill_tree_system import SkillTreeManager; m=SkillTreeManager(None); print('Extended manager created')"`
- ヒント: 既存のSkillTreeManagerにメソッドを追加していく形で実装

### 5.6 skill_tree_system.py エクスクルーシブスキルマネージャー実装 (Step 60)
- `skill_tree_system.py` のエクスクルーシブスキル関連メソッドを実装
- ジョブマッチチェック（プレイヤーの現在のジョブとスキル要求ジョブが一致）
- スキルポイント消費チェック
- 習得記録（mastered_exclusive_skillsリストに追加）
- 検証: `python -c "from skill_tree_system import SkillTreeManager, SkillTreeRegistry; from job_system import JobRegistry; from entity import Entity; str_reg=SkillTreeRegistry(); str_reg.load(); job_reg=JobRegistry(); job_reg.load(); m=SkillTreeManager(str_reg); p=Entity(); p.job='warrior'; p.skill_points=50; # Would need exclusive skill data loaded too"`
- ヒント: まずはジョブマッチングだけでも実装し、後でデータ連携を追加

### 5.7 entity.py エクスクルーシブ・継承スキルフィールド追加 (Step 61)
- `entity.py` のEntityクラスにエクスクルーシブ・継承関連フィールドを追加:
  - mastered_exclusive_skills: List[str] = field(default_factory=list)
  - inherited_skills: List[str] = field(default_factory=list)
- 場所: 専用・継承スキル関連のコメントブロック内（約605-606行付近）
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); cls=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='Entity'][0]; fields=[n.note for n in cls.body if isinstance(n,ast.AnnAssign)]; req=['mastered_exclusive_skills','inherited_skills']; found=[f for f in req if f in fields]; print(f'Exclusive/inheritance fields: {len(found)}/2 ({found})')"`
- ヒント: これもデフォルトファクトリーで空のリストを設定

### 5.8 systems.py エクスクルーシブスキルCombatSystem統合準備 (Step 62)
- `systems.py` の `CombatSystem` クラスにエクスクルーシブスキル用のスタブメソッドを追加
- `is_exclusive_skill(skill_id: str) -> bool`
- `get_exclusive_skill_data(skill_id: str) -> Optional[Dict]`
- 検証: `python -c "import ast; tree=ast.parse(open('systems.py').read()); combat=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='CombatSystem'][0]; methods=[n.name for n in combat.body if isinstance(n,ast.FunctionDef)]; has_excl=any('exclusive' in m for m in methods); print(f'CombatSystem has exclusive methods: {has_excl}')"`
- ヒント: まずはスタブで構造を作り、後で実際のスキルデータ連携を実装

### 5.9 systems.py エクスクルーシブスキルCombatSystem実装 (Step 63)
- `systems.py` の `CombatSystem` クラスにエクスクルーシブスキルの実際の処理を実装
- スキル使用時にエクスクルーシブスキルかどうかを判定
- エクスクルーシブスキルの場合は、専用のダメージ計算や効果適用ロジックを実行
- エフェクトの種類（damage, status等）に応じて適切な処理を分岐
- 検証: `python -c "from systems import CombatSystem; print('CombatSystem can process exclusive skills')"`
- ヒント: 既存のスキル処理ロジック（cast_spell等）と同様のパターンで追加

### 5.10 data/skill_fusion.yaml 基本構造作成 (Step 64)
- ファイル `data/skill_fusion.yaml` を作成し、基本的なYAML構造を定義
- スキル融合のトップレベルキー `fusions:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_fusion.yaml')); print('OK' if data and 'fusions' in data else 'ERROR')"`
- ヒント: これまでのYAMLファイルと同様のパターンで構造を作る

### 5.11 data/skill_fusion.yaml 魔剣術融合定義 (Step 65)
- `data/skill_fusion.yaml` に「魔剣術」融合を追加
- name, description
- required_skills: ["sword_mastery", "magic_basic"]
- result_skills: ["elemental_slash", "mana_blade"]（融合で習得できるスキルリスト）
- bonus_effects: 元素ダメージ追加等
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_fusion.yaml')); fb=data.get('fusions',{}).get('spellblade'); print(f'Spellblade fusion exists: {fb is not None}'); print(f'Requires sword mastery: {\"sword_mastery\" in fb.required_skills if fb else False}')"`
- ヒント: 必要スキルは両方習得していることが融合の条件

### 5.12 data/skill_fusion.yaml 聖騎士融合定義 (Step 66)
- `data/skill_fusion.yaml` に「聖騎士」融合を追加（戦士+信仰+神ジュレ必要）
- 同様の構造で設定
- required_job: "warrior" と required_god: "jure" を追加条件とする
- bonus_effects: 不死系に対するダメージ増加とキル時ヒール
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_fusion.yaml')); hk=data.get('fusions',{}).get('holy_knight'); print(f'Holy knight exists: {hk is not None}'); print(f'Requires warrior job: {\"required_job\" in hk and hk.required_job==\"warrior\" if hk else False}')"`
- ヒント: 融合条件にジョブや神信仰を追加することで、より特殊な条件を作れる

### 5.13 data/skill_fusion.yaml 影の暗殺者融合定義 (Step 67)
- `data/skill_fusion.yaml` に「影の暗殺者」融合を追加
- 同様の構造で設定
- required_job: "rogue" （後でローグジョブを追加する前提）
- bonus_effects: 会心率増加とバックステabマルチプライヤー
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/skill_fusion.yaml')); sa=data.get('fusions',{}).get('shadow_assassin'); print(f'Shadow assassin exists: {sa is not None}'); print(f'Requires dagger mastery: {\"dagger_mastery\" in sa.required_skills if sa else False}')"`
- ヒント: ここでいう「rogue」ジョブは後で追加する予定として、現在はコメントアウトまたはダミー条件にしておく

### 5.14 skill_fusion_system.py 新規ファイル作成 (Step 68)
- 新規ファイル `skill_fusion_system.py` を作成
- 基本的なファイルヘッダーとモジュール docstring を追加
- 検証: `python -c "print('File exists' if open('skill_fusion_system.py').readline().strip() else 'Empty or missing')"`
- ヒント: これまでの_*_system.pyファイルと同様の構造

### 5.15 skill_fusion_system.py FusionEffectクラス定義 (Step 69)
- `skill_fusion_system.py` に `@dataclass` デコレータ付きの `FusionEffect` クラスを定義
- フィールド: type (str), value (Union[int, float, str]), そしてエフェクト固有の追加フィールド（必要に応じて）
- 検証: `python -c "from skill_fusion_system import FusionEffect; e=FusionEffect(type='elemental_damage', value=20); print(f'Fusion effect: {e.type} {e.value}')"`
- ヒント: スキルツリーエフェクトと同じ構造で問題ない

### 5.16 skill_fusion_system.py FusionDataクラス定義 (Step 70)
- `skill_fusion_system.py` に `@dataclass` デコレータ付きの `FusionData` クラスを定義
- フィールド: id, name, description, required_skills (List[str]), required_job (Optional[str]), required_god (Optional[str]), result_skills (List[str]), bonus_effects (List[FusionEffect])
- 検証: `python -c "from skill_fusion_system import FusionData; f=FusionData('test','Test Fusion','Desc',['req1'],None,None,['res1'],[]); print(f'Fusion: {f.name} needs {len(f.required_skills)} skills')"`
- ヒント: オプションフィールド（ジョブ・神要求）にはOptionalを使う

### 5.17 skill_fusion_system.py FusionRegistryクラス作成 (Step 71)
- `skill_fusion_system.py` に `FusionRegistry` クラスを作成（シングルトンパターン）
- `__new__` メソッドと `load(path: str = "data/skill_fusion.yaml")` メソッドのスタブ
- `all()` と `get(fusion_id: str)` アクセッサーのスタブ
- 検証: `python -c "from skill_fusion_system import FusionRegistry; r=FusionRegistry(); r2=FusionRegistry(); print(f'Same instance: {r is r2}'); print('Fusion registry created')"`
- ヒント: 今まで作ってきたレジストリパターンをコピペして名前を変えるだけ

### 5.18 skill_fusion_system.py FusionRegistry.load()実装 (Step 72)
- `skill_fusion_system.py` の `FusionRegistry.load()` メソッドを実装
- YAMLファイルを読み込み、fusionsキーのデータをパースして内部辞書に格納
- エラーハンドリング（ファイルがない場合は空で開始）を追加
- 検証: `python -c "from skill_fusion_system import FusionRegistry; r=FusionRegistry(); r.load(); print(f'Loaded {len(r.all())} fusions')"`
- ヒント: エラーハンドリングを忘れずに、これでステップ72完了

---

## 🎯 フェーズ6：最終検証と統合 (Step 73-80)
**目的: スキルツリー・ジョブシステムの完全性を検証する。**

### 6.1 システム統合テスト (Step 73)
- スキルツリー・ジョブシステムの統合テストを作成
- スキルポイントの獲得、スキルの習得、ジョブの変更を検証
- 検証: `python -c "from skill_tree_system import SkillTreeManager; from job_system import JobManager; from entity import Entity; # 統合テストの実行"`
- ヒント: 各コンポーネントを連携させて動作確認

### 6.2 UI連携テスト (Step 74)
- スキルツリーUIとジョブUIの連携テスト
- キー入力時のゲームステート遷移を検証
- 検証: `python -c "import game; # UI連携テストの実行"`
- ヒント: ゲームステート管理の動作を確認

### 6.3 セーブ/ロードテスト (Step 75)
- スキルツリー・ジョブデータのセーブ/ロードテスト
- スキル進捗、ジョブ経験値の保存・復元を検証
- 検証: `python -c "from save_system import SaveSystem; # セーブ/ロードテストの実行"`
- ヒント: SaveSystemの動作を確認

### 6.4 バランステスト (Step 76)
- スキルツリー・ジョブシステムのバランステスト
- スキルポイントの分配、ジョブの unlocksを検証
- 検証: `python -c "from balance_simulator import BalanceChecker; # バランステストの実行"`
- ヒント: BalanceCheckerの動作を確認

### 6.5 パフォーマンステスト (Step 77)
- スキルツリー・ジョブシステムのパフォーマンステスト
- 大量のスキルポイント処理、複雑な前提条件チェックを検証
- 検証: `python -c "import time; # パフォーマンステストの実行"`
- ヒント: パフォーマンスのボトルネックを特定

### 6.6 ドキュメント更新 (Step 78)
- スキルツリー・ジョブシステムのドキュメントを更新
- APIドキュメント、使い方ガイドを整備
- 検証: `python -c "# ドキュメントの更新"`
- ヒント: ユーザー向けのドキュメントを提供

### 6.7 テストスイート統合 (Step 79)
- スキルツリー・ジョブシステムのテストスイートを統合
- 既存のテストフレームワークに統合
- 検証: `python -c "# テストスイートの統合"`
- ヒント: 包括的なテストカバレッジを確保

### 6.8 最終検証 (Step 80)
- スキルツリー・ジョブシステムの最終検証
- すべての要件を満たしているか確認
- 検証: `python -c "# 最終検証の実行"`
- ヒント: 商用リリース基準を満たしているか確認

---

## 📋 まとめ

**スキルツリー・ジョブシステムの実装計画書 (72ステップ)**

この計画書は、低性能なLLMでも実装可能なように1ステップ1タスクの極小単位に分割されています。各ステップには検証方法が含まれており、進捗状況を追跡できます。

**主要コンポーネント:**
1. データ構造（skill_trees.yaml、jobs.yaml、exclusive_skills.yaml、skill_fusion.yaml）
2. スキルツリーシステム（SkillTreeRegistry、SkillTreeManager）
3. ジョブシステム（JobRegistry、JobManager）
4. エクスクルーシブスキルシステム
5. スキル融合システム
6. ゲーム統合（entity.py、game.py、ui_fx_systems.py）
7. テストと検証

**依存関係:**
- スキルツリーシステムはジョブシステムに依存
- 両システムはentity.pyとgame.pyに統合
- エクスクルーシブスキルと融合スキルはスキルツリーシステムに統合

**検証方法:**
各ステップにはPythonの検証コードが含まれており、進捗状況を追跡できます。計画書に従って実装を進めることで、体系的なスキルツリー・ジョブシステムを構築できます。

**期待される成果:**
- 3つのスキルツリー（剣術、魔法、体術）×3段階のティア
- 4つのジョブ（見習い、戦士、剣聖、魔法使い、大賢者）
- エクスクルーシブスキル（シールドバッシュ、居合術、メテオ）
- スキル融合（魔剣術、聖騎士、影の暗殺者）
- 完全なスキルポイントシステム
- 完全なジョブ経験値システム
- 統合されたUI
- 包括的なテストスイート

この計画書に従って実装を進めることで、商用レベルのスキルツリー・ジョブシステムを構築できます。