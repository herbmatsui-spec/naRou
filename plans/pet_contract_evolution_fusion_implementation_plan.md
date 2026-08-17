# ペット契約・進化・融合システム 詳細実装計画書
低性能なLLMでも実装可能なように1～72までの小さなステップに分割

---

## Step 1: data/pet_contracts.yaml 基本構造作成
- ファイル `data/pet_contracts.yaml` を作成し、基本的なYAML構造を定義
- ペット契約のトップレベルキー `pet_contracts:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_contracts.yaml', encoding='utf-8')); print('OK' if data and 'pet_contracts' in data else 'ERROR')"`
- ヒント: 最初は空の構造から始め、後に内容を追加

## Step 2: data/pet_contracts.yaml デフォルト契約定義
- `data/pet_contracts.yaml` に「標準契約」の基本構造を追加
- name, icon, max_bond, 空のbond_gain, 空のbond_decay, 空のbond_effects
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_contracts.yaml', encoding='utf-8')); c=data.get('pet_contracts',{}).get('default'); print(f'Contract exists: {c is not None}'); print(f'Name: {c.get(\"name\") if c else \"Missing\"}')"`
- ヒント: まずは最小限の構造から始める

## Step 3: data/pet_contracts.yaml 絆度増加ルール追加
- 「標準契約」に bond_gain を追加（feeding: 10, gift: 25, combat_together: 5, walking: 1）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_contracts.yaml', encoding='utf-8')); c=data.get('pet_contracts',{}).get('default'); gain=c.get('bond_gain',{}) if c else {}; print(f'Bond gain: {gain}'); print('Has feeding gain' if 'feeding' in gain else 'Missing feeding gain')"`
- ヒント: キーと値のペア形式に注意

## Step 4: data/pet_contracts.yaml 絆度減少ルール追加
- 「標準契約」に bond_decay を追加（neglected: 2, defeated: 50, dismissed: 100）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_contracts.yaml', encoding='utf-8')); c=data.get('pet_contracts',{}).get('default'); decay=c.get('bond_decay',{}) if c else {}; print(f'Bond decay: {decay}'); print('Has neglected decay' if 'neglected' in decay else 'Missing neglected decay')"`
- ヒント: キーと値のペア形式に注意

## Step 5: data/pet_contracts.yaml 絆度効果追加（200閾値）
- 「標準契約」に bond_effects を追加し、最初の効果を定義（閾値200でstrength+2, agility+2）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_contracts.yaml', encoding='utf-8')); c=data.get('pet_contracts',{}).get('default'); effects=c.get('bond_effects',[]) if c else []; print(f'Bond effects count: {len(effects)}'); print('Has threshold 200 effect' if any(e.get('threshold')==200 for e in effects) else 'Missing threshold 200 effect')"`
- ヒント: 効果はリストなのでインデックスに注意

## Step 6: data/pet_contracts.yaml 絆度効果追加（500閾値・800閾値）
- bond_effectsに残りの2つの効果を追加（閾値500でスキル解放と経験値ボーナス、閾値800で進化ボーナスとスキル解放）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_contracts.yaml', encoding='utf-8')); c=data.get('pet_contracts',{}).get('default'); effects=c.get('bond_effects',[]) if c else []; thresholds=[e.get('threshold') for e in effects]; print(f'Effect thresholds: {thresholds}'); print('Has all three thresholds' if all(t in thresholds for t in [200,500,800]) else 'Missing some thresholds')"`
- ヒント: 3つの効果すべてが定義されていることを確認

## Step 7: data/pet_evolutions.yaml 基本構造作成
- ファイル `data/pet_evolutions.yaml` を作成し、基本的なYAML構造を定義
- ペット進化のトップレベルキー `pet_evolutions:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_evolutions.yaml', encoding='utf-8')); print('OK' if data and 'pet_evolutions' in data else 'ERROR')"`
- ヒント: pet_contracts.yamlと同様のパターン

## Step 8: data/pet_evolutions.yaml 子犬基本定義
- `data/pet_evolutions.yaml` に「子犬」の基本構造を追加
- name: "子犬" と 空のevolutionsリスト
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_evolutions.yaml', encoding='utf-8')); p=data.get('pet_evolutions',{}).get('puppy'); print(f'Puppy exists: {p is not None}'); print(f'Name: {p.get(\"name\") if p else \"Missing\"}')"`
- ヒント: まずは最小限の構造から始める

## Step 9: data/pet_evolutions.yaml 子犬進化オプション準備（構造のみ）
- 「子犬」に evolutions: リストを追加（空またはプレースホルダー）
- 後で実際の進化オプションを追加しやすくするため
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_evolutions.yaml', encoding='utf-8')); p=data.get('pet_evolutions',{}).get('puppy'); evos=p.get('evolutions',[]) if p else []; print(f'Puppy evolutions: {evos}'); print('Evolutions list prepared')"`
- ヒント: 現在は構造のみを確認

## Step 10: data/pet_evolutions.yaml 猟犬進化オプション追加
- 「子犬」の進化オプションに「猟犬」を追加
- id: "hound", name: "猟犬" と 空のrequirements, 空のstat_changes, 空のskill_changes, 空のevolution_bonus
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_evolutions.yaml', encoding='utf-8')); p=data.get('pet_evolutions',{}).get('puppy'); evos=p.get('evolutions',[]) if p else []; hound=[e for e in evos if e.get('id')=='hound']; print(f'Hound evolution found: {len(hound)>0}'); print(f'Hound name: {hound[0].get(\"name\") if hound else \"Missing\"}')"`
- ヒント: まずは基本構造から始め、後で詳細を追加

## Step 11: data/pet_evolutions.yaml 猟犬進化オプション詳細追加
- 「猟犬」進化オプションに requirements, stat_changes, skill_changes, evolution_bonus を追加
- requirements: level: 15, bond: 300, items: ["leather", "meat"], location: "forest"
- stat_changes: strength: +5, agility: +8, hp: +20
- skill_changes: add: ["tracking", "bite"], remove: ["playful_bark"]
- evolution_bonus: type: "permanent_exp_bonus", value: 0.1
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_evolutions.yaml', encoding='utf-8')); p=data.get('pet_evolutions',{}).get('puppy'); hound=[e for e in p.get('evolutions',[]) if e.get('id')=='hound'][0] if p else None; req=hound.get('requirements',{}) if hound else {}; print(f'Requirements level: {req.get(\"level\")}'); print(f'Requirements bond: {req.get(\"bond\")}'); print(f'Stat changes strength: {hound.get(\"stat_changes\",{}).get(\"strength\") if hound else \"Missing\"}')"`
- ヒント: ネスト構造に注意してインデントを合わせる

## Step 12: data/pet_evolutions.yaml 警備犬進化オプション追加
- 「子犬」の進化オプションに「警備犬」を同様に追加
- id: "guard_dog", name: "警備犬"
- requirements: level: 15, bond: 400, items: ["metal_ingot", "magic_crystal"], location: "town"
- stat_changes: strength: +10, constitution: +5, hp: +30
- skill_changes: add: ["guard_bark", "intercept"], remove: ["playful_bark"]
- evolution_bonus: type: "permanent_gold_find", value: 0.15
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_evolutions.yaml', encoding='utf-8')); p=data.get('pet_evolutions',{}).get('puppy'); evos=p.get('evolutions',[]) if p else []; guard=[e for e in evos if e.get('id')=='guard_dog']; print(f'Guard dog evolution found: {len(guard)>0}'); print(f'Requirements items: {guard[0].get(\"requirements\",{}).get(\"items\",[]) if guard else \"Missing\"}')"`
- ヒント: 2つ目の進化オプションが追加されていることを確認

## Step 13: data/pet_evolutions.yaml 魔導猟犬進化オプション追加
- 「子犬」の進化オプションに「魔導猟犬」を追加（3つ目の進化路線）
- id: "magic_hound", name: "魔導猟犬"
- requirements: level: 20, bond: 500, items: ["magic_herb", "mana_potion"], location: "magic_tower", skills: ["magic_basic"]
- stat_changes: intelligence: +8, agility: +5, mp: +25
- skill_changes: add: ["magic_bite", "mana_sense"], remove: ["bite"]
- evolution_bonus: type: "hybrid_bonus", value: {strength: +3, intelligence: +3}
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_evolutions.yaml', encoding='utf-8')); p=data.get('pet_evolutions',{}).get('puppy'); evos=p.get('evolutions',[]) if p else []; magic=[e for e in evos if e.get('id')=='magic_hound']; print(f'Magic hound evolution found: {len(magic)>0}'); print(f'Requirements skills: {magic[0].get(\"requirements\",{}).get(\"skills\",[]) if magic else \"Missing\"}'); print(f'Evolution bonus: {magic[0].get(\"evolution_bonus\",{}) if magic else \"Missing\"}')"`
- ヒント: 3つの進化オプションすべてが定義されていることを確認

## Step 14: entity.py PetAIクラス bondフィールド追加準備
- `entity.py` のPetAIクラスに bond フィールドを追加するための準備（コメント追加等）
- 実際のフィールド追加は次のステップで行う
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); print('PetAI class found')"`
- ヒント: まずはファイルが読めることを確認

## Step 15: entity.py PetAIクラス bondフィールド追加
- `entity.py` のPetAIクラスに `bond: int = 0` を追加
- 場所: PetAIクラス内の適切な場所（既存フィールドの後に追加）
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); petai=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='PetAI'][0]; fields=[n.note for n in petai.body if isinstance(n,ast.AnnAssign)]; has_bond='bond' in fields; print(f'Bond field: {has_bond}')"`
- ヒント: デフォルト値0を設定（契約度の初期値）

## Step 16: entity.py PetAIクラス contract_idフィールド追加
- `entity.py` のPetAIクラスに `contract_id: str = "default"` を追加
- 場所: bondフィールドの直後
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); petai=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='PetAI'][0]; fields=[n.note for n in petai.body if isinstance(n,ast.AnnAssign)]; has_contract='contract_id' in fields; print(f'Contract ID field: {has_contract}')"`
- ヒント: デフォルト値"default"を設定（pet_contracts.yamlのキーと合わせる）

## Step 17: entity.py PetAIクラス evolution_pathフィールド追加
- `entity.py` のPetAIクラスに `evolution_path: List[str] = field(default_factory=list)` を追加
- 場所: contract_idフィールドの直後
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); petai=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='PetAI'][0]; fields=[n.note for n in petai.body if isinstance(n,ast.AnnAssign)]; has_path='evolution_path' in fields; print(f'Evolution path field: {has_path}')"`
- ヒント: デフォルトファクトリーを使って空のリストを初期化

## Step 18: entity.py PetAIクラス evolution_stageフィールド追加
- `entity.py` のPetAIクラスに `evolution_stage: int = 0` を追加
- 場所: evolution_pathフィールドの直後
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); petai=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='PetAI'][0]; fields=[n.note for n in petai.body if isinstance(n,ast.AnnAssign)]; has_stage='evolution_stage' in fields; print(f'Evolution stage field: {has_stage}')"`
- ヒント: デフォルト値0を設定（初期段階）

