# DESIGN_V2_BASELINE — テスト基準表

`feature/design-v2` の出発点 `c7def04` で実測した基準。**以降のステップで「pass が減った」を判定するために使う。**
新規に落ちたものだけを回帰とみなす（`既知の赤` は赤字で許容する）。

基準コミット: `c7def04`（`main` = `46ee71d` から `feature/run-carrying` を経由）

---

## 全体基準

| スイート | 実測 | 採取日 |
|---|---|---|
| `main` 全体 | **15 failed / 636 passed** (141.55s) | 2026-10-04（`README.md:152` の記録と一致） |
| Phase 0 高速ゲート | （Step 8 で記入） | |

## スイート別（`c7def04`）

| スイート | 実測 | 備考 |
|---|---|---|
| `test_audio_fallback.py` | 16 passed | 緑（Step `f8c8b4d` で修正済み） |
| `test_input_layer.py` | 22 passed | 緑（`general-2` の成果） |
| `test_tutorial_guides.py` | 23 passed | 緑 |
| `test_enemy_abilities.py` + `test_enemy_intent.py` + `test_enemy_intent_formation.py` | **8 failed / 93 passed** (364.21s) | `general-1` の中断作業。8件は全て `test_enemy_intent_formation.py` の `TypeError: 'NoneType' object is not subscriptable` |

## 高速ゲート（毎ステップで実行する）

```bash
python3 -m pytest tests/test_non_vacuity.py tests/test_data_integrity.py \
                  tests/test_reachability.py tests/test_balance_snapshot.py -q
```

CI は `.github/workflows/ci.yml:28` の `pytest -m "not integration"` で新テストを自動収集するため、
ゲート用の設定変更は不要（計画の Step 8.3 の「`workflow.yaml` への登録」は取りやめた。
`workflow.yaml` はファイル整理用の別物で、テストゲートを入れる場所ではない）。

## 既知の赤（Phase 1/2 で解消する）

- `test_enemy_intent_formation.py` の 8 件: `TypeError: 'NoneType' object is not subscriptable`（`compute_intent` が `None` を返す）
- `general-1` の敵能力 21 件（`c7def04` で中断）

## 計画が導入する xfail（Phase 0）

| テスト | 導入ステップ | 解消ステップ | 現状 |
|---|---|---|---|
| `test_data_integrity.py::test_no_placeholder_data_files` | Step 4 | （D8・将来） | xfail |
| `test_data_integrity.py::test_every_monster_skill_id_resolves` | Step 4 | Step 47 | xfail |
| `test_reachability.py::test_meta_progression_rewards_have_readers` | Step 5 | Step 30 | xfail |
| `test_reachability.py::test_main_quest_rewards_reach_the_player` | Step 5 | Step 27 | xfail |
| `test_reachability.py::test_quest_chain_terminates` | Step 5 | **Step 7（解消済）** | **緑** |

**注意（Step 5 の実施記録）**: 最初の `test_quest_chain_terminates` は `xfail(strict=True)` に
よって **XPASS として即座に落ちた**。原因は `entry.get("id")` で読んでおり、実際のキーは
`quest_id` だったため全エントリが None になり「鎖に break がない」ように見えていた。
これは本リポジトリで4度目となる「緑だが検出力のないテスト」の一例であり、
strict xfail を最初に使ったことで 1 コマンドで検出できた。
修正後は「リストが空でないこと」「全要素に quest_id があること」を明示的に assert している。

**計画からの逸脱（Step 5 の 3件目）**: 当初 `test_meta_progression_rewards_have_readers` は
「全 `reward_bonus` に Python 参照がある」を要求していた。しかし `data/meta_progression.yaml` は
既に各ボーナスに `reserved:` キーとブロック理由をコメントで明記しており、これは
「読める、または明示的に保留されている」という**誠実な形**である。
この状態に対して「参照があること」を要求すると恒久的に xfail のまま残るだけなので、
「**読める、または `reserved:` で保留が宣言されている**」を要求する形に書き換えた。
このテストは現時点で緑であり、将来の退化に対する恒久的なガードになる。

---

## フェーズ別記入欄

### Phase 0（Step 1–9）— 完了

高速ゲート実測: **14 passed, 3 xfailed in 4.43s**（コミット `33b6ef1`）

| テスト | 件数 | 結果 |
|---|---|---|
| `test_non_vacuity.py` | 7 | passed |
| `test_data_integrity.py` | 2 | xfailed（strict） |
| `test_reachability.py` | 3 | 2 passed / 1 xfailed |
| `test_balance_snapshot.py` | 5 | passed |

既存の敵系スイートは **8 failed / 93 passed** のまま（Phase 0 では変化なし）。

### Phase 1（Step 10–32, エージェント A）
（Step 31 で記入）

### Phase 2（Step 33–56, エージェント B）
（Step 45 / Step 56 で記入）

### Phase 3（Step 57–72, エージェント C）
（Step 64 / Step 71 で記入）

---

## 3サブエージェントへの割当（Phase 0 完了後に起動）

| エージェント | ブランチ（`feature/design-v2` から分岐） | worktree | Step |
|---|---|---|---|
| A | `feature/v2-phase1` | `.worktrees/v2-a` | 10–32 |
| B | `feature/v2-phase2` | `.worktrees/v2-b` | 33–56 |
| C | `feature/v2-phase3` | `.worktrees/v2-c` | 57–72 |

**所有権**（同時編集の禁止ファイル）:

| エージェント | 独占編集 | 読み取りのみ |
|---|---|---|
| A | `engine/engine.py` `ecs/entity.py` `ecs/components/components.py` `managers/combat_manager.py` `config.yaml` `save_system.py` `main_quest_system.py` `constants.py` `reincarnation_system.py` | 他全部 |
| B | `systems.py` `input_actions.py` `input_handler.py` `skill_eater/ai/**` `enemy_intent.py` `turn_manager.py` `data/monsters.yaml` `data/spells.yaml` `data/schemas/monster/**` `data/generated/monster/**` | `engine/engine.py` `ecs/entity.py` |
| C | `item_system.py` `data/items.yaml` `data/item_affixes.yaml` `data/text/**` `localization_manager.py` `README.md` `COMMERCIAL_EVALUATION_REPORT.md` `NAROU_9_WORLDS_DESIGN.md` | 他全部 |

各エージェントは自分の Step 終了時に `git diff main --name-only` で
**他エージェントの所有ファイルを1件も触っていないこと**を報告書に書く。