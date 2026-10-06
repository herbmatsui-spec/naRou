# GAME_DESIGN_V2 — 72ステップ実装計画（ゲームデザイン大改造）

対象リポジトリ: `/home/herbmatsui/narou` (Python roguelike, Elona系)
基準コミット: `main` = `46ee71d` / 実装ブランチ: `feature/design-v2`（`feature/run-carrying` = `c7def04` から分岐）

---

## 0. 計測された現状（この計画の根拠）

すべて `main` @ `46ee71d` に対して実測した値。設計判断は必ずこの表に紐づける。

### 0.1 量的な逆転（プロジェクトの定義的な問題）

| 指標 | 実測値 |
|---|---|
| 追跡済み製品 `.py` | **432ファイル / 100,183行** |
| 追跡済みテスト `.py` | 128ファイル / 18,680行 |
| 追跡済み `*.md`（計画書・報告） | **161ファイル / 1.84 MB** |
| プレイヤーが触れる内容（`data/` の抜粋9ファイル） | **31.2 KB** |
| アセット | 535ファイル / 10.1 MB、うち **324ファイル（60%）が200バイト未満** |
| プレースホルダ（`# placeholder` 13バイト・`None` にparse） | **6ファイル**：`jobs.yaml` `skill_trees.yaml` `skill_fusion.yaml` `pet_quests.yaml` `procedural_scenarios.yaml` `quest_generation_fallback.yaml` |

設計文書はゲーム内容の**約59倍**。コードは10万行に対し、触れるものは31 KB。

### 0.2 進行（実測）

| 項目 | 実測値 | 出典 |
|---|---|---|
| 1階あたりの敵数 | **6.7体**（`SPAWN_MONSTER_CHANCE=0.6` × 部屋数中央値10） | `constants.py:191`, `packages/gameplay/package.py:74` |
| 1階までの移動距離（マンハッタン） | 中央値 **36** | `map_engine.py:359-403` を3000回実測 |
| 開始 max_hp | **45** | `ecs/entity.py:1156-1161` |
| 開始装備 | 7点（長剣・盾・ポーション×8・パン×5・呪書・楽器・願いの杖） | `packages/gameplay/package.py:8-33` |
| 敵のHP範囲 | **10（ナニメナミ）〜 220（ドラゴン）** | `data/monsters.yaml` |
| プレイヤーの1打平均 | **約11**（2d6+1+str/3=14、的の耐性で-3） | `systems.py:186-216` |
| 敵→プレイヤー1打 | **1〜3**（`easy`難度で `×0.5`、`config.yaml:19`） | `systems.py:231`, `core/difficulty.py:50` |
| プレイヤー死亡に必要な命中数 | **約26回** | 45 HP ÷ 平均1.7 |
| 経験値の必要レベル | `exp_next = 100` **固定・どこでも 据え置き** | `ecs/entity.py:94` |
| 50到達に必要な階層数（推定） | **約6.6階層 / 約47 kills** | 35×L XP/kill から算出 |
| 階層数の上限 | **なし**（`engine/engine.py:1994` は `+= 1` のみ） | — |

### 0.3 終局（ここが最大の問題）

- **`GameState.VICTORY` と `GameState.GAME_OVER` は宣言されたが NEVER ASSIGNED**（`constants.py:249-250`）。产品コードで1度も代入されない。
- プレイヤーの死亡ハンドラが存在しない。唯一の「GAME OVER」は `engine/engine.py:1628` のログ文字列で、しかもその行は `_npc_ai` の中にあるが、`ai_system` short-circuit（`engine/engine.py:1606-1608`）により**到達不能**。生きた経路は `skill_eater/ai/ai_system.py:150` のログのみ。
- `devour` の拒否反動（`engine/engine.py:1015`）と毒性（`packages/gameplay/package.py:379`）は両方 `max(1, ...)` でHPが1以下にならない。
- 自然回復は `turns % 10 == 0` で `+1`（`engine/engine.py:1482-1487`）。`turns` は毎フレームも加算される（`engine/engine.py:2114`）ため、実質**フレームレート依存**。

### 0.4 経済（金貨バグ）

- `managers/combat_manager.py:51-57` の `q.reward_gold` 支払いが **if 文の外**にあり、**毎killで全クエスト分の報酬**（+1100金 +5白金）を支払う。
- 結果、約47 kills で **約51,700金**。
- -hover: 店・買い・売りのコードパスは `engine` / `input_actions` / `item_system` に**存在しない**。金は**永久に消費不能**。

### 0.5 戦闘と敵

- `GameplayLoop.player_act`（`packages/gameplay/package.py:195-304`）がやることは **3つだけ**：敵のマスなら攻撃、歩けるなら移動、どちらもでなければ何もしない。
- プレイヤーの射程攻撃動詞は**存在しない**。唯一の遠距離は `cast_fireball` で、座標が `self.player.x + 3, self.player.y` に**ハードコード**（`engine/engine.py:1738`）。
- `spells.yaml` に8呪文が設計されて_sensorが、到達できるのは `fireball` **1種だけ**。
- モンスター12種のうち、4種が `skills` を持たない（`slime:16` `red_slime:36` は空リスト、`snail` `kobold` はキーなし）。
- `mob.skills` は `data_manager.py:448` で**代入されるだけで読まれない**。monster が宣言する skill id 15種のうち **14種が data 内のどこにも定義されていない**。
- AIツリーは7本（`skill_eater/ai/ai_system.py:475-514`）。到達可能な行動は **9種**（自己回復・逃走・近接・呪文・追跡・分裂・彷徨い・距離取り・挟撃）。
- 意図テレグラフ `enemy_intent.py:42-88` は距離・視線・HP比・`ai_type` だけを見ており、**実際のAIツリーを参照しない**。結果、`aggressive`/`boss`（HP35%未満を示すが木に回復がない）で「回復」と表示される。

### 0.6 データと虚偽表示

- `data/text/en.yaml` は **13バイト / 1キー**。ja/ko/zh-cn/zh-tw はそれぞれ **170キー**あり、「英語ベースファイルを翻訳する」と書いているが、その英語ファイルにそのキーは**1つも無い**。`localization_manager.py:23` の既定は `en`（＝スタブ）。
- `data/main_quests.yaml:56` の `next_quest_id: "confrontation_01"` は**リポジトリ全体で1箇所にしか現れない**。`main_quest_system.py:311-312` のガードで静かに無視される。
- メインストの報酬は `engine.survival_system` に書かれるが（`main_quest_system.py:293-294`）、`engine.survival` は**別のオブジェクト**（`engine/engine.py:284-286`）。6100金は**不活性**。
- `COMMERCIAL_EVALUATION_REPORT.md` は A+/89 を掲げ、skill tree / job / reincarnation / pets / guilds / procedural quests の100%完了を主張するが、上記 实測と矛盾する。
- `map_engine.py:990-1011` の4帯（地上界0-10 / 地下界11-50 / 異界51-100 / 天界101-200）は**デッドコード**。`handle_stairs_interaction` に呼出し元が無く、`GameMap` は `world_layer` なしで構築される（`engine/engine.py:1998`）。

---

## 1. 九つの方向性

この計画は下列9方向を72ステップに落としたもの。各方向は他のどれかと排他であり、全部を並列実行できるわけではないため、Phase順に並べる。

| # | 方向 | 中核 | コスト |
|---|---|---|---|
| D1 | **死と終局を実在させる** | GAME_OVER / VICTORY が未代入、死亡ハンドラなし。/state遷移を一級市民にする | 難易度急上昇。現在の「死ねない」前提で設計された進行・平衡が全て見直し対象になる |
| D2 | **進行の曲線を設計する** | `exp_next=100` 固定、50到達が6.6階層。階層上限なし | 平衡表と既存セーブが無効化される |
| D3 | **経済を成立させる** | 毎kill 1100金のバグ、店も卖出も存在しない | 埋もれたstiara オブジェクトが値を出し始める |
| D4 | **戦闘解決モデルを入れ替える** | 「当たって壁を潰す」 בלבד。AP/射程/向きが無い | 全AIツリー・全平衡数値・全戦闘テストを Georges に書き直す必要がある |
| D5 | **敵を12体の個体にする** | `mob.skills` が読まれない、15種の能力idの14種が未定義、意図テレグラフが嘘 | モンスター1体ごとに능力の執筆が必要。難易度と直結するので D1 より後 |
| D6 | **戦利品を判断にする** | affix が0、38品すべてが事前鑑定済み、同一ogyに選択ralがない | インベントリの負荷が上がる。鑑定・売却の動詞を新設する必要がある |
| D7 | **9世界を1世界にする** | 設計9 / 実装1。深さはプロシージャルのみ、4帯構造はデッドコード | 「vast world」の販促コピーと `NAROU_9_WORLDS_DESIGN.md` 35KB の主張が変わる |
| D8 | **成長軸を1本に絞る** | jobs / skill_trees / skill_fusion は全て空データだがコードは存在する。SPの受け皿が無い | 広告済みの機能リストを撤回する必要がある |
| D9 | **表示を全部真にする** | 意図テレグラフ・英語スタブ・`A+/89` の主張・`confrontation_01` の死鎖 | 既存の文書とUI文言の大量削除。見た目は後退に見えても実測は改善する |

