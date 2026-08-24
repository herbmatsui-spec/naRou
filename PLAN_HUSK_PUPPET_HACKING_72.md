# 実装計画書: 【傀儡ハッキング】抜け殻（Husk）再プログラム＆キメラ使役システム（全72ステップ）

- **目的**: スキルを奪われ「抜け殻（Husk）」となった敵を、余剰スキル／キメラコードで再注入し、自律使役ユニット（護衛スレイブ・迎撃タレット・回収ドローン）へ変換するシステムを実装する。
- **対象**: 低性能なLLMでも1ステップずつ確実に実装・検証できるよう、各ステップを「1つの小さな変更 ＋ 決まった検証」に分割。
- **前提知識**: Python 3.10+、既存コード（`naRou/skill_eater_*.py` は `naRou/systems/` への転送シェル、`naRou/ecs/components/components.py` の dataclass、`naRou/feature_flags.py`、`naRou/config.py`、`tests/`）。
- **規約**: 各ステップは「独立してコンパイル/動作する」こと。前のステップが成功してから次へ。検証は必ず実行すること。新規ロジックは原則 `naRou/systems/skill_eater_husk_*.py` に書き、`naRou/skill_eater_husk_*.py` に転送シェルを置く（既存の `skill_eater_servant_system.py` 等と同じパターン）。

---

## フェーズ1（Huskの取得と保持）〔ステップ1〜18〕

### Step 1 — 機能フラグ `ENABLE_HUSK_PUPPET_HACKING` を追加
- **変更ファイル**: `naRou/feature_flags.py`
- **実装**: `_feature_flags` に `"ENABLE_HUSK_PUPPET_HACKING": False` を追加。
- **検証**: `python -c "from naRou.feature_flags import is_enabled; print(is_enabled('ENABLE_HUSK_PUPPET_HACKING'))"` → `False`。

### Step 2 — 設定ファイルに `husk:` セクションを追加
- **変更ファイル**: `config.yaml`
- **実装**: トップレベルに `husk:\n  enabled: false\n  decay_per_turn: 1\n  max_inventory: 10` を追加。
- **検証**: `python -c "from naRou.config import get_config; print(get_config('husk.enabled'))"` → `False`。

### Step 3 — `get_husk_enabled()` ヘルパ
- **変更ファイル**: `naRou/feature_flags.py`
- **実装**: フラグまたは config(`husk.enabled`) のいずれか True なら True を返す関数 `get_husk_enabled()` を追加。
- **検証**: 両方 False で `False`、フラグ True で `True`。

### Step 4 — `HuskComponent` データクラスを追加
- **変更ファイル**: `naRou/ecs/components/components.py`
- **実装**: `@dataclass class HuskComponent:` を追加。`husk_id: str`, `source_monster: str`, `tier: int = 1`, `decay: int = 0`, `max_decay: int = 100`, `corruption: int = 0`, `slots: int = 1`, `injected_skills: list[str] = field(default_factory=list)`, `injected_codes: list[str] = field(default_factory=list)` を持つ。`to_dict`/`from_dict` も実装。
- **検証**: `python -c "from naRou.ecs.components.components import HuskComponent; h=HuskComponent(husk_id='h1',source_monster='slime'); print(h.to_dict()['source_monster'])"` → `slime`。

### Step 5 — `HuskComponent` の単体テスト
- **変更ファイル**: `tests/test_husk_component.py`（新規）
- **実装**: `to_dict`→`from_dict` の往復で `source_monster` が保存されることを `assert`。
- **検証**: `python -m pytest tests/test_husk_component.py -q` が GREEN。

### Step 6 — プレイヤー側 `HuskInventoryComponent` を追加
- **変更ファイル**: `naRou/ecs/components/components.py`
- **実装**: `@dataclass class HuskInventoryComponent:` を追加。`husks: list[HuskComponent] = field(default_factory=list)` のみ。
- **検証**: `python -c "from naRou.ecs.components.components import HuskInventoryComponent as H; print(len(H().husks))"` → `0`。