## Step 19: pet_contract_system.py 新規ファイル作成
- 新規ファイル `pet_contract_system.py` を作成
- 基本的なファイルヘッダーとモジュール docstring を追加
- 検証: `python -c "print('File exists' if open('pet_contract_system.py').readline().strip() else 'Empty or missing')"`
- ヒント: 他の_*_system.pyファイルと同様の構造

## Step 20: pet_contract_system.py PetContractDataクラス定義
- `pet_contract_system.py` に `@dataclass` デコレータ付きの `PetContractData` クラスを定義
- フィールド: id, name, icon, max_bond (int), bond_gain (Dict[str, int]), bond_decay (Dict[str, int]), bond_effects (List[Dict])
- bond_effectsの各要素は threshold (int) と effects (List[Dict]) を持つ
- 検証: `python -c "from pet_contract_system import PetContractData; c=PetContractData('test','Test Contract','🤝',1000,{},{},[]); print(f'Contract: {c.name} max bond:{c.max_bond}')"`
- ヒント: ネスト構造に注意してタイプヒントを付ける

## Step 21: pet_contract_system.py PetContractRegistryクラス作成
- `pet_contract_system.py` に `PetContractRegistry` クラスを作成（シングルトンパターン）
- `__new__` メソッドと `load(path: str = "data/pet_contracts.yaml")` メソッドのスタブ
- `all()` と `get(contract_id: str)` アクセッサーのスタブ
- 検証: `python -c "from pet_contract_system import PetContractRegistry; r=PetContractRegistry(); r2=PetContractRegistry(); print(f'Same instance: {r is r2}'); print('Pet contract registry created')"`
- ヒント: 今まで作ってきたレジストリパターンをコピペして名前を変えるだけ

