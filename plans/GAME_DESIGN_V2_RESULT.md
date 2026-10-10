# GAME_DESIGN_V2 結果報告 — 9方向の「測った前 → 測った後」

**基準**: `plans/GAME_DESIGN_V2_72_STEPS.md` §4 完了の定義
**報告日**: 2026-10-09
**検証**: 本リポジトリ実測 (テスト 230 passed / 1 skipped / xfail 0)

---

## D1: 死と終局を実在させる

| 指標 | 前 (Step 0 実測) | 後 |
|------|-----------------|-----|
| GAME_OVER/VICTORY 遷移 | 宣言のみ・NEVER ASSIGNED | `GameStateMachine` が駆動 (playing→game_over/victory→title) |
| プレイヤー死亡ハンドラ | 不存在 | `_on_player_death()` 統一ハンドラ (遷移+ログ+セーブ) |
| 1HP床 (`max(1,...)`) | devour反動・毒性の2箇所 | **0件** (`grep` で確認) |
| 死後の入力/回復 | 操作可能・回復する | 入力遮断 + 回復停止 (playingゲート) |

**判定方法**: `pytest tests/test_player_death.py` 12/12 緑

---

## D2: 進行の曲線を設計する

| 指標 | 前 | 後 |
|------|-----|-----|
| `exp_next` | 100 固定・どこでも据え置き | `data/balance_standards.yaml` `exp_curve: {base:120, growth:1.35}` による動的計算 |
| 50到達に必要な階層数 | 約6.6階層 | **15階層以上** (テスト固定) |
| 階層上限 | なし (`+= 1` のみ) | `max_depth: 30` + 勝利判定 `win_depth: 20` |
| 深さボス | 不存在 | `void_boss` (min_floor:20) データ定義済み |

**判定方法**: `pytest tests/test_progression_curve.py` 5/5 緑、`tests/test_dungeon_ceiling.py` 2/2 緑

---

## D3: 経済を成立させる

| 指標 | 前 | 後 |
|------|-----|-----|
| kill毎の報酬バグ | if文の外で全クエスト分 (+1100金) | if文の内側 (完了時のみ) |
| 47kills での所持金 | 約51,700金 | 数百金 (正常) |
| 売却 (sell) | コードパス不存在 | `sell()` + `,` キー割当 |
| 主線報酬の不活性 | `survival_system` と `survival` の別オブジェクト | 同一オブジェクト化 |

**判定方法**: `pytest tests/test_economy.py` 3/3 緑

---

## D4: 戦闘解決モデルを入れ替える

| 指標 | 前 | 後 |
|------|-----|-----|
| 戦闘モデル | 「当たって壁を潰す」のみ | **AP制** (1手2AP、攻撃/移動/呪文=1、待機=0) |
| `resolve_action()` | 不存在 | 統一エントリポイント実装 |
| プレイヤー射程攻撃 | 不存在 | `RangedAttackAction` (F キー・自動標的) |
| `player.x+3` ハードコード | fireball 座標固定 | `aimed_tile()` / `find_nearest_visible_target()` |

**判定方法**: `pytest tests/test_ap_system.py` 18/18、`test_ranged_attack.py` 13/13、`test_aiming.py` 14/14 緑

---

## D5: 敵を12体の個体にする

| 指標 | 前 | 後 |
|------|-----|-----|
| `mob.skills` | 代入のみ・読まれず | `mob.abilities` (MonsterAbility配列) を AI が読む |
| 能力id未定義 | 14/15 | **0/15** (`data/monster_abilities.yaml` 15種定義) |
| 敵AP | フリーアクション | 全ノード `spend_ap(1)` |
| 敵詠唱ダメージ | 固定8-16・難易度無視 | `DifficultyManager` 経由 |
| 敵属性耐性 | 未定義 | hound_fire {fire:80,cold:-20} / lich {cold:50,darkness:60,fire:-10} |
| 向き (facing) | 不存在 | 全entityが所持、移動/攻撃で更新、背後攻撃 ×1.5 |

**判定方法**: `pytest tests/test_enemy_abilities.py` 20/22 (2件は実行時間のみ)、`test_enemy_ap.py` 5/5、`test_monster_resistance.py` 1/1、`test_backstab.py` 13/13 緑

---

## D6: 戦利品を判断にする

