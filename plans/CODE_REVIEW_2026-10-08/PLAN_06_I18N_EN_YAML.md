# 実装計画書: PLAN_06 英語ロケール完全化 (ja.yaml 構造から en.yaml 生成)

**対象発見**: F015, F034 (high ×2) — en.yaml 13バイトスタブで i18n 破綻、検証テスト失敗  
**優先度**: 6 (英語ユーザー完全切り捨て；商用リリースの最低ライン)  
**作業見積**: 1–1.5時間 (Phase 0: 10分 + 実装: 30–45分 + 検証: 15分)  
**方針**: **機械翻訳 + 人間レビュー最小** — 構造完全一致を最優先、翻訳品質は後続イテレーション

---

## 0. 回帰安全網 (Phase 0 — 直列、最初に完了)

| # | テストファイル | テスト名 | 目的 | 初期状態 |
|---|---|---|---|---|
| 0.1 | `tests/test_i18n_structure.py` (新規) | `test_i18n_en_yaml_structure_matches_ja` | `en.yaml` と `ja.yaml` が **完全同一キー構造** を持つ (値は異なってよい) | `xfail(strict=True)` |
| 0.2 | `tests/test_i18n_structure.py` | `test_localization_validate_passes` | `LocalizationManager.validate()["valid"] == True` (既存失敗テストの green 化) | `xfail(strict=True)` |
| 0.3 | `tests/test_non_vacuity.py` | `assert_distinguishes(check_structure_match, good_en_yaml, bad_en_yaml_missing_keys)` | キー欠落を検出できる非空虚性証明 | 実装後 green |

**非空虚性証明**: `bad_en_yaml_missing_keys` = `ui.menu` セクション削除版 → 検出。

---

## 1. 実装ステップ (ファイル単位、アトミック)

### Step 1: `scripts/generate_en_yaml.py` (新規) — ja.yaml から en.yaml 骨格生成スクリプト
- **処理**:
  1. `data/text/ja.yaml` を読込 (YAML safe_load)
  2. 全キーを再帰走査、葉ノードの値をプレースホルダー英語に置換
  3. `data/text/en.yaml` に書出し (順序保持: `yaml.Dumper` で `sort_keys=False`)
- **プレースホルダー規則**:
  - `meta.*` → 手動修正 (language, name, native_name)
  - `ui.*` → `"[EN] " + ja_text` (視認性のためプレフィックス)
  - `game.*` → 同上
  - 以降、機械翻訳 API (libretranslate 等) があれば実翻訳、なければプレースホルダー維持
- **出力**: 完全同一構造の `en.yaml` (180行、~5KB)
- **回帰テスト**: 0.1, 0.2 が green になる。

### Step 2: `data/text/en.yaml` — 生成結果をコミット
- **手順**: スクリプト実行 → 出力確認 → `git add data/text/en.yaml`
- **手動微調整**: `meta` セクションのみ人間が正しい英語メタデータに書換
  ```yaml
  meta:
    language: "en"
    name: "English"
    native_name: "English"
  ```

### Step 3: `localization_manager.py` — fallback 言語設定確認
- **現状**: `default_language = "en"` だが en.yaml が空で fallback 失敗
- **確認**: `validate()` が構造チェックのみなら Step 1-2 で解決。値チェックなら緩和。

### Step 4: 他スタブロケール (ko.yaml, zh-cn.yaml, zh-tw.yaml) — 同一スクリプト適用 (任意)
- **理由**: 同一問題を抱える；スクリプト汎用化で一括処理可能
- **優先度**: 低 (英語完了後)

---

## 2. 検証手順

```bash
# Phase 0: 赤確認
/usr/bin/python3 -m pytest tests/test_i18n_structure.py -v --runxfail

# Step 1 実行
/usr/bin/python3 scripts/generate_en_yaml.py

# Step 2 後 (meta 手動修正含む)
/usr/bin/python3 -m pytest tests/test_i18n_structure.py -v
/usr/bin/python3 -m pytest tests/internationalization/test_internationalization.py -v

# 非空虚性
/usr/bin/python3 -m pytest tests/test_non_vacuity.py::assert_distinguishes -v
```

---

## 3. 完了の定義

- [ ] `test_i18n_en_yaml_structure_matches_ja` PASS (キー構造完全一致)
- [ ] `test_localization_validate_passes` PASS (既存失敗テスト green 化)
- [ ] 非空虚性証明 PASS
- [ ] `en.yaml` が `ja.yaml` と同一行数・同一キー階層 (値は英語プレースホルダー以上)
- [ ] `meta` セクションが正しい英語メタデータ
- [ ] ruff/mypy clean
- [ ] (任意) ko/zh-CN/zh-TW も同一スクリプトで生成済み