## Step 22: pet_contract_system.py PetContractRegistry.load()実装
- `pet_contract_system.py` の `PetContractRegistry.load()` メソッドを実装
- YAMLファイルを読み込み、pet_contractsキーのデータをパースして内部辞書に格納
- エラーハンドリング（ファイルがない場合は空で開始）を追加
- 検証: `python -c "from pet_contract_system import PetContractRegistry; r=PetContractRegistry(); r.load(); print(f'Loaded {len(r.all())} pet contracts')"`
- ヒント: エラーハンドリングを忘れずに（FileNotFoundError等）

## Step 23: pet_contract_system.py PetContractManagerクラス作成
- `pet_contract_system.py` に `PetContractManager` クラスを作成
- `__init__` で registry 参照を保持
- 主要メソッドのスタブを作成:
  - `update_bond(pet: 'PetAI', amount: int) -> int` (絆度更新、0-max_bondでクランプ)
  - `get_bond_effects(pet: 'PetAI') -> List[Dict]` (現在の絆度で適用される効果リスト)
  - `can_evolve(pet: 'PetAI', evolution_data: Dict) -> bool` (進化可能かチェック)
- 検証: `python -c "from pet_contract_system import PetContractManager; m=PetContractManager(None); print('Pet contract manager created')"`
- ヒント: まずはスタブで構造を作り、後で実装を埋める

## Step 24: pet_contract_system.py PetContractManager.update_bond実装
- `pet_contract_system.py` の `PetContractManager.update_bond` を実装
- 現在のbondにamountを加算し、0以上max_bond以下でクランプ
- 更新後のbond値を返す
- 検証: `python -c "from pet_contract_system import PetContractManager, PetContractRegistry; from entity import Entity; r=PetContractRegistry(); r.load(); m=PetContractManager(r); pet=Entity().pet_ai; result=m.update_bond(pet, 50); print(f'Bond update result: {result}'); print(f'Pet bond after: {pet.bond}')"`
- ヒント: クランプ処理を忘れずに（min(0, min(max_bond, current + amount))）

## Step 25: pet_contract_system.py PetContractManager.get_bond_effects実装
- `pet_contract_system.py` の `PetContractManager.get_bond_effects` を実装
- プレイヤーのpetのcontract_idを参照して契約データを取得
- 現在のbond値を超えるすべてのthresholdのeffectsをリストアップ
- 検証: `python -c "from pet_contract_system import PetContractManager, PetContractRegistry; from entity import Entity; r=PetContractRegistry(); r.load(); m=PetContractManager(r); pet=Entity().pet_ai; pet.bond=250; effects=m.get_bond_effects(pet); print(f'Bond effects for bond 250: {len(effects)}'); print('Has threshold 200 effect' if any(e.get('threshold')==200 for effect_group in effects for e in effect_group.get('effects',[])) else 'Missing effect')"`
- ヒント: bond_effectsはリストで、各要素はthresholdとeffectsリストを持つネスト構造

## Step 26: pet_contract_system.py PetContractManager.can_evolve実装（基本版）
- `pet_contract_system.py` の `PetContractManager.can_evolve` を実装（基本版）
- 進化データのbond要件と現在のbondを比較（シンプル版：bond以上かチェック）
- 検証: `python -c "from pet_contract_system import PetContractManager, PetContractRegistry; from entity import Entity; r=PetContractRegistry(); r.load(); m=PetContractManager(r); pet=Entity().pet_ai; pet.bond=400; evolution={'bond': 300}; print(f'Can evolve with bond 400 vs req 300: {m.can_evolve(pet, evolution)}')"`
- ヒント: 後で他の要件（レベル、アイテム等）もチェックするように拡張

## Step 27: entity.py PetAIクラスに絆度増加メソッド追加準備
- `entity.py` のPetAIクラスに絆度増加のためのメソッド追加準備（コメント追加等）
- 実際のメソッド追加は次のステップで行う
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); petai=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='PetAI'][0]; print(f'PetAI methods: {[n.name for n in petai.body if isinstance(n,ast.FunctionDef)]}')"`
- ヒント: 既存メッソドを確認して場所を決定

## Step 28: entity.py PetAIクラスに絆度増加メソッド追加
- `entity.py` のPetAIクラスに `increase_bond(self, amount: int, reason: str = "") -> int` メソッドを追加
- PetContractManagerを使ってbondを更新し、結果を返す
- reasonを記録する設計も考慮（後でログ等に使用）
- 検証: `python -c "from entity import Entity; pet=Entity().pet_ai; result=pet.increase_bond(25, 'feeding'); print(f'Bond increase result: {result}'); print(f'Pet bond after: {pet.bond}')"`
- ヒント: PetContractManagerのインスタンスを取得する方法を考える（シングルトン経由か引き渡しか）

## Step 29: game.py _pet_aiメソッド絆度増減追加準備
- `game.py` の `_pet_ai` メソッドを修準備（絆度増減ロジック追加のためのフックポイント作成）
- 現在の_pet_aiロジックを確認し、絆度変更ポイントを作る
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); pet_ai=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_pet_ai'][0]; print(f'_pet_ai lines: {pet_ai.end_lineno-pet_ai.lineno+1}')"`
- ヒント: まずはファイルが読めることを確認

