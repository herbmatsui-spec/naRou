# ギルド・派閥・ランキングシステム 詳細実装計画書
低性能なLLMでも実装可能なように1～72までの小さなステップに分割

---

## Step 1: data/guilds.yaml 基本構造作成
- ファイル `data/guilds.yaml` を作成し、基本的なYAML構造を定義
- ギルドのトップレベルキー `guilds:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guilds.yaml', encoding='utf-8')); print('OK' if data and 'guilds' in data else 'ERROR')"`
- ヒント: 最初は空の構造から始め、後に内容を追加

## Step 2: data/guilds.yaml 冒険者ギルド基本定義
- `data/guilds.yaml` に「冒険者ギルド」の基本構造を追加
- name, icon, description, hall_location, 空のfacilities, 空のmembership_benefits, 空のrank_requirements, max_members
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guilds.yaml', encoding='utf-8')); g=data.get('guilds',{}).get('adventurers_guild'); print(f'Guild exists: {g is not None}'); print(f'Name: {g.get(\"name\") if g else \"Missing\"}')"`
- ヒント: まずは最小限の構造から始める

## Step 3: data/guilds.yaml 冒険者ギルド施設追加
- 「冒険者ギルド」に facilities を追加（quest_board, storage, training_ground）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guilds.yaml', encoding='utf-8')); g=data.get('guilds',{}).get('adventurers_guild'); fac=g.get('facilities',[]) if g else []; print(f'Facilities: {fac}'); print('Has quest_board' if 'quest_board' in fac else 'Missing quest_board')"`
- ヒント: YAMLのリスト形式に注意（- 項目 形式）

## Step 4: data/guilds.yaml 冒険者ギルドメンバー特典追加
- 「冒険者ギルド」に membership_benefits を追加（日次クエストボーナス20%、アイテム割引10%）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guilds.yaml', encoding='utf-8')); g=data.get('guilds',{}).get('adventurers_guild'); bens=g.get('membership_benefits',[]) if g else []; print(f'Benefits count: {len(bens)}'); print('Has daily quest bonus' if any(b.get('type')=='daily_quest_bonus' for b in bens) else 'Missing')"`
- ヒント: 辞書のリストなので、インデントと項目構造に注意

## Step 5: data/guilds.yaml 冒険者ギルドランク要件追加
- 「冒険者ギルド」に rank_requirements を追加（novice:0, member:100, veteran:500, officer:2000, leader:5000）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guilds.yaml', encoding='utf-8')); g=data.get('guilds',{}).get('adventurers_guild'); req=g.get('rank_requirements',{}) if g else {}; print(f'Rank requirements: {req}'); print('Has member rank' if 'member' in req else 'Missing member rank')"`
- ヒント: キーと値のペア形式に注意

## Step 6: data/guilds.yaml 他ギルド追加準備（構造のみ）
- 他のギルド構造のためのプレースホルダーを追加（コメントまたは空オブジェクト）
- 後で実際のギルドデータを追加しやすくするため
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guilds.yaml', encoding='utf-8')); print(f'Guild count: {len(data.get(\"guilds\",{}))}')"`
- ヒント: 現在は冒険者ギルドのみだが、構造を確認

## Step 7: data/factions.yaml 基本構造作成
- ファイル `data/factions.yaml` を作成し、基本的なYAML構造を定義
- 派閥のトップレベルキー `factions:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/factions.yaml', encoding='utf-8')); print('OK' if data and 'factions' in data else 'ERROR')"`
- ヒント: guilds.yamlと同様のパターン

## Step 8: data/factions.yaml ガルド王国基本定義
- `data/factions.yaml` に「ガルド王国」の基本構造を追加
- name, color (RGBリスト), 空のterritories, 空のallied_factions, 空のrival_factions, influence
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/factions.yaml', encoding='utf-8')); f=data.get('factions',{}).get('kingdom_garde'); print(f'Faction exists: {f is not None}'); print(f'Name: {f.get(\"name\") if f else \"Missing\"}')"`
- ヒント: 色は[0, 100, 200]ような形式で指定

## Step 9: data/factions.yaml ガルド王国領土・同盟・ rival追加
- 「ガルド王国」に territories, allied_factions, rival_factions を追加
- territories: ["vernis", "palmia", "pael"], allied_factions: ["church_of_lumiest"], rival_factions: ["shadow_hand"]
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/factions.yaml', encoding='utf-8')); f=data.get('factions',{}).get('kingdom_garde'); terr=f.get('territories',[]) if f else []; print(f'Territories: {terr}'); print('Has vernis' if 'vernis' in terr else 'Missing vernis')"`
- ヒント: それぞれがリスト形式であることを確認

## Step 10: data/factions.yaml 他派閥追加（ルミエスト教会・シャドウハンド）
- 「ルミエスト教会」と「シャドウハンド」を同様の構造で追加
- 各派閥の適切な色・領土・同盟・ライバル関係を設定
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/factions.yaml', encoding='utf-8')); factions=data.get('factions',{}); print(f'Faction count: {len(factions)}'); names=list(factions.keys()); print(f'Faction names: {names}')"`
- ヒント: 3つの派閥が定義されていることを確認

## Step 11: entity.py ギルド関連フィールド追加準備
- `entity.py` のEntityクラスにギルド関連フィールドを追加するための準備（コメント追加等）
- 実際のフィールド追加は次のステップで行う
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); print('Entity class found')"`
- ヒント: まずはファイルが読めることを確認

## Step 12: entity.py ギルド関連フィールド追加
- `entity.py` のEntityクラスに以下を追加:
  - guild_id: Optional[str] = None
  - guild_rank: str = "none"
  - guild_contribution: int = 0
  - guild_role: Optional[str] = None
- 場所: ギルド関連のコメントブロック内（適切な場所に追加）
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); cls=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='Entity'][0]; fields=[n.note for n in cls.body if isinstance(n,ast.AnnAssign)]; req=['guild_id','guild_rank','guild_contribution','guild_role']; found=[f for f in req if f in fields]; print(f'Guild fields: {len(found)}/4 ({found})')"`
- ヒント: dataclassフィールドなので、デフォルト値を正しく設定（None or "none" or 0）

## Step 13: entity.py ファクション関連フィールド追加
- `entity.py` のEntityクラスにファクション関連フィールドを追加:
  - faction_reputation: Dict[str, int] = field(default_factory=dict)
  - completed_faction_events: List[str] = field(default_factory=list)
  - ranking_titles: List[str] = field(default_factory=list)
- 場所: ファクション関連のコメントブロック内
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); cls=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='Entity'][0]; fields=[n.note for n in cls.body if isinstance(n,ast.AnnAssign)]; req=['faction_reputation','completed_faction_events','ranking_titles']; found=[f for f in req if f in fields]; print(f'Faction fields: {len(found)}/3 ({found})')"`
- ヒント: 辞書とリストにはfield(default_factory=...)を使用

## Step 14: entity.py クエスト関連フィールド追加
- `entity.py` のEntityクラスにギルドクエスト進捗フィールドを追加:
  - guild_quest_progress: Dict[str, int] = field(default_factory=dict)  # quest_id -> progress
- 場所: クエスト関連のコメントブロック内
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); cls=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='Entity'][0]; fields=[n.note for n in cls.body if isinstance(n,ast.AnnAssign)]; has_gqp='guild_quest_progress' in fields; print(f'Guild quest progress field: {has_gqp}')"`
- ヒント: クエストIDをキー、進捗値（0-100または同様）を値とする辞書

