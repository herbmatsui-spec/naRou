# 街（ハブ拠点）構築・動的町状態 詳細実装計画書
低性能なLLMでも実装可能なように 1～72 までの小さなステップに分割

## 目標概要
1. 既存の `SlumBaseExpansionManager`（スラム拠点拡張）を**訪問可能なマップ**にし、ショップ／ギルド（guilds.yaml）／酒場を配置。拡張レベル（Tier）で店が増え、世界の成長を体感できる。
2. `factions.yaml` / `faction_events.yaml` / `world_events.yaml` を `world_state.yaml` 経由で街の**見た目・NPCの態度・商品**に反映。勢力の消長で「今週はオーク街が封鎖されている」が起きる。

## 既存資産（再利用）
- `skill_eater_base_expansion.py:9` `SlumBaseExpansionManager`（Tier1-3、unlocked_merchants 等）
- `map_engine.py:511` `GameMap.generate_town()`（外壁＋床＋3棟建物）
- `data/factions.yaml`（kingdom_garde / church_of_lumiest / shadow_hand、influence、territories）
- `data/faction_events.yaml`、`data/world_events.yaml`
- `data/world_state.yaml`（template: location_states / faction_relations / global_events）
- `packages/world_a/package.py:119`（slum_base_expansion_manager 登録済み）

---

## Phase 1: ハブ拠点データの下地（Steps 1-12）

## Step 1: data/hub_town.yaml 基本構造作成
- ファイル `data/hub_town.yaml` を作成し、トップレベルキー `hub_town:` を定義
- 検証: `python -c "import yaml; d=yaml.safe_load(open('data/hub_town.yaml',encoding='utf-8')); print('OK' if d and 'hub_town' in d else 'ERROR')"`
- ヒント: 空の構造から始める。既存の `data/guilds.yaml` と同パターン。

## Step 2: data/hub_town.yaml 街基本情報追加
- `hub_town:` 配下に `town_name: "ネオン・スラム地下街"`, `base_location: "slum"`, `default_tier: 1` を追加
- 検証: `python -c "import yaml; d=yaml.safe_load(open('data/hub_town.yaml',encoding='utf-8')); h=d['hub_town']; print(h.get('town_name'), h.get('default_tier'))"`
- ヒント: SlumBaseExpansionManager の `tier_names` 表記と揃える。

## Step 3: data/hub_town.yaml 建物スロット定義（ショップ）
- `hub_town:` 配下に `buildings:` リストを作り、1件目 `shop_general`（type: shop）を追加
- 検証: `python -c "import yaml; d=yaml.safe_load(open('data/hub_town.yaml',encoding='utf-8')); b=d['hub_town']['buildings']; print(b[0]['id'], b[0]['type'])"`
- ヒント: 各建物は `id/type/name/required_tier` を持つ構造にする。

## Step 4: data/hub_town.yaml ギルドホール建物追加
- `buildings:` に `guild_hall`（type: guild, guild_id: adventurers_guild, required_tier: 1）を追加
- 検証: `python -c "import yaml; d=yaml.safe_load(open('data/hub_town.yaml',encoding='utf-8')); g=[x for x in d['hub_town']['buildings'] if x['type']=='guild'][0]; print(g['guild_id'])"`
- ヒント: `guild_id` は `data/guilds.yaml` のキーと一致させる。

## Step 5: data/hub_town.yaml 酒場建物追加
- `buildings:` に `tavern`（type: tavern, required_tier: 1）を追加
- 検証: `python -c "import yaml; d=yaml.safe_load(open('data/hub_town.yaml',encoding='utf-8')); t=[x for x in d['hub_town']['buildings'] if x['type']=='tavern']; print('tavern OK' if t else 'ERROR')"`
- ヒント: 酒場は噂（faction rumor）とクエストボードの入口とする。

## Step 6: data/hub_town.yaml 拡張Tier別建物マッピング追加
- `hub_town:` 配下に `tier_building_unlocks:` を追加。`2:` に shop_blackmarket、`3:` に shop_legendary をリストで記述
- 検証: `python -c "import yaml; d=yaml.safe_load(open('data/hub_town.yaml',encoding='utf-8')); u=d['hub_town']['tier_building_unlocks']; print(u.get('2'), u.get('3'))"`
- ヒント: Tier上昇で店が増える仕組みのデータ側定義。

