# プロシージャル・クエスト生成システム 強化版 実装計画書（36ステップ）

> 対象：前フェーズで構築したプロシージャル・クエスト生成システムの3つの強化
> ①表示名の日本語ローカライズマップ ②連鎖クエスト（報酬カスケード）の自動生成 ③既存UI（journal_ui/ログブック）への統合表示
> 設計原則：既存の Registry/Manager/Data 3層パターンと ECS コンポーネント永続化に厳密準拠。

---

## フェーズA：事前設計（ステップ 1-4）

### ステップ 1：3提案の要件定義とスコープ確定
前フェーズの検証で判明した課題（敵/アイテムの英語IDがそのまま表示される）を解消する「日本語化」を最優先とし、それに「連鎖クエスト」と「UI統合」を加えた3提案を本計画の対象とする。各提案の完了条件を明文化し、既存の生成器・マネージャ・コンポーネントを壊さず拡張することを前提とする。

### ステップ 2：既存コード調査
`procedural_quest_generator.py` の `_compose`（テンプレート置換箇所）、`GeneratedQuest`/`QuestObjectiveSpec` 構造、`ProceduralQuestManager.complete_quest` のフローを確認。`journal_ui.py` の `render()` が `engine.main_quest_system` のみを描画していることを確認し、生成クエスト用セクションの追加方針を定める。`components.py` の `ProceduralQuestComponent` を確認し連鎖状態の永続化拡張点を洗い出す。

### ステップ 3：データ・拡張スキーマ設計
`data/procedural_scenarios.yaml` の `quest_generation` に `display_names`（enemy/item/stage/difficulty の日英対応）と `chain_config`（max_depth/escalation）を追加する設計を行う。同時に `GeneratedQuest` へ `chain_id/parent_id/depth` を、`QuestObjectiveSpec` へ `cascade_bonus` を追加するデータクラス拡張を設計する。

### ステップ 4：36ステップ分割とテスト戦略定義
本計画のステップ分割（A:1-4 / B:5-12 / C:13-26 / D:27-34 / E:35-36）を確定し、各ステップに対応するテストアサーションを定義する。検証用テスト `tests/test_procedural_quest_enhancement_36_steps.py` を作成し、日本語化・連鎖・UIの3軸をカバーする。

---

## フェーズB：提案1 表示名の日本語ローカライズマップ（ステップ 5-12）

### ステップ 5：display_names セクション追加
`data/procedural_scenarios.yaml` の `quest_generation` に `display_names` トップキーを追加。配下に `enemy`/`item`/`stage`/`difficulty` の4カテゴリを持たせ、英語ID→日本語表示名の対応表を定義する。既存セクションは維持。

### ステップ 6：敵表示名マップ定義
`display_names.enemy` に、敵プールの英語ID（goblin/wolf/slime/skeleton/ghost/golem/ifrit/yeti/crocodile 等）を日本語名（ゴブリン/オオカミ/スライム/スケルトン/ゴースト/ゴーレム/イフリート/イエティ/クロコダイル 等）へ対応させる。これがタイトル/説明文の `{enemy}` 置換に使われる。

### ステップ 7：アイテム表示名マップ定義
`display_names.item` に、報酬プールの英語ID（heal_herb/stone/iron_ingot/steel_ingot/potion_heal/gem 等）を日本語名（癒しのハーブ/石/鉄インゴット/鋼インゴット/回復薬/宝石 等）へ対応させる。`{item}` 置換に使われる。

### ステップ 8：舞台・難易度の表示名追加
`display_names.stage` は既存 `stage_settings.*.name`（街/森/洞窟…）をそのまま利用し、`display_names.difficulty` は `difficulty_tiers.*.name`（序/低/中/高/極/深淵）を利用する。追加定義は最小とし、既存 name を表示名ソースとする。

### ステップ 9：Registry への display_names 読み込み
`QuestGenerationRegistry` に `display_names` 辞書（category→{id→jp}）の読み込みを追加。`load()` 内で `qg.get("display_names", {})` を `_build` 経由で保持する。

### ステップ 10：get_display_name 取得メソッド追加
`QuestGenerationRegistry` に `get_display_name(category: str, id: str) -> str` を追加。該当があれば日本語名を、なければ元の id をそのまま返す（フォールバック）ことで、未定義IDでも壊らないようにする。

### ステップ 11：_compose のテンプレート置換を日本語化
`ProceduralQuestGenerator._compose` 内の `{enemy}`/`{item}`/`{boss}` 置換時に `registry.get_display_name("enemy", enemy)` 等を通すよう改修。説明文の `{setting}` も `get_display_name("stage", setting.id)` に差し替える。難易度はタイトルに含めないが、必要なら `difficulty` カテゴリも利用可能にする。