## Step 30: game.py _pet_aiメソッドに絆度増減ロジック追加（歩行時）
- `game.py` の `_pet_ai` メソッドに、プレイヤーと同じ場所にいるときの絆度増加ロジックを追加（walking: 1ポイント/ターン）
- ペットがプレイヤーと同一座標か、隣接座標にいるかをチェック
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); pet_ai=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_pet_ai'][0]; print(f'_pet_ai has walking bond logic: {\"walking\" in ast.dump(pet_ai) and \"bond\" in ast.dump(pet_ai)}')"`
- ヒント: ターンベースなので、advance_worldで1ターンごとにチェックする形でも良い

## Step 31: game.py アイテム使用時絆度増加トリガー追加準備
- `game.py` のアイテム使用関数（use_item等）を修準備（ペットへのプレゼント時絆度増加のためのフックポイント作成）
- 現在のアイテム使用ロジックを確認し、ペットへの使用時ポイントを作る
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); print(f'game.py has item use functions')"`
- ヒント: アイテム使用関数を探して場所を決定

## Step 32: game.py アイテム使用時絆度増加トリガー追加（プレゼント）
- `game.py` のアイテム使用時に、ペットにアイテムを使用したときの絆度増加ロジックを追加（gift: 25ポイント）
- アイテムタイプに応じてポイントを変える設計も考慮（高級アイテム＝多ポイント）
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); use_item=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and ('use' in n.name.lower() or 'item' in n.name.lower())]; print(f'Found item use functions: {[f.name for f in use_item[:3]]}')"`
- ヒント: まずは固定値（25ポイント）から始め、後でアイテムベースにする

## Step 33: game.py _on_killメソッド絆度増加トリガー追加（共闘時）
- `game.py` の `_on_kill` メソッドに、ペットと共闘時の絆度増加ロジックを追加（combat_together: 1ターンごとに5ポイント）
- ペットが生存しているかつ同じ敵を攻撃しているかを簡易的にチェック
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); on_kill=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_on_kill'][0]; print(f'_on_kill has combat together bond logic: {\"combat\" in ast.dump(on_kill) and \"bond\" in ast.dump(on_kill)}')"`
- ヒント: まずはペットが生存しているかだけチェックし、後で共闘判定を精密化

## Step 34: game.py _pet_aiメソッドに絆度減少ロジック追加（放置時）
- `game.py` の `_pet_ai` メソッドに、プレイヤーから遠隔にいるときの絆度減少ロジックを追加（neglected: 2ポイント/ターン）
- プレイヤーとの距離が一定以上かどうかをチェック（マンハッタン距離またはユークリッド距離）
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); pet_ai=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_pet_ai'][0]; print(f'_pet_ai has neglected bond logic: {\"neglected\" in ast.dump(pet_ai) and \"bond\" in ast.dump(pet_ai)}')"`
- ヒント: まずは単純な距離チェック（同一マップ内かどうか）から始め、後で精密化

## Step 35: game.py _pet_aiメソッドに絆度減少ロジック追加（戦闘不能時）
- `game.py` の `_pet_ai` メソッドに、ペットが戦闘不能になったときの絆度減少ロジックを追加（defeated: 50ポイント）
- ペットのHPが0以下になった瞬間を検知して減少
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); pet_ai=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_pet_ai'][0]; print(f'_pet_ai has defeated bond logic: {\"defeated\" in ast.dump(pet_ai) and \"bond\" in ast.dump(pet_ai)}')"`
- ヒント: HP変化をチェックして、以前は生存していたのに今では戦闘不能になったかを検知

## Step 36: data/pet_evolutions.yaml 他ペット種別追加準備（構造のみ）
- `data/pet_evolutions.yaml` に他のペット種別（子猫等）の構造を追加するためのプレースホルダー
- 後で実際のペット種別データを追加しやすくするため
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_evolutions.yaml', encoding='utf-8')); pets=list(data.get('pet_evolutions',{}).keys()); print(f'Pet types: {pets}'); print('Pet types prepared')"`
- ヒント: 現在は子犬のみだが、構造を確認

## Step 37: pet_evolution_system.py 新規ファイル作成
- 新規ファイル `pet_evolution_system.py` を作成
- 基本的なファイルヘッダーとモジュール docstring を追加
- 検証: `python -c "print('File exists' if open('pet_evolution_system.py').readline().strip() else 'Empty or missing')"`
- ヒント: これまでの_*_system.pyファイルと同様の構造

## Step 38: pet_evolution_system.py PetEvolutionDataクラス定義
- `pet_evolution_system.py` に `@dataclass` デコレータ付きの `PetEvolutionData` クラスを定義
- フィールド: id, name, requirements (Dict[str, Any]), stat_changes (Dict[str, int]), skill_changes (Dict[str, List[str]]), evolution_bonus (Dict[str, Any])
- skill_changesは add と remove のリストを持つ
- 検証: `python -c "from pet_evolution_system import PetEvolutionData; e=PetEvolutionData('test','Test Evolution',{},{},{},{}); print(f'Evolution: {e.name}')"`
- ヒント: ネスト構造に注意してタイプヒントを付ける

## Step 39: pet_evolution_system.py PetEvolutionRegistryクラス作成
- `pet_evolution_system.py` に `PetEvolutionRegistry` クラスを作成（シングルトンパターン）
- `__new__` メソッドと `load(path: str = "data/pet_evolutions.yaml")` メソッドのスタブ
- `all()` と `get(evolution_id: str)` アクセッサーのスタブ（ペット種別IDと進化IDで階層取得可能）
- 検証: `python -c "from pet_evolution_system import PetEvolutionRegistry; r=PetEvolutionRegistry(); r2=PetEvolutionRegistry(); print(f'Same instance: {r is r2}'); print('Pet evolution registry created')"`
- ヒント: ペット種別ごとに進化オプションをグループ化した構造を想定

## Step 40: pet_evolution_system.py PetEvolutionRegistry.load()実装
- `pet_evolution_system.py` の `PetEvolutionRegistry.load()` メソッドを実装
- YAMLファイルを読み込み、pet_evolutionsキーのデータをパースして内部辞書に格納
- エラーハンドリング（ファイルがない場合は空で開始）を追加
- 検証: `python -c "from pet_evolution_system import PetEvolutionRegistry; r=PetEvolutionRegistry(); r.load(); print(f'Loaded evolutions for {len(r.all())} pet types')"`
- ヒント: エラーハンドリングを忘れずに

## Step 41: pet_evolution_system.py PetEvolutionManagerクラス作成
- `pet_evolution_system.py` に `PetEvolutionManager` クラスを作成
- `__init__` で registry 参照を保持
- 主要メソッドのスタブを作成:
  - `get_available_evolutions(pet_type: str, pet: 'PetAI') -> List[PetEvolutionData]` (利用可能進化リスト)
  - `apply_evolution(pet: 'PetAI', evolution_data: PetEvolutionData) -> bool` (進化適用)
- 検証: `python -c "from pet_evolution_system import PetEvolutionManager; m=PetEvolutionManager(None); print('Pet evolution manager created')"`
- ヒント: まずはスタブで構造を作り、後で実装を埋める

## Step 42: pet_evolution_system.py PetEvolutionManager.get_available_evolutions実装
- `pet_evolution_system.py` の `PetEvolutionManager.get_available_evolutions` を実装
- ペットの種類（元の種族）を取得し、その種別の進化オプションリストを取得
- 各進化オプションについて、PetContractManagerを使って進化可能かチェック
- 進化可能かつまだ進化していないオプションのみを返す
- 検証: `python -c "from pet_evolution_system import PetEvolutionManager, PetEvolutionRegistry; from pet_contract_system import PetContractManager, PetContractRegistry; from entity import Entity; er=PetEvolutionRegistry(); er.load(); cr=PetContractRegistry(); cr.load(); m=PetEvolutionManager(er); pet_type='puppy'; pet=Entity().pet_ai; pet.bond=400; evolutions=m.get_available_evolutions(pet_type, pet); print(f'Available evolutions for {pet_type}: {len(evolutions)}'); print('Has hound evolution' if any(e.get('id')=='hound' for e in evolutions) else 'Missing hound')"`
- ヒント: まずはbond要件のみチェックし、後でレベル・アイテム等もチェックするように拡張

## Step 43: pet_evolution_system.py PetEvolutionManager.apply_evolution実装
- `pet_evolution_system.py` の `PetEvolutionManager.apply_evolution` を実装
- 進化データのstat_changesをペットのベースステータスに適用
- skill_changesのaddスキルをペットのスキルリストに追加、removeスキルを削除
- evolution_pathに進化IDを追加、evolution_stageをインクリメント
- evolution_bonusを適用（永続ボーナス等）
- 検証: `python -c "from pet_evolution_system import PetEvolutionManager, PetEvolutionRegistry; from entity import Entity; er=PetEvolutionRegistry(); er.load(); m=PetEvolutionManager(er); pet=Entity().pet_ai; # Setup pet as puppy with sufficient bond"`
- ヒント: まずは基本的な統計変更とスキル変更から実装し、後で進化記録・ボーナス適用を追加

## Step 44: game.py _pet_aiメソッド進化条件チェック追加準備
- `game.py` の `_pet_ai` メソッドを修準備（進化条件チェックのためのフックポイント作成）
- 現在の_pet_aiロジックを確認し、進化チェックポイントを作る
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); pet_ai=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_pet_ai'][0]; print(f'_pet_ai lines: {pet_ai.end_lineno-pet_ai.lineno+1}')"`
- ヒント: 定期的にチェックする設計（例: 10ターンごと）