## Step 7: entity.py 街訪問・対話用フィールド追加
- `entity.py` の Entity に `current_town: Optional[str] = None` と `interacting_building: Optional[str] = None` を追加
- 検証: `python -c "import ast; t=ast.parse(open('entity.py').read()); c=[n for n in ast.walk(t) if isinstance(n,ast.ClassDef) and n.name=='Entity'][0]; f=[n.targets[0].id for n in c.body if isinstance(n,ast.Assign)] if False else [n.target.id if isinstance(n,ast.AnnAssign) else None for n in c.body]; print('current_town' in [x for x in f if x], 'interacting_building' in [x for x in f if x])"`
- ヒント: dataclass なら `field(default=None)`、そうでなければ `__init__` で初期化。

## Step 8: entity.py 訪問済み街フラグ追加
- Entity に `visited_towns: List[str] = field(default_factory=list)` を追加
- 検証: `python -c "import ast; t=ast.parse(open('entity.py').read()); c=[n for n in ast.walk(t) if isinstance(n,ast.ClassDef) and n.name=='Entity'][0]; print('visited_towns' in [n.target.id if isinstance(n,ast.AnnAssign) else None for n in c.body])"`
- ヒント: faction_reputation と同様に `field(default_factory=list)` を使う。

## Step 9: data/world_state.yaml 町状態セクション追加（テンプレ）
- `world_state_template:` 配下に `town_states:` を追加。`slum:` に `controlled_faction: null`, `blocked_districts: []`, `prosperity: 50` を置く
- 検証: `python -c "import yaml; d=yaml.safe_load(open('data/world_state.yaml',encoding='utf-8')); ts=d['world_state_template']['town_states']['slum']; print(ts['prosperity'])"`
- ヒント: location_states と同階層に置く。

## Step 10: data/world_state.yaml 地区（district）別勢力管理追加
- `town_states.slum:` に `districts:` を追加。`orc_street: {controlled_faction: shadow_hand, blocked: false}` など 2-3 地区を定義
- 検証: `python -c "import yaml; d=yaml.safe_load(open('data/world_state.yaml',encoding='utf-8')); ds=d['world_state_template']['town_states']['slum']['districts']; print(list(ds.keys()))"`
- ヒント: 「オーク街が封鎖」は `districts.ork_street.blocked` で表現する。

## Step 11: data/hub_town.yaml 拡張レベルで建物数増加の設定確定
- `tier_building_unlocks:` に Tier1 の基本 3 棟（shop_general, guild_hall, tavern）も明示的に列挙し、Tierごとの総数をコメントで記述
- 検証: `python -c "import yaml; d=yaml.safe_load(open('data/hub_town.yaml',encoding='utf-8')); print('tier1' in d['hub_town'].get('tier_building_unlocks',{}))"`
- ヒント: データの整合性確認ステップ。

## Step 12: 全YAMLロード一括検証
- `hub_town.yaml` / `factions.yaml` / `faction_events.yaml` / `world_events.yaml` / `world_state.yaml` をまとめてロードしエラーがないことを確認
- 検証: `python -c "import yaml; [yaml.safe_load(open(f,encoding='utf-8')) for f in ['data/hub_town.yaml','data/factions.yaml','data/faction_events.yaml','data/world_events.yaml','data/world_state.yaml']]; print('ALL YAML OK')"`
- ヒント: インデント崩れをここで検出。

---

## Phase 2: ハブ拠点マップ生成と建物配置（Steps 13-30）

## Step 13: hub_town_manager.py 新規ファイル作成
- 新規ファイル `hub_town_manager.py` を作成し、モジュール docstring を追加
- 検証: `python -c "print('File exists' if open('hub_town_manager.py').readline().strip() else 'Empty')"`
- ヒント: 既存の `skill_eater_base_expansion.py` と同スタイル。