## Step 15: guild_system.py 新規ファイル作成
- 新規ファイル `guild_system.py` を作成
- 基本的なファイルヘッダーとモジュール docstring を追加
- 検証: `python -c "print('File exists' if open('guild_system.py').readline().strip() else 'Empty or missing')"`
- ヒント: 他の_*_system.pyファイルと同様の構造

## Step 16: guild_system.py GuildDataクラス定義
- `guild_system.py` に `@dataclass` デコレータ付きの `GuildData` クラスを定義
- フィールド: id, name, icon, description, hall_location, facilities (List[str]), membership_benefits (List[Dict]), rank_requirements (Dict[str, int]), max_members (int)
- 検証: `python -c "from guild_system import GuildData; g=GuildData('test','Test Guild','🏰','Desc','town',['fac'],[],{},10); print(f'Guild: {g.name} location:{g.hall_location}')"`
- ヒント: リストと辞フィールドには適切なタイプヒントを付ける

## Step 17: guild_system.py GuildRegistryクラス作成
- `guild_system.py` に `GuildRegistry` クラスを作成（シングルトンパターン）
- `__new__` メソッドと `load(path: str = "data/guilds.yaml")` メソッドのスタブ
- `all()` と `get(guild_id: str)` アクセッサーのスタブ
- 検証: `python -c "from guild_system import GuildRegistry; r=GuildRegistry(); r2=GuildRegistry(); print(f'Same instance: {r is r2}'); print('Guild registry created')"`
- ヒント: 今まで作ってきたレジストリパターンをコピペして名前を変えるだけ

## Step 18: guild_system.py GuildRegistry.load()実装
- `guild_system.py` の `GuildRegistry.load()` メソッドを実装
- YAMLファイルを読み込み、guildsキーのデータをパースして内部辞書に格納
- エラーハンドリング（ファイルがない場合は空で開始）を追加
- 検証: `python -c "from guild_system import GuildRegistry; r=GuildRegistry(); r.load(); print(f'Loaded {len(r.all())} guilds')"`
- ヒント: エラーハンドリングを忘れずに（FileNotFoundError等）

## Step 19: guild_system.py GuildManagerクラス作成
- `guild_system.py` に `GuildManager` クラスを作成
- `__init__` で registry 参照を保持
- 主要メソッドのスタブを作成:
  - `can_join_guild(player, guild_id) -> bool`
  - `join_guild(player, guild_id) -> bool`
  - `leave_guild(player) -> bool`
  - `get_guild_info(player) -> Optional[GuildData]`
  - `get_guild_members_count(guild_id) -> int` (簡易版)
- 検証: `python -c "from guild_system import GuildManager; m=GuildManager(None); print('Guild manager created')"`
- ヒント: まずはスタブで構造を作り、後で実装を埋める

## Step 20: guild_system.py GuildManager.can_join_guild実装
- `guild_system.py` の `GuildManager.can_join_guild` を実装
- プレイヤーが既にギルドに所属していないかチェック
- ギルドが存在するかチェック
- ギルドの定員に達していないかチェック（メンバー数取得は簡易版で後ほど改善）
- 検証: `python -c "from guild_system import GuildManager, GuildRegistry; from entity import Entity; r=GuildRegistry(); r.load(); m=GuildManager(r); p=Entity(); print(f'Can join adventurers_guild: {m.can_join_guild(p, \"adventurers_guild\")}')"`
- ヒント: 現時点ではギルドデータが空かもしれないので、その場合のハンドリングも考慮

## Step 21: guild_system.py GuildManager.join_guild実装
- `guild_system.py` の `GuildManager.join_guild` を実装
- 参加可能チェック → ギルドID設定 → 初期ランク・「なし」設定 → 貢献度0で開始
- 検証: `python -c "from guild_system import GuildManager, GuildRegistry; from entity import Entity; r=GuildRegistry(); r.load(); m=GuildManager(r); p=Entity(); # Need to have guild data loaded first"`
- ヒント: 参加成功時はplayer.guild_id = guild_id, player.guild_rank = "none", player.guild_contribution = 0を設定