---

## 2. 実行規約（全72ステップ共通）

### 2.1 1ステップの分解単位（これを必ず守る）

各ステップは **2〜5個の原子サブステップ**に分解される。原子サブステップは次の条件を全て満たす：

- **1ファイル以下**の変更、または1つの純粋な関数追加
- 変更前後で **既存テストの pass/count が変わらない**（緑→緑）
- 単独で revert 可能
- 「説明 Hennry」で終わらない（`add affix schema` ではなく `data/schemas/item/affix.py に Affix dataclass を追加`）

### 2.2 各ステップの Definition of Done

1. 関連テストが緑
2. 既存テストの pass count が**減っていない**（`--last-failed` で確認）
3. `ruff check` クリーン
4. 意図的に壊した時（**非空虚性の証明**）に新しいテストが赤くなることを確認済み
5. 1コミット。メッセージに Step 番号を書く（例: `step-12: プレイヤー死亡ハンドラを追加する`）

### 2.3 非空虚性の証明（このリポジトリで3度 목격した罠）

緑テストが空振りして**赤いoshiなくなる**ことが、このリポジトリでは3回起きている（READMEのバッジ、balance tool の `PASS`、重複検出アサーションの無効化）。**新しいテストを主張Bronには、必ず「1つだけ意図的に壊す → 赤になる」を実行し、そのコマンド出力をコミットメッセージに残す。**

テスト自体の構造的帮手は `tests/helpers/non_vacuity.py` の `assert_non_vacuous()` を使う（Step 3 で追加）。

### 2.4 故意に赤になるテストの扱い

データ不備_step（Step 4/5など）は、**最初に `pytest.mark.xfail(strict=True)` で導入**し、対応ステップで `@xfail` を外して緑に戻す。strict=True なので「勝手に直ったら落ちる」。

---

## 3. 3サブエージェントへの分割

Phase 0（Step 1-9）は**共通土台**なので主エージェントが直列で実装する。その後 Step 10-72 を3つの作業束に分割し、各1サブエージェントに**専用worktree・専用ブランチ**を割り当てて並列実行する。最後に主エージェントが依存順にマージし、全スイートを緑にして検証する。

| エージェント | 担当 Step | 作業束 | 主なファイル | 競合リスク |
|---|---|---|---|---|
| **A** | 10–32 | D1 死と終局 → D2 進行曲線 → D3 経済 | `engine/engine.py` `ecs/entity.py` `managers/combat_manager.py` `config.yaml` `save_system.py` | **最も高い**（engine.py を独占） |
| **B** | 33–56 | D4 戦闘解決モデル → D5 敵の能力 | `systems.py` `input_actions.py` `input_handler.py` `skill_eater/ai/ai_system.py` `enemy_intent.py` `data/monsters.yaml` | 中（engine.py を車読み） |
| **C** | 57–72 | D6 戦利品 → D9 表示の誠実性 | `item_system.py` `data/items.yaml` `data/text/*.yaml` `tests/` 文書群 | 低（engine.py に触れない） |

**分離の根拠**: A は `engine.py` を独占させて他2エージェントを排除する。B は B が所有する AI・入力・戦闘表のみ触る。こうすると3者が同じファイルを同時に編集することが起きない。`ecs/entity.py` は A が独占所有と宣言し、B/C は読むだけに留める。

---
## Phase 0: 安全網と基準（Step 1–9）— 主エージェント直列

Phase 0 は3並列の前提になる共通土台であり、ここだけは並列化しない。

### Step 1: 実装ブランチと worktree を確定する
**目的**: 以降すべての変更の土台を固定する。
- 1.1 `.worktrees/design` のブランチ `feature/design-direction` を作業ブランチ `feature/design-v2` にリネームする
- 1.2 `git branch -m feature/design-v2` を実行し、HEAD が `c7def04` のままであることを確認する
- 1.3 `savegame.bin*` と `balance_report.*` を `git stash push` で退避し、作業ツリーを clean にする
- 1.4 `plans/DESIGN_V2_BASELINE.md` の scaffolding を作る（Step 2 で記入）
**テスト**: なし（コード変更なし）
**DoD**: `git status --short` が空、`git log --oneline -1` が `c7def04`

### Step 2: テスト基準表を実測して記録する
**目的**: 以降「/pass が減った」を機械的に判定できるようにする。
- 2.1 `feature/design-v2` 上で `tests/test_enemy_abilities.py tests/test_enemy_intent.py tests/test_enemy_intent_formation.py` を実行し結果を記録（現状 8 failed / 93 passed）
- 2.2 同様に `tests/test_audio_fallback.py tests/test_input_layer.py tests/test_tutorial_guides.py` を実行して記録
- 2.3 `main` の全体基準（15 failed / 636 passed）を `plans/DESIGN_V2_BASELINE.md` に転記
- 2.4 「既知の赤」を一覧化し、**新規に落ちたものだけ**を以後Perturbation として扱うルールを明文化する
**テスト**: なし
**DoD**: `plans/DESIGN_V2_BASELINE.md` に実測値がすべて入っている

### Step 3: 非空虚性ヘルパーを追加する
**目的**: 「新しいテストが本当に赤になれるか」を一発で証明する道具を作る。
- 3.1 `tests/helpers/__init__.py` を作る
- 3.2 `tests/helpers/non_vacuity.py` に `assert_non_vacuous(coro_fn, expect=AssertionError)` を実装する（渡された呼び出しを一回だけ故意に失敗させ、捕捉できなければ fail）
- 3.3 `tests/test_non_vacuity.py` を書いてヘルパー自身を検証（正常系で緑、意図的に壊した版で赤）
- 3.4 `tests/conftest.py` に `tests/helpers` を `sys.path` へ追加
**テスト**: `tests/test_non_vacuity.py`（3ケース）
**DoD**: 3ケース緑。「壊した版が赤」を実行した出力をコミットに残す

### Step 4: データ整合性テストを作る（xfail で導入）
**目的**: 13バイトのプレースホルダと、解決できない能力id を機械的に検出する。
- 4.1 `tests/test_data_integrity.py` に `test_no_placeholder_data_files()` を書く（13バイト / `# placeholder` / YAMLとして `None` にparseされるファイルを列挙）
- 4.2 同ファイルに `test_every_monster_skill_id_resolves()` を書く（`data/monsters.yaml` の全 skill id が `data/**` 内で解決されることを要求）
- 4.3 両方を `@pytest.mark.xfail(strict=True, reason="Phase 4 / Phase 8 で解消")` で包む
- 4.4 非空虚性: `xfail` が本当に「テストが失敗している」ため に機能していることを確認する（`--runxfail` で走らせ failing を見る）
**テスト**: `pytest tests/test_data_integrity.py` → 2 xfailed
**DoD**: `xfail(strict=True)` で xfail として報告される。`--runxfail` で 2 failed になる

### Step 5: 到達不能リファレンスのテストを作る（xfail で導入）
**目的**: 「宣言されているが解決先が無い」を検出する。
- 5.1 `tests/test_reachability.py` に `test_quest_chain_terminates()` を書く（`main_quests.yaml` の全ての `next_quest_id` が実在する）
- 5.2 `test_meta_progression_rewards_have_readers()` を書く（`reward_bonus` の各文字列に最低1つのPython参照がある）
- 5.3 `test_main_quest_rewards_reach_the_player()` を書く（`survival_system` と `survival` が同一オブジェクトである）
- 5.4 3つを `@pytest.mark.xfail(strict=True, reason="Step 34 / Step 61 で解消")` で包む
**テスト**: `pytest tests/test_reachability.py` → 3 xfailed
**DoD**: 同上