## Step 14: hub_town_manager.py HubTownData データクラス定義
- `@dataclass` の `HubTownData` を定義。フィールド: `town_id`, `town_name`, `tier`, `buildings: List[Dict]`, `districts: Dict[str,Dict]`
- 検証: `python -c "from hub_town_manager import HubTownData; h=HubTownData('slum','S',1,[],{}); print(h.town_name, h.tier)"`
- ヒント: SlumBaseExpansionManager の状態を受け取る入れ物。

## Step 15: hub_town_manager.py HubTownManager クラス作成（スタブ）
- `HubTownManager` クラスを作成。`__init__` で `slum_mgr` 参照を保持。主要メソッドのスタブを置く
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); print('manager created')"`
- ヒント: まずはスタブで骨組み。

## Step 16: hub_town_manager.py load() 実装
- `load(path='data/hub_town.yaml')` を実装。YAML を読み `hub_town` キーを `HubTownData` に変換して保持（FileNotFoundError 時は空で開始）
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); print('loaded', m.data.town_id if m.data else 'none')"`
- ヒント: エラーハンドリング必須。

## Step 17: map_engine.py generate_town に建物リスト受け取りを追加
- `generate_town(self, buildings=None)` の引数を追加。渡された建物ごとに RectRoom を生成し `self.building_tiles` に (rect, building_id) を記録
- 検証: `python -c "import ast; t=ast.parse(open('map_engine.py').read()); f=[n for n in ast.walk(t) if isinstance(n,ast.FunctionDef) and n.name=='generate_town'][0]; print('has buildings param' if any(a.arg=='buildings' for a in f.args.args) else 'no')"`
- ヒント: 既存の 3 棟ハードコードを building リストから生成する形に置換。

## Step 18: hub_town_manager.py generate_hub_map() 実装
- `HubTownManager.generate_hub_map(self) -> GameMap` を実装。`GameMap(...)` を作り `generate_town(buildings)` を呼ぶ。Tier に応じ建物を `tier_building_unlocks` から選定
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); gm=m.generate_hub_map(); print('map_type', gm.map_type)"`
- ヒント: `from map_engine import GameMap` を import。

## Step 19: 建物タイル配置（ショップ）
- Tier1 の `shop_general` をマップ上の建物スロットに配置し、扉タイルを `TILE_FLOOR` にする
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); gm=m.generate_hub_map(); print('building_tiles count', len(gm.building_tiles))"`
- ヒント: Step17 の `building_tiles` が埋まるか確認。

## Step 20: 建物タイル配置（ギルドホール・酒場）
- `guild_hall` と `tavern` も同様に配置。type に応じ `interact_type` を付与
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); gm=m.generate_hub_map(); ids=[b[1] for b in gm.building_tiles]; print('guild_hall' in ids, 'tavern' in ids)"`
- ヒント: 3 棟すべて配置されることを確認。

## Step 21: 建物上判定 get_building_at() 実装
- `HubTownManager.get_building_at(self, x, y) -> Optional[Dict]` を実装。座標が建物矩形内なら該当建物を返す
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); gm=m.generate_hub_map(); bx,by=gm.building_tiles[0][0].center; print(m.get_building_at(bx,by))"`
- ヒント: RectRoom.center を利用。

## Step 22: 建物グリフ・色の定義
- `data/hub_town.yaml` の各建物に `glyph`（例: 店='$', ギルド='#', 酒場='~'）と `color`（RGBリスト）を追加
- 検証: `python -c "import yaml; d=yaml.safe_load(open('data/hub_town.yaml',encoding='utf-8')); b=d['hub_town']['buildings'][0]; print(b.get('glyph'), b.get('color'))"`
- ヒント: 描画で使う文字と色。

## Step 23: map_engine.py 建物描画（勢力色オーバーレイ準備）
- マップ描画時に `building_tiles` を通常床とは別のグリフ/色で描画するフックを追加（まだ勢力色は未適用）
- 検証: `python -c "import ast; t=ast.parse(open('map_engine.py').read()); print('render has building hook' if 'building_tiles' in ast.dump(t) else 'no')"`
- ヒント: 後で faction color をブレンドする拡張点。

## Step 24: packages/world_a/package.py へ HubTownManager 登録
- `setup()` 内で `from hub_town_manager import HubTownManager` し `kernel.register_system("hub_town_manager", HubTownManager(slum_mgr))` を追加
- 検証: `python -c "import ast; t=ast.parse(open('packages/world_a/package.py').read()); print('hub_town_manager registered' if 'hub_town_manager' in ast.dump(t) else 'no')"`
- ヒント: SlumBaseExpansionManager のインスタンスを引数に渡す。