## Step 22: guild_system.py GuildManager.leave_guild実装
- `guild_system.py` の `GuildManager.leave_guild` を実装
- 現在のギルドIDをクリア → ランクを「なし」に戻す → 役職をクリア
- 注意: 貢献度は保持するか、ゼロにリセットするか設計による（ここでは保持）
- 検証: `python -c "from guild_system import GuildManager, GuildRegistry; from entity import Entity; r=GuildRegistry(); r.load(); m=GuildManager(r); p=Entity(); p.guild_id='adventurers_guild'; result=m.leave_guild(p); print(f'Leave result: {result}; Guild ID after: {p.guild_id}')"`
- ヒント: 元のギルドIDを覚えておく必要がある場合は別途実装が必要

## Step 23: guild_system.py GuildManager.get_guild_info実装
- `guild_system.py` の `GuildManager.get_guild_info` を実装
- プレイヤーのguild_idを参照して、対応するGuildDataをレジストリから取得
- ギルドIDが設定されていない場合はNoneを返す
- 検証: `python -c "from guild_system import GuildManager, GuildRegistry; from entity import Entity; r=GuildRegistry(); r.load(); m=GuildManager(r); p=Entity(); info=m.get_guild_info(p); print(f'Info for no guild: {info}'); p.guild_id='adventurers_guild'; info2=m.get_guild_info(p); print(f'Info for adventurers_guild: {info2.name if info2 else \"None\"}')"`
- ヒント: ギルドが存在しない場合も考慮（Noneを返すかデフォルトギルドを返すか）

## Step 24: game.py ギルドマネージャー参照追加
- `game.py` のEngineクラスに `guild_manager: GuildManager` フィールドを追加
- `__init__` で初期化（GuildRegistryをロード済みのインスタンスを渡す）
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); engine=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='Engine'][0]; init=[n for n in engine.body if isinstance(n,ast.FunctionDef) and n.name=='__init__'][0]; has_gm=any('guild_manager' in ast.dump(n) for n in init.body); print(f'Guild manager field: {has_gm}')"`
- ヒント: 既存のマネージャーフィールドと同じパターンで追加

## Step 25: data/guild_quests.yaml 基本構造作成
- ファイル `data/guild_quests.yaml` を作成し、基本的なYAML構造を定義
- ギルドクエストのトップレベルキー `guild_quests:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guild_quests.yaml', encoding='utf-8')); print('OK' if data and 'guild_quests' in data else 'ERROR')"`
- ヒント: これまでのYAMLファイルと同様のパターン

## Step 26: data/guild_quests.yaml 冒険者ギルドデイリークエスト追加
- `data/guild_quests.yaml` に「冒険者ギルド」のデイリークエスト構造を追加
- adventurers_guild の下に daily: リストを作成
- 1つ目のクエスト: "slay_goblins" - ゴブリン5匹倒す
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guild_quests.yaml', encoding='utf-8')); ag=data.get('guild_quests',{}).get('adventurers_guild',{}); daily=ag.get('daily',[]) if ag else []; print(f'Daily quests: {len(daily)}'); print('Has slay_goblins' if any(q.get('id')=='slay_goblins' for q in daily) else 'Missing')"`
- ヒント: ネスト構造(guild_quests -> adventurers_guild -> daily -> [クエストオブジェクト])に注意

## Step 27: data/guild_quests.yaml goblin退治クエスト詳細追加
- 「slay_goblins」クエストに description, requirements, reward を追加
- requirements: monster_kills: {goblin: 5}
- reward: contribution: 50, gold: 100, item: "heal_herb"
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guild_quests.yaml', encoding='utf-8')); q=None; for ag in data.get('guild_quests',{}).values(): for dq in ag.get('daily',[]): if dq.get('id')=='slay_goblins': q=dq; break; if q: break; print(f'Quest found: {q is not None}'); print(f'Reward contribution: {q.get(\"reward\",{}).get(\"contribution\",0) if q else \"Missing\"}')"`
- ヒント: 要件と報酬のネスト構造に注意してインデントを合わせる

## Step 28: data/guild_quests.yaml 冒険者ギルドウィークリークエスト追加
- 「冒険者ギルド」に weekly: リストを追加
- 1つ目のウィークリークエスト: "explore_dungeon" - 未探索ダンジョン10階層進める
- 同上の構造で description, requirements (dungeon_depth: 10), reward (contribution: 300, gold: 1000, item: "steel_ingot")
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guild_quests.yaml', encoding='utf-8')); ag=data.get('guild_quests',{}).get('adventurers_guild',{}); weekly=ag.get('weekly',[]) if ag else []; print(f'Weekly quests: {len(weekly)}'); print('Has explore_dungeon' if any(q.get('id')=='explore_dungeon' for q in weekly) else 'Missing')"`
- ヒント: ダailyとweekly両方のリストがあることを確認

## Step 29: data/guild_quests.yaml 他ギルドクエスト準備（構造のみ）
- 他のギルドのクエスト構造のためのプレースホルダーを追加
- 後で実際のクエストデータを追加しやすくするため
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guild_quests.yaml', encoding='utf-8')); gqs=data.get('guild_quests',{}); print(f'Guilds with quests: {list(gqs.keys())}')"`
- ヒント: 現在は冒険者ギルドのみだが、構造を確認

## Step 30: entity.py ギルドクエスト進捗フィールド追加（再確認・最終調整）
- ステップ13で追加したguild_quest_progressフィールドが正しく定義されているか最終確認
- 必要に応じて修正（タイポ修正など）
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); cls=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='Entity'][0]; fields=[n.note for n in cls.body if isinstance(n,ast.AnnAssign)]; has_gqp='guild_quest_progress' in fields; print(f'Guild quest progress field correctly defined: {has_gqp}')"`
- ヒント: これがステップ29で使われるフィールドなので、正しく定義されていることを確認