## Step 45: game.py _pet_aiメソッドに進化条件チェックロジック追加
- `game.py` の `_pet_ai` メソッドに、一定ターンごとの進化条件チェックロジックを追加
- PetEvolutionManagerを使って利用可能進化を取得し、利用可能ならば進化実行を促すフラグを設定
- 実際の進化はプレイヤーの確認を得てから実行する設計も考慮（自動進化vs手動進化）
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); pet_ai=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_pet_ai'][0]; print(f'_pet_ai has evolution check logic: {\"evolution\" in ast.dump(pet_ai) and \"check\" in ast.dump(pet_ai)}')"`
- ヒント: ターンベースで定期チェックを行い、進化可能ならフラグを設定（後でUIで確認）

## Step 46: game.py アイテム使用時進化トリガー追加（特別アイテム）
- `game.py` のアイテム使用時に、特定アイテムを使用したときの進化トリガーを追加
- 例: 「魔法の石」を使用したら該当する進化オプションを強制的に利用可能にする
- アイテムIDに応じて特定の進化を解放する設計
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); use_item=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and ('use' in n.name.lower() or 'item' in n.name.lower())]; print(f'Found item use functions: {[f.name for f in use_item[:3]]}')"`
- ヒント: まずは特定アイテム名のハードコーディングから始め、後でデータ駆動にする

## Step 47: data/pet_fusion.yaml 基本構造作成
- ファイル `data/pet_fusion.yaml` を作成し、基本的なYAML構造を定義
- ペット融合のトップレベルキー `pet_fusion:` を追加
- fusion_recipes: リストを作成（空またはプレースホルダー）
- 検訨: `python -c "import yaml; data = yaml.safe_load(open('data/pet_fusion.yaml', encoding='utf-8')); print('OK' if data and 'pet_fusion' in data else 'ERROR')"`
- ヒント: pet_evolutions.yamlと同様のパターン

## Step 48: data/pet_fusion.yaml ドラゴンハウンド融合レシピ追加準備（構造のみ）
- `data/pet_fusion.yaml` に fusion_recipes リストを追加し、最初のレシピのためのプレースホルダーを作成
- 後で実際の融合レシピデータを追加しやすくするため
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_fusion.yaml', encoding='utf-8')); recipes=data.get('pet_fusion',{}).get('fusion_recipes',[]) if data else []; print(f'Fusion recipes: {recipes}'); print('Fusion recipes list prepared')"`
- ヒント: 現在は空だが、構造を確認

## Step 49: data/pet_fusion.yaml ドラゴンハウンド融合レシピ基本情報追加
- fusion_recipesの最初の要素に「ドラゴンハウンド」の基本情報を追加
- id: "dragon_hound", name: "ドラゴンハウンド", icon: "🐉🐕", description: "猛々しい猟犬と幼龍の遺伝子を融合"
- 必要な項目のプレースホルダーを作成（required_pets等）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_fusion.yaml', encoding='utf-8')); f=data.get('pet_fusion',{}).get('fusion_recipes',[[]])[0] if data.get('pet_fusion',{}) else {}; print(f'Fusion recipe found: {bool(f)}'); print(f'Name: {f.get(\"name\") if f else \"Missing\"}')"`
- ヒント: まずは基本情報から始め、後で詳細を追加

## Step 50: data/pet_fusion.yaml ドラゴンハウンド融合レシピ必要ペット追加
- 「ドラゴンハウンド」融合レシピに required_pets を追加
- ["hound", "drake"] （進化後猟犬と幼龍）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_fusion.yaml', encoding='utf-8')); f=data.get('pet_fusion',{}).get('fusion_recipes',[[]])[0] if data.get('pet_fusion',{}) else {}; pets=f.get('required_pets',[]) if f else []; print(f'Required pets: {pets}'); print('Has hound requirement' if 'hound' in pets else 'Missing hound requirement'); print('Has drake requirement' if 'drake' in pets else 'Missing drake requirement')"`
- ヒント: これらのペット種別はpet_evolutions.yamlで定義されていることを前提とする

## Step 51: data/pet_fusion.yaml ドラゴンハウンド融合レシピ必要契約度・レベル追加
- 「ドラゴンハウンド」融合レシピに required_bond と required_level を追加
- required_bond: [400, 350] （ハウンド:400, ドラケ:350）
- required_level: [20, 15] （ハウンド:20, ドラケ:15）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_fusion.yaml', encoding='utf-8')); f=data.get('pet_fusion',{}).get('fusion_recipes',[[]])[0] if data.get('pet_fusion',{}) else {}; bond=f.get('required_bond',[]) if f else []; level=f.get('required_level',[]) if f else []; print(f'Required bond: {bond}'); print(f'Required level: {level}'); print('Bond requirements correct' if bond==[400,350] else 'Incorrect bond requirements'); print('Level requirements correct' if level==[20,15] else 'Incorrect level requirements')"`
- ヒント: 順序に注意（最初が最初のペット、2番目が2番目のペット）

## Step 52: data/pet_fusion.yaml ドラゴンハウンド融合レシピ必要アイテム・施設追加
- 「ドラゴンハウンド」融合レシピに required_items と required_facility を追加
- required_items: ["dragon_scale", "magic_crystal", "philosophers_stone"]
- required_facility: "alchemy_lab"
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_fusion.yaml', encoding='utf-8')); f=data.get('pet_fusion',{}).get('fusion_recipes',[[]])[0] if data.get('pet_fusion',{}) else {}; items=f.get('required_items',[]) if f else []; facility=f.get('required_facility') if f else None; print(f'Required items: {items}'); print('Required facility: {facility}'); print('Has dragon scale' if 'dragon_scale' in items else 'Missing dragon scale'); print('Has alchemy lab' if facility=='alchemy_lab' else 'Missing alchemy lab')"`
- ヒント: アイテムIDはitem_system.yamlで定義されていることを前提とする（後で作成）

## Step 53: data/pet_fusion.yaml ドラゴンハウンド融合レシピ結果ペット・継承率追加
- 「ドラゴンハウンド」融合レシピに result_pet と inheritance_rate を追加
- result_pet: "dragon_hound"
- inheritance_rate: 0.7 （70%の確率で親特性を継承）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_fusion.yaml', encoding='utf-8')); f=data.get('pet_fusion',{}).get('fusion_recipes',[[]])[0] if data.get('pet_fusion',{}) else {}; result=f.get('result_pet') if f else None; inherit=f.get('inheritance_rate') if f else None; print(f'Result pet: {result}'); print(f'Inheritance rate: {inherit}'); print('Result pet correct' if result=='dragon_hound' else 'Incorrect result pet'); print('Inheritance rate correct' if inherit==0.7 else 'Incorrect inheritance rate')"`
- ヒント: 結果ペットIDは新規作成されるため、現在はそのIDとして扱う

## Step 54: data/pet_fusion.yaml ドラゴンハウンド融合レシピステータステンプレート追加
- 「ドラゴンハウンド」融合レシピに stat_template を追加
- strength: 18, agility: 16, constitution: 14, intelligence: 10, hp: 120, mp: 40
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_fusion.yaml', encoding='utf-8')); f=data.get('pet_fusion',{}).get('fusion_recipes',[[]])[0] if data.get('pet_fusion',{}) else {}; stat=f.get('stat_template',{}) if f else {}; print(f'Stat template strength: {stat.get(\"strength\")}'); print(f'Stat template agility: {stat.get(\"agility\")}'); print(f'Stat template hp: {stat.get(\"hp\")}'); print(f'Stat template mp: {stat.get(\"mp\")}'); print('Stat template complete' if all(k in stat for k in ['strength','agility','constitution','intelligence','hp','mp']) else 'Incomplete stat template')"`
- ヒント: 6つのステータスすべてが定義されていることを確認

## Step 55: data/pet_fusion.yaml ドラゴンハウンド融合レシピスキル継承情報追加
- 「ドラゴンハウンド」融合レシピに skill_inheritance を追加
- houndからtrackingとbiteを80%の確率で継承
- drakeからfire_breathとwing_flutterを60%の確率で継承
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_fusion.yaml', encoding='utf-8')); f=data.get('pet_fusion',{}).get('fusion_recipes',[[]])[0] if data.get('pet_fusion',{}) else {}; skill_inherit=f.get('skill_inheritance',[]) if f else []; print(f'Skill inheritance count: {len(skill_inherit)}'); print('Has hound inheritance' if any(s.get('from')=='hound' for s in skill_inherit) else 'Missing hound inheritance'); print('Has drake inheritance' if any(s.get('from')=='drake' for s in skill_inherit) else 'Missing drake inheritance')"`
- ヒント: 継承情報はリストで、各要素はfrom, skills, rateを持つ

## Step 56: data/pet_fusion.yaml ドラゴンハウンド融合レシピ突然変異情報追加
- 「ドラゴンハウンド」融合レシピに possible_mutations を追加
- ice_breathがfire_breathを30%の確率で置き換える
- two_headsが10%の確率で発生し、攻撃+20%とHP+15%
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_fusion.yaml', encoding='utf-8')); f=data.get('pet_fusion',{}).get('fusion_recipes',[[]])[0] if data.get('pet_fusion',{}) else {}; mutations=f.get('possible_mutations',[]) if f else []; print(f'Possible mutations count: {len(mutations)}'); print('Has ice breath mutation' if any(m.get('type')=='ice_breath' for m in mutations) else 'Missing ice breath mutation'); print('Has two heads mutation' if any(m.get('type')=='two_heads' for m in mutations) else 'Missing two heads mutation')"`
- ヒント: 突然変異情報はリストで、各要素はtype, chance, そしてreplacesまたはeffectsを持つ

## Step 57: data/pet_fusion.yaml ユニコーンペガサス融合レシピ追加準備
- fusion_recipesに2番目の要素として「ユニコーンペガサス」の基本情報を追加
- id: "unicorn_pegasus", name: "ユニコーンペガサス", icon: "🦄🪽", description: "聖なる角と天馬の翼を併せ持つ神獣"
- 必要な項目のプレースホルダーを作成（続けて詳細を追加）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_fusion.yaml', encoding='utf-8')); f_list=data.get('pet_fusion',{}).get('fusion_recipes',[]) if data.get('pet_fusion',{}) else []; print(f'Fusion recipes count: {len(f_list)}'); print('Has second recipe' if len(f_list)>=2 else 'Missing second recipe'); second=f_list[1] if len(f_list)>=2 else {}; print(f'Second recipe name: {second.get(\"name\") if second else \"Missing\"}')"`
- ヒント: 2つ目の融合レシピが追加されていることを確認

## Step 58: data/pet_fusion.yaml ユニコーンペガサス融合レシピ詳細追加
- 「ユニコーンペガサス」融合レシピに必要な項目をすべて追加（ペット・契約度・レベル・アイテム・施設・結果・継承率等）
- 必要ペット: ["unicorn", "pegasus"]
- 必要契約度: [500, 500]
- 必要レベル: [25, 25]
- 必要アイテム: ["holy_water", "feather_of_angel", "unicorn_horn"]
- 必要施設: "shrine"
- 結果ペット: "unicorn_pegasus"
- （突然変異情報は省略しても良いが、あれば尚良し）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/pet_fusion.yaml', encoding='utf-8')); f_list=data.get('pet_fusion',{}).get('fusion_recipes',[]) if data.get('pet_fusion',{}) else []; second=f_list[1] if len(f_list)>=2 else {}; pets=second.get('required_pets',[]) if second else []; print(f'Second recipe required pets: {pets}'); print('Has unicorn requirement' if 'unicorn' in pets else 'Missing unicorn requirement'); print('Has pegasus requirement' if 'pegasus' in pets else 'Missing pegasus requirement'); print('Required bond: {second.get(\"required_bond\",[])}'); print('Required level: {second.get(\"required_level\",[])}')"`
- ヒント: 1番目と同様の構造で詳細を追加していく

## Step 59: pet_fusion_system.py 新規ファイル作成
- 新規ファイル `pet_fusion_system.py` を作成
- 基本的なファイルヘッダーとモジュール docstring を追加
- 検証: `python -c "print('File exists' if open('pet_fusion_system.py').readline().strip() else 'Empty or missing')"`
- ヒント: これまでの_*_system.pyファイルと同様の構造

## Step 60: pet_fusion_system.py PetFusionDataクラス定義
- `pet_fusion_system.py` に `@dataclass` デコレータ付きの `PetFusionData` クラスを定義
- フィールド: id, name, description, icon, required_pets (List[str]), required_bond (List[int]), required_level (List[int]), required_items (List[str]), required_facility (Optional[str]), result_pet (str), inheritance_rate (float), mutation_chance (float), stat_template (Dict[str, int]), skill_inheritance (List[Dict]), possible_mutations (List[Dict])
- 必要に応じて追加フィールド（確率等）を定義しても良い
- 検証: `python -c "from pet_fusion_system import PetFusionData; f=PetFusionData('test','Test Fusion','Desc','🔬',[],[],[],[],None,'',0.0,0.0,{},{},[]); print(f'Fusion: {f.name} result:{f.result_pet}')"`
- ヒント: ネスト構造に注意してタイプヒントを付ける（特にオプションフィールド）

## Step 61: pet_fusion_system.py PetFusionRegistryクラス作成
- `pet_fusion_system.py` に `PetFusionRegistry` クラスを作成（シングルトンパターン）
- `__new__` メソッドと `load(path: str = "data/pet_fusion.yaml")` メソッドのスタブ
- `all()` と `get(fusion_id: str)` アクセッサーのスタブ
- 検証: `python -c "from pet_fusion_system import PetFusionRegistry; r=PetFusionRegistry(); r2=PetFusionRegistry(); print(f'Same instance: {r is r2}'); print('Pet fusion registry created')"`
- ヒント: 今まで作ってきたレジストリパターンをコピペして名前を変えるだけ

## Step 62: pet_fusion_system.py PetFusionRegistry.load()実装
- `pet_fusion_system.py` の `PetFusionRegistry.load()` メソッドを実装
- YAMLファイルを読み込み、pet_fusionキーのデータをパースして内部辞書に格納
- エラーハンドリング（ファイルがない場合は空で開始）を追加
- 検証: `python -c "from pet_fusion_system import PetFusionRegistry; r=PetFusionRegistry(); r.load(); print(f'Loaded {len(r.all())} pet fusion recipes')"`
- ヒント: エラーハンドリングを忘れずに（FileNotFoundError等）

## Step 63: pet_fusion_system.py PetFusionManagerクラス作成
- `pet_fusion_system.py` に `PetFusionManager` クラスを作成
- `__init__` で registry 参照を保持
- 主要メソッドのスタブを作成:
  - `can_fuse(pets: List['PetAI'], player: 'Entity') -> Optional[str]` (融合可能かチェック、可能なら結果ペットID)
  - `execute_fusion(pets: List['PetAI'], player: 'Entity', result_pet_id: str) -> bool` (融合実行、親ペット消去・新ペット生成)
- 検証: `python -c "from pet_fusion_system import PetFusionManager; m=PetFusionManager(None); print('Pet fusion manager created')"`
- ヒント: まずはスタブで構造を作り、後で実装を埋める

## Step 64: pet_fusion_system.py PetFusionManager.can_fuse実装（基本版）
- `pet_fusion_system.py` の `PetFusionManager.can_fuse` を実装（基本版）
- すべての融合レシピをチェックし、必要ペット種別・契約度・レベルが一致する最初のレシピを返す
- アイテム・施設要件は後で実装（ここでは無視）
- 検証: `python -c "from pet_fusion_system import PetFusionManager, PetFusionRegistry; from entity import Entity; r=PetFusionRegistry(); r.load(); m=PetFusionManager(r); # Setup two pets as hound and drake with sufficient bond and level"`
- ヒント: まずはペット種別・契約度・レベルのみチェックし、後でアイテム・施設もチェックするように拡張

## Step 65: entity.py PetAIクラスにequipmentフィールド追加
- `entity.py` のPetAIクラスに `equipment: Dict[str, str] = field(default_factory=list)` を追加（スロット -> アイテムID）
- 注意: field(default_factory=list)ではなくfield(default_factory=dict)に修正が必要
- 場所: evolution_stageフィールドの直後（または適切な場所）
- �検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); petai=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='PetAI'][0]; fields=[n.note for n in petai.body if isinstance(n,ast.AnnAssign)]; has_equip='equipment' in fields; print(f'Equipment field: {has_equip}'); print(f'Equipment type correct' if 'Dict' in str(fields[fields.index('equipment') if 'equipment' in fields else -1]) else 'Type may be incorrect')"`
- ヒント: 辞書タイプなのでfield(default_factory=dict)を使用（listではない）

## Step 66: entity.py PetAIクラス equipmentフィールドタイプ修正
- ステップ65で間違えていたequipmentフィールドのタイプを修正
- `equipment: Dict[str, str] = field(default_factory=dict)` に正しく変更
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); petai=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='PetAI'][0]; fields=[n.note for n in petai.body if isinstance(n,ast.AnnAssign)]; has_equip='equipment' in fields; print(f'Equipment field: {has_equip}'); print(f'Equipment type correct' if 'Dict' in str(fields[fields.index('equipment') if 'equipment' in fields else -1]) else 'Type may be incorrect')"`
- ヒント: タイプヒントが正しくDict[str, str]になっていることを確認

## Step 67: game.py 融合施設利用時トリガー追加準備
- `game.py` の施設利用関数（特定施設でのアクション）を修準備（ペット融合施設利用時トリガーのためのフックポイント作成）
- 現在の施設利用ロジックを確認し、融合施設でのアクションポイントを作る
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); print(f'game.py has facility use functions')"`
- ヒント: 施設利用関数を探して場所を決定（鍛冶場・調合所・神社等）

## Step 68: game.py 融合施設利用時トリガー追加（アルケミーラボ）
- `game.py` のアルケミーラボ施設利用時に、ペット融合のトリガーを追加
- 2体以上のペットが選択されている場合、PetFusionManagerを使って融合可能かチェック
- 融合可能ならば、融合実行確認プロンプトを表示
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read(); facility_use=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and ('facility' in n.name.lower() or 'use' in n.name.lower())]; print(f'Found facility use functions: {[f.name for f in facility_use[:3]]}')"`
- ヒント: まずは施設名のハードコーディングから始め、後でデータ駆動にする

## Step 69: entity.py PetAIクラスにpet_fusion_historyフィールド追加
- `entity.py` のEntityクラスに `pet_fusion_history: List[Dict] = field(default_factory=list)` を追加（融合記録）
- 場所: Entityクラス内の適切な場所（ペット関連フィールドの後に追加）
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); entity=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='Entity'][0]; fields=[n.note for n in entity.body if isinstance(n,ast.AnnAssign)]; has_history='pet_fusion_history' in fields; print(f'Pet fusion history field: {has_history}')"`
- ヒント: デフォルトファクトリーを使って空のリストを初期化