## Step 25: 街への移動アクション（入場）
- `input_actions.py` に `enter_hub_town(engine)` を追加。player.current_town='slum' をセットし `engine.enter_town()` を呼ぶスタブ
- 検証: `python -c "import ast; t=ast.parse(open('input_actions.py').read()); print('enter_hub_town defined' if 'enter_hub_town' in ast.dump(t) else 'no')"`
- ヒント: ダンジョン内の特定タイル（拠点入口）から呼ぶ。

## Step 26: 街からの退出アクション
- `input_actions.py` に `exit_hub_town(engine)` を追加。player.current_town=None を戻し `engine.enter_dungeon()` を呼ぶスタブ
- 検証: `python -c "import ast; t=ast.parse(open('input_actions.py').read()); print('exit_hub_town defined' if 'exit_hub_town' in ast.dump(t) else 'no')"`
- ヒント: 入口タイルに戻る。

## Step 27: game.py 街状態（GameState.TOWN）追加
- `constants.GameState` に `TOWN` を追加（未存在の場合）。`engine.enter_town()` / `engine.enter_dungeon()` メソッドのスタブを追加
- 検証: `python -c "import ast; t=ast.parse(open('game.py').read()); print('enter_town defined' if 'enter_town' in ast.dump(t) else 'no')"`
- ヒント: EXPLORING と同格の状態として扱う。

## Step 28: game.py マップ切り替えロジック実装
- `enter_town()` で `state_data.game_map = hub_mgr.generate_hub_map()` を設定し `current_state=TOWN`。`enter_dungeon()` でダンジョン再生成
- 検証: `python -c "import ast; t=ast.parse(open('game.py').read()); print('game_map assigned in enter_town' if 'generate_hub_map' in ast.dump(t) else 'no')"`
- ヒント: 既存の `state_data.game_map.generate_dungeon()` パターンを参照。

## Step 29: 建物対話トリガー（重なり判定）
- `game.py` の移動処理で、移動先が `hub_mgr.get_building_at()` にヒットしたら `player.interacting_building` をセットし対話メニューを開く
- 検証: `python -c "import ast; t=ast.parse(open('game.py').read()); print('building interact' if 'interacting_building' in ast.dump(t) else 'no')"`
- ヒント: ダンジョン侵入タイルと同じ要領。

## Step 30: マップ生成統合の一括検証
- テストスクリプトで「enter_town → 建物3棟存在 → exit」が動くことを確認（最小 assert）
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); gm=m.generate_hub_map(); assert gm.map_type=='town'; assert len(gm.building_tiles)>=3; print('HUB MAP OK')"`
- ヒント: Phase 2 完了のチェックポイント。

---

## Phase 3: ショップ・ギルド・酒場と拡張成長（Steps 31-44）

## Step 31: data/hub_town.yaml ショップ商品カタログ追加
- `shop_general` に `stock:` リストを追加（item_id / price のペア、例: heal_herb: 20）
- 検証: `python -c "import yaml; d=yaml.safe_load(open('data/hub_town.yaml',encoding='utf-8')); s=[b for b in d['hub_town']['buildings'] if b['id']=='shop_general'][0]; print(s['stock'])"`
- ヒント: item_id は `data/items.yaml` と一致。

## Step 32: 商品データを items.yaml から解決するヘルパ
- `HubTownManager.resolve_item(item_id)` を実装。`data/items.yaml` を読み id から名前/価格を返す
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); print(type(m.resolve_item('heal_herb')))"`
- ヒント: items.yaml が巨大なら遅延ロード（load 時にキャッシュ）。

## Step 33: SlumBaseExpansionManager に get_available_buildings() 追加
- `skill_eater_base_expansion.py` に `get_available_buildings(self) -> List[str]` を追加。`tier_building_unlocks` を参照し現在 Tier で解放済みの建物 id を返す
- 検証: `python -c "from skill_eater_base_expansion import SlumBaseExpansionManager; m=SlumBaseExpansionManager(); print(m.get_available_buildings()); m.invested_junk=500; m.invested_skill_points=5; m.check_and_update_tier(); print('tier', m.base_tier, m.get_available_buildings())"`
- ヒント: hub_town_manager から呼び出す。