### Step 6: 平衡スナップショットテストを作る
**目的**: 改造のたびに意図せず変わる数値を固定する。
- 6.1 `tests/test_balance_snapshot.py` に `test_starting_max_hp_is_45()` を書く
- 6.2 `test_starting_kit_is_seven_items()` を書く
- 6.3 `test_monster_hp_span()` を書く（min=10, max=220）
- 6.4 `test_exp_next_is_flat_100()` を書く（**現在の壊れた挙動の記録**。Step 26 で更新して書き換える）
- 6.5 `test_monsters_per_floor_is_about_6_7()` を書く（生成を100回走らせて平均を1桁まで検証）
**テスト**: `tests/test_balance_snapshot.py`（5件）
**DoD**: 5件緑。数値は一律ハードコードで、fixture から読まない

### Step 7: 不活性な参照を1件だけ直す（最初の xfail 解除）
**目的**: 「xfail を緑に変える」が実際に動くことを1件で証明する。
- 7.1 `data/main_quests.yaml:56` の `next_quest_id: "confrontation_01"` を、既存3クエストの終端として `null` に変更する
- 7.2 `tests/test_reachability.py::test_quest_chain_terminates` の `xfail` を外す
- 7.3 既存テストに回帰がないか 2.2 のスイートで確認
**テスト**: `tests/test_reachability.py::test_quest_chain_terminates` が緑、xfail 数が 3→2
**DoD**: xfail 数が1減ったことを実測で確認

### Step 8: pre-commit に品質ゲートを追加する
**目的**: 空振りテストの再発を機械的に防ぐ。
- 8.1 `.pre-commit-config.yaml` に `ruff` フックを追加（既にある場合は `files` を `\.py$` に絞る）
- 8.2 `ruff check` が clean であることを確認し、赤いものだけ `ruff check --fix` で直す
- 8.3 `tests/test_non_vacuity.py tests/test_balance_snapshot.py tests/test_data_integrity.py tests/test_reachability.py` を高速ゲートとして `workflow.yaml` に登録する
**テスト**: `pre-commit run --all-files`
**DoD**: pre-commit 緑、高速ゲート4ファイルが全て緑/xfail

### Step 9: Phase 0 を確定する
**目的**: 3並列に入る前の.green の状態を固定する。
- 9.1 高速ゲート4ファイルを実行し結果を `plans/DESIGN_V2_BASELINE.md` の Phase 0 欄に追記
- 9.2 `git add -A && git commit -m "step-09: Phase 0 の安全網を確定する"`（本計画書、`DESIGN_V2_BASELINE.md`、`tests/helpers/non_vacuity.py`、4つのテストファイル、`data/main_quests.yaml` の修正）
- 9.3 `git log --oneline -3` を確認し、Step 1〜9 のコミットが揃っていることを確認
**テスト**: 高速ゲート全緑
**DoD**: 作業ツリー clean。以降の全ステップの前提|This is the baseline.

## Phase 1: 死・終局・進行・経済（Step 10–32）— サブエージェント A

**所有ファイル宣言**: A は `engine/engine.py` `ecs/entity.py` `ecs/components/components.py` `managers/combat_manager.py` `config.yaml` `save_system.py` `main_quest_system.py` `constants.py` を独占する。B と C はこれらのファイルを**読argetingだけ**、編集しない。

### Step 10: ゲーム状態の正本ようにする
**目的**: `GameState` を列挙型から**実際に駆動される状態機械**に変える。
- 10.1 `engine/game_state.py` を新規作成し、`class GameStateMachine` を定義する（`current: str`、`transition(to)`、`history: list[tuple[str,str,float]]`）
- 10.2 `transition()` は未登録の遷移を `ValueError` にする。許可表は `{"playing": {"game_over","victory"}, "game_over": {"title"}, "victory": {"title"}}`
- 10.3 `Engine.__init__` 内で `self.game_state = GameStateMachine("playing")` を生成
- 10.4 `constants.py` の `GameState` は**削除しない**（文字列定数として残し、sm のキーと一致させる）
**テスト**: `tests/test_game_state.py::test_unregistered_transition_raises`（新ファイル）
**DoD**: 新テスト緑、既存 pass 数不変

### Step 11: 遷移テストを先に書いてから Step 12 のために慣らす
- 11.1 `tests/test_game_state.py` に `test_playing_to_game_over_is_allowed()` を追加
- 11.2 `test_history_records_timestamps()` を追加
- 11.3 `test_victory_is_reachable_from_playing()` を追加
- 11.4 非空虚性: 許可表から `"victory"` を削除して赤になることを証明
**テスト**: `tests/test_game_state.py`（4件）
**DoD**: 4件緑、うち1件は非空虚性の証明済み

### Step 12: プレイヤー死亡ハンドラを新設する
**目的**: 「GAME OVER の文字列を出すだけの行」を、**状態遷移を行う関数**に置き換える。
- 12.1 `engine/engine.py` に `def _on_player_death(self) -> None:` を追加する。中身は `self.game_state.transition("game_over")`、`self.log(...)`、`PersistenceManager().save(self)`（あれば）
- 12.2 `skill_eater/ai/ai_system.py:150` の `【死亡】` ログを、`actor.is_player` なら `engine._on_player_death()` を呼ぶ分岐に置き換える
- 12.3 `engine/engine.py:1628` の到達不能な `GAME OVER` ログを削除する
- 12.4 `MeleeAttackAction`（`skill_eater/ai/ai_system.py:131-146`）のダメージ適用後に `if target.is_player and target.hp <= 0:` を追加する
**テスト**: `tests/test_player_death.py::test_zero_hp_triggers_game_over`
**DoD**: 緑。かつ既存テストで壊れたものも0件

### Step 13: 呪文のダメージでも死亡させる
- 13.1 `CastSpellAction.execute`（`skill_eater/ai/ai_system.py:187-213`）の `apply` 後に同じ死亡チェックを追加する
- 13.2 同じ死亡チェックをトラップ（`packages/gameplay/package.py:259`）と毒性（`:379`）にも入れる
- 13.3 `tests/test_player_death.py::test_spell_damage_can_kill()` を追加する
**テスト**: `tests/test_player_death.py`（2件）
**DoD**: 2件緑

### Step 14: 死亡後の入力を遮断する
**目的**: 「死んだのに操作できる」状態を終わらせる。
- 14.1 `engine/engine.py` の入力受付メソッドの先頭に `if self.game_state.current != "playing": return None` を追加する
- 14.2 `advance_world` も同じゲートを通るようにする（敵は停止する）
- 14.3 `tests/test_player_death.py::test_no_input_accepted_after_death()` を追加する
**テスト**: `tests/test_player_death.py`（3件）
**DoD**: 3件緑

### Step 15: 死亡後のHP回復を止める
- 15.1 `engine/engine.py:1482-1487` の自然回復に `and self.game_state.current == "playing"` を追加する
- 15.2 `input_handler.py` のポーション使用（`:443`）にも同じゲートを追加する
- 15.3 `tests/test_player_death.py::test_regen_does_not_revive_the_dead()` を追加する
**テスト**: `tests/test_player_death.py`（4件）
**DoD**: 4件緑

### Step 16: cannot-be-killed な 1 HP 床を撤去する
- 16.1 `engine/engine.py:1015` の `max(1, self.player.hp - backlash)` を `self.player.hp -= backlash` に変更
- 16.2 `packages/gameplay/package.py:379` の `max(1, ...)` を撤去
- 16.3 `tests/test_player_death.py::test_devour_backlash_can_be_lethal()` を追加する
- 16.4 `tests/test_player_death.py::test_toxicity_can_be_lethal()` を追加する
**テスト**: `tests/test_player_death.py`（6件）
**DoD**: 6件緑。`max(1,` の残存を `grep -n "player.hp = max(1" engine/ packages/` で0件にする

