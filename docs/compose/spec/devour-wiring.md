---
feature: devour-wiring
status: designed
updated: 2026-10-04
branch: feature/devour
commits:
---

# 案B 「喰う」を成立させる

## Report

## [S1] Problem

### S1.1 喰った enemy's LSR はいつも同じになる

`engine/engine.py` の devour 経路は `CharacterState` を倒された敵から作っているように見えるが、実際には固定値で組み立てている。

- `atk=15 / defense=10 / intelligence=15 / speed=100` (`engine/engine.py:958-969`)
- 対象側の `mp=10 / intelligence=5 / speed=80` (`engine/engine.py:974-981`)
- `CharacterState` には一度もスキル不入らないため、`if not target_state.skills:` が常に成立し `target_state.add_skill("com_combat_001")` (`engine/engine.py:983`) が毎回発火する
- 直後の `remove_skill("com_combat_001")` (`engine/engine.py:988`) も同じ固定 id を使う

結果、どの敵を倒しても取得するスキルは常に `com_combat_001`（初級剣術）で、獲得率がいくら変動しても「何を買うか」の判断が成立しない。

### S1.2 喰ったスキルは使えない

取得先は `self.game_state_data.world_a_data["skills"]` というリスト (`engine/engine.py:998`) で、読み手は fusion 炉と HUD のSkills カウンタのみ。`player.skills` にも一切書かない。

ここで注意すべきは、`player.skills` が「唱えられるスキル集合」ではないという点である。実測した構造は次の3層に分かれている。

- `Entity.skills` (＝`player.skills`) — 所有者フラグと成長用の入れ物。読み手は `gain_skill_exp` と数箇所の真偽判定のみ
- `CharacterState.skills` — 実質的な戦闘用の呪術書。これが詠唱される
- `SkillEaterRegistry` — 定義

`cast_skill` 等の汎用詠唱動詞はリポジトリに存在せず、`player.skills` をキーとする詠唱経路も無い。`player.skills` に書く実装は `skill_awakening_system.py:127` と `skill_fusion_system.py:303` のみで、どちらも devour の経路上にない。

したがって devour が「何をするか」を3層で切り分けると、奪取そのものは成立する（どの敵を倒したかが結果を変える）が、**取得した能力は依然として詠唱できない**。本次は所有権の獲得までを成立させ、詠唱への接続は行わない（`[S3]`）。

### S1.3 モンスターが参照するスキルが定義されていない

`data_manager.py:124` は `self.skills = SkillRepository({})` とハードコードされており、コメントにも「スタンドアロン skills.yaml は未定義のため空リポジトリ」とある。`SkillRepository.get()` は定義済みのスキルを含め全 id で None を返す。

`data/monsters.yaml` は 12 体に対し 15 のスキル id を参照するが、`backstab` 以外の 14 個はいずれの data ファイルにも定義がない。`data_manager.py:448` が `mob.skills` へコピーするのはその文字列リストにすぎない。

## [S2] Design

### S2.1 devour は倒された敵の実データを読む

- `CharacterState` を倒した敵の実データから構成する。既存の `Entity` が保持する属性と `mob.skills`（`data_manager.py:448` が設定する文字列リスト）をそのまま反映させ、固定値の既定値を使わない。
- `engine/engine.py:983` の `if not target_state.skills: add_skill("com_combat_001")` を削除する。敵が実際に持つスキルのない個体（`skills: []` の 4 体）に対しては、奪取が成立しないのが正しい挙動であり、既定値を差し入れる gimmic は要らない。
- 奪取対象は敵が実際に持つスキルのうち 1 つとし、複数保有時は敵の並び順の先頭とする。抽選は不要で、敵が異なれば結果も異なることが契約である。

契約: `skills` が異なる 2 体を倒すと、記録される奪取スキル id も異なる / `skills` が空の敵を倒すと奪取は不成立になり、スキルが増えない。

### S2.2 奪ったスキルは「所有した」状態として既存システムから見えるようにする

**本節は「唱えられる」を目標としない。** 仕様初稿は「唱えられる形で得る」と書いていたが、S1.2 のとおり `player.skills` は詠唱可能な器ではない。詠唱は `CharacterState.skills` 上で起こり、devour はプレイヤーの `CharacterState` を触らない。詠唱への接続は `[S3]` の別 feature とする。本次が成立させる事実は「奪った id が `player.skills` に登録され、既存システム（合成・覚醒・施設）から見える所有権になる」ことまでである。