## Step 34: Tier上昇で店が増えるマップ生成
- `generate_hub_map()` で `slum_mgr.get_available_buildings()` のみを建物リストに含めるよう修正
- 検証: `python -c "from hub_town_manager import HubTownManager; from skill_eater_base_expansion import SlumBaseExpansionManager; s=SlumBaseExpansionManager(); s.invested_junk=2000; s.invested_skill_points=20; s.check_and_update_tier(); m=HubTownManager(s); m.load(); gm=m.generate_hub_map(); print(len(gm.building_tiles))"`
- ヒント: Tier3 で建物数が増えることを確認。

## Step 35: ショップUI（メニュー表示）
- `HubTownManager.render_shop(self, building) -> Dict` を実装。stock 一覧と価格を辞書で返す
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); b=m.data.buildings[0]; print('items', len(m.render_shop(b).get('stock',[])))"`
- ヒント: UI 層は後で tcod/テキスト描画へ渡す。

## Step 36: ショップ購入処理
- `HubTownManager.buy_item(self, player, item_id) -> Dict` を実装。ゴールド確認→ inventory 追加→ ゴールド減算
- 検証: `python -c "from hub_town_manager import HubTownManager; from entity import Entity; m=HubTownManager(None); m.load(); p=Entity(); p.gold=100; r=m.buy_item(p,'heal_herb'); print(r['success'], p.gold)"`
- ヒント: inventory は `item_system.Inventory` を想定。

## Step 37: ショップ売却処理
- `HubTownManager.sell_item(self, player, item_id) -> Dict` を実装。所持品から削除→ ゴールド加算（買値の半額等）
- 検証: `python -c "from hub_town_manager import HubTownManager; from entity import Entity; m=HubTownManager(None); m.load(); p=Entity(); p.gold=0; r=m.sell_item(p,'heal_herb'); print(r['success'])"`
- ヒント: 持っていない場合は失敗を返す。

## Step 38: 物価の町繁栄度連動
- `buy_item`/`sell_item` の価格に `world_state.town_states[slum].prosperity` を乗じる（繁栄度↑で売却高↑など）
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); print('prosperity factor', m.price_factor(50))"`
- ヒント: `price_factor(prosperity)` ヘルパを作る。

## Step 39: ギルドホールUI
- `HubTownManager.render_guild_hall(self, building) -> Dict` を実装。`guild_id` から `data/guilds.yaml` の info を返す
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); b=[x for x in m.data.buildings if x['type']=='guild'][0]; print(m.render_guild_hall(b).get('name'))"`
- ヒント: 既存の GuildRegistry があればそれを使う。

## Step 40: 酒場UI（噂・クエストボード）
- `HubTownManager.render_tavern(self, building) -> Dict` を実装。`rumors`（faction 噂）と `quest_board`（guild_quests 参照）を返す
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); b=[x for x in m.data.buildings if x['type']=='tavern'][0]; print(m.render_tavern(b).keys())"`
- ヒント: 噂テキストは Step41 で faction 反映。

## Step 41: 酒場の噂テキスト生成（勢力反映）
- `HubTownManager.generate_rumors(self, world_state) -> List[str]` を実装。勢力 influence と district.blocked から噂文を生成
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); print(m.generate_rumors(None))"`
- ヒント: 「今週はオーク街が封鎖されている」はここで作る（Step58 で接続）。

## Step 42: Tierでショップ在庫が増える
- `render_shop` で Tier に応じ stock 数を増やす（Tier1: 基本、Tier3: レア枠追加）
- 検証: `python -c "from hub_town_manager import HubTownManager; from skill_eater_base_expansion import SlumBaseExpansionManager; s=SlumBaseExpansionManager(); m=HubTownManager(s); m.load(); print('tier1 stock', len(m.render_shop(m.data.buildings[0])['stock']))"`
- ヒント: 成長実感の核心。