### Step 17: 「死が確定している」テストを書く
- 17.1 `tests/test_player_death.py::test_player_hp_never_lands_below_zero_without_death()` を追加する（HP<=0 なら必ず game_over であること）
- 17.2 `test_no_production_code_assigns_game_state_directly()` を追加する（`GameState.GAME_OVER` への直接代入がConstants の他で0件であることを grep で検証するテスト）
- 17.3 非空虚性: `_on_player_death` の遷移を no-op にすると Step 17.1 が赤になることを証明
**テスト**: `tests/test_player_death.py`（8件）
**DoD**: 8件緑、非空虚性の証明を出力として残す

### Step 18: 自然回復のフレーム連結バグを直す
**目的**: `turns` が毎フレーム加算される（`engine/engine.py:2114`）ため、`turns % 10` は実質フレーム数になっている。
- 18.1 `tests/test_balance_snapshot.py::test_natural_regen_is_turn_gated()` を追加する（現状は**xfail**、バグの記録）
- 18.2 `engine/engine.py:2114` の毎フレーム加算を削除し、ターン進行に一本化する
- 18.3 18.1 の `xfail` を外して緑にする
- 18.4 回復量が `+1 / 10ターン` に正確になることを確認する
**テスト**: `tests/test_balance_snapshot.py`（6件）
**DoD**: 6件緑

### Step 19: 勝利条件を定義して実装する
**目的**: 「永遠に降り続ける」状態を終わらせる。
- 19.1 `docs/compose/spec/win-condition.md` に勝利条件を1つ書く（**深さ到達**を採る：depth 20 の`void_boss` を倒す）
- 19.2 `data/world_state.yaml` に `win: {kind: "depth_boss", depth: 20}` を追加する
- 19.3 `Engine` に `def check_win_condition(self) -> None:` を追加し、到達時に `game_state.transition("victory")` する
- 19.4 `tests/test_win_condition.py::test_reaching_depth_boss_wins()` を追加する
**テスト**: `tests/test_win_condition.py`（1件）
**DoD**: 緑。深さBoss の実体は Step 44 で実装するまではダミーでもよいが、`transitions` は本実装

### Step 20: 「勝っても負けてもラン Airborne する」を定義する
- 20.1 `save_system.py` に `def clear_run(self) -> None:` を追加し、ラン内状態を破棄して `GameStateMachine("playing")` から再入できるようにする
- 20.2 `tests/test_run_boundary.py::test_run_can_be_restarted_after_death()` を追加する
- 20.3 `tests/test_run_boundary.py::test_run_can_be_restarted_after_victory()` を追加する
- 20.4 非空虚性: `clear_run` の呼び出しを削除して緑が壊れることを証明
**テスト**: `tests/test_run_boundary.py`（2件）
**DoD**: 2件緑

### Step 21: 進行曲線を実データにする
- 21.1 `data/balance_standards.yaml` に `exp_curve: {base: 120, growth: 1.35}` を追加する
- 21.2 `ecs/entity.py:94` の `exp_next = 100` ハードコードを、`growth ** level` ベースの実計算に置き換える
- 21.3 `ecs/components/components.py:275` にも同じ式を適用する（重複定義の解消）
- 21.4 `tests/test_progression_curve.py::test_exp_next_is_monotonic()` を追加する
**テスト**: `tests/test_progression_curve.py`（1件）
**DoD**: 緑、レベル50までが単調増加

### Step 22: 到達難度を検証する
- 22.1 `tests/test_progression_curve.py::test_level_50_requires_at_least_15_floors()` を追加する（現状の6.6階層が改善されたことの固定）
- 22.2 `test_level_50_costs_a_plausible_number_of_kills()` を追加する（50 kills 以上）
- 22.3 `tests/test_balance_snapshot.py::test_exp_next_is_flat_100()` を新しい期待値に書き換える
**テスト**: `tests/test_progression_curve.py`（3件）＋ 更新1件
**DoD**: 3件緑。書き換えたスナップショットは**意図的に値をRéaliserした**ことをコミットに残す

### Step 23: 階層に終端を与える
- 23.1 `config.yaml` に `dungeon: {max_depth: 30, win_depth: 20}` を追加する
- 23.2 `engine/engine.py:1994` の `self.dungeon_level += 1` に上限判定と勝敗チェックを追加する
- 23.3 `tests/test_dungeon_ceiling.py::test_descent_stops_at_max_depth()` を追加する
- 23.4 `tests/test_dungeon_ceiling.py::test_dead_code_four_zone_layer_is_removed()` を追加する（`map_engine.py:990-1011` と `handle_stairs_interaction` の呼出し0件を検証）
**テスト**: `tests/test_dungeon_ceiling.py`（2件）
**DoD**: 2件緑

### Step 24: 深さ-Merchant の敵プールを枯渇させない
**目的**: 54階以降で全12種が等確率になる（`data_manager.py:465-466` のフォールバック）。
- 24.1 `tests/test_enemy_pool.py::test_every_depth_has_at_least_two_valid_monsters()` を追加する（**xfail** で開始）
- 24.2 `data/monsters.yaml` の `max_floor` を 30 階以上まで延ばし、プールを枯渇させない
- 24.3 `data_manager.py` のフォールバックで「等確率12種」に戻すのではなく「深さに最も近い3種」を選ぶよう変更する
- 24.4 24.1 の `xfail` を外す
**テスト**: `tests/test_enemy_pool.py`（1件）
**DoD**: 緑

### Step 25: 金貨バグを直す
**目的**: `managers/combat_manager.py:51-57` の `q.reward_gold` が if の外にあり毎kill全クエスト分を支払う。
- 25.1 `tests/test_economy.py::test_quest_gold_only_paid_on_completion()` を追加する（**xfail** で開始）
- 25.2 `managers/combat_manager.py:51-57` を if の内側に移動する
- 25.3 25.1 の `xfail` を外す
**テスト**: `tests/test_economy.py`（1件）
**DoD**: 緑。47 kills で約51,700金ではなく**数百金**になる

### Step 26: 金を消費できるようにする
- 26.1 `data/items.yaml` の各アイテムに `sell_price` を追加する（`base_value` の30%）
- 26.2 `item_system.py` に `def sell(self, item, gold_holder) -> int:` を追加する
- 26.3 `input_actions.py` に `SellAction` を追加し、`input_handler.py` に `,` を割り当てて**重複がないこと**を `ActionRegistry._claim` の警告が上げないことを確認する
- 26.4 `tests/test_economy.py::test_items_can_be_sold_for_gold()` を追加する
**テスト**: `tests/test_economy.py`（2件）
**DoD**: 2件緑、重複登録警告なし

### Step 27: 主 线 報酬が別オブジェクトに落ちるのを直す
- 27.1 `tests/test_reachability.py::test_main_quest_rewards_reach_the_player()` の `xfail` を外す前に、`main_quest_system.py:293-294` の `engine.survival_system` を `engine.survival` に置き換える
- 27.2 `packages/gameplay/package.py:443` の登録と `engine/engine.py:284-286` の生成を**同一オブジェクト**にする（kernel 登録daterence を使う）
- 27.3 `tests/test_reachability.py::test_main_quest_rewards_reach_the_player()` を緑にする
**テスト**: `tests/test_reachability.py` xfail 数が 2→1
**DoD**: 6100金が実際に creeся

### Step 28: 難易度プリセットを作り直す
**目的**: `easy` の `player_damage_taken: 0.5`（`config.yaml:19`）が死を発生不可能にしている。
- 28.1 `config.yaml` の既定を `game.difficulty: normal` に変更する
- 28.2 `easy` を `player_damage_taken: 0.75, player_regen: 1.2` に変更する（easy でも死は起きる）
- 28.3 `tests/test_difficulty.py::test_every_difficulty_can_kill_the_player()` を追加する（全プリセットで1hp以下まで落ちる経路が存在することを数値で示す）
- 28.4 `tests/test_balance_snapshot.py` に `test_default_difficulty_is_normal()` を追加する
**テスト**: `tests/test_difficulty.py`（1件）＋ スナップショット1件
**DoD**: 緑。1,000回のシミュレーションで easy でも死亡が発生することを実測

### Step 29: 自然回復・毒性・飢えの関係を設計する
- 29.1 `docs/compose/spec/survival-balance.md` に 3系統の関係を数値で書く
- 29.2 `tests/test_survival_balance.py::test_starving_outpaces_regen_within_a_run()` を追加する
- 29.3 `tests/test_survival_balance.py::test_idle_player_reaches_a_nonlethal_starvation()` を追加する
**テスト**: `tests/test_survival_balance.py`（2件）
**DoD**: 2件緑。8000空腹 ÷ 1/turn に対し、回復が追いつかないことが保証される