### Step 7 — スキル喰らいで「全スキルが空」になった敵を検知するフック
- **変更ファイル**: `naRou/systems/skill_eater_system.py`
- **実装**: 既存のスキル奪取処理の直後、`if get_husk_enabled() and 敵.残スキル数 == 0:` の分岐を空（`pass`）で追加（まだ Husk 生成はしない）。
- **検証**: `python -c "import naRou.systems.skill_eater_system"` がエラーなし。

### Step 8 — `create_husk(monster)` 関数の追加（空実装）
- **変更ファイル**: `naRou/systems/skill_eater_husk_system.py`（新規）
- **実装**: 関数 `create_husk(source_monster: str, tier: int) -> HuskComponent` を定義し、`HuskComponent(husk_id=..., source_monster=source_monster, tier=tier)` を返す（id は `f"husk_{id(source_monster)}_{tier}"` 等で固定文字列）。
- **検証**: `python -c "from naRou.systems.skill_eater_husk_system import create_husk; print(create_husk('slime',1).tier)"` → `1`。

### Step 9 — 転送シェルを作成
- **変更ファイル**: `naRou/skill_eater_husk_system.py`（新規）
- **実装**: `"""Forwarding shim for naRou.systems.skill_eater_husk_system."""` と `from naRou.systems.skill_eater_husk_system import *` のみ。
- **検証**: `python -c "from naRou.skill_eater_husk_system import create_husk"` がエラーなし。

### Step 10 — スキル喰らいで実際に Husk を生成
- **変更ファイル**: `naRou/systems/skill_eater_system.py` + `naRou/systems/skill_eater_husk_system.py`
- **実装**: Step 7 の `pass` を `husk = create_husk(敵名, 敵tier); player.husk_inventory.husks.append(husk)` に置換（プレイヤー取得は既存 `engine.player` 等から）。
- **検証**: 敵のスキルを全奪取する最小スクリプトで `len(player.husk_inventory.husks) >= 1`。

### Step 11 — インベントリ上限の適用
- **変更名**: `naRou/systems/skill_eater_husk_system.py`
- **実装**: `create_husk` 呼び出し側で `if len(inv.husks) >= get_config('husk.max_inventory'): 最古を破棄` を追加。
- **検証**: 上限を超えて生成しても `len(inv.husks) <= max_inventory`。

### Step 12 — ティア（等級）に応じたスロット数
- **変更ファイル**: `naRou/systems/skill_eater_husk_system.py`
- **実装**: `create_husk` 内で `husk.slots = max(1, tier)` とする。
- **検証**: `create_husk('boss',3).slots == 3`。

### Step 13 — 腐敗（decay）のターン更新
- **変更ファイル**: `naRou/systems/skill_eater_husk_system.py`
- **実装**: 関数 `tick_husk_decay(player)` を追加。各 Husk の `decay += get_config('husk.decay_per_turn')`、上限 `max_decay` でクランプ。
- **検証**: `python -c "from naRou.systems.skill_eater_husk_system import tick_husk_decay; ..."` で decay が増える。

### Step 14 — decay 単体テスト
- **変更ファイル**: `tests/test_husk_decay.py`（新規）
- **実装**: Husk 1つを持つプレイヤーで `tick_husk_decay` を呼び `decay == decay_per_turn` を assert。
- **検証**: `pytest tests/test_husk_decay.py -q` が GREEN。

### Step 15 — シリアライズ（保存）対応
- **変更ファイル**: `naRou/systems/save_system.py`（または該当シリアライズ箇所）
- **実装**: プレイヤー保存時に `HuskInventoryComponent` を `to_dict` し、読込時に `from_dict` する最小フックを追加。
- **検証**: セーブ→ロードで `husks` の `source_monster` が復元される。

### Step 16 — メッセージログ出力
- **変更ファイル**: `naRou/systems/skill_eater_husk_system.py`
- **実装**: `create_husk` 成功時に `from naRou.message_log import MessageLog; MessageLog.add(f"{source_monster} を抜け殻にした")` を呼ぶ（既存 MessageLog API に合わせる）。
- **検証**: Husk 生成後にログに該当文字列が含まれる。