## Step 43: 購入フロー統合検証
- `enter_town → shop_general で buy → inventory 増 → gold 減` の最小アサーション
- 検証: `python -c "from hub_town_manager import HubTownManager; from entity import Entity; m=HubTownManager(None); m.load(); p=Entity(); p.gold=999; b=m.data.buildings[0]; r=m.buy_item(p,'heal_herb'); assert r['success']; print('SHOP OK', p.gold)"`
- ヒント: Phase 3 中間チェック。

## Step 44: 街訪問ループ一括検証
- Tier1/Tier3 それぞれで建物数・ショップ購入が期待通りか一括 assert
- 検証: `python -c "import yaml; d=yaml.safe_load(open('data/hub_town.yaml',encoding='utf-8')); print('tier unlocks', d['hub_town']['tier_building_unlocks'])"`
- ヒント: Phase 3 完了。

---

## Phase 4: 動的町状態（勢力・政治）（Steps 45-60）

## Step 45: data/world_state.yaml 地区勢力制御フィールド拡充
- `town_states.slum.districts` に `controlled_faction` と `blocked` と `blocked_until_turn` を追加
- 検証: `python -c "import yaml; d=yaml.safe_load(open('data/world_state.yaml',encoding='utf-8')); ds=d['world_state_template']['town_states']['slum']['districts']; print(all('blocked' in v for v in ds.values()))"`
- ヒント: 封鎖期限で自動解除する設計の下地。

## Step 46: faction_manager から influence を取得するフック
- `managers/faction_manager.py` に `get_faction_influence(faction_id) -> int` スタブを確認/追加
- 検証: `python -c "import ast; t=ast.parse(open('managers/faction_manager.py').read()); print('get_faction_influence' in ast.dump(t))"`
- ヒント: 既存の faction 影響力計算と接続。

## Step 47: HubTownManager.load_town_state(world_state) 実装
- `load_town_state(self, world_state)` を実装。`world_state.town_states.slum` を `self.town_state` に保持
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); m.load_town_state({'town_states':{'slum':{'prosperity':60}}}); print(m.town_state['prosperity'])"`
- ヒント: GameStateData に world_state があればそこから取得。

## Step 48: 地区封鎖判定 is_district_blocked()
- `HubTownManager.is_district_blocked(self, district_id) -> bool` を実装。`blocked` または `turn < blocked_until_turn` で True
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); m.load_town_state({'town_states':{'slum':{'districts':{'orc_street':{'blocked':True}}}}}); print(m.is_district_blocked('orc_street'))"`
- ヒント: 封鎖の真偽のみ。

## Step 49: 封鎖地区の描画（バリケード）
- `map_engine.py` の建物/地区描画で `is_district_blocked` ならバリケードグリフ（'X'）と赤色で上書き
- 検証: `python -c "import ast; t=ast.parse(open('map_engine.py').read()); print('blocked render hook' if 'is_district_blocked' in ast.dump(t) or 'blocked' in ast.dump(t) else 'no')"`
- ヒント: まずはフック追加、実際の色は Step23 拡張点に統合。

## Step 50: NPC態度計算（評判＋勢力）
- `HubTownManager.npc_attitude(self, player, faction_id) -> str` を実装。`player.faction_reputation[faction_id]` と勢力 influence から friendly/neutral/hostile を返す
- 検証: `python -c "from hub_town_manager import HubTownManager; from entity import Entity; m=HubTownManager(None); p=Entity(); p.faction_reputation={'shadow_hand':80}; print(m.npc_attitude(p,'shadow_hand'))"`
- ヒント: 閾値は 50/75 等。

## Step 51: NPC対話態度バリエーション
- `HubTownManager.npc_dialogue(self, player, faction_id) -> str` を実装。attitude に応じ異なる台詞を返す
- 検証: `python -c "from hub_town_manager import HubTownManager; from entity import Entity; m=HubTownManager(None); p=Entity(); print(m.npc_dialogue(p,'kingdom_garde'))"`
- ヒント: 友好なら歓迎、敵対なら拒絶。

## Step 52: 商品の勢力制御反映
- `render_shop` で `controlled_faction` が敵対勢力なら該当商品を在庫から除外（販売不可フラグ）
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); print('shop respects faction' if hasattr(m,'render_shop') else 'no')"`
- ヒント: 封鎖地区の店は品切れ/閉店。

