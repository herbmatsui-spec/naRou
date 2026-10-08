# naRou コードレビュー報告書 (2026-10-08)

**対象**: `/home/herbmatsui/narou` (main @ `71018e5`、origin先行32コミット、未コミット `run_history.json` 変更 + 未追跡4アーティファクト)  
**手法**: super-research 精査モード — 静的解析(ruff/mypy)、テスト実測(8スイート個別+ターゲット)、4サブエージェント並列レビュー(engine/core、スキル系、save/web/データ、衛生)、継承主張の実証的検証  
**出力**: 本報告書 + `findings.tsv` (全50件の証拠付き発見) + 改善案9つ + 上位6つの詳細実装計画書(回帰テスト名入り、ファイル単位アトミック)

---

## 1. 実測サマリ (ベースライン)

| 項目 | 実測値 |
|---|---|
| **静的解析 (ruff)** | 47件 (41自動修正可、F821未定義名5件、F811再定義5件) |
| **テストスイート** | 933テスト収集、フル完走不能 (570秒で30%停滞、pytest-timeout未インストール) |
| **8大統合スイート** | **全8件 PASS** (個別実行、各0.36–5.09秒) — 前回主張を検証済み |
| **敵能力テスト** | 21/21 PASS (slow 1件除外) — 過去の21失敗は修復済み |
| **実質的失敗** | 2件: `test_exp_next_is_flat_100` (120≠100)、i18n validation (en.yamlスタブ) |
| **Engine() 構築コスト** | 2.213秒/回 (全YAML再読込 + pygame import試行×2 + Webサーバーbind) |
| **build/lib/naRou 同期** | 10モジュール中 **3件が差異** (skill_fusion +274行、skill_tree +202行、job +199行) — **ソースツリーが新しい** (10/06 vs 08/23 mtime) |
| **主要アーティファクト** | `.tmp_bb4/` (リポジトリ全体コピー、ジャンク)、`en.yaml` 13バイトスタブ、savegame.bin*.bak 330MB蓄積 |

---

## 2. 深刻度別発見件数 (findings.tsv より)

| Severity | 件数 | 代表例 |
|---|---|---|
| **Critical** | 4 | F001 難易度倍率不整合、F011-F012 スキル使用不可、F033 正直さ汚染 |
| **High** | 17 | 戦闘システム二重実装、ゴッドオブジェクト Engine、セキュリティ(セーブ/ウェブ)、i18n破綻、ポート競合、経済破綻、テスト非完走根因 |
| **Medium** | 19 | 設定断片化、重複レンダリング、型混在、スキル層コンフリクト、デッドコード、衛生 |
| **Low** | 10 | 重複プロパティ、レートリミットリーク、複数エントリーポイント等 |

---

## 3. 重要トップ5 (即時対応推奨)

| # | 発見 | 理由 | 修正難易度 |
|---|---|---|---|
| **1** | **F001: Easy難易度で意図より25%多くダメージを受ける** | 配布ビルドのバランスが黙って壊れている；商用品質として不可 | 低 (config.yaml:19 を 0.5 に、またはコード preset を 0.75 に統一) |
| **2** | **F011-F012: 融合/覚醒スキルが「所有」のみで「使用」不可** | スキルシステムの核心機能がデッドコード化；プレイヤー体験に直結 | 中 (Entity.skills → CharacterState.skills へのブリッジ実装) |
| **3** | **F002+F008: CombatSystem が二重実装で責任分断** | バグ修正が二ヶ所必要；AoE は旧、報酬は新と相互呼び出し | 高 (どちらかに統合、段階的移行) |
| **4** | **F014+F044: 金策のみで金消費なし — 経済がインフレ必至** | 店未実装、評判ゲートもスタブ；クエスト報酬のみ増える | 中 (最小店実装 + skill_transfer 以外の消費追加) |
| **5** | **F036: Engine() 2.2秒 × テスト数 = テストスイート完走不能** | CI/開発ループの根本ボトルネック；データキャッシュとbind抑制で解決 | 中 (Lazy init + env flag でbind抑制 + YAMLキャッシュ) |

---

## 4. 検証済み継承主張の真偽