### Step 17 — フラグ無効時は何もしない確認
- **変更ファイル**: `naRou/systems/skill_eater_system.py`
- **実装**: Step 10 のブロック冒頭で `if not get_husk_enabled(): return` を確実に入れる。
- **検証**: フラグ False のままスキル喰らいしても `husks` が増えない。

### Step 18 — フェーズ1統合テスト
- **変更ファイル**: `tests/test_husk_phase1.py`（新規）
- **実装**: フラグ ON → 敵全スキル奪取 → Husk 生成 → decay 増加 → シリアライズ往復、を通しで assert。
- **検証**: `pytest tests/test_husk_phase1.py -q` が GREEN。

---

## フェーズ2（傀儡炉と再注入）〔ステップ19〜36〕

### Step 19 — `PuppetForgeSystem` の空クラス
- **変更ファイル**: `naRou/systems/skill_eater_husk_forge.py`（新規）＋ `naRou/skill_eater_husk_forge.py`（転送シェル）
- **実装**: `class PuppetForgeSystem:` に `__init__` のみ（ロジックなし）。
- **検証**: `python -c "from naRou.skill_eater_husk_forge import PuppetForgeSystem; PuppetForgeSystem()"`.

### Step 20 — 制御負荷（ControlLoad）計算
- **変更ファイル**: `naRou/systems/skill_eater_husk_forge.py`
- **実装**: `def calc_control_load(husk) -> int:` を追加。負荷 = `len(injected_skills)*10 + len(injected_codes)*5`。
- **検証**: スキル2個注入済み Husk で `calc_control_load >= 20`。

### Step 21 — `inject_skill(husk, skill)` 関数
- **変更ファイル**: `naRou/systems/skill_eater_husk_forge.py`
- **実装**: `husk.injected_skills.append(skill)` のみ（容量チェックは後）。
- **検証**: `inject_skill(h, 'fire_bolt'); assert 'fire_bolt' in h.injected_skills`。

### Step 22 — スロット容量チェック
- **変更ファイル**: `naRou/systems/skill_eater_husk_forge.py`
- **実装**: `inject_skill` 冒頭で `if len(husk.injected_skills) >= husk.slots: raise ValueError("slots full")`。
- **検証**: slots=1 の Husk に2回 inject で `ValueError` が出る。

### Step 23 — キメラコード注入
- **変更ファイル**: `naRou/systems/skill_eater_husk_forge.py`
- **実装**: `inject_code(husk, code)` を追加。`husk.injected_codes.append(code)`。容量は `slots` の半分（最小1）まで。
- **検証**: `inject_code(h,'chimera_a'); assert 'chimera_a' in h.injected_codes`。

### Step 24 — 職能クラス決定
- **変更ファイル**: `naRou/systems/skill_eater_husk_forge.py`
- **実装**: `def role_of(husk) -> str:` を追加。注入スキルの属性（攻撃/防御/移動）の過半数で `'escort'|'turret'|'drone'` を返す。属性マップは `{"fire_bolt":"attack",...}` の小さな dict で固定。
- **検証**: 攻撃スキル主体で `role_of == 'escort'`。

### Step 25 — 注入の単体テスト
- **変更ファイル**: `tests/test_husk_forge.py`（新規）
- **実装**: 容量超過 `ValueError` と `role_of` の結果を assert。
- **検証**: `pytest tests/test_husk_forge.py -q` が GREEN。

### Step 26 — 忠誠（Loyalty）／汚染（Corruption）の初期化
- **変更ファイル**: `naRou/ecs/components/components.py`
- **実装**: Step 34 の `PuppetUnitComponent` を見越し、`HuskComponent` に `loyalty: int = 0` を追加（Corruption は既存）。
- **検証**: `HuskComponent().loyalty == 0`。