## Step 31: guild_quest_system.py 新規ファイル作成
- 新規ファイル `guild_quest_system.py` を作成
- 基本的なファイルヘッダーとモジュール docstring を追加
- 検証: `python -c "print('File exists' if open('guild_quest_system.py').readline().strip() else 'Empty or missing')"`
- ヒント: これまでの_*_system.pyファイルと同様の構造

## Step 32: guild_quest_system.py GuildQuestDataクラス定義
- `guild_quest_system.py` に `@dataclass` デコレータ付きの `GuildQuestData` クラスを定義
- フィールド: id, name, description, requirements (Dict[str, Any]), reward (Dict[str, Any])
- 必要に応じてクエストタイプ（daily/weekly/monthly等）を追加しても良い
- 検証: `python -c "from guild_quest_system import GuildQuestData; q=GuildQuestData('test','Test Quest','Desc',{},{}); print(f'Quest: {q.name}')"`
- ヒント: requirementsとrewardは柔軟な構造のためAnyまたは詳細な構造を定義

## Step 33: guild_quest_system.py GuildQuestRegistryクラス作成
- `guild_quest_system.py` に `GuildQuestRegistry` クラスを作成（シングルトンパターン）
- `__new__` メソッドと `load(path: str = "data/guild_quests.yaml")` メソッドのスタブ
- `all()` と `get(guild_id, quest_type=None)` アクセッサーのスタブ（ギルドIDとクエストタイプでフィルタリング可能）
- 検証: `python -c "from guild_quest_system import GuildQuestRegistry; r=GuildQuestRegistry(); r2=GuildQuestRegistry(); print(f'Same instance: {r is r2}'); print('Guild quest registry created')"`
- ヒント: ギルドIDごとにクエストをグループ化した構造を想定

## Step 34: guild_quest_system.py GuildQuestRegistry.load()実装
- `guild_quest_system.py` の `GuildQuestRegistry.load()` メソッドを実装
- YAMLファイルを読み込み、guild_questsキーのデータをパースして内部辞書に格納
- エラーハンドリング（ファイルがない場合は空で開始）を追加
- 検証: `python -c "from guild_quest_system import GuildQuestRegistry; r=GuildQuestRegistry(); r.load(); print(f'Loaded quests for {len(r.all())} guilds')"`
- ヒント: エラーハンドリングを忘れずに

## Step 35: guild_quest_system.py GuildQuestManagerクラス作成
- `guild_quest_system.py` に `GuildQuestManager` クラスを作成
- `__init__` で registry 参照を保持
- 主要メソッドのスタブを作成:
  - `get_available_quests(player, quest_type: str = "daily") -> List[GuildQuestData]`
  - `update_quest_progress(player, quest_id: str, amount: int) -> bool`
  - `can_complete_quest(player, quest_id: str) -> bool`
  - `complete_quest(player, quest_id: str) -> Tuple[bool, str, Dict]` (成功フラグ, メッセージ, 報酬)
- 検証: `python -c "from guild_quest_system import GuildQuestManager; m=GuildQuestManager(None); print('Guild quest manager created')"`
- ヒント: まずはスタブで構造を作り、後で実装を埋める

## Step 36: guild_quest_system.py GuildQuestManager.get_available_quests実装
- `guild_quest_system.py` の `GuildQuestManager.get_available_quests` を実装
- プレイヤーのギルドIDを取得し、そのギルドの指定タイプのクエストリストを取得
- ギルドに所属していない場合は空リストを返す
- 検証: `python -c "from guild_quest_system import GuildQuestManager, GuildQuestRegistry; from entity import Entity; r=GuildQuestRegistry(); r.load(); m=GuildQuestManager(r); p=Entity(); avail=m.get_available_quests(p, \"daily\"); print(f'Available daily quests: {len(avail)}')"`
- ヒント: プレイヤーがギルドに所属していない場合は早期リターンで空リスト

## Step 37: guild_quest_system.py GuildQuestManager.update_quest_progress実装
- `guild_quest_system.py` の `GuildQuestManager.update_quest_progress` を実装
- プレイヤーのguild_quest_progress[quest_id] に amount を加算（上限100などでクランプ）
- 進捗が100以上になったかどうかを返す（クエスト完了判定用）
- 検証: `python -c "from guild_quest_system import GuildQuestManager, GuildQuestRegistry; from entity import Entity; r=GuildQuestRegistry(); r.load(); m=GuildQuestManager(r); p=Entity(); p.guild_quest_progress={}; result=m.update_quest_progress(p, \"slay_goblins\", 30); print(f'Progress update result: {result}; Progress: {p.guild_quest_progress.get(\"slay_goblins\",0)}')"`
- ヒント: 進捗値は0-100の範囲で管理し、100で完了とする

## Step 38: guild_quest_system.py GuildQuestManager.can_complete_quest実装
- `guild_quest_system.py` の `GuildQuestManager.can_complete_quest` を実装
- クエストの進捗が100以上かどうかをチェック
- 必要に応じて追加要件（アイテム所持数等）もチェック可能に拡張設計
- 検証: `python -c "from guild_quest_system import GuildQuestManager, GuildQuestRegistry; from entity import Entity; r=GuildQuestRegistry(); r.load(); m=GuildQuestManager(r); p=Entity(); p.guild_quest_progress={\"slay_goblins\": 100}; print(f'Can complete slay_goblins: {m.can_complete_quest(p, \"slay_goblins\")}')"`
- ヒント: シンプルに進捗 >= 100 で完了と判定

