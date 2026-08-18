# UI/UXデザインシステム確立：実装計画書 (Unified Product Transformation)

## 1. 目的とビジョン
本計画は、現在個別のHTML/JSファイルとして散在している24以上のデモシーンを、共通のデザイントークンとコンポーネントライブラリによって統合し、「一つの統一された製品」としてのブランド価値と開発効率を最大化することを目的とする。

**ビジョン:** 
- **Single Source of Truth:** デザイン変更は `design-tokens.json` 一箇所で行い、全シーンに即座に反映される。
- **Stateless UI:** ロジック（データ）と見た目（UI）を完全に分離し、再利用可能なコンポーネントとして実装する。

---

## 2. アーキテクチャ設計

### 2.1 デザイントークン・スキーマ (`design-tokens.json`)
以下の構造で定義し、CSS変数として注入する。
- `colors`: 意味論的な命名 (Semantic Naming)
  - `brand`: primary, secondary, accent
  - `surface`: background, surface-low, surface-high, border
  - `content`: text-main, text-muted, text-inverse
  - `status`: success, warning, danger, info
- `spacing`: 4pxベースのスケール (`spacing-1` to `spacing-12`)
- `typography`: サイズ、ウェイト、行間
- `motion`: duration (fast, standard, slow), easing functions

### 2.2 UIProvider (Token-to-CSS Bridge)
JavaScriptによる動的なCSS変数注入エンジンを実装。
- `design-tokens.json` をフェッチし、`:root` 要素に `--color-primary: #...` 形式でスタイルを適用。
- ダークモード/ライトモードの切り替えをJSONのプロファイル切り替えで実現。

### 2.3 ステートレスコンポーネント設計
各コンポーネントは `render(props)` 関数を持ち、HTML文字列またはDOM要素を返す。
- `LogWindow`: メッセージタイプに基づいたスタイル適用、自動スクロール。
- `StatusBar`: `%`ベースのゲージ表示、色のトークン指定。
- `InventoryGrid`: アイテムスロットの生成、レアリティに応じた枠線の適用。
- `SkillTree`: ノード間の接続線描画、状態（Locked/Learned）の視覚化。

---

## 3. 詳細実装ステップ (1〜36)

本計画を、依存関係に基づいた36のマイクロステップに分割する。

### フェーズ1：基盤構築 (Tokens & Bridge)
1. [ ] `design-tokens.json` の基本スキーマ設計（Color/Spacing/Typography）
2. [ ] 基本カラーパレットの定義（ブランド色、背景色、テキスト色）
3. [ ] ステータスカラー（Success/Danger等）の定義
4. [ ] スペーシングスケールの定義（4px単位の定義）
5. [ ] タイポグラフィトークンの定義（h1, body, caption等）
6. [ ] モーショントークンの定義（Duration, Easing）
7. [ ] `UIProvider.js` の基本クラス実装（JSON読み込み機能）
8. [ ] CSS変数への変換ロジック実装（`--token-name` 形式）
9. [ ] `:root` へのスタイル注入機能実装
10. [ ] `UIProvider` のエラーハンドリング（JSON欠損時のフォールバック）
11. [ ] デザイントークンのバリデーションスクリプト作成
12. [ ] 最小構成のHTMLテストページでのトークン反映確認

### フェーズ2：共通コンポーネント実装 (Stateless UI Library)
13. [ ] `Component` 基本クラス/インターフェースの定義
14. [ ] `LogWindow` コンポーネント：基本構造実装
15. [ ] `LogWindow`：メッセージタイプ別スタイルの適用
16. [ ] `LogWindow`：アニメーション（フェードイン）の実装
17. [ ] `StatusBar` コンポーネント：ゲージ描画ロジック実装
18. [ ] `StatusBar`：トークンによる色変更機能の実装
19. [ ] `ItemSlot` コンポーネント：基本枠とアイコン配置実装
20. [ ] `ItemSlot`：レアリティ別ボーダー色の適用ロジック実装
21. [ ] `InventoryGrid` コンポーネント：グリッドレイアウト実装
22. [ ] `InventoryGrid`：アイテムリストからの動的生成機能実装
23. [ ] `SkillNode` コンポーネント：状態別（Locked/Learned）スタイル実装
24. [ ] `SkillTree` コンポーネント：ノード配置ロジック実装
25. [ ] `SkillTree`：ノード間接続線の描画（SVG/Canvas）実装
26. [ ] 全コンポーネントのアクセシビリティ（aria-label等）対応
27. [ ] コンポーネント専用のストーリーブック（カタログページ）作成
28. [ ] 共通コンポーネントのパフォーマンス最適化（DOM操作の最小化）

### フェーズ3：全デモへの統合とリファクタリング (Unified Product)
29. [ ] 全デモHTMLへの `UIProvider.js` 導入
30. [ ] 各デモ内のハードコードされた色のCSS変数をトークンに置換
31. [ ] 各デモ内の余白/パディングをスペーシングトークンに置換
32. [ ] 個別実装されていたログウィンドウを `LogWindow` コンポーネントに置換
33. [ ] 個別実装されていたステータス表示を `StatusBar` コンポーネントに置換
34. [ ] インベントリ/スキル画面を持つデモを共通コンポーネントに移行
35. [ ] 全24シーンでの視覚的整合性チェック（Visual QA）
36. [ ] 最終的なデザイントークンの微調整と最適化

---

## 4. 成功基準 (Definition of Done)
- [ ] **一括変更可能性:** `design-tokens.json` のメインカラーを変更して、全シーンの配色が同時に変わること。
- [ ] **コード削減:** 各HTMLファイル内の `<style>` セクションが大幅に削減され、CSS変数の参照に置き換わっていること。
- [ ] **UI一貫性:** 全てのデモでログウィンドウ、ステータスバーの挙動と見た目が同一であること。
- [ ] **拡張性:** 新しいコンポーネントを追加した際、既存のデザイントークンを適用するだけでデザインが完結すること。

## 5. リスクと対策
- **リスク:** 既存デモのレイアウトが崩れる。
  - **対策:** `UIProvider` 導入後、まずは「色の置換」から段階的に行い、レイアウト変更は個別に検証する。
- **リスク:** JavaScript依存によるレンダリング遅延。
  - **対策:** トークンの注入を `head` タグ直後に行い、FOUC（Flash of Unstyled Content）を防止する。