| 主張 | 検証結果 | 証拠 |
|---|---|---|
| 「8スイート全PASS」 | **真** | 8件個別実行で全PASS確認 (各1テスト、統合スイート) |
| 「敵能力21失敗」 | **偽 (修復済み)** | 現状21/21 PASS (slow 1件除外) |
| 「build/lib→ソースへコピーが唯一の残タスク」 | **逆** | **ソース→build/libが正** (ソースが +193/+159/+156行で新しい) |
| 「死亡ハンドラ未実装/フェイルステートなし」 | **偽 (修復済み)** | `engine/systems/game_loop.py:122-141` で状態遷移・RunSummary・履歴記録済み |
| 「プレイヤー動詞は3つのみ」 | **偽 (陳腐化)** | `input_actions.py` に30+ Verb 実装済み |
| 「GAME_OVER enum値が生成されない」 | **偽** | 死亡時に `game_over` 遷移する実装が存在 |

---

## 5. 改善案9つ (優先順位順)

| # | 改善案 | 対象発見 | リグレッション防止テスト (命名) |
|---|---|---|---|
| **1** | **難易度プリセット整合性の修正とロック** | F001, F004 | `test_difficulty_preset_matches_config` (constants + config.yaml 双方向検証) |
| **2** | **スキル「所有→使用」パイプライン実装** (Entity→CharacterState ブリッジ) | F011, F012, F013 | `test_fused_skill_becomes_castable`, `test_learned_skill_appears_in_spellbook` |
| **3** | **CombatSystem 統合 — 単一実装への段階的移行** | F002, F008 | `test_combat_damage_calc_matches_reference`, `test_kill_rewards_trigger_once` |
| **4** | **最小機能ショップ実装 + 金消費パス追加** | F014, F044 | `test_shop_buy_item_reduces_gold`, `test_shop_sell_item_increases_gold`, `test_gold_inflation_bounded_over_100_quests` |
| **5** | **Engine() 構築高速化: YAMLキャッシュ + ヘッドレス時Web bind抑制** | F036 | `test_engine_construct_under_500ms_headless`, `test_engine_construct_cache_hit` |
| **6** | **英語ロケール完全化 (ja.yaml 構造から en.yaml 生成)** | F015, F034 | `test_i18n_en_yaml_structure_matches_ja`, `test_localization_validate_passes` |
| **7** | **セーブシステム: pickle 置換 → 安全スキーマ直列化 (msgpack/JSON + Pydantic)** | F018, F019 | `test_save_load_roundtrip_preserves_state`, `test_malformed_save_rejected_safely` |
| **8** | **リポジトリ衛生: ジャンク削除 + .gitignore 強化 + バックアップローテーション** | F027-F031 | `test_repo_clean_no_junk_artifacts`, `test_gitignore_excludes_savegame_backups` |
| **9** | **設定システム単一化: ConfigManager 単一エントリーポイントへ統合** | F009 | `test_config_single_source_of_truth`, `test_difficulty_reads_from_unified_config` |

---

## 6. 方法論メモ

- **測定主義**: すべての定量値は本セッションで実測 (ruff, pytest, stat, diff, cat)。推定には「(推定)」を付記。
- **仮説検証**: 継承された主張を「仮説」として扱い、コード・実行・diff で真偽を判定 (4方向3件の楽観誤認パターンを踏襲せず)。
- **全ログ保存**: `findings.tsv` に全50件 (失敗・デッドエンド含む) を機械可読形式で記録。
- **深さ優先**: 1ファイル精読 > 10ファイル斜め読み。矛盾する証拠 (例: 旧監査の「死亡なし」vs 現コードの死亡ハンドラ) は **矛盾そのものを発見として記録**。

---

## 7. 成果物パス

- 報告書: `plans/CODE_REVIEW_2026-10-08/REPORT.md` (本ファイル)
- 証拠ログ: `plans/CODE_REVIEW_2026-10-08/findings.tsv`
- 実装計画書 (6本): `plans/CODE_REVIEW_2026-10-08/PLAN_01_DIFFICULTY_FIX.md` 〜 `PLAN_06_I18N_EN_YAML.md`

---

## 8. 次のアクション

上位6改善案 (1–6) の詳細実装計画書を作成済み。各計画は:
- フェーズ0 (回帰安全網) 直列実行
- ファイル所有権ベースのサブエージェント fan-out (衝突なし)
- 回帰テスト名を計画に明記 (`xfail(strict=True)` で導入、解決時に自動赤化)
- `tests/helpers/non_vacuity.py` の `assert_can_fail` / `assert_distinguishes` で非空虚性保証

実装着手の承認を得次第、Phase 0 から順次開始します。