### ステップ 12：日本語化のテスト
生成クエストの `title`/`description` に英語ID（例 `magma_elemental`, `stone`）が含まれないことをアサーション。全アーキタイプ×舞台のサンプル生成で、日本語表示名が入っていることを確認。

---

## フェーズC：提案2 連鎖クエスト（報酬カスケード）（ステップ 13-26）

### ステップ 13：GeneratedQuest への chain 情報追加
`GeneratedQuest` に `chain_id: str = ""`、`parent_id: str = ""`、`depth: int = 0` を追加。`to_dict`/`from_dict` に対応フィールドを追加し、永続化互換を保つ。

### ステップ 14：QuestObjectiveSpec への cascade_bonus 追加
`QuestObjectiveSpec` に `cascade_bonus: Dict[str, int] = {}` を追加。連鎖の最終目的で追加報酬（名声/友好/メタ）を段階的に与えるために用いる。`to_dict`/`from_dict` に対応。

### ステップ 15：chain_config セクション追加
`quest_generation.chain_config` に `max_depth: 5`、`difficulty_escalation: 1`（ティア+1/階層）、`reward_escalation: 1`（報酬テーブル+1段階）、`cascade_fame_per_depth: 2` 等を定義。

### ステップ 16：連鎖設定の読み込み
`QuestGenerationRegistry` に `chain_config()` 取得メソッドと、`_build` での `chain_config` 保持を追加。

### ステップ 17：generate_followup の実装
`ProceduralQuestGenerator` に `generate_followup(parent: GeneratedQuest, player)` を実装。親と同じアーキタイプ・舞台を引き継ぎ、難易度を1ティア上位（clamp）、報酬を1段階上位（clamp）、`depth = parent.depth + 1`、`chain_id` を共有、`parent_id = parent.quest_id` とする新クエストを生成する。

### ステップ 18：報酬カスケード合成
フォローアップ生成時に、親の報酬を基底とし、深さに応じて `gold`/`exp` を `reward_escalation` に従い乗算、ボーナス（名声/友好/メタ）を `cascade_fame_per_depth * depth` だけ累積加算する。これが「カスケード」の核心。

### ステップ 19：present_followup（提示）の実装
`ProceduralQuestManager` に `present_followup(player, parent)` を追加。完了時に次のフォローアップを生成し、ボード（`active_board`）またはNPC（`npc_pending`）へ追加して提示する。

### ステップ 20：complete_quest での自動フォローアップ
`ProceduralQuestManager.complete_quest` 内で、報酬付与後に `present_followup` を呼び出し、連鎖の次を自動生成・提示する。`depth >= max_depth` の場合はフォローアップを打ち切る。

### ステップ 21：連鎖深度上限と終了条件
`chain_config.max_depth` を超えた場合は生成を停止し、連鎖を自然終了させる。終了時は「一連の任務を完遂した」旨のログを出す。

### ステップ 22：連鎖専用フレーバー文生成
フォローアップの説明文先頭に「《続編》」や「更深き脅威へ…」等の連鎖専用フレーバーを付与し、一連の物語であることを演出する。

### ステップ 23：連鎖状態のセーブ/ロード
`ProceduralQuestComponent` に `active_chains: Dict[str, List[str]]`（chain_id→quest_id列）を追加し、永続化する。ロード後も連鎖の続きが再開できるよう保証。

### ステップ 24：累積報酬の段階的加算
連鎖の各達成で、通常報酬に加え `cascade_bonus`（名声/友好/メタ）を `depth` に応じて加算。`complete_quest` の報酬付与ループに組み込む。

### ステップ 25：連鎖のテスト（ループ完了）
1本のクエストを完了→フォローアップ生成→さらに完了…を `max_depth` 回繰り返し、各段階で報酬が累積し、最終的に連鎖が終了することをアサーション。

### ステップ 26：連鎖の決定論
同一 `chain_id`＋同一シードでは、各階層のフォローアップが常に同一内容になることをアサーション（リプレイ性の保証）。

---

## フェーズD：提案3 既存UI（journal_ui）への統合表示（ステップ 27-34）

### ステップ 27：UI統合方針の策定
`journal_ui.py` の `render()` に「生成クエスト」セクションを追加。メインクエストの表示ブロックの後に、受諾中の生成クエスト一覧（タイトル＋目的進捗）を描画する。既存メインクエスト描画は一切変更しない。