### Step 27 — 暴走リスク計算式
- **変更ファイル**: `naRou/systems/skill_eater_husk_forge.py`
- **実装**: `def rebellion_risk(husk) -> float:` を追加。`risk = max(0.0, (calc_control_load(husk) - husk.loyalty*2)/100)` を返す。
- **検証**: 負荷高・忠誠0 で `risk > 0`。

### Step 28 — 支配の紋（制御プロトコル）ランク適用
- **変更ファイル**: `naRou/systems/skill_eater_husk_forge.py`
- **実装**: `def effective_power(husk, protocol_rank: int) -> float:` を追加。`1.0 + 0.1*protocol_rank - rebellion_risk(husk)` をクランプ（最低0.1）。
- **検証**: protocol_rank=3 で `effective_power > 1.0`。

### Step 29 — 傀儡炉メニュー（開く）の空 UI
- **変更ファイル**: `naRou/ui/ui_fx_systems.py`（既存 UI ファイルのいずれか）または新規 `naRou/skill_eater_husk_ui.py`
- **実装**: `def open_forge_ui(player): return "forge_menu"` という関数だけ追加。
- **検証**: `python -c "from naRou.skill_eater_husk_ui import open_forge_ui; print(open_forge_ui(None))"` → `forge_menu`。

### Step 30 — Husk 一覧表示
- **変更ファイル**: `naRou/skill_eater_husk_ui.py`
- **実装**: `def list_husks(player) -> list[str]:` で `f"{h.husk_id}({h.source_monster})"` のリストを返す。
- **検証**: Husk 2つで `len(list_husks(player)) == 2`。

### Step 31 — 注入可能スキル一覧
- **変更ファイル**: `naRou/skill_eater_husk_ui.py`
- **実装**: `def list_injectable_skills(player) -> list[str]:` でプレイヤーが持つ余剰スキルのリストを返す（ここでは `get_config('husk.test_skills',['fire_bolt','guard','dash'])` 等の固定リストで代用）。
- **検証**: リストが空でない。

### Step 32 — 注入アクションの UI ハンドラ
- **変更ファイル**: `naRou/skill_eater_husk_ui.py`
- **実装**: `def ui_inject(player, husk_id, skill): inject_skill(該当husk, skill)` を呼ぶだけ。
- **検証**: UI 経由で `injected_skills` に追加される。

### Step 33 — 制御負荷／暴走予測の表示文字列
- **変更ファイル**: `naRou/skill_eater_husk_ui.py`
- **実装**: `def forge_status(husk) -> str:` で `f"load={calc_control_load(husk)} risk={rebellion_risk(husk):.2f}"` を返す。
- **検証**: 文字列に `load=` を含む。

### Step 34 — `PuppetUnitComponent` データクラス
- **変更ファイル**: `naRou/ecs/components/components.py`
- **実装**: `@dataclass class PuppetUnitComponent:` を追加。`unit_id: str`, `role: str`, `husk_ref: str`, `state: str = "sleep"`, `loyalty: int = 0`, `corruption: int = 0`, `hp: int = 10`, `max_hp: int = 10`, `order: str = "follow"`, `location: str = "base"`。
- **検証**: `PuppetUnitComponent(unit_id='u1',role='escort').role == 'escort'`。

### Step 35 — `create_unit(husk)` でユニット化
- **変更ファイル**: `naRou/systems/skill_eater_husk_forge.py`
- **実装**: `def create_unit(husk) -> PuppetUnitComponent:` を追加。`role_of(husk)` と `effective_power` から hp を決定し返す。注入スキルはユニットへコピー。
- **検証**: `create_unit(h).role in ('escort','turret','drone')`。

### Step 36 — 傀儡炉の燃料コスト
- **変更ファイル**: `config.yaml` + `naRou/systems/skill_eater_husk_forge.py`
- **実装**: `config` に `husk.forge_fuel: 5` を追加。`create_unit` でプレイヤーの資源（EconomyComponent.gold 等）を `forge_fuel` 消費。
- **検証**: `create_unit` 後に資源が `forge_fuel` 減っている。