## Step 39: guild_quest_system.py GuildQuestManager.complete_quest実装
- `guild_quest_system.py` の `GuildQuestManager.complete_quest` を実装
- 完了可能チェック → 報酬決定 → 貢献度・ゴールド・アイテム付与 → 進捗リセット（またはクエスト消去）
- 日次クエストの場合は日次リセットタイミングまで再参加不可にする設計も考慮
- 検証: `python -c "from guild_quest_system import GuildQuestManager, GuildQuestRegistry; from entity import Entity; r=GuildQuestRegistry(); r.load(); m=GuildQuestManager(r); p=Entity(); p.guild_quest_progress={\"slay_goblins\": 100}; p.gold=0; result,msg,reward=m.complete_quest(p, \"slay_goblins\"); print(f'Complete result: {result}, {msg}'); print(f'Gold after: {p.gold}'); print(f'Progress after: {p.guild_quest_progress.get(\"slay_goblins\",0)}')"`
- ヒント: 報酬はクエストデータから取得し、プレイヤーに適用（item付与はinventoryシステムと連携が必要だが、ここでは簡易版）

## Step 40: game.py _on_killメソッドギルドクエスト進捗追加
- `game.py` の `_on_kill` メソッドに、モンスター撃破時のギルドクエスト進捗更新ロジックを追加
- プレイヤーがギルドに所属している場合、倒したモンスター名に応じたクエスト進捗を更新
- 例: ゴブリンを倒したら「slay_goblins」クエストの進捗を+1
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); on_kill=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_on_kill'][0]; print(f'_on_kill has guild quest logic: {\"guild_quest_progress\" in ast.dump(on_kill)}')"`
- ヒント: まずは特定モンスター（ゴブリン等）のハードコーディングから始め、後でデータ駆動にする

## Step 41: game.py advance_worldメソッドギルドクエスト日次リセットチェック追加
- `game.py` の `advance_world` メソッドに、一定間隔（例: 1日）でのギルドクエスト日次リセットチェックを追加
- 日が変わったら、プレイヤーの日次クエスト進捗をリセット
- 週次クエストについては週単位で同様の処理
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); advance=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='advance_world'][0]; print(f'advance_world has daily reset logic: {\"day\" in ast.dump(advance) and \"reset\" in ast.dump(advance)}')"`
- ヒント: ターンベースで日数を管理し、特定ターン数でリセット（例: 1000ターン = 1日）

## Step 42: data/guild_rewards.yaml 基本構造作成
- ファイル `data/guild_rewards.yaml` を作成し、基本的なYAML構造を定義
- ギルド報酬のトップレベルキー `guild_rewards:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guild_rewards.yaml', encoding='utf-8')); print('OK' if data and 'guild_rewards' in data else 'ERROR')"`
- ヒント: これまでのYAMLファイルと同様のパターン

## Step 43: data/guild_rewards.yaml 冒険者ギルドランク報酬追加
- `data/guild_rewards.yaml` に「冒険者ギルド」のランク報酬構造を追加
- adventurers_guild の下に rank_rewards: を作成
- 各ランク（novice, member, veteran, officer, leader）の報酬リストを定義
- 例: memberランクでは title:"guild_novice" と skill_unlock:"guild_training"
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guild_rewards.yaml', encoding='utf-8')); ar=data.get('guild_rewards',{}).get('adventurers_guild',{}); rr=ar.get('rank_rewards',{}) if ar else {}; member_rr=rr.get('member',[]) if rr else []; print(f'Member rewards: {member_rr}'); print('Has title reward' if any(r.get('type')=='title' for r in member_rr) else 'Missing title reward')"`
- ヒント: ランクごとに報酬リストがあるネスト構造に注意

## Step 44: data/guild_rewards.yaml 各ランク報酬詳細追加
- 各ランク（member, veteran, officer, leader）の報酬を詳細に定義
- member: タイトルとスキルアンロック
- veteran: タイトルとステータスボーナス(strength+2, agility+2)
- officer: エクスクルーシブスキルと施設アンロック(private_vault)
- leader: （後でランキング報酬と統合するためここでは基本的な報酬のみ）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guild_rewards.yaml', encoding='utf-8')); ar=data.get('guild_rewards',{}).get('adventurers_guild',{}); rr=ar.get('rank_rewards',{}) if ar else {}; vet_rr=rr.get('veteran',[]) if rr else []; print(f'Veteran rewards count: {len(vet_rr)}'); print('Has stat bonus' if any(r.get('type')=='stat_bonus' for r in vet_rr) else 'Missing stat bonus')"`
- ヒント: ステータスボーナスは辞書形式でvalueを指定（例: value: {strength: 2, agility: 2}）

## Step 45: data/guild_rewards.yaml ランキング報酬追加準備
- 「冒険者ギルド」に leaderboard_rewards: を追加（構造のみまたはプレースホルダー）
- 後で実際のランキング報酬データを追加しやすくするため
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guild_rewards.yaml', encoding='utf-8')); ar=data.get('guild_rewards',{}).get('adventurers_guild',{}); lb=ar.get('leaderboard_rewards',[]) if ar else []; print(f'Leaderboard rewards: {lb}'); print('Leaderboard rewards prepared')"`
- ヒント: ここは後で実際のランキング報酬を追加する場所として準備

## Step 46: guild_system.py ギルド報酬マネージャー追加準備
- `guild_system.py` の `GuildManager` クラスに、ギルド報酬関連メソッドのスタブを追加
- `check_rank_up(player) -> Optional[str]` (新しいランクIDまたはNone)
- `apply_rank_rewards(player, new_rank: str) -> None`
- `get_leaderboard_rewards() -> List[Dict]` (ランキング報酬取得)
- 検証: `python -c "from guild_system import GuildManager; m=GuildManager(None); print('Extended manager created')"`
- ヒント: 既存のGuildManagerにメソッドを追加していく形で実装

## Step 47: guild_system.py ギルドランクアップチェック実装
- `guild_system.py` の `GuildManager.check_rank_up` を実装
- プレイヤーの現在のギルドと貢献度を取得
- ギルドデータのrank_requirementsを参照して、満たしている最高ランクを返す
- 現在のランクと同じか低い場合はNoneを返す（ランクアップのみを対象）
- 検証: `python -c "from guild_system import GuildManager, GuildRegistry; from entity import Entity; r=GuildRegistry(); r.load(); m=GuildManager(r); p=Entity(); p.guild_id='adventurers_guild'; p.guild_contribution=150; new_rank=m.check_rank_up(p); print(f'Rank up to: {new_rank}')"`
- ヒント: 現在のランクよりも高いランクのみを返すように実装（昇格のみ対象）

## Step 48: guild_system.py ギルド報酬適用実装
- `guild_system.py` の `GuildManager.apply_rank_rewards` を実装
- 新しいランクの報酬リストを取得し、各報酬を適用
- 報酬タイプごとに分岐処理:
  - title: title_system.pyを使ってタイトル付与（後で実装）
  - skill_unlock: プレイヤーがスキルを習得可能にする（スキルツリーシステムと連携）
  - stat_bonus: 一時的または永続的なステータスボーナスを適用（recalculate_statsと連携）
  - exclusive_skill: エクスクルーシブスキル習得を許可（後で実装）
  - facility_unlock: 特定施設の利用を許可（後で実装）
- 検証: `python -c "from guild_system import GuildManager, GuildRegistry; from entity import Entity; r=GuildRegistry(); r.load(); m=GuildManager(r); p=Entity(); p.guild_id='adventurers_guild'; p.guild_rank='member'; m.apply_rank_rewards(p, \"veteran\"); print(f'Applied veteran rewards (check stats)')"`
- ヒント: まずはタイトル付与とステータスボーナスから実装し、後で他の報酬タイプを追加

## Step 49: data/faction_war.yaml 基本構造作成（派閥抗争用）
- ファイル `data/faction_war.yaml` を作成し、基本的なYAML構造を定義
- 派閥抗争のトップレベルキー `faction_war_conditions:` を追加（提案通りの名前に変更）
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/faction_war.yaml', encoding='utf-8')); print('OK' if data and 'faction_war_conditions' in data else 'ERROR')"`
- ヒント: 提案名と実際のファイル名を合わせるため調整

## Step 50: data/faction_war.yaml ガルド王国抗争条件追加
- `data/faction_war.yaml` に「ガルド王国」の抗争条件を追加
- 影響力、同盟派閥、ライバル派閥を参照しやすい構造で定義
- 実際の抗争ロジックではこれらのデータを使用して影響力変動を計算
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/faction_war.yaml', encoding='utf-8')); fw=data.get('faction_war_conditions',{}).get('kingdom_garde',{}); print(f'Faction war data for kingdom_garde: {fw is not None}'); print(f'Influence: {fw.get(\"influence\",0) if fw else \"Missing\"}')"`
- ヒント: 影響力値などの数値データを含める

## Step 51: data/faction_war.yaml 他派閥抗争条件追加
- 「ルミエスト教会」と「シャドウハンド」の抗争条件を同様に追加
- 各派閥の影響力・同盟・ライバル関係を定義
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/faction_war.yaml', encoding='utf-8')); fw=data.get('faction_war_conditions',{}); print(f'Factions with war data: {list(fw.keys())}')"`
- ヒント: 3つの派閥すべてにデータがあることを確認

## Step 52: faction_war_system.py 新規ファイル作成
- 新規ファイル `faction_war_system.py` を作成
- 基本的なファイルヘッダーとモジュール docstring を追加
- 検証: `python -c "print('File exists' if open('faction_war_system.py').readline().strip() else 'Empty or missing')"`
- ヒント: これまでの_*_system.pyファイルと同様の構造

## Step 53: faction_war_system.py FactionWarDataクラス定義
- `faction_war_system.py` に `@dataclass` デコレータ付きの `FactionWarData` クラスを定義
- フィールド: id, name, color (List[int]), territories (List[str]), allied_factions (List[str]), rival_factions (List[str]), influence (int)
- 検証: `python -c "from faction_war_system import FactionWarData; f=FactionWarData('test','Test Faction',[0,0,0],['t1'],['a1'],['r1'],50); print(f'Faction: {f.name} influence:{f.influence}')"`
- ヒント: 色はRGBの3要素リスト、リストフィールドには適切なタイプヒント

## Step 54: faction_war_system.py FactionWarRegistryクラス作成
- `faction_war_system.py` に `FactionWarRegistry` クラスを作成（シングルトンパターン）
- `__new__` メソッドと `load(path: str = "data/faction_war.yaml")` メソッドのスタブ
- `all()` と `get(faction_id: str)` アクセッサーのスタブ
- 検証: `python -c "from faction_war_system import FactionWarRegistry; r=FactionWarRegistry(); r2=FactionWarRegistry(); print(f'Same instance: {r is r2}'); print('Faction war registry created')"`
- ヒント: 今まで作ってきたレジストリパターンをコピペして名前を変えるだけ

## Step 55: faction_war_system.py FactionWarRegistry.load()実装
- `faction_war_system.py` の `FactionWarRegistry.load()` メソッドを実装
- YAMLファイルを読み込み、faction_war_conditionsキーのデータをパースして内部辞書に格納
- エラーハンドリング（ファイルがない場合は空で開始）を追加
- 検証: `python -c "from faction_war_system import FactionWarRegistry; r=FactionWarRegistry(); r.load(); print(f'Loaded {len(r.all())} faction war configs')"`
- ヒント: エラーハンドリングを忘れずに

## Step 56: faction_war_system.py FactionWarManagerクラス作成
- `faction_war_system.py` に `FactionWarManager` クラスを作成
- `__init__` で registry 参照を保持
- 主要メソッドのスタブを作成:
  - `calculate_influence_change(faction_id: str, game_state: Any) -> int` (影響力変動量計算)
  - `check_war_conditions(faction1_id: str, faction2_id: str) -> bool` (抗争発生条件チェック)
  - `apply_influence_effects(faction_id: str, change: int) -> None` (影響力変動適用)
- 検証: `python -c "from faction_war_system import FactionWarManager; m=FactionWarManager(None); print('Faction war manager created')"`
- ヒント: まずはスタブで構造を作り、後で実装を埋める

## Step 57: faction_war_system.py FactionWarManager.calculate_influence_change実装
- `faction_war_system.py` の `FactionWarManager.calculate_influence_change` を実装
- 基本的な影響力変動ロジック:
  - 時間経過による自然回復/減衰
  - 同盟派閥の成功によるプラス影響
  - ライバル派閥の成功によるマイナス影響
  - 領土支配状況によるボーナス/ペナルティ
- ゲーム状態から必要情報を取得して計算（プレーヤーの行動等も考慮に入れる余地を残す）
- 検証: `python -c "from faction_war_system import FactionWarManager, FactionWarRegistry; r=FactionWarRegistry(); r.load(); m=FactionWarManager(r); change=m.calculate_influence_change('kingdom_garde', None); print(f'Influence change for kingdom_garde: {change}')"`
- ヒント: 最初は固定値または簡易的な計算から始め、後でデータ駆動・状況依存の計算に発展

## Step 58: faction_war_system.py FactionWarManager.check_war_conditions実装
- `faction_war_system.py` の `FactionWarManager.check_war_conditions` を実装
- 2つの派閥の間で抗争が発生する条件をチェック
- 条件例:
  - 互いがライバル関係にあるか
  - 両方の影響力が一定以上か
  - 領土紛争があるか（共有領土または隣接領土）
  - 最近の挑発行動があるか（プレイヤーが一方を助けて他方を害した等）
- 検証: `python -c "from faction_war_system import FactionWarManager, FactionWarRegistry; r=FactionWarRegistry(); r.load(); m=FactionWarManager(r); can_war=m.check_war_conditions('kingdom_garde', 'shadow_hand'); print(f'Can war between kingdom_garde and shadow_hand: {can_war}')"`
- ヒント: 現時点ではライバル関係チェックのみを実装し、後で他の条件を追加

## Step 59: map_engine.py 描画時に派閥色でタイルを着色追加準備
- `map_engine.py` のマップ描画関数を修準備（派閥色着色のためのフックポイント作成）
- 現在のタイル描画ロジックを確認し、派閥に応じた色調整ポイントを作る
- 検証: `python -c "import ast; tree=ast.parse(open('map_engine.py').read()); print(f'map_engine.py lines: {len(tree.body)}')"`
- ヒント: まずはファイルが読めることを確認

## Step 60: map_engine.py 描画時に派閥色でタイルを着色追加
- `map_engine.py` のマップ描画に派閥色によるタイル着色ロジックを追加
- タイルの所属派閥を参照し、対応する色で少し色調整（例: ブレンドまたはオーバーレイ）
- 派閥が設定されていないタイルは通常の色で描画
- 検証: `python -c "import ast; tree=ast.parse(open('map_engine.py').read()); render_funcs=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and 'render' in n.name.lower()]; print(f'Found render functions: {[f.name for f in render_funcs]}')"`
- ヒント: 既存の描画ロジックに色調整コードを追加する形で実装

## Step 61: entity.py ファクション評判フィールド追加確認
- ステップ13で追加したfaction_reputationフィールドが正しく定義されているか最終確認
- 必要に応じて修正（タイポ修正など）
- 検証: `python -c "import ast; tree=ast.parse(open('entity.py').read()); cls=[n for n in ast.walk(tree) if isinstance(n,ast.ClassDef) and n.name=='Entity'][0]; fields=[n.note for n in cls.body if isinstance(n,ast.AnnAssign)]; has_fr='faction_reputation' in fields; print(f'Faction reputation field correctly defined: {has_fr}')"`
- ヒント: これが派閥システムで使われるフィールドなので、正しく定義されていることを確認

## Step 62: game.py advance_worldメソッド派閥影響力変動追加
- `game.py` の `advance_world` メソッドに派閥影響力変動ロジックを追加
- 一定ターンごと（例: 100ターン）にFactionWarManagerを使って各派閥の影響力変動を計算・適用
- 影響力の変動に応じて、領土獲得/喪失イベントをトリガーする設計も考慮
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); advance=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='advance_world'][0]; print(f'advance_world has faction influence logic: {\"faction\" in ast.dump(advance) and \"influence\" in ast.dump(advance)}')"`
- ヒント: ターンベースで定期チェックを行い、変動を適用する

## Step 63: game.py _on_killメソッド派閥評判更新追加（オプション）
- `game.py` の `_on_kill` メソッドに、特定派閥に敵対的なモンスターを倒したときの評判更新ロジックを追加（オプション機能）
- 例: シャドウハンドのモンスターを倒したらルミエスト教会への評判+5
- まずはコメントアウトまたは設定可能にしておき、後でバランス調整のために有効化する
- 検証: `python -c "import ast; tree=ast.parse(open('game.py').read()); on_kill=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_on_kill'][0]; print(f'_on_kill has faction rep logic: {\"faction_reputation\" in ast.dump(on_kill)}')"`
- ヒント: まずは実装せず、後でバランス調整のためにオプションとして残すか、簡易的な実装から始める

## Step 64: data/guild_skills.yaml 基本構造作成
- ファイル `data/guild_skills.yaml` を作成し、基本的なYAML構造を定義
- ギルドスキルのトップレベルキー `guild_skills:` を追加
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guild_skills.yaml', encoding='utf-8')); print('OK' if data and 'guild_skills' in data else 'ERROR')"`
- ヒント: これまでのYAMLファイルと同様のパターン

## Step 65: data/guild_skills.yaml 冒険者ギルドスキルロック条件追加
- `data/guild_skills.yaml` に「冒険者ギルド」のスキル構造を追加
- unlock_conditions: を作成し、ギルドレベル必要数を設定（例: guild_level: 2）
- skills: リストを作成し、 guildスキルオブジェクトを格納
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guild_skills.yaml', encoding='utf-8')); ag=data.get('guild_skills',{}).get('adventurers_guild',{}); uc=ag.get('unlock_conditions',{}) if ag else {}; print(f'Unlock conditions: {uc}'); print('Requires guild level 2' if uc.get('guild_level')==2 else 'Missing or incorrect guild level requirement')"`
- ヒント: ギルドレベルは別途トラッキングが必要（ギルド自身のレベル概念）

## Step 66: data/guild_skills.yaml ギルドスキル詳細定義（ギルドの知識）
- 「冒険者ギルド」のスキルリストに「ギルドの知識」を追加
- id: "guild_lore", name: "ギルドの知識", type: "passive"
- effects: 経験値ボーナス15% (type: "exp_bonus", value: 0.15, target: "all")
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guild_skills.yaml', encoding='utf-8')); ag=data.get('guild_skills',{}).get('adventurers_guild',{}); skills=ag.get('skills',[]) if ag else []; lore=[s for s in skills if s.get('id')=='guild_lore']; print(f'Found guild_lore: {len(lore)>0}'); print(f'Exp bonus 0.15' if lore and lore[0].get('effects',[{}])[0].get('value')==0.15 else 'Missing or incorrect value')"`
- ヒント: エフェクトはリストなので、インデックスアクセスに注意

## Step 67: data/guild_skills.yaml ギルドスキル詳細定義（ギルドの財宝・ネットワーク）
- 「冒険者ギルド」のスキルリストに残りの2つを追加
- 「ギルドの財宝」: 倉庫容量+50, 腐敗抵抗+0.2
- 「ギルドのネットワーク」: アクティブスキル、コスト10, クールダウン600(10分), リモートストレージアクセス
- 検証: `python -c "import yaml; data = yaml.safe_load(open('data/guild_skills.yaml', encoding='utf-8')); ag=data.get('guild_skills',{}).get('adventurers_guild',{}); skills=ag.get('skills',[]) if ag else []; ids=[s.get('id') for s in skills]; print(f'Skill IDs: {ids}'); print('Has all three skills' if len([i for i in ['guild_lore','guild_storage','guild_network'] if i in ids])==3 else 'Missing some skills')"`
- ヒント: 3つのスキルすべてが定義されていることを確認

## Step 68: guild_skill_system.py 新規ファイル作成
- 新規ファイル `guild_skill_system.py` を作成
- 基本的なファイルヘッダーとモジュール docstring を追加
- 検証: `python -c "print('File exists' if open('guild_skill_system.py').readline().strip() else 'Empty or missing')"`
- ヒント: これまでの_*_system.pyファイルと同様の構造

## Step 69: guild_skill_system.py GuildSkillDataクラス定義
- `guild_skill_system.py` に `@dataclass` デコレータ付きの `GuildSkillData` クラスを定義
- フィールド: id, name, description, type (str: "active"/"passive"), cost (int), cooldown (int), effects (List[Dict])
- 必要に応じて追加フィールド（アイコン等）を定義しても良い
- 検証: `python -c "from guild_skill_system import GuildSkillData; s=GuildSkillData('test','Test Skill','Desc','passive',0,0,[]); print(f'Skill: {s.name} type:{s.type}')"`
- ヒント: active/passiveタイプで処理を分ける設計

## Step 70: guild_skill_system.py GuildSkillRegistryクラス作成
- `guild_skill_system.py` に `GuildSkillRegistry` クラスを作成（シングルトンパターン）
- `__new__` メソッドと `load(path: str = "data/guild_skills.yaml")` メソッドのスタブ
- `all()` と `get(guild_id: str)` アクセッサーのスタブ（ギルドIDごとにスキルを取得）
- 検証: `python -c "from guild_skill_system import GuildSkillRegistry; r=GuildSkillRegistry(); r2=GuildSkillRegistry(); print(f'Same instance: {r is r2}'); print('Guild skill registry created')"`
- ヒント: ギルドIDごとにスキルリストを返す構造を想定

## Step 71: guild_skill_system.py GuildSkillRegistry.load()実装
- `guild_skill_system.py` の `GuildSkillRegistry.load()` メソッドを実装
- YAMLファイルを読み込み、guild_skillsキーのデータをパースして内部辞書に格納
- エラーハンドリング（ファイルがない場合は空で開始）を追加
- 検証: `python -c "from guild_skill_system import GuildSkillRegistry; r=GuildSkillRegistry(); r.load(); print(f'Loaded skills for {len(r.all())} guilds')"`
- ヒント: エラーハンドリングを忘れずに

## Step 72: guild_skill_system.py GuildSkillManagerクラス作成・基本実装
- `guild_skill_system.py` に `GuildSkillManager` クラスを作成
- `__init__` で registry 参照を保持
- 主要メソッドのスタブを作成:
  - `get_available_skills(guild_id: str) -> List[GuildSkillData]` (ギルドが習得可能なスキルリスト)
  - `is_skill_active(player, skill_id: str) -> bool` (スキルが現在有効かどうか)
  - `apply_skill_effects(player, skill_data: GuildSkillData) -> None` (スキル効果をプレイヤーに適用)
- 検証: `python -c "from guild_skill_system import GuildSkillManager; m=GuildSkillManager(None); print('Guild skill manager created')"`
- ヒント: これでステップ72完了。実際の実装は後続のステップで行われる想定。

---
**注意:** この実装計画書は72ステップに分割されていますが、実際の開発では一部のステップを並行して進めたり、依存関係に応じて順序を調整したりすることができます。各ステップは小さな変更単位となっているため、低性能なLLMでも一つずつ確実に実装していくことが可能です。