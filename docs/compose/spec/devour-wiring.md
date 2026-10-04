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

取得先は `self.game_state_data.world_a_data["skills"]` というリスト (`engine/engine.py:998`) で、読み手は fusion 炉と HUD のSkills カウンタのみ。プレイヤーが実際に唱えるスキルは `player.skills` にあり、devour はそこに一切書かない。**奪った能力は使い物にならない。**

`player.skills` に書く実装は `skill_awakening_system.py:127` と `skill_fusion_system.py:303` のみで、どちらも devour の経路上にない。

### S1.3 モンスターが参照するスキルが定義されていない

`data_manager.py:124` は `self.skills = SkillRepository({})` とハードコードされており、コメントにも「スタンドアロン skills.yaml は未定義のため空リポジトリ」とある。`SkillRepository.get()` は定義済みのスキルを含め全 id で None を返す。

`data/monsters.yaml` は 12 体に対し 15 のスキル id を参照するが、`backstab` 以外の 14 個はいずれの data ファイルにも定義がない。`data_manager.py:448` が `mob.skills` へコピーするのはその文字列リストにすぎない。

## [S2] Design

### S2.1 devour は倒された敵の実データを読む

- `CharacterState` を倒した敵の実データから構成する。既存の `Entity` が保持する属性と `mob.skills`（`data_manager.py:448` が設定する文字列リスト）をそのまま反映させ、固定値の既定値を使わない。
- `engine/engine.py:983` の `if not target_state.skills: add_skill("com_combat_001")` を削除する。敵が実際に持つスキルのない個体（`skills: []` の 4 体）に対しては、奪取が成立しないのが正しい挙動であり、既定値を差し入れる gimmic は要らない。
- 奪取対象は敵が実際に持つスキルのうち 1 つとし、複数保有時は敵の並び順の先頭とする。抽選は不要で、敵Different なら結果 Different であることが契約である。

契約: `skills` が異なる 2 体を倒すと、記録される奪取スキル id も異なる / `skills` が空の敵を倒すと奪取は不成立になり、スキルが增えない。

### S2.2 奪ったスキルは唱えられる形で得る

- 奪取に成功したとき、実行可能スキルを追加する既存の経路（`Entity.skills` が保持する、`ecs/entity.py:1248-1252` の `gain_skill_exp` が読むのと同じ辞書）へ登録する。
- `world_a_data["skills"]` への run 記録は残す。HUD 表示と fusion 炉が既に読んでいるため。
- 登録に失敗した場合（id が解決できない等）は、記録せず理由をログに残す。黙って失敗したonga ように見せない。

契約: 奪取成功後、プレイヤーの実行可能スキル集合にその id が含まれる / 同じ敵を 2 体倒すと集合は増えない（重複排除）。

### S2.3 参照されているスキルを解決できるようにする

- `data_manager.py:124` の `SkillRepository({})` を実データで埋める。読み込み元は既存の data 配置に従い、紗存のスキーマから生成したモデルを壊さない。
- `data/monsters.yaml` が参照する 15 id すべてが解決できる状態にする。定義が無い 14 id については、実際に名前と効果を持つデータを与える。既存の `data/worlds/skill_eater/skills.yaml` と同じ記法に揃え、既存 id（`com_combat_001` 等）を壊さない。
- 未知 id を参照するモンスターは、実行時に握り潰さずログで明示する。未知のまま放置すると S1.1 の再incarnation に戻る。

契約: `DataManager()` の `skills` が空でない / `data/monsters.yaml` が参照する全 id が `SkillRepository.get()` で解決する / `mob.skills` の id を実際に解決できないモンスターが実行時に握り潰されない。

### S2.4 リグレッション防止テスト

- `tests/test_devour.py` — S2.1〜S2.3 の契約。敵 Different なら奪取 id Different / スキル無しの敵では奪取不成立 / 奪取成功で `player.skills` に入る / 重複獲得しない / `DataManager().skills` が空でない / モンスター参照 id が全て解決する。
- 既存 15 件の既知失敗は本 feature の残件ではない。

## [S3] Out of Scope

- `skill_eater/combat/engine.py:604` の `execute_devour` 本体の移植・統合。暗号スキルのゲート条件、罠のウイルスダメージ、擬態解除、husk 状態といった詳細な挙動の書き直しは本 feature の外であり、本 feature が扱うのは現在の production 経路が「敵の実データを読んでプレイヤーに渡す」最低限の事実を成立させること。受け皿を整えたうえで統合する。
- acious したスキルの视觉效果・SE・专用 UI。
- fusion・awakening・inheritance とのより深い連結。
- `data_manager.py` 以外の未宣言リポジトリ（jobs / skill_trees / skill_fusions が空である件）。案C の領域であり、本 feature は `skills` だけを対象にする。
- equilibrium（`calculate_devour_rate`）の式変更。現行式をそのまま使う。

## Tasks

- [ ] T1: devour が倒した敵の実データから奪取対象を選ぶようにする。固定値の `CharacterState` と `add_skill("com_combat_001")` の既定差し入れを廃止する — acceptance: `skills` が異なる 2 体から異なるスキル id が記録され、`skills` が空の敵では奪取が成立しない (covers: S2.1)
- [ ] T2: 奪取成功時に奪ったスキルを実行可能スキルへ登録する — acceptance: 奪取後に `player.skills` にその id が含まれ、同じ敵を 2 回倒しても増えない (covers: S2.2)
- [ ] T3: `data_manager.py` の空 `SkillRepository({})` を実データで埋め、`data/monsters.yaml` が参照する 15 id を全て解決できるようにする — acceptance: `DataManager().skills` が空でなく、モンスター参照 id が全て解決し、未知 id は握り潰さずログに残る (covers: S2.3)
- [ ] T4: リグレッション防止テスト `tests/test_devour.py` を追加する — acceptance: 各テストが S2.1〜S2.3 の不具合を再現する形で失敗し、T1〜T3 適用後は全て成功する (covers: S2.1, S2.2, S2.3)