- 奪取に成功したとき、`Entity.skills`（`ecs/entity.py:1248-1252` の `gain_skill_exp` が読むのと同じ辞書）へ登録する。値は `ecs/components/components.py:285` の `Skill` インスタンスとし、`.name` / `.level` / `.experience` / `.potential` を曝露する。
- `world_a_data["skills"]` への run 記録は残す。HUD 表示と fusion 炉が既に読んでいるため。
- 登録に失敗した場合（id が解決できない等）は、記録せず理由をログと画面の両方に残す。黙って失敗したように見せない。

**偽りの禁止**: 画面・ログ・仕様書のいずれも、取得した id が「唱えられる」「発動する」ことを示す語を使ってはならない。今回の範囲ではそれは成立しない。案内文は「獲得した」「登録した」に限る。

契約: 奪取成功後、`player.skills` にその id が `Skill` インスタンスとともに登録される / 同じ敵を 2 体倒すと増えない（重複排除）/ 解決できない id はログと画面の双方に残る。

### S2.3 参照されているスキルを解決できるようにする

- `data_manager.py:124` の `SkillRepository({})` を実データで埋める。読み込み元は既存の data 配置に従い、紗存のスキーマから生成したモデルを壊さない。
- `data/monsters.yaml` が参照する 15 id すべてが解決できる状態にする。定義が無い 14 id については、実際に名前と効果を持つデータを与える。既存の `data/worlds/skill_eater/skills.yaml` と同じ記法に揃え、既存 id（`com_combat_001` 等）を壊さない。
- 未知 id を参照するモンスターは、実行時に握り潰さずログで明示する。未知のまま放置すると S1.1 の再incarnation に戻る。

契約: `DataManager()` の `skills` が空でない / `data/monsters.yaml` が参照する全 id が `SkillRepository.get()` で解決する / `mob.skills` の id を実際に解決できないモンスターが実行時に握り潰されない。

### S2.4 リグレッション防止テスト

- `tests/test_devour.py` — S2.1〜S2.3 の契約。敵が異なれば奪取 id も異なる / スキル無しの敵では奪取不成立 / 奪取成功で `player.skills` に `Skill` インスタンスとともに登録される / 重複獲得しない / `DataManager().skills` が空でない / モンスター参照 id が全て解決する。**「唱えられる」ことを検証するテストは書かない** — 今回それは成立しないため、そのテストは嘘になる。
- 既存 15 件の既知失敗は本 feature の残件ではない。

## [S3] Out of Scope

- **奪ったスキルの詠唱接続**。`player.skills` は所有権の入れ物であり、詠唱は `CharacterState.skills` 上で起こる。devour の取得でプレイヤーの永続 `CharacterState` に書き込む経路と、そこから技を使う動詞の新設が必要で、本 feature の S3 を超える。別 feature とする。
- `skill_eater/combat/engine.py:604` の `execute_devour` 本体の移植・統合。暗号スキルのゲート条件、罠のウイルスダメージ、擬態解除、husk 状態といった詳細な挙動の書き直しは本 feature の外であり、本 feature が扱うのは現在の production 経路が「敵の実データを読んでプレイヤーに渡す」最低限の事実を成立させること。受け皿を整えたうえで統合する。
- 獲得したスキルの視覚効果・SE・専用 UI。
- fusion・awakening・inheritance とのより深い連結。
- `data_manager.py` 以外の未宣言リポジトリ（jobs / skill_trees / skill_fusions が空である件）。案C の領域であり、本 feature は `skills` だけを対象にする。
- 奪取率（`calculate_devour_rate`）の式変更。現行式をそのまま使う。

## Tasks

- [ ] T1: devour が倒した敵の実データから奪取対象を選ぶようにする。固定値の `CharacterState` と `add_skill("com_combat_001")` の既定差し入れを廃止する — acceptance: `skills` が異なる 2 体から異なるスキル id が記録され、`skills` が空の敵では奪取が成立しない (covers: S2.1)
- [ ] T2: 奪取成功時に奪った id を `player.skills` へ「所有権」として登録する。詠唱可能なのは `CharacterState.skills` であり本次は接続しない — acceptance: 奪取後に `player.skills` にその id が `Skill` インスタンスとともに登録され、同じ敵を 2 回倒しても増えない。画面・ログに「唱えられる」語を使わない (covers: S2.2)
- [ ] T3: `data_manager.py` の空 `SkillRepository({})` を実データで埋め、`data/monsters.yaml` が参照する 15 id を全て解決できるようにする — acceptance: `DataManager().skills` が空でなく、モンスター参照 id が全て解決し、未知 id は握り潰さずログに残る (covers: S2.3)
- [ ] T4: リグレッション防止テスト `tests/test_devour.py` を追加する — acceptance: 各テストが S2.1〜S2.3 の不具合を再現する形で失敗し、T1〜T3 適用後は全て成功する (covers: S2.1, S2.2, S2.3)