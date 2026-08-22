# 提案5: ビジュアルスタイル統一（デモ ↔ 実ゲーム） — 実装計画書

## 現状分析

- **デモHTML群** (`demos/scene_*.html`, `gallery_24_scenes.html`): Tailwind CSS + 絵文字グリッド + カスタムCSS
- **実ゲームWeb** (`web_game_client.html`): PixiJS + ピクセルアート + 動的ライティング
- **実ゲームターミナル**: tcod + タイル描画（提案1-3で実装済み）
- **共通基盤なし**: デザイントークン、カラーパレット、タイポグラフィがバラバラ

---

## 実装ステップ（全18ステップ）

### Phase 1: デザイントークン抽出・定義（Step 1-5）

#### Step 1: 既存スタイルの棚卸し
```bash
# 色・フォント・スペーシング抽出
grep -r "color:\|background:\|font-\|spacing:\|--color" demos/ --include="*.html" --include="*.css" | sort -u
grep -r "class=\"" demos/*.html | sed 's/.*class="\([^"]*\)".*/\1/' | tr ' ' '\n' | sort -u | head -50
```
- 成果: `design_audit.md` に色・フォント・ユーティリティクラス一覧化

#### Step 2: デザイントークン定義ファイル作成
```json
// design_tokens.json
{
  "colors": {
    "primary": {"50": "#f0f4f8", "100": "#d9e2ec", "500": "#2c3e50", "900": "#1a252f"},
    "semantic": {
      "bg": "primary.900", "surface": "primary.800", "border": "primary.600",
      "text": "neutral.100", "text-muted": "neutral.400",
      "accent": "amber.400", "danger": "red.400", "success": "green.400", "warning": "amber.300"
    },
    "tiles": {
      "wall": "#2c3e50", "floor": "#1c2230", "water": "#2980b9",
      "player": "#ecf0f1", "enemy": "#e74c3c", "pet": "#f8b500"
    }
  },
  "typography": {
    "fontFamilies": { "main": "'Noto Sans JP', sans-serif", "mono": "'JetBrains Mono', monospace", "pixel": "'Press Start 2P', cursive" },
    "fontSizes": { "xs": "0.75rem", "sm": "0.875rem", "base": "1rem", "lg": "1.125rem", "xl": "1.25rem" },
    "lineHeights": { "tight": 1.25, "normal": 1.5, "relaxed": 1.75 }
  },
  "spacing": { "0": "0", "1": "0.25rem", "2": "0.5rem", "3": "0.75rem", "4": "1rem", "6": "1.5rem", "8": "2rem" },
  "borderRadius": { "none": "0", "sm": "0.125rem", "md": "0.375rem", "lg": "0.5rem", "full": "9999px" },
  "shadows": { "sm": "0 1px 2px rgba(0,0,0,0.05)", "md": "0 4px 6px rgba(0,0,0,0.1)", "lg": "0 10px 15px rgba(0,0,0,0.1)" },
  "transitions": { "fast": "150ms ease", "normal": "250ms ease", "slow": "350ms ease" },
  "zIndices": { "base": 0, "dropdown": 100, "modal": 200, "tooltip": 300, "toast": 400 }
}
```

#### Step 3: トークン→CSS変数変換スクリプト作成
```python
# tools/tokens_to_css.py
import json


def tokens_to_css(tokens, prefix="--"):
    css = [":root {"]

    def flatten(d, path=""):
        for k, v in d.items():
            new_path = f"{path}{k}"
            if isinstance(v, dict):
                flatten(v, f"{new_path}-")
            else:
                css.append(f"  {prefix}{new_path}: {v};")

    flatten(tokens)
    css.append("}")
    return "\n".join(css)


with open("design_tokens.json") as f:
    tokens = json.load(f)
print(tokens_to_css(tokens))
```

#### Step 4: CSS変数ファイル生成・共通化
```bash
python tools/tokens_to_css.py > assets/css/design_tokens.css
```
- 全HTMLで `@import "design_tokens.css"` または `<link>` で読み込み

#### Step 5: 既存HTMLのクラス置換・移行
```bash
# 例: bg-gray-900 → var(--color-bg)
# 手動またはスクリプトで段階的置換
# 対象: demos/*.html, web_game_client.html
```

---

### Phase 2: 共通コンポーネントライブラリ構築（Step 6-10）