### Step 30: 到達不能な meta_progression を解決する
- 30.1 `tests/test_reachability.py::test_meta_progression_rewards_have_readers()` の `xfail` を残したまま、`data/meta_progression.yaml` の `reward_bonus` を**実読されるキー**へ置き換える（`damage_boost` / `gold_gain` の実数へ）
- 30.2 `meta_progression_system.py` にその2キーの適用コードを追加する
- 30.3 `tests/test_reachability.py` の `xfail` を外す
**テスト**: `tests/test_reachability.py` xfail 数が 1→0
**DoD**: xfail ゼロ

### Step 31: Phase 1 全体の回帰確認
- 31.1 Phase 1 の新規テストファイル7本を一括実行する
- 31.2 `plans/DESIGN_V2_BASELINE.md` の Phase 1 欄を実行結果で埋める
- 31.3 `tests/test_data_integrity.py` と `tests/test_reachability.py` の xfail 数を確認する
**テスト**: 新規7ファイル
**DoD**: 全て緑。xfail は残。就这样のはずが1つでも増えたら却下

### Step 32: サブエージェントAのコミット
- 32.1 `git status` で未追跡のスクラッチファイルがないことを確認する
- 32.2 Step 10〜31 のコミット列が連番になっていることを確認する
- 32.3 `plans/DESIGN_V2_PHASE1_REPORT.md` に「ArchivingSymmetry した到達不能はどれか」「赤くなった既存テストはどれか」を書く
**テスト**: 直前ステップと同じ
**DoD**: 作業ツリー clean。A の担当範囲外（`ai_system.py` `item_system.py`）に1行も変更がないことを `git diff main --name-only` で確認

## Phase 2: 戦闘解決モデル・敵の能力（Step 33–56）— サブエージェント B

**所有ファイル宣言**: B は `systems.py` `input_actions.py` `input_handler.py` `skill_eater/ai/ai_system.py` `enemy_intent.py` `data/monsters.yaml` `data/spells.yaml` `data/schemas/monster/` `data/generated/monster/monster.py` `ecs/components/ai*.py` を独占する。`engine/engine.py` と `ecs/entity.py` は**読むだけ**（A が所有）。必要な変更があれば A のブランチに **NOTE コメントのみ**を残す。

### Step 33: 戦闘解決モデルの仕様を書く
- 33.1 `docs/compose/spec/combat-resolution.md` にAP制の仕様を書く（1手2AP、攻撃1AP・移動1AP、多数子是 1AP消費ごとに1tick）
- 33.2 仕様書に「既存バグ攻撃Ctx. `player.x + 3` と `xp_next` 定数をどうplacesするか」を明記する
- 33.3 仕様に**移行期間中の二重実装**方針を書く（`legacy_bump` フラグ）
- 33.4 仕様を `docs/compose/spec/shipping-chain.md` の索引に登録する
**テスト**: なし
**DoD**: 文書が存在し、A の `engine.py` への要求が列挙されている

### Step 34: AP clamber を追加する
- 34.1 `ecs/components/components.py` に `ap: int = 2` を追加する
- 34.2 `ecs/entity.py` の `Entity` に `ap` の getter/setter を追加する（**A 所有** → 34.2 は A のブランチへの要求として `docs/compose/spec/combat-resolution.md` に追記し、A は Step 42 で対応する）
- 34.3 `tests/test_ap_system.py::test_ap_defaults_to_two()` を追加する
**テスト**: `tests/test_ap_system.py`（1件）
**DoD**: 緑

### Step 35: 攻撃に AP を消費させる
- 35.1 `CombatSystem` に `AP_COST = {"attack": 1, "move": 1, "wait": 0, "spell": 1}` を定義する
- 35.2 `GameplayLoop.player_act` 相当の解決を `systems.py` の `resolve_action()` に切り出す
- 35.3 `tests/test_ap_system.py::test_attack_costs_one_ap()` を追加する
- 35.4 `tests/test_ap_system.py::test_three_attacks_per_turn_at_two_ap()` を追加する（**AP 制 Masuk** ことを数値で固定）
**テスト**: `tests/test_ap_system.py`（3件）
**DoD**: 3件緑

### Step 36: プレイヤーの射程攻撃動詞を追加する
- 36.1 `input_actions.py` に `RangedAttackAction` を追加する（`(dx, dy)` を保持し、視線が通る最も近い敵Urbanを対象にする）
- 36.2 `input_handler.py` に**既存の重複がないキー**（未使用を実測して確定する）を割り当てる
- 36.3 `data/monsters.yaml` の敵が射程を持つ条件を決める（`min_floor` と射程の相関）
- 36.4 `tests/test_ranged_attack.py::test_ranged_attack_requires_line_of_sight()` を追加する
- 36.5 `tests/test_ranged_attack.py::test_ranged_attack_picks_the_nearest_visible_enemy()` を追加する
**テスト**: `tests/test_ranged_attack.py`（2件）
**DoD**: 2件緑。キー割当ては `ActionRegistry` の重複警告が0件であることを実行で確認

### Step 37: 硬-coded 座標を消���
- 37.1 `engine/engine.py:1738` の `tx, ty = self.player.x + 3, self.player.y` は A 所有 → A への要求として仕様書に追記し、**B は `systems.py` 側に `def aimed_tile(origin, direction, distance) -> Point` を新設**する
- 37.2 `tests/test_aiming.py::test_aimed_tile_is_direction_relative()` を追加する
- 37.3 `tests/test_aiming.py::test_aim_cannot_wrap_to_the_other_side_of_a_wall()` を追加する
**テスト**: `tests/test_aiming.py`（2件）
**DoD**: 2件緑。`x + 3` パターンが `engine/` から消えていることは **A 側の Step 42 で** 検証される

### Step 38: 向きと背後攻撃を導入する
- 38.1 `ecs/entity.py` ではなく、`ecs/components/components.py` に `facing: str = "S"` を追加する
- 38.2 `systems.py:calculate_melee_attack` に `attacker` の向きと `defender` の向きから `is_backstab` を求める分岐を追加する
- 38.3 背中で撃たれた場合のみ `×1.5` を `roll_dmg` に乗算する（`systems.py:191-192` のクリティカル身旁と**別系統**にする）
- 38.4 `tests/test_backstab.py::test_attack_from_behind_deals_more()` を追加する
- 38.5 `tests/test_backstab.py::test_backstab_is_deterministic_not_a_dice_roll()` を追加する
**テスト**: `tests/test_backstab.py`（2件）
**DoD**: 2件緑。`rng` を引数が**1つ**減っていることで「ダイスではない」ことを assertion で保証する

### Step 39: 敵も向きを持つ
- 39.1 `MeleeAttackAction` 実行時に攻撃者の `facing` を対象方向へ更新する
- 39.2 `ChaseAction` / `KiteAction` でも移動方向に `facing` を更新する
- 39.3 `tests/test_backstab.py::test_monster_facing_follows_its_movement()` を追加する
**テスト**: `tests/test_backstab.py`（3件）
**DoD**: 3件緑

### Step 40: 8 呪文すべてを到達可能にする
- 40.1 `input_actions.py` に `CastSpellAction(skill_id)` を追加し、`data/spells.yaml` の `spells` を列挙する
- 40.2 `engine/engine.py:1713 cast_fireball` は A 所有 → B は `systems.py` に `def cast(spell_id, caster, target)` を新設して、A に置換を要求する
- 40.3 `tests/test_spells.py::test_every_spell_in_yaml_is_castable()` を追加する（**xfail** で開始）
- 40.4 8 呪文すべてに**異なる効果**を与える（heal_light/heal_heavy は回復、teleport は安全マスへ移動、haste は 30 ターン速度上昇、beam 系は貫通）
- 40.5 40.3 の `xfail` を外す
**テスト**: `tests/test_spells.py`（1件）＋ 効果別のケース4件
**DoD**: 緑。`spells.yaml` の8キーが全てテストで列挙されていることを assertion で確認