---

## フェーズ3（使役ユニットの運用）〔ステップ37〜54〕

### Step 37 — `PuppetUnitComponent` の保存対応
- **変更ファイル**: `naRou/systems/save_system.py`
- **実装**: プレイヤーの `units: list[PuppetUnitComponent]` を `to_dict`/`from_dict` するフック（Husk と同様）。
- **検証**: セーブ→ロードで `unit_id` が復元される。

### Step 38 — ユニット状態の更新
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`（新規）＋ 転送シェル
- **実装**: `def tick_units(player):` を追加。各ユニットの `state` に応じ何もしない（後で拡張）。
- **検証**: `tick_units(player)` が例外なし。

### Step 39 — 命令書（Order）のデータ
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`
- **実装**: `ORDERS = {"follow":"追従","hold":"固定迎撃","patrol":"巡回回収"}` の dict を追加。`set_order(unit, order)` で `unit.order=order`。
- **検証**: `set_order(u,'hold'); u.order=='hold'`。

### Step 40 — 護衛スレイブ：プレイヤー追従
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`
- **実装**: `def update_escort(unit, player):` で `role=='escort'` の場合 `unit.location = player.location` をセット。
- **検証**: プレイヤー座標更新でユニット location が追従する。

### Step 41 — 護衛の戦闘参加（既存使役システムの再利用）
- **変更ファイル**: `naRou/systems/skill_eater_servant_system.py`（既存）＋ `naRou/systems/skill_eater_husk_units.py`
- **実装**: `update_escort` 内で、注入スキルを既存 `servant_system` の攻撃ヘルパに渡す呼び出しを 1 行追加（詳細ロジックは既存に委譲）。
- **検証**: 戦闘ターンでユニットが敵へダメージを与える（最小アサート）。

### Step 42 — 迎撃タレット：拠点固定
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`
- **実装**: `def update_turret(unit):` で `role=='turret'` なら `unit.state='active'; unit.location='base'` を固定。
- **検証**: `update_turret(u_turret); u_turret.location=='base'`。

### Step 43 — タレット自動迎撃
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`
- **実装**: `update_turret` で「拠点侵入イベント」を既存ベース防衛システム（`skill_eater_base_defense.py`）のフックに 1 行で渡す。
- **検証**: 侵入フラグありでタレットが攻撃ログを出す。

### Step 44 — 回収ドローン：自動素材収集
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`
- **実装**: `def update_drone(unit, warehouse):` で `role=='drone'` なら `warehouse.materials += 1`（最小）。
- **検証**: `update_drone(u_drone, wh); wh.materials == 1`。

### Step 45 — ドローン巡回ルート設定
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`
- **実装**: `set_route(unit, route: list[str])` を追加。`unit.route = route` を保持（PuppetUnitComponent に `route: list[str] = field(default_factory=list)` を追加）。
- **検証**: `set_route(u,['a','b']); u.route==['a','b']`。

### Step 46 — 活動中の汚染（Corruption）蓄積
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`
- **実装**: `tick_units` 内で `state=='active'` のユニット `corruption += 1`。
- **検証**: 活動ユニットで corruption が増える。

### Step 47 — 充電で汚染低下・忠誠上昇
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`
- **実装**: `state=='charging'` のユニット `corruption = max(0, corruption-2); loyalty += 1`。
- **検証**: charging で corruption 減・loyalty 増。

### Step 48 — ユニット運用の単体テスト
- **変更ファイル**: `tests/test_husk_units.py`（新規）
- **実装**: escort 追従・turret 固定・drone 回収・corruption 蓄積を assert。
- **検証**: `pytest tests/test_husk_units.py -q` が GREEN。

### Step 49 — 派遣 UI（役割割り当て）
- **変更ファイル**: `naRou/skill_eater_husk_ui.py`
- **実装**: `def dispatch(player, husk_id, role):` で `create_unit` して `player.units.append` する。
- **検証**: `dispatch` 後に `len(player.units)` が増える。

### Step 50 — 拠点防衛へのタレット組み込み
- **変更ファイル**: `naRou/systems/skill_eater_base_defense.py`
- **実装**: 防衛計算で `player.units` の `role=='turret'` を数え、数に応じて防衛力を +N する最小フック。
- **検証**: タレット1体で防衛力が上がる。

### Step 51 — ドローン回収の倉庫反映
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py` + 倉庫コンポーネント
- **実装**: `update_drone` の回収先を既存倉庫（`EconomyComponent` または専用 `warehouse`）へ反映。
- **検証**: ドローン活動後に倉庫資源が増える。