#### Step 6: 共通ベースHTMLテンプレート作成
```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}naRou{% endblock %}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&family=JetBrains+Mono:wght@400;500&family=Press+Start+2P&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/css/design_tokens.css">
  <link rel="stylesheet" href="/assets/css/components.css">
  {% block extra_head %}{% endblock %}
</head>
<body class="bg-[var(--color-bg)] text-[var(--color-text)] font-[var(--font-main)]">
  {% block content %}{% endblock %}
  {% block scripts %}{% endblock %}
</body>
</html>
```

#### Step 7: 共通UIコンポーネントCSS作成
```css
/* assets/css/components.css */
.btn { @apply px-4 py-2 rounded-md font-medium transition-colors duration-200; }
.btn-primary { @apply bg-[var(--color-accent)] text-[var(--color-bg)] hover:opacity-90; }
.btn-secondary { @apply bg-[var(--color-surface)] text-[var(--color-text)] border border-[var(--color-border)] hover:bg-[var(--color-border)]; }
.btn-danger { @apply bg-[var(--color-danger)] text-white hover:opacity-90; }

.card { @apply bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg p-4; }
.panel { @apply bg-[var(--color-bg)] border border-[var(--color-border)] rounded-lg; }

.input { @apply w-full px-3 py-2 bg-[var(--color-bg)] border border-[var(--color-border)] rounded-md text-[var(--color-text)] placeholder-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-accent)]; }

.badge { @apply inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium; }
.badge-primary { @apply bg-[var(--color-accent)] text-[var(--color-bg)]; }
.badge-danger { @apply bg-[var(--color-danger)] text-white; }
```

#### Step 8: デモHTMLをテンプレートベースに移行
```html
<!-- demos/scene_01_adventurer_start.html 書き換え例 -->
{% extends "templates/base.html" %}
{% block title %}冒険者の始まり - naRou Demo{% endblock %}
{% block content %}
<div class="container mx-auto px-4 py-8">
  <header class="mb-8">
    <h1 class="text-3xl font-bold text-[var(--color-accent)]">冒険者の始まり</h1>
    <p class="text-[var(--color-text-muted)] mt-2">シーンデモ: ギルド受付</p>
  </header>
  <main>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <section class="card">
        <h2 class="text-xl font-semibold mb-4">シーン概要</h2>
        <!-- 既存コンテンツをカード内に -->
      </section>
    </div>
  </main>
</div>
{% endblock %}
```

#### Step 9: 実ゲームWeb版（web_game_client.html）も共通化
```html
<!-- web_game_client.html の head 部分書き換え -->
<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>naRou - Web Client</title>
  <link rel="stylesheet" href="/assets/css/design_tokens.css">
  <link rel="stylesheet" href="/assets/css/game_ui.css">  /* ゲーム固有UI */
  <style>
    /* インラインCSS最小限に */
    canvas { display: block; }
  </style>
</head>
<body>
  <div id="game-container" class="relative w-full h-screen"></div>
  <!-- UIオーバーレイはHTMLで構築可能に -->
  <div id="ui-overlay" class="fixed inset-0 pointer-events-none" aria-hidden="true">
    <!-- HPバー、メッセージログ等 -->
  </div>
  <script src="https://cdn.pixijs.com/pixi.js"></script>
  <script type="module" src="demos/lib/TileAtlas.js"></script>
  <!-- ... -->
</body>
</html>
```

#### Step 10: Tailwind CSS 完全除去・自前CSSのみに
```bash
# CDN リンク削除、自前CSSのみに
# 設定ファイル tailwind.config.js があれば削除
rm -f tailwind.config.js
# package.json から tailwind 関連削除
```

---

### Phase 3: ターミナル側カラーパレット同期（Step 11-14）

#### Step 11: design_tokens.json からターミナル用パレット生成
```python
# tools/generate_palette.py
import json

with open("design_tokens.json") as f:
    tokens = json.load(f)

# tcod用 16色パレット生成（16bit JRPG準拠）
palette = [
    tokens["colors"]["semantic"]["bg"],  # 0: 背景
    tokens["colors"]["semantic"]["text"],  # 1: 前景
    tokens["colors"]["tiles"]["wall"],  # 2: 壁
    tokens["colors"]["tiles"]["floor"],  # 3: 床
    tokens["colors"]["tiles"]["water"],  # 4: 水
    tokens["colors"]["tiles"]["player"],  # 5: プレイヤー
    tokens["colors"]["tiles"]["enemy"],  # 6: 敵
    tokens["colors"]["tiles"]["pet"],  # 7: ペット
    tokens["colors"]["semantic"]["accent"],  # 8: アクセント
    tokens["colors"]["semantic"]["danger"],  # 9: 危険/ダメージ
    tokens["colors"]["semantic"]["success"],  # 10: 成功/回復
    tokens["colors"]["semantic"]["warning"],  # 11: 警告
    "#8b9bb4",
    "#6b7b94",
    "#4b5b74",
    "#2c3e50",  # 12-15: グレースケール
]

# Pythonリスト形式で出力
print("PALETTE_16 = [")
for i, c in enumerate(palette):
    r, g, b = int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)
    print(f"    ({r}, {g}, {b}),  # {i}")
print("]")
```