### Step 41: 呪文の効果テスト详細
- 41.1 `tests/test_spells.py::test_beam_spells_hit_all_tiles_in_a_line()` を追加する
- 41.2 `tests/test_spells.py::test_teleport_moves_the_caster_to_a_walkable_safe_tile()` を追加する
- 41.3 `tests/test_spells.py::test_haste_expires_after_its_duration()` を追加する
- 41.4 `tests/test_spells.py::test_heal_spells_never_heal_above_max_hp()` を追加する
**テスト**: `tests/test_spells.py` 合計5件
**DoD**: 5件緑

### Step 42: 「やめる」重生を唯一のAP経路にする
- 42.1 `input_actions.py:441-446` の `WaitAction` を `advance_world()` ではなく `pass_turn()` を呼ぶ実装に変更する（現状は `engine/engine.py` の while が回らず**世界が止まる**）
- 42.2 `tests/test_turn_advance.py::test_wait_advances_the_world()` を追加する（**xfail** で開始）
- 42.3 `WaitAction` に `N` 回の繰り返し待机を追加する
- 42.4 42.2 の `xfail` を外す
**テスト**: `tests/test_turn_advance.py`（1件）
**DoD**: 緑。待機1回で敵が1tick進むことを乱数seed固定で証明

### Step 43: 敵の AI をAP 解決モデルに追従させる
- 43.1 `skill_eater/ai/ai_system.py` の各 `BehaviorNode.execute` が AP を消費するようにする（敵1体は AP 1-2）
- 43.2 `TurnQueue.step_next_actor`（`turn_manager.py:123-145`）は**読むだけ**（A 所有）
- 43.3 `tests/test_enemy_ap.py::test_enemies_have_ap_not_free_actions()` を追加する
**テスト**: `tests/test_enemy_ap.py`（1件）
**DoD**: 緑

### Step 44: 深さボスを実装する（勝利条件の実体）
- 44.1 `data/monsters.yaml` に `void_boss`（`min_floor: 20, max_floor: 30, ai_type: boss`）を追加する
- 44.2 `tests/test_win_condition.py` の `test_reaching_depth_boss_wins()` を実体の `void_boss` に接続する（A が所有するテストだが、B のデータ追加で緑になる）
- 44.3 `data/schemas/monster/monster.json` に `abilities` 配列のスキーマを追加する（44.4 の前倒し）
- 44.4 `tests/test_win_condition.py::test_void_boss_exists_in_data()` を追加する
**テスト**: `tests/test_win_condition.py` の2件が緑
**DoD**: 緑。`void_boss` が `data/monsters.yaml` に1体だけ存在する

### Step 45: 戦闘系の xfail を解く
- 45.1 `tests/test_data_integrity.py::test_every_monster_skill_id_resolves()` の `xfail` はまだ外さない（Step 48 で）
- 45.2 `tests/test_ap_system.py` `tests/test_ranged_attack.py` `tests/test_aiming.py` `tests/test_spells.py` `tests/test_turn_advance.py` `tests/test_enemy_ap.py` を一括実行する
- 45.3 `tests/test_enemy_abilities.py tests/test_enemy_intent.py tests/test_enemy_intent_formation.py` を実行し、**Step 1 の 8 failed からの変化**を記録する（増えたら赤入れ状態で報告）
**テスト**: 上記7ファイル＋敵3ファイル
**DoD**: 新規6ファイル緑。敵系は**减少了**endedだけであることを報告書に書く

### Step 46: 敵能力のスキーマを定義する
- 46.1 `data/schemas/monster/monster.json` に `abilities: [{id, name, cost, cooldown, range, effect}]` を追加する
- 46.2 `data/generated/monster/monster.py` に `MonsterAbility` と `abilities: list[MonsterAbility]` を追加する
- 46.3 `tests/test_monster_ability_schema.py::test_ability_schema_accepts_a_minimal_ability()` を追加する
**テスト**: `tests/test_monster_ability_schema.py`（1件）
**DoD**: 緑

### Step 47: 15 種の能力 id を実定義に解決する
**目的**: 現状 `throw_stone` 等の 15 種のうち **14 種が data のどこにも定義されていない**。
- 47.1 `data/monsters.yaml` の `skills` リストを `abilities` に置き換え、各 id に実体を定義する（`data/spells.yaml` か `data/monster_abilities.yaml` を新規作成）
- 47.2 12 体すべてに、最低 1 つの意味のある能力を与える（slime は分裂、goblin は投石、orc はパワーバッシュ、lich は火球+absorbing）
- 47.3 `tests/test_data_integrity.py::test_every_monster_skill_id_resolves()` の `xfail` を外す
**テスト**: `tests/test_data_integrity.py` xfail 数が 1→0
**DoD**: 緑。`grep -rn "<各id>" data/` で全 id が 2 箇所以上（宣言+定義）出現

### Step 48: `mob.skills` を実際に読ませる
- 48.1 `skill_eater/ai/ai_system.py` に `SelectAbilityNode` を追加し、`actor.abilities` から次の行動を選ぶ
- 48.2 `data_manager.py:448` の `mob.skills` 代入を `mob.abilities` に改名する（**呼び出し元は B のみ**）
- 48.3 `tests/test_enemy_abilities.py` の 21 件を1つずつ緑にする
- 48.4 緑にできないものは**断言」を弱めず**、実装を足して緑にする
**テスト**: `tests/test_enemy_abilities.py`（21件）
**DoD**: 21件緑。**テストファイルは書き換えない**（1件も）

### Step 49: 能力のテストを написа���減る
- 49.1 `tests/test_enemy_abilities.py::test_each_monster_has_at_least_one_ability()` を追加する
- 49.2 `test_ability_declared_in_data_is_executed_by_ai()` を追加する（宣言と実行の**一致**）
- 49.3 `test_ability_cooldown_is_respected()` を追加する
**テスト**: 上記3件
**DoD**: 3件緑。3件とも `mob.abilities` を**反射的に**読むため、データを変えればテストも動く

### Step 50: 詠唱AIの固定 40% とターン浪費を止める
**目的**: `CastSpellAction`（`skill_eater/ai/ai_system.py:187-213`）は `random.randint(8,16)` を**難易度補正なしで**当て、失敗 60% で `return False`（ターン浪費）。
- 50.1 `CalcSpellSuccess` の補正を**プレイヤーと同一の `DifficultyManager`** を通す
- 50.2 失敗時にAPを消費せずagnitude する実装に変更する（return=False は残すが AP は戻す）
- 50.3 `tests/test_enemy_casting.py::test_enemy_spell_damage_respects_difficulty()` を追加する
- 50.4 `tests/test_enemy_casting.py::test_failed_cast_returns_action_points()` を追加する
**テスト**: `tests/test_enemy_casting.py`（2件）
**DoD**: 2件緑

### Step 51: 敵の耐性と属性を入れる
- 51.1 `ecs/entity.py` の `resistances` は読むだけ（A 所有）→ B は `data/monsters.yaml` に `resistances: {fire: 20, cold: -10}` を書き込む
- 51.2 `data/generated/monster/monster.py` に `resistances` を追加する
- 51.3 `tests/test_monster_resistance.py::test_element_resistance_reduces_damage()` を追加する
**テスト**: `tests/test_monster_resistance.py`（1件）
**DoD**: 緑。`resistances` が定義に apply されることを数値で示す

### Step 52: 意図テレグラフをAIに合わせる
**目的**: `enemy_intent.py:42-88` はAI**ツリーを見ずに**距離・HP比・`ai_type` だけで判定するため、`aggressive`/`boss` で「回復」と表示される（嘘）。
- 52.1 `skill_eater/ai/ai_system.py` の各 `BehaviorNode` に `predict_next(self, actor, engine) -> str | None` を実装する
- 52.2 `SelectorNode` は子を順に `predict_next` して最初の非 None を返す
- 52.3 `enemy_intent.py:compute_intent` を `predict_next` の結果を使う実装に置き換える（HP比ハックと `_is_ranged` を削除）
**テスト**: `tests/test_intent_truthfulness.py::test_shown_intent_matches_the_tree_first_action()` を追加する
**DoD**: 緑。5倍数テスト**：12 体 × HP 状態 3 通り = 36 ケースを全走査し、**1 件の食い違いも無い**ことを assertion で強制する