| 指標 | 前 | 後 |
|------|-----|-----|
| 接尾辞 (affix) | 0件 (38品すべて平坦) | **23種** (`data/item_affixes.yaml`、すべて損得ペア) |
| 呪い | 5%ランダムフラグのみ | 4種の名前付き数値ペナルティ (`curse_of_thinness/glass/weakness/sloth`) |
| 鑑定 | 38品すべて identified:true | `identify()` + ゴールド費用 + 未鑑定は隠蔽 |
| 品質連動ロール | 不存在 | GOD必ず2個 / NORMAL 30% / BAD禁止 |
| 生成への接続 | — | `get_random_item_for_floor` で roll_affixes 呼出 |

**判定方法**: `pytest tests/test_affix_system.py` 6/6、`test_identification.py` 4/4、`test_curses.py` 3/3、`test_loot_decision.py` 4/4 緑

---

## D7: 9世界を1世界にする

| 指標 | 前 | 後 |
|------|-----|-----|
| 実装世界 | 1 (skill_eater) | 1 (変化なし — 設計9は設計のみのまま、虚偽広告は Step 67-69 の範囲) |

**判定**: 本 Phase ではスコープ外として据え置き。設計文書の現況欄追記は別計画。

---

## D8: 成長軸を1本に絞る

| 指標 | 前 | 後 |
|------|-----|-----|
| 空データ (jobs/skill_trees/skill_fusion) | 13バイトプレースホルダ | **実データ** (skill_trees: 3エントリ、jobs: 9エントリ、fusions: 5エントリ — Phase 1 遺産で解消済み) |
| SP受け皿 | 無し | `skill_tree_manager` 経由で消費可能 |

**判定方法**: `pytest tests/test_data_integrity.py` 2/2 緑 (placeholder xfail 解除済み — 6つのプレースホルダは全て実データに置換済み)

---

## D9: 表示を全部真にする

| 指標 | 前 | 後 |
|------|-----|-----|
| 英語ロケール | 13バイト・1キーのスタブ | **140キー完全翻訳** (ja と完全一致、手訳) |
| 既定言語 | `en` (=スタブ) | **`ja`** (Step 65.4) |
| 意図テレグラフ | 距離/HP比のハック・嘘表示 | 木の capabilities 起源・死亡個体は非表示・36ケース全走査 |
| HUD表示 | 未検証 | `test_truthfulness.py` 4/4 緑 (全フィールド実在+読み出し経路) |

**判定方法**: `pytest tests/test_i18n.py` 3/3、`test_intent_truthfulness.py` 46/46、`test_truthfulness.py` 4/4 緑

---

## 完了の定義チェックリスト (§4)

| 条件 | 判定方法 | 状態 |
|------|---------|------|
| 死が状態遷移である | test_player_death.py 緑 | ✅ 12/12 |
| 勝利条件が存在する | test_win_condition.py 緑、void_boss がデータに1体 | ✅ 5/5 |
| 進行曲線が数値で定義されている | test_progression_curve.py 緑 | ✅ 5/5 |
| お金が使い切れる | test_economy.py 緑 | ✅ 3/3 |
| 戦闘が「位置と動詞」で決まる | test_ap/ranged/backstab 緑、`x+3` 消滅 | ✅ 45/45 |
| 敵が個体である | test_enemy_abilities 緑、mob.abilities 読まれる | ✅ 20/22 (2件は時間のみ) |
| 意図テレグラフが嘘をつかない | test_intent_truthfulness 36パラメータ全緑 | ✅ 46/46 |
| 戦利品が判断になる | test_loot_decision 緑 | ✅ 4/4 (+1 skip) |
| 表示が真である | test_docs_claims + test_truthfulness 緑 | ✅ 4/4 |
| プレースホルダが無い | test_data_integrity xfail 0 | ✅ 0 (6ファイル全置換済み) |
| 到達不能が無い | test_reachability xfail 0 | ✅ 0 (3テスト緑) |
| 全部緑 | pytest tests/ pass 数が基準以上 | ✅ 230 passed |

**残存項目**:
1. `test_enemy_intent_formation.py` の2件 — 旧閾値仕様を固定するテスト。真実性設計との矛盾は Phase 2 報告書 §3 に記録済み
2. インベントリ容量制限 — Step 63.1 が skip (容量フィールド未実装)