### Step 52 — 忠誠閾値ボーナス
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`
- **実装**: `effective_bonus(unit) -> float:` を追加。`loyalty>=50` で `1.2`、それ以外 `1.0`。
- **検証**: loyalty=50 で `effective_bonus==1.2`。

### Step 53 — ユニット「再起動待機」化
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`
- **実装**: hp<=0 のユニットを `state='reboot'` にし、完全消去しない（拠点帰還で修理可能な枠）。
- **検証**: hp=0 で `state=='reboot'` になり `units` から消えない。

### Step 54 — フェーズ3統合テスト
- **変更ファイル**: `tests/test_husk_phase3.py`（新規）
- **実装**: dispatch→escort/turret/drone 各動作→corruption→再起動待機、を通し assert。
- **検証**: `pytest tests/test_husk_phase3.py -q` が GREEN。

---

## フェーズ4（経済・融合・リスク）〔ステップ55〜66〕

### Step 55 — 維持費（Maintenance）の適用
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`
- **実装**: `tick_units` で `player` から `len(units)*get_config('husk.upkeep',1)` の資源を消費。
- **検証**: ユニット2体で維持費 2 が引かれる。

### Step 56 — 拠点評価の上昇
- **変更ファイル**: `naRou/systems/skill_eater_base_defense.py`
- **実装**: タレット迎撃成功時に `base_evaluation += 1` する最小フック（既存評価変数がなければ `player.base_evaluation: int = 0` を追加）。
- **検証**: 迎撃成功で評価が +1。

### Step 57 — 評価に応じた徴税効率
- **変更ファイル**: `naRou/systems/skill_eater_economy_system.py`（既存）
- **実装**: 徴税額に `1 + base_evaluation*0.05` を乗じる最小フック。
- **検証**: 評価高で徴税額が増える。

### Step 58 — 融合（Fusion）システムの追加
- **変更ファイル**: `naRou/systems/skill_eater_husk_fusion.py`（新規）＋ 転送シェル
- **実装**: `def fuse(a: HuskComponent, b: HuskComponent) -> HuskComponent:` を追加。`injected_skills` を統合し `tier = max(a.tier,b.tier)+1`。
- **検証**: `fuse(h1,h2).tier == max(tier)+1`。

### Step 59 — 融合でのシナジー発現
- **変更ファイル**: `naRou/systems/skill_eater_husk_fusion.py`
- **実装**: 特定组合（例 `fire_bolt`+`dash`）で `injected_codes.append('synergy_speed_burn')` する if を 1 つ追加。
- **検証**: 該当组合で synergy コードが入る。

### Step 60 — 融合の希釈リスク
- **変更ファイル**: `naRou/systems/skill_eater_husk_fusion.py`
- **実装**: `fuse` で `slots = max(a.slots, b.slots)` とし、スキル数が slots を超えた分を `pop` して捨てる。
- **検証**: 超過スキルが捨てられる。

### Step 61 — エリート化（長期使役）
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`
- **実装**: `tick_units` で `loyalty>=100` のユニットに `unit.elite = True`（PuppetUnitComponent に `elite: bool = False` 追加）。
- **検証**: loyalty=100 で `elite==True`。

### Step 62 — 暴走（Rebellion）発動
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`
- **実装**: `tick_units` で `corruption >= get_config('husk.rebellion_threshold',100)` なら `unit.state='rebel'`。
- **検証**: corruption 限界で `state=='rebel'`。

### Step 63 — 暴走の連鎖
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`
- **実装**: `state=='rebel'` のユニットがいると、他ユニットの `corruption += 3`（最小拡散）。
- **検証**: 暴走1体で他の corruption が増える。