### Step 53: テレグラフの Bulk テスト
- 53.1 `tests/test_intent_truthfulness.py::test_no_telegraph_for_every_monster_hp_band()` を追加する（36 ケースをパラメータ化）
- 53.2 `tests/test_intent_truthfulness.py::test_intent_is_none_for_dead_entities()` を追加する
- 53.3 `tests/test_intent_truthfulness.py::test_intent_is_none_for_non_monster_factions()` を追加する
**テスト**: `tests/test_intent_truthfulness.py`（4件、うち1件は36パラメータ）
**DoD**: 4件緑

### Step 54: 死なない AI を废弃する
**目的**: 7本のツリーのうち `kiter`/`flanker` はデータから到達できない（`ai_role` は名前部分一致 `弓/魔/術` で自動導出、`ecs/entity.py:1114-1123`）。
- 54.1 `data/monsters.yaml` に `ai_role` を明示的に書き込む（12体すべて）
- 54.2 名前部分一致のフォールバックを削除し、未定義は `tactical` に落とす
- 54.3 `tests/test_ai_role_coverage.py::test_every_monster_declares_ai_role()` を追加する
**テスト**: `tests/test_ai_role_coverage.py`（1件）
**DoD**: 緑。名前文字列に依存した挙動がなくなる

### Step 55: 敵AIの回帰テスト
- 55.1 `tests/test_enemy_ai_regression.py` に**8体のai_roleごとの1ターン挙動**を固定するスナップショットを追加する
- 55.2 seed を固定し、同じ seed で同じ行動列になることを assertion にする
- 55.3 `tests/test_enemy_intent_formation.py` の 8 failed のうち、**Phase 2 由来で直ったもの**を1件ずつ緑にする（**テストは書き換えない**）
**テスト**: `tests/test_enemy_ai_regression.py`（1件）＋ `tests/test_enemy_intent_formation.py` の進捗
**DoD**: 緑。残った failed の**理由**を 1件ずつ報告書に書く

### Step 56: サブエージェントBのコミット
- 56.1 `git diff main --name-only` で A 所有ファイル（`engine/engine.py` `ecs/entity.py` `managers/combat_manager.py` `config.yaml` `save_system.py` `main_quest_system.py` `constants.py`）に変更がないことを確認する
- 56.2 A への要求がすべて `docs/compose/spec/combat-resolution.md` に列挙されていることを確認する
- 56.3 `plans/GAME_DESIGN_V2_PHASE2_REPORT.md` を書く（Step 48 の 21件と Step 55 の 8件それぞれの成否）
**テスト**: 直前ステップと同じ
**DoD**: 作業ツリー clean、所有権違反ゼロ

## Phase 3: 戦利品・表示の誠実性（Step 57–72）— サブエージェント C

**所有ファイル宣言**: C は `item_system.py` `data/items.yaml` `data/text/*.yaml` `localization_manager.py` 文書群（`README.md` `COMMERCIAL_EVALUATION_REPORT.md` `NAROU_9_WORLDS_DESIGN.md`）と `tests/test_docs_claims.py` を独占する。A 所有（`engine.py` `ecs/entity.py` `config.yaml` `save_system.py`）にも B 所有（`systems.py` `input_actions.py` `ai_system.py` `data/monsters.yaml`）にも触れない。

### Step 57: 接尾辞のスキーマを定義する
**目的**: 現状 `affix` は `*.py` にも `*.yaml` にも**1件も存在しない**。38品すべてが平坦なステータスで、**床に残す理由が無い**。
- 57.1 `data/schemas/item/affix.json` を新規作成し（`id`/`name`/`slot`/`mods`/`weight`/`tier`）、JSON Schema を書く
- 57.2 `data/item_affixes.yaml` を新規作成し、20 種以上の接尾辞を実装する（`of the vulture`: str+3/dv-2、`of the frail`: endurance-2/dv+3、`glowing`: HP/MP regen など）
- 57.3 `item_system.py` に `Affix` dataclass と `roll_affixes(item, rng) -> Item` を追加する
- 57.4 `tests/test_affix_system.py::test_affix_schema_is_valid()` を追加する
**テスト**: `tests/test_affix_system.py`（1件）
**DoD**: 緑

### Step 58: 接尾辞を実際のアイテムに載せる
- 58.1 `data_manager.py:367-399` の `get_random_item_for_floor` で接尾辞をロールする（`roll_affixes` を呼ぶ）
- 58.2 ロール確率を品質と連動させる（`QUALITY_GOD` は必ず2個、`QUALITY_NORMAL` は確率0.3、`QUALITY_BAD` は禁止）
- 58.3 `tests/test_affix_system.py::test_item_generation_attaches_affixes()` を追加する
- 58.4 `tests/test_affix_system.py::test_affixes_trade_off_two_ways()` を追加する（**必ず損得の両方**を持つ）
**テスト**: `tests/test_affix_system.py`（3件）
**DoD**: 3件緑。**損得の両方が可視**であることを assertion で強制する

### Step 59: 床に残す理由を作るテスト
- 59.1 `tests/test_loot_decision.py::test_two_items_with_same_base_can_differ_by_affix()` を追加する（同一基础・接尾辞違いで**比較可能**であることを示す）
- 59.2 `test_identical_base_and_affix_compare_by_quality()` を追加する
- 59.3 `test_player_has_a_reason_to_leave_a_weaker_item_on_the_floor()` を追加する（**最重要**。これは Step 66 まで xfail）
- 59.4 59.3 を `@pytest.mark.xfail(strict=True, reason="Step 66 で解消")` で導入する
**テスト**: `tests/test_loot_decision.py`（3件、うち1件 xfail）
**DoD**: 緑 + xfail 1件

### Step 60: 鑑定システムを入れる
**目的**: 38品すべてが `identified: true` のため、拾った瞬間に全情報が得られる。
- 60.1 `data/schemas/item/item.json` に `identified: bool = false` と `affix_ids: list[str]` を追加する
- 60.2 `item_system.py` に `identify(item, cost) -> Item` を追加する
- 60.3 `input_actions.py` は B 所有 → C は `item_system.py` に `def can_identify(item) -> bool` を置く（A/B の要求として `plans/GAME_DESIGN_V2_PHASE3_REPORT.md` に記載）
- 60.4 `tests/test_identification.py::test_unidentified_item_hides_its_affixes()` を追加する
- 60.5 `tests/test_identification.py::test_identification_costs_gold()` を追加する
**テスト**: `tests/test_identification.py`（2件）
**DoD**: 2件緑

### Step 61: 鑑定のテストを詳細にする
- 61.1 `tests/test_identification.py::test_identified_item_persists_through_save_load()` を追加する
- 61.2 `test_identification_failure_can_destroy_the_item()` を追加する（失敗率を導入する場合）
- 61.3 `test_gold_is_required_for_identification()` を追加する（経済と接続する）
**テスト**: `tests/test_identification.py`（5件）
**DoD**: 5件緑

### Step 62: 呪いを導入する
**目的**: 現状 `cursed` フラグは `item_system.py:116` に存在するが、生成は `data_manager.py:398` の `random.random() < 0.05` のみで、**.Symbol がない**。
- 62.1 `data/item_affixes.yaml` に `curse_*` を実装する（`curse_of_thinness`: dv-5、`curse_of_glass`: 装備時に HP-3）
- 62.2 `item_system.py:362` の既存 `if item.cursed:` 分岐を、**具体的なペナルティ**を持つようにする
- 62.3 `tests/test_curses.py::test_cursed_item_has_a_named_penalty()` を追加する（名前feld が必ず 具体示例を持つ）
- 62.4 `tests/test_curses.py::test_cursed_item_is_never_better_than_its_clean_twin()` を追加する
**テスト**: `tests/test_curses.py`（2件）
**DoD**: 2件緑。呪いの影響が**文字列ではなく数値**で観測できること

### Step 63: インベントリの選択テスト
- 63.1 `tests/test_loot_decision.py::test_inventory_full_forces_a_choice()` を追加する
- 63.2 `test_drop_verb_exists_and_works()` を追加する（`input_handler.py:452` の Drop が実動していることの固定）
**テスト**: `tests/test_loot_decision.py`（5件）
**DoD**: 5件緑 + xfail 1件