## Step 53: data/world_events.yaml に町イベント追加
- `world_events:` に `orc_street_blockade` を追加（trigger_conditions: turns_interval/chance、effects: town_district_blocked: orc_street）
- 検証: `python -c "import yaml; d=yaml.safe_load(open('data/world_events.yaml',encoding='utf-8')); print('orc_street_blockade' in d['world_events'])"`
- ヒント: blood_moon と同構造。

## Step 54: data/faction_events.yaml に町影響イベント追加
- `shadow_hand` に `take_over_orc_street` を追加。成功で `effects: set_district_control: {district: orc_street, faction: shadow_hand}`
- 検証: `python -c "import yaml; d=yaml.safe_load(open('data/faction_events.yaml',encoding='utf-8')); print('take_over_orc_street' in d['faction_events']['shadow_hand'])"`
- ヒント: 勢力の消長を町に反映させるトリガー。

## Step 55: イベント発火で world_state を書き換える
- イベント適用関数 `apply_town_event(world_state, event)` を `hub_town_manager.py` に追加。district.blocked / controlled_faction を更新
- 検証: `python -c "from hub_town_manager import HubTownManager; ws={'town_states':{'slum':{'districts':{'orc_street':{'blocked':False}}}}}; HubTownManager.apply_town_event(ws,{'effects':{'set_district_blocked':'orc_street'}}); print(ws['town_states']['slum']['districts']['orc_street']['blocked'])"`
- ヒント: 純関数にしてテストしやすく。

## Step 56: game.py advance_world で町状態再計算
- `advance_world()` に `hub_mgr.recompute_town_state(world_state)` 呼び出しを追加（一定ターンごとに勢力 influence を反映）
- 検証: `python -c "import ast; t=ast.parse(open('game.py').read()); print('recompute_town_state' in ast.dump(t))"`
- ヒント: 既存の `advance_world` フック（game.py:1266）に追加。

## Step 57: 週次リセット・勢力変動チック
- `HubTownManager.recompute_town_state(self, world_state)` を実装。`blocked_until_turn` を過ぎた封鎖を解除し、influence 変動を district へ反映
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); ws={'town_states':{'slum':{'districts':{'orc_street':{'blocked':True,'blocked_until_turn':0}}}}}, }; m.recompute_town_state(ws); print('unblocked', not ws['town_states']['slum']['districts']['orc_street']['blocked'])"`
- ヒント: 自動解除の確認。

## Step 58: 「今週はオーク街が封鎖されている」メッセージ生成
- `HubTownManager.town_news(world_state) -> List[str]` を実装。blocked 地区から「今週は{orc街}が封鎖されている」を生成
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); ws={'town_states':{'slum':{'districts':{'orc_street':{'blocked':True}}}}}; print(m.town_news(ws))"`
- ヒント: ユーザーが挙げた例そのもの。

## Step 59: 勢力 influence 変動の町反映検証
- influence が閾値を超えたら controlled_faction が変わるロジックを `recompute_town_state` に追加し検証
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); ws={'town_states':{'slum':{'districts':{'orc_street':{'controlled_faction':'kingdom_garde'}}}}}; m.recompute_town_state(ws, influences={'shadow_hand':90}); print(ws['town_states']['slum']['districts']['orc_street']['controlled_faction'])"`
- ヒント: 勢力の消長を体感。

## Step 60: 封鎖地区描画の統合検証
- 封鎖フラグが立った状態でマップ描画がバリケード色になることを確認（最小 assert）
- 検証: `python -c "from hub_town_manager import HubTownManager; m=HubTownManager(None); m.load(); ws={'town_states':{'slum':{'districts':{'orc_street':{'blocked':True}}}}}; m.load_town_state(ws); print('blocked render ready', m.is_district_blocked('orc_street'))"`
- ヒント: Phase 4 完了。

---

## Phase 5: 提示・統合・テスト（Steps 61-72）

## Step 61: world_news_manager に町ニュース追加
- `managers/world_news_manager.py` のニュース生成に `hub_mgr.town_news(world_state)` の結果をマージ
- 検証: `python -c "import ast; t=ast.parse(open('managers/world_news_manager.py').read()); print('town_news' in ast.dump(t))"`
- ヒント: 既存の news パイプラインに差し込む。