### ステップ 28：engine からマネージャ取得のヘルパ
`journal_ui.render` 内で `engine.procedural_quest_manager`（なければ `engine.systems_mgr.get("procedural_quest_manager")`）を安全に取得するヘルパを追加。存在しない場合はセクションをスキップ。

### ステップ 29：受諾中クエスト一覧の描画
`player.procedural_quest.accepted_quests` から `GeneratedQuest` を復元し、各クエストの `title` をハイライトカラーで描画。空の場合は「生成クエスト: なし」と表示。

### ステップ 30：目的チェックリスト描画
各生成クエストの `objectives` を `✓/○` マーク付きで描画し、`(current_count/required_count)` を表示。メインクエストと同じ表記で統一感を出す。

### ステップ 31：完了通知ログの統合
生成クエスト達成時、`ProceduralQuestManager` は既存 `engine.log`（message_log）へ達成メッセージを出力済み。これを冒険日誌の「完了した記録」セクションに反映できるよう、完了済み生成クエストも記録対象とする。

### ステップ 32：完了済み生成クエストの記録表示
`player.procedural_quest.completed_quest_ids` を `completed_count` 件まで「✓ タイトル」として描画。メインクエストの完了記録ブロックの直下に配置。

### ステップ 33：キー操作で生成クエストセクションへ移動
`handle_input` を拡張し、既存の上下移動に加え、生成クエスト一覧内の選択も `selected_index` で追えるよう調整（簡易実装、既存動作を壊さない範囲）。

### ステップ 34：UI統合のテスト
モック `console` を用い `journal_ui.render` を呼び、受諾中生成クエストのタイトルと目的進捗が描画されることをアサーション（tcod に依存しない簡易モックで検証）。

---

## フェーズE：統合・テスト（ステップ 35-36）

### ステップ 35：36ステップ総合テスト作成
`tests/test_procedural_quest_enhancement_36_steps.py` を作成し、各ステップを番号付きアサーションで検証。日本語化（英語ID非含有）、連鎖（ループ完了＋決定論＋累積報酬）、UI（render描画）の3軸すべてをカバー。

### ステップ 36：最終検証
`pytest tests/test_procedural_quest_enhancement_36_steps.py` を全ステップ成功させる。併せて既存の `test_procedural_quest_generation_36_steps.py` / `test_procedural_quest_gameplay_hook.py` も緑を維持することを確認し、手動検証チェックリスト（ボード生成→受諾→討伐→完了→日本語表示→連鎖続編→日誌反映）を満たす。

---

## 成果指標（KPI）
- 日本語化率：生成クエスト表示の英語ID含有率 0%（=100%日本語化）。
- 連鎖持続性：max_depth 回の連鎖完了で報酬が階層的に累積し、深いほど報酬が指数増加。
- UI可視性：冒険日誌で生成クエストの受諾/進捗/完了が追跡可能。
- リプレイ性：同一シード再現率 100%、連鎖系列も決定論的に再現。

---

## 付録：具体的なデータ例と実装メモ（ステップの詳細補足）

### 付録1：display_names の YAML 例（ステップ 5-8 の具体像）
```yaml
quest_generation:
  display_names:
    enemy:
      goblin: "ゴブリン"
      wolf: "オオカミ"
      slime: "スライム"
      skeleton: "スケルトン"
      ghost: "ゴースト"
      golem: "ゴーレム"
      fire_lizard: "ファイアリザード"
      magma_elemental: "マグマエレメンタル"
      ifrit: "イフリート"
      yeti: "イエティ"
      crocodile: "クロコダイル"
      abyssal_horror: "アビサルホラー"
      void_lord: "ヴォイドロード"
      bandit: "バンディット"
      pickpocket: "スリ"
    item:
      heal_herb: "癒しのハーブ"
      stone: "石"
      iron_ingot: "鉄インゴット"
      steel_ingot: "鋼インゴット"
      potion_heal: "回復薬"
      gem: "宝石"
      ancient_book: "古代魔導書"
      dragon_scale: "竜の鱗"
      holy_relic: "聖なる遺物"
    stage:   # 既存 stage_settings.*.name を流用
      town: "街"
      forest: "森"
      cave: "洞窟"
      ruins: "遺跡"
      volcano: "火山"
      snowfield: "雪原"
      swamp: "沼"
      abyss: "深淵"
    difficulty:  # 既存 difficulty_tiers.*.name を流用
      tutorial: "序"
      easy: "低"
      normal: "中"
      hard: "高"
      extreme: "極"
      abyss: "深淵"
```
実装メモ：`get_display_name(category, id)` は `self._display_names.get(category, {}).get(id, id)` を返すだけで十分。未定義IDは元の文字列を返すため、どんな組み合わせでも壊らない。