## Step 70: advanced_systems.py SaveSystemにペットデータ保存追加
- `advanced_systems.py` のSaveSystemクラスに、ペット関連データの保存・読み込みロジックを追加
- ペットのbond, contract_id, evolution_path, evolution_stage, equipment, pet_fusion_history等を保存
- 後方互換性のため、古いセーブデータにはデフォルト値を設定
- 検証: `python -c "import ast; tree=ast.parse(open('advanced_systems.py').read()); savesys=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='SaveSystem'][0]; methods=[n.name for n in savesys.body if isinstance(n,ast.FunctionDef)]; has_pet_logic=any('pet' in m.lower() for m in methods); print(f'SaveSystem has pet logic: {has_pet_logic}')"`
- ヒント: saveメソッドとloadメソッドにペットデータの処理を追加

## Step 71: ui_fx_systems.py ペット融合エフェクト追加準備
- `ui_fx_systems.py` にペット融合のためのエフェクト関数を追加する準備（コメント追加等）
- 実際のエフェクト追加は次のステップで行う
- 検証: `python -c "import ast; tree=ast.parse(open('ui_fx_systems.py').read()); print(f'ui_fx_systems.py lines: {len(tree.body)}')"`
- ヒント: まずはファイルが読めることを確認

## Step 72: ui_fx_systems.py ペット融合エフェクト追加
- `ui_fx_systems.py` にペット融合時に表示するエフェクト関数を追加
- 融合成功時のフラッシュエフェクト・音効果・メッセージ表示
- 新しく生成されたペットの紹介アニメーション
- 融合失敗時のエフェクトも考慮
- 検証: `python -c "import ast; tree=ast.parse(open('ui_fx_systems.py').read()); effect_funcs=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and ('fusion' in n.name.lower() or 'pet' in n.name.lower())]; print(f'Found pet/fusion effect functions: {[f.name for f in effect_funcs]}')"`
- ヒント: これでステップ72完了。実際のゲームへの統合は以降のステップで行われる想定。

---
**注意:** この実装計画書は72ステップに分割されていますが、実際の開発では一部のステップを並行して進めたり、依存関係に応じて順序を調整したりすることができます。各ステップは小さな変更単位となっているため、低性能なLLMでも一つずつ確実に実装していくことが可能です。

**主要な実装領域:**
1. ペット契約システム（絆度管理・効果適用）
2. ペット進化システム（進化分岐・条件チェック・適用）
3. ペット融合システム（遺伝子融合・新種創造・突然変異）
4. ペット装備システム（装備・スロット管理・効果適用）
5. ゲームループ統合（絆度増減・進化チェック・融合トリガー）
6. セーブ/ロード対応（ペットデータの永続化・後方互換性）
7. UI・エフェクト追加（融合エフェクト・契約度表示等）