## Step 62: 街BGM（sound_manager の town アンビエンス）
- プレイヤーが TOWN 状態のとき `sound_manager.play_bgm('town')` を呼ぶ（既存 town アンビエンス活用）
- 検証: `python -c "import ast; t=ast.parse(open('sound_manager.py').read()); print('town' in ast.dump(t))"`
- ヒント: sound_manager.py:365 の既存分岐を利用。

## Step 63: 街ステータスUI（get_base_status_ui 拡張）
- `SlumBaseExpansionManager.get_base_status_ui()` の返値に `buildings`（現在の建物一覧）を追加
- 検証: `python -c "from skill_eater_base_expansion import SlumBaseExpansionManager; m=SlumBaseExpansionManager(); print('buildings' in m.get_base_status_ui())"`
- ヒント: 成長の見える化。

## Step 64: 街バナー（勢力名表示）
- TOWN 描画時に `controlled_faction` 名を街バナーとして表示するフックを `map_engine` / UI に追加
- 検証: `python -c "import ast; t=ast.parse(open('map_engine.py').read()); print('faction banner hook' if 'controlled_faction' in ast.dump(t) else 'no')"`
- ヒント: 势力色でバナー着色。

## Step 65: world_state 町状態の保存・読込
- `managers/persistence_manager.py` のセーブ/ロードに `town_states` を含める
- 検証: `python -c "import ast; t=ast.parse(open('managers/persistence_manager.py').read()); print('town_states' in ast.dump(t))"`
- ヒント: 既存の persistence フローに key を追加。

## Step 66: テスト hub_town 生成（tests/test_hub_town_*.py 作成）
- `tests/` に `test_hub_town_generation.py` を作成。`generate_hub_map()` で建物3棟＋Tier増で増えることを assert
- 検証: `python -m pytest tests/test_hub_town_generation.py -q`
- ヒント: 既存の `test_world_a_*.py` と同スタイル。

## Step 67: テスト ショップ売買
- `test_hub_town_shop.py` を作成。`buy_item`/`sell_item` のゴールド・inventory 変化を assert
- 検証: `python -m pytest tests/test_hub_town_shop.py -q`
- ヒント: Step43 の検証をテスト化。

## Step 68: テスト 地区封鎖
- `test_hub_town_blockade.py` を作成。`apply_town_event` / `is_district_blocked` を assert
- 検証: `python -m pytest tests/test_hub_town_blockade.py -q`
- ヒント: Step55/58 をテスト化。

## Step 69: テスト 拡張Tierで店増
- `test_hub_town_expansion.py` を作成。Tier1→Tier3 で `get_available_buildings()` 件数増を assert
- 検証: `python -m pytest tests/test_hub_town_expansion.py -q`
- ヒント: Step34 をテスト化。

## Step 70: テスト world_state 反映
- `test_hub_town_world_state.py` を作成。`recompute_town_state` で influence 変化→controlled_faction 変化を assert
- 検証: `python -m pytest tests/test_hub_town_world_state.py -q`
- ヒント: Step59 をテスト化。

## Step 71: 統合テスト（E2E）
- `test_hub_town_integration.py` を作成。「入場→買物→勢力でオーク街封鎖→該当商品購入不可」の一連を assert
- 検証: `python -m pytest tests/test_hub_town_integration.py -q`
- ヒント: すべての Phase をつなぐ総合確認。

## Step 72: 最終 lint / typecheck / demo
- リントと型チェックを実行（プロジェクトで定義されたコマンドがあればそれを使用）。`demo.html` 相当の簡易デモで街訪問を目視確認
- 検証: `python -c "import hub_town_manager, skill_eater_base_expansion, map_engine; print('IMPORTS OK')"`
- ヒント: これでステップ72完了。実装は各ステップの検証コマンドで逐次確認しながら進める。

---

**注意:** 各ステップは小さな変更単位です。低性能なLLMでも一つずつ検証コマンドで確認しながら実装できます。依存関係により順序を入れ替えても構いませんが、Phase 1→2→3→4→5 の順で進めるのが最も安全です。