### Step 64 — 鎮圧コスト
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py`
- **実装**: `def suppress(player, unit):` で資源を消費して `unit.state='sleep'; unit.corruption=0`。
- **検証**: `suppress` で state が sleep に戻る。

### Step 65 — 倫理・評判ペナルティ
- **変更ファイル**: `naRou/systems/skill_eater_husk_units.py` + `naRou/systems/karma_system.py`（既存）
- **実装**: `len(units) > get_config('husk.ethics_limit',5)` のとき `karma` を減らす最小フック。
- **検証**: ユニット過多で karma が下がる。

### Step 66 — フェーズ4統合テスト
- **変更ファイル**: `tests/test_husk_phase4.py`（新規）
- **実装**: 融合→シナジー→維持費→暴走→鎮圧→倫理ペナルティを assert。
- **検証**: `pytest tests/test_husk_phase4.py -q` が GREEN。

---

## フェーズ5（UI統合・テスト・完成）〔ステップ67〜72〕

### Step 67 — Web 管理パネル（HTML）
- **変更ファイル**: `web_game_client.html`（または `naRou/web/` 内の既存 UI）
- **実装**: `/api/husks` から一覧を取得し、Husk とユニットを表示する `<div id="husk-panel">` を追加。
- **検証**: ページに `husk-panel` 要素が存在。

### Step 68 — 使役マップ配置ビュー
- **変更ファイル**: `web_game_client.html`
- **実装**: 拠点／ダンジョンにユニットアイコンを描画する最小 `render_units()` JS 関数を追加。
- **検証**: 関数が定義されエラーなし（console で呼べる）。

### Step 69 — エンドポイント `/api/husks`
- **変更ファイル**: `naRou/web_server.py`
- **実装**: `GET /api/husks` で `player.husk_inventory.husks` と `player.units` の JSON を返す。
- **検証**: `curl localhost:8080/api/husks` が JSON を返す。

### Step 70 — 全体統合テスト（フルループ）
- **変更ファイル**: `tests/test_husk_full_loop.py`（新規）
- **実装**: フラグON→Husk生成→注入→ユニット化→派遣→tick（corruption/回収/維持費）→保存→ロード、を通し assert。
- **検証**: `pytest tests/test_husk_full_loop.py -q` が GREEN。

### Step 71 — ドキュメントと CHANGELOG
- **変更ファイル**: `docs/HUSK_PUPPET_HACKING.md`（新規）＋ `CHANGELOG.md`
- **実装**: 仕様3行と、CHANGELOG に「傀儡ハッキング（Husk使役）追加」を記載。
- **検証**: 両ファイルが存在し Markdown として読める。

### Step 72 — lint / typecheck の最終確認
- **変更ファイル**: なし（検証のみ）
- **実装**: 変更した `.py` に対して `ruff .` と `mypy`（設定通り）を実行し警告を解消。
- **検証**: `ruff .` と `mypy naRou/skill_eater_husk*.py` がエラー0。

---

## 実装の進め方（LLM向け）
1. 必ず **1ステップずつ** 実装し、そのステップの「検証」を満たしてから次へ。
2. 検証に `pytest` が含まれるステップは、テストファイルを先に書いてから本体を実装（TDD）。
3. ステップ間で import エラーが出たら、依存する「前のステップ」だけを確認する（広く探さない）。
4. 新規ロジックは `naRou/systems/skill_eater_husk_*.py` に書き、`naRou/skill_eater_husk_*.py` に転送シェルを置く（既存 `skill_eater_servant_system.py` 等と同一パターン）。
5. 72完了時に `pytest tests/test_husk_*.py -q` が全 GREEN になり、フラグ `ENABLE_HUSK_PUPPET_HACKING=True` で「敵を空殻化→注入→使役」の一連が動くことを確認。