### Step 64: 戦利品フェーズの回帰確認
- 64.1 `tests/test_affix_system.py` `tests/test_identification.py` `tests/test_curses.py` `tests/test_loot_decision.py` を一括実行
- 64.2 既存の `tests/test_inventory*.py` 相当を実行し、pass 数が減っていないことを確認
- 64.3 `plans/DESIGN_V2_BASELINE.md` の Phase 3 欄を実行結果で埋める
**テスト**: 上記4ファイル
**DoD**: 4ファイル緑

### Step 65: 英語テクスチャを実体にする
**目的**: `data/text/en.yaml` は **13バイト・1キー**。ja/ko/zh は 170 キーあり「英語ベースを翻訳する」と書いているが、その英語にそのキーは1つも無い。`localization_manager.py:23` の既定は `en` ＝スタブ。
- 65.1 `ja.yaml` の 170 キー全部に対し、英語テキストを書く（機械翻訳ではなくlust鍛錬の訳。名前・数値・感情を分ける）
- 65.2 `tests/test_i18n.py::test_all_locales_have_identical_key_sets()` を追加する（**xfail** で開始）
- 65.3 65.2 の `xfail` を外す
- 65.4 `localization_manager.py:23` の既定を `ja` に変更する（日本語が主言語の本番向け）
**テスト**: `tests/test_i18n.py`（1件＋既存）
**DoD**: 緑。5ロケール（en/ja/ko/zh-cn/zh-tw）のキー集合が完全一致することを assertion で強制する

### Step 66: 「残す理由がある」を実際に成立させる
- 66.1 `tests/test_loot_decision.py::test_player_has_a_reason_to_leave_a_weaker_item_on_the_floor()` の `xfail` を外す前に、接尾辞の重み付けを_DATABASE_ 上で確認する
- 66.2 同一基础・同一蒙蒙の2品が**比較可能**になるよう、表示に接尾辞を出す（`item_system.py:193` の `to_string`）
- 66.3 `tests/test_loot_decision.py::test_dropping_a_worse_item_is_possible()` を追加する
- 66.4 59.3 の `xfail` を外す
**テスト**: `tests/test_loot_decision.py`（6件）
**DoD**: 緑。xfail ゼロ

### Step 67: 9世界→1世界の文書を実測に合わせる
**目的**: `NAROU_9_WORLDS_DESIGN.md`（35KB）は 9 世界を列挙するが、`data/worlds/` には `skill_eater` の**1つだけ**。`map_engine.py:990-1011` の4帯構造は**デッドコード**（呼出し元0）。
- 67.1 `tests/test_docs_claims.py::test_designed_worlds_have_data_files()` を追加する（**xfail** で開始）
- 67.2 `NAROU_9_WORLDS_DESIGN.md` の先頭に「**現状は1世界のみ実装 / 残り8世界は設計のみ**」の現況欄を追加し、**未実装であることを明記**する
- 67.3 67.1 の `xfail` を残したまま `map_engine.py:990-1011` のデッドコード**削除**を B へ要求する（Phase 2 の Step 23.4 が既に検証している）
- 67.4 `tests/test_docs_claims.py::test_doc_does_not_claim_unimplemented_features()` を追加する
**テスト**: `tests/test_docs_claims.py`（2件、うち1件 xfail）
**DoD**: 緑 + xfail 1件

### Step 68: 商業評価報告の虚偽主張を訂正する
**目的**: `COMMERCIAL_EVALUATION_REPORT.md:30-34` は skill tree / job / reincarnation / pets / guilds / procedural quests の**100%完了**を主張するが、実測は jobs/skill_trees/skill_fusion が**空データ**、procuedural_quest_generator は `config_loader` が存在せず常にフォールバック。
- 68.1 `tests/test_docs_claims.py::test_commercial_report_does_not_claim_100_percent_completion_of_empty_systems()` を追加する（**xfail** で開始）
- 68.2 `COMMERCIAL_EVALUATION_REPORT.md:30-34` の主張を実測値に書き換える（A+/89 → **機械可読な推定**、100% → 実態）
- 68.3 `tests/test_docs_claims.py::test_commercial_report_rating_is_backed_by_a_measurement()` を追加する
- 68.4 68.1 の `xfail` を外す
**テスト**: `tests/test_docs_claims.py`（4件）
**DoD**: 緑。評価の**根拠が本文中に実測値として存在する**ことを assertion で強制する

### Step 69: README の数値を実測に合わせる
- 69.1 `tests/test_docs_claims.py::test_readme_test_count_matches_reality()` を追加する（README:152 の `15 failed, 636 passed` を実測から**動的に生成**する仕組みにする）
- 69.2 README の徽章と数値を実測に合わせる
- 69.3 `README.md:156-158` の「空データファイルは既知の未実装由来」という注記を、Step 4 の `test_no_placeholder_data_files` が緑になったことに合わせて更新する
**テスト**: `tests/test_docs_claims.py`（5件）
**DoD**: 緑

### Step 70: 「表示は真である」を全体テストにする
- 70.1 `tests/test_truthfulness.py::test_no_hud_label_claims_a_value_the_game_does_not_track()` を追加する
- 70.2 `test_no_log_message_promises_a_mechanic_that_does_not_exist()` を追加する（`data/tutorial_guides.yaml` の `first_low_hp` は「[i]で回復ポーション」だが Step 47 まで無意味だった。**今は動く**ことを assertion にする）
- 70.3 `test_every_hud_field_is_backed_by_a_read()` を追加する
**テスト**: `tests/test_truthfulness.py`（3件）
**DoD**: 緑。**広告ではなく実測**であることをテストの構造自体で保証する

### Step 71: 全スイートを緑にする
- 71.1 全サブエージェントのブランチを依存順（A → B → C）にマージする
- 71.2 衝突解決の際、**A 所有ファイルを C が編集していない**ことを再確認する
- 71.3 `pytest tests/` 全実行し、pass 数が `plans/DESIGN_V2_BASELINE.md` の基準以上であることを確認する
- 71.4 `xfail` の残存数を記録する（0であることが目標）
- 71.5 `ruff check` クリーンを確認
**テスト**: 全スイート
**DoD**: 全緑。xfail 0件。1件でも落ちたら**報告して止まる**（無理に進めない）

### Step 72: 計画を確定する
- 72.1 `plans/DESIGN_V2_72_STEPS.md` の各ステップに**実績**（ accomplished / deferred）を書き込む
- 72.2 `plans/GAME_DESIGN_V2_RESULT.md` に 9 方向それぞれについて「測った前 → 測った後」を数値で並べる
- 72.3 `docs/compose/spec/shipping-chain.md` の索引に本計画を登録する
- 72.4 `git commit -m "step-72: 72ステップ計画を確定する"` で全成果を確定する
**テスト**: 全スイート
**DoD**: 作業ツリー clean、9方向すべてに前��後���数値がある

---

## 4. 完了の定義（このプロジェクト全体の）

以下が全て揃って初めて「做完」と呼べる。

| 条件 | 判定方法 |
|---|---|
| 死が状態遷移である | `pytest tests/test_player_death.py` 緑、`grep -rn "GameState.GAME_OVER" ` の代入がConstants の他0件 |
| 勝利条件が存在する | `pytest tests/test_win_condition.py` 緑、`void_boss` がデータに1体 |
| 進行曲線が数値で定義されている | `pytest tests/test_progression_curve.py` 緑 |
| お金が使い切れる | `pytest tests/test_economy.py` 緑、kill毎1100金のバグが0件 |
| 戦闘が「位置と動詞」で決まる | `pytest tests/test_ap_system.py tests/test_ranged_attack.py tests/test_backstab.py` 緑、`x + 3` パターンが `engine/` から消えている |
| 敵が個体である | `pytest tests/test_enemy_abilities.py` 21件緑、`mob.abilities` がAIで読まれている |
| 意図テレグラフが嘘をつかない | `pytest tests/test_intent_truthfulness.py` の36パラメータ全緑 |
| 戦利品が判断になる | `pytest tests/test_loot_decision.py` 緑、xfail 0 |
| 表示が真である | `pytest tests/test_docs_claims.py tests/test_truthfulness.py` 緑 |
| プレースホルダが無い | `pytest tests/test_data_integrity.py` xfail 0 |
| 到達不能が無い | `pytest tests/test_reachability.py` xfail 0 |
| 全部緑 | `pytest tests/` の pass 数が基準以上 |

**この表の各行に「測った値」を書ける状態になったとき、この計画は完了する。文書を漂亮にすることでは完了しない。**