### 付録2：日本語化前後の比較（ステップ 11-12 の検証基準）
- 日本語化前（検証時に確認された課題）：`火山のmagma_elemental討伐` / `洞窟のstone採取`
- 日本語化後（期待値）：`火山のマグマエレメンタル討伐` / `洞窟の石採取`
テストでは「生成タイトルおよび説明文に a-z のみの連続文字列（英語ID）が含まれない」ことを正規表現でアサーションする。ただし「ゴブリン」等の日本語や記号は許容。

### 付録3：chain_config の YAML 例（ステップ 15-16 の具体像）
```yaml
quest_generation:
  chain_config:
    max_depth: 5
    difficulty_escalation: 1     # 階層ごとに難易度ティア+1
    reward_escalation: 1        # 階層ごとに報酬テーブル+1段階
    gold_multiplier_per_depth: 1.5
    exp_multiplier_per_depth: 1.4
    cascade_fame_per_depth: 2
    cascade_relationship_per_depth: 1
    cascade_meta_per_depth: 1
```

### 付録4：連鎖エスカレーションの計算メモ（ステップ 17-18, 24）
- 難易度インデックス：difficulty_order 内の位置を `i` とし、次階層は `min(len-1, i + difficulty_escalation)` のティアを採用（clamp で上限）。
- 報酬テーブルも同様に `min(len-1, j + reward_escalation)`。
- 報酬 gold は `base_gold * (gold_multiplier_per_depth ** depth)` で階層ごとに指数増加。これが「指数拡張」を連鎖でも担保する。
- cascade_bonus は `fame = cascade_fame_per_depth * depth` 等で段階加算し、`complete_quest` の報酬付与ループで `player.guild_contribution += fame` / `relationship` / `meta_progression` へ反映。

### 付録5：連鎖専用フレーバー例（ステップ 22）
- depth==1: `《続編》`
- depth>=2: `《第{n}章》更深き脅威へ…`
- 最終階層手前: `《終幕》`
フォローアップ生成時に `description` 先頭へ挿入。連鎖の context を player が直感的に理解できるよう演出。

### 付録6：UI統合の描画レイアウト想定（ステップ 27-34）
冒険日誌の既存「現在の目標（メインクエスト）」ブロックの直下に以下を追加：
```
【生成クエスト（受諾中）】
  📌 火山のマグマエレメンタル討伐
     ○ マグマエレメンタルを討ち取れ (0/1)
  📌 森の深層調査
     ● 8階層まで踏破 (3/8)
【完了した生成クエスト】
  ✓ 街の石採取
  ✓ 遺跡のスケルトン討伐
```
実装メモ：`journal_ui.render` 内は既存メインクエスト描画を一切変更せず、`current_y` をそのまま流用して続きに描画。ウィンドウ高さ（window_height=20）が足りない場合は、生成クエスト表示を `max_depth` 件で打ち切り「…他」と省略。

### 付録7：エッジケースと対応方針
- 連鎖中にプレイヤーがボードをリフレッシュした場合：`active_chains` に親クエストが残るため、フォローアップは `parent_id` 経由で再提示され、連鎖が維持される。
- 同一 chain_id のフォローアップが重複生成されないよう、`present_followup` は `active_chains[chain_id]` に既に含まれる場合はスキップ。
- 日本語表示名が未定義の敵/アイテムが将来追加された場合でも `get_display_name` のフォールバックにより英語IDがそのまま出るだけでクラッシュしない。
- セーブ/ロード後：連鎖状態も `ProceduralQuestComponent.active_chains` 経由で復元され、再開時に続きのフォローアップが生成される。

### 付録8：テスト分割の最終形（ステップ 35-36）
テスト関数を3ブロックに分け、それぞれが独立してグリーンになるよう設計：
1. 日本語化ブロック（ステップ 5-12 相当）：全組み合わせサンプルで英語ID非含有を確認。
2. 連鎖ブロック（ステップ 13-26 相当）：max_depth ループ完了＋決定論＋累積報酬の検証。
3. UIブロック（ステップ 27-34 相当）：モック console で render が生成クエストを描画することを検証。
最後に既存2テスト（`test_procedural_quest_generation_36_steps.py` / `test_procedural_quest_gameplay_hook.py`）も緑を維持することを確認し、回帰がないことを保証。