#### Step 12: palette.py 更新・同期
```bash
python tools/generate_palette.py > core/palette_generated.py
# core/palette.py とマージ or 置換
```

#### Step 13: Web版 CSS 変数とターミナルパレットの整合性テスト
```python
# tools/test_palette_parity.py
def test_palette_parity():
    # 1. design_tokens.json の色
    # 2. core/palette.py の PALETTE_16
    # 3. assets/css/design_tokens.css の --color-* 変数
    # 全て同一値であることを確認
    pass
```

#### Step 14: 色覚対応パレット生成（プロタノピア/デュータノピア/トリタノピア）
```python
# tools/generate_colorblind_palettes.py
def simulate_protanopia(rgb): ...
def simulate_deuteranopia(rgb): ...
def simulate_tritanopia(rgb): ...


# 各色覚タイプ用に design_tokens.json を変換し
# design_tokens.protanopia.json 等を生成
```

---

### Phase 4: レスポンシブ・アクセシビリティ・検証（Step 15-18）

#### Step 15: レスポンシブブレークポイント統一
```css
/* assets/css/components.css に追加 */
@media (max-width: 640px) { .container { @apply px-2; } }
@media (min-width: 641px) and (max-width: 1024px) { .container { @apply px-4; } }
@media (min-width: 1025px) { .container { @apply px-8 max-w-7xl mx-auto; } }
```

#### Step 16: ダーク/ライト/ハイコントラストモード対応
```css
/* assets/css/themes.css */
@media (prefers-color-scheme: dark) {
  :root { /* デフォルトはダーク */ }
}
@media (prefers-color-scheme: light) {
  :root {
    --color-bg: var(--color-primary-50);
    --color-surface: var(--color-primary-100);
    --color-text: var(--color-primary-900);
    --color-text-muted: var(--color-primary-600);
  }
}
@media (prefers-contrast: more) {
  :root {
    --color-border: var(--color-text);
    --color-text-muted: var(--color-text);
  }
}
```

#### Step 17: `prefers-reduced-motion` 対応
```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  /* パーティクル・ライティングアニメーションも無効化は JS 側で */
}
```

#### Step 18: ビジュアル回帰テスト・完了確認
```bash
# tools/visual_regression.py --generate で参照画像生成
# tools/visual_regression.py --compare で全ページ比較
# チェックリスト:
# - [ ] 全デモページが共通テンプレートベース
# - [ ] web_game_client.html が共通CSS使用
# - [ ] ターミナルパレットと同期
# - [ ] 色覚シミュレーション画像生成
# - [ ] prefers-reduced-motion でアニメ停止確認
```

---

## 完了判定基準

- [ ] `design_tokens.json` 単一ソースから全色・フォント・スペース生成
- [ ] 全デモHTMLが共通テンプレートベース
- [ ] `web_game_client.html` が共通CSS変数使用
- [ ] ターミナル `palette.py` と同期
- [ ] 色覚対応パレット生成済み
- [ ] レスポンシブ・ダークモード・ハイコントラスト・減少モーション対応
- [ ] 視覚的回帰テスト全パス

---

## ファイル変更マップ

| ファイル | 変更内容 |
|----------|----------|
| `design_tokens.json` | 新規: 単一ソース |
| `tools/tokens_to_css.py` | 新規: 変換スクリプト |
| `tools/generate_palette.py` | 新規: ターミナルパレット生成 |
| `tools/generate_colorblind_palettes.py` | 新規: 色覚対応 |
| `assets/css/design_tokens.css` | 生成: CSS変数 |
| `assets/css/components.css` | 新規: 共通コンポーネント |
| `assets/css/themes.css` | 新規: テーマ対応 |
| `templates/base.html` | 新規: 共通テンプレート |
| `demos/*.html` | 書き換え: テンプレートベース |
| `web_game_client.html` | 書き換え: 共通CSS使用 |
| `core/palette.py` | 更新: 生成パレット同期 |
| `docs/VISUAL_UNIFICATION.md` | 新規: ドキュメント |
