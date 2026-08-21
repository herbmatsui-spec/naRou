# 詳細実装計画：Elona レンダリング層の HTML5 Canvas 2D へのリファクタリング

> 想定スコープ: 現在の Elona（naRou）は描画技術が断片化しているため、それを単一の
> HTML5 Canvas 2D レイヤーに統合する。
> - `src/render/Renderer.ts` … three.js / **WebGL2**（シーンデモ）
> - `demos/lib/*.js` … **PixiJS**（`ParticleSystem`, `FluidRenderer`, `LightingSystem`, `BoidSystem` 等）
> - `elona_engine.js`（計画中） … **Canvas 2D**（プレイ動画のマップ/HUD）
> - 各種 `*.html` デモ … 生 DOM / インライン canvas
>
> 注: リクエストの "elona foobar" は本リポジトリに存在しないモジュール名のため、
> "Elona の描画/ビジュアライゼーション層全体" と解釈して計画を作成している。
> 特定のサブモジュール（例: 戦闘UI、マップのみ）への絞り込みを希望する場合は要調整。

## 1. 背景と問題点

| 現状 | 課題 |
|---|---|
| シーンデモ = three.js(WebGL2) | 重い依存（three r160+）、ビルド必須、モバイル/低スペックで不安定 |
| エフェクト = PixiJS | 別の巨大依存、WebGL 前提、`demos/lib` に Git 競合マーカー（<<<<<<< ours）が残存 |
| 動画エンジン = 生 canvas | 未実装・計画のみで、既存エフェクト資産と重複 |
| HTML デモ群 | 外部依存・方針がバラバラ、`file://` 再生性が不揃い |

結果として、**同一ゲームで 3 つの異なる描画パイプライン**が并存し、
保守・知識伝達・バンドルサイズのコストが跳ね上がっている。

## 2. ゴール

- 単一の **HTML5 Canvas 2D** 描画コア（`canvas-core`）に統合する。
- 外部 GPU 依存（three / PixiJS / WebGL）を排除し、**依存ゼロ・`file://` ダブルクリック再生**を達成する。
- 既存の表現（タイル、パーティクル、ライティング、流体、HUD、スクリーンシェイク）を Canvas 2D で再現する。
- 既存のデータ層（`MOBTYPES`, `PLAYER`, `genMap`, `computeAttack` 等）は**変更しない**（描画のみ分離）。

## 3. ターゲットアーキテクチャ

```
elona_canvas_core.js        // 描画コア: Canvas2D コンテキスト管理・ループ・レイヤー
  ├─ TileRenderer2D         // タイルアトラス描画 (Renderer.ts の WebGL 版を 2D に)
  ├─ ParticleSystem2D       // ParticleSystem.js(Pixi) を Canvas 2D に移植
  ├─ FluidRenderer2D        // FluidRenderer.js(Pixi) → Canvas メタボール + 閾値カット
  ├─ LightingSystem2D       // LightingSystem.js → 加算ブレンドの光円
  ├─ BoidSystem2D           // BoidSystem.js → 群衆/敵群のステアリング
  ├─ ScreenShake2D          // カメラ振動 (PostProcess は不要・直接座標オフセット)
  ├─ DecalSystem2D          // 血痕/焼跡デカール (永続レイヤー)
  ├─ HUD2D                  // ステータス/ログ/ガイド/ターゲットHPバー
  └─ AnimationController2D   // フレームアニメ・tween (requestAnimationFrame ベース)
```

既存 `elona_engine.js`（計画）のゲームロジックは `sim` として分離し、
`elona_canvas_core.js` を `sim.render(ctx)` から呼ぶ形にする（MVC 分離）。

## 4. モジュール別マッピングと実装方針

### 4.1 TileRenderer2D（Renderer.ts 代替）
- `TilesetData` / `TileDefinition` インターフェースをそのまま再利用。
- WebGL `THREE.Mesh` + テクスチャ → `ctx.drawImage(atlasCanvas, sx, sy, sw, sh, dx, dy, dw, dh)` へ置換。
- アニメーション: `animationTime` を `frame = floor(t*fps)%frames` で算出しソース矩形を切替。
- カメラ: 直交カメラは不要。viewport オフセット + `ctx.translate` で代用。

### 4.2 ParticleSystem2D（ParticleSystem.js 代替）
- Pixi `Container`/`Graphics` → 自前の `{x,y,vx,vy,life,size,color}` 配列。
- プール再利用（既存 `particlePools`）を維持し GC 負荷を抑制。
- 描画: 小さい `fillRect` / `arc` のバッチ。`globalCompositeOperation='lighter'` で発光。

### 4.3 FluidRenderer2D（FluidRenderer.js 代替）
- Pixi `RenderTexture` メタボール → Canvas `OffscreenCanvas` または隠し canvas に
  半径ブラー円を描き、**アルファ閾値で cutoff** して from canvas を本レイヤへ合成。
- 毒沼/血痕/水滴の融合表現を維持。

### 4.4 LightingSystem2D
- 影マップ canvas を用意し、光円を `radialGradient` + `globalCompositeOperation='multiply'`（または 'lighter'）で合成。

### 4.5 HUD2D
- 現在 `elona_engine.js` 計画の HUD(3段・実形式)・カラーログ・右ガイドをそのまま Canvas テキスト描画へ。
- `measureText` でレイアウト、フォントは等幅ビットマップ風を CSS で指定。

### 4.6 AnimationController2D
- `requestAnimationFrame` 単一ループで `update(dt)` → `render(ctx)`。
- 既存の `fps`/`frames`/`directions` メタデータを流用。

## 5. マイグレーション手順（フェーズ分け）

### Phase A — コア確立（非破壊）
1. `elona_canvas_core.js` を新規作成（依存ゼロ classic script）。
2. `TileRenderer2D` のみ実装し、`Renderer.ts` のシーンデモ `webgl_template.html` を並行して Canvas 版 `canvas_template.html` で再現。
3. 視覚 diff テスト（スクリーンショット比較）で WebGL 版と等価性を確認。

### Phase B — エフェクト移植
4. `ParticleSystem2D` / `FluidRenderer2D` / `LightingSystem2D` を移植。
5. `demos/lib/*.js` の Git 競合マーカーを解消しつつ、Canvas 版へ書き換え。
6. デカール・ボイド・スクリーンシェイクを統合。

### Phase C — エンジン統合
7. 計画中 `elona_engine.js` の `sim` ロジックを `elona_canvas_core.js` と接続。
8. 3 分割動画（`elona_video1..3.html`）を Canvas コア経由で再生可能に。

### Phase D — 旧依存の削除（破壊的）
9. `Renderer.ts`（three.js）と `package.json` の three 依存を削除。
10. PixiJS 依存を削除。`demos/lib` の Pixi 版を廃止。
11. `vite.config.js` / `package.json` を最小化（ビルド不要化へ）。

## 6. パフォーマンス考慮

- タイルは毎フレーム `drawImage` のため、静的レイヤー（床/壁）は**オフスクリーンキャッシュ**し、動的エンティティのみ再描画（ダーティ矩形）。
- パーティクルはプール + 上限（`maxParticles=500`）維持。
- デバイスピクセル比は `min(dpr,2)` で clamp（Renderer.ts 既存方針を継承）。
- 流体メタボールは低解像度オフスクリーン（1/2～1/4）で計算後アップスケール。

## 7. 検証

- **単体**: Node スタブで各 2D サブシステムの `update/render` が例外なく動くことを確認。
- **視覚**: Phase A で WebGL 版と Canvas 版のスクリーンショットをピクセル比較（許容差 3%）。
- **統合**: 3 動画の全章 `stepTurn` を実行し、移動/戦闘/クエスト/転生が動く（既存計画の検証を流用）。
- **手動**: `file://` で各 HTML をダブルクリック再生、シーク/速度変更を確認。
- **バンドル**: `npm run build` 不要・外部 CDN ゼロを Lighthouse/手動で確認。

## 8. リスクと対策

| リスク | 対策 |
|---|---|
| Canvas 2D は WebGL より大規模シーンで遅い | オフスクリーンキャッシュ・ダーティ矩形・解像度スケールで抑制 |
| three/Pixi 特有の表現（シェーダー光沢等）の劣化 | フェーズAで視覚 diff を取り、許容内か判断 |
| 既存デモ資産の破壊 | Phase D まで旧実装を並行保持し、段階的に切替 |
| `demos/lib` の競合マーカー残存 | Phase B 着手前に `git diff` で確定・解消 |

## 9. 成果物ファイル

- `elona_canvas_core.js`（描画コア・新規）
- `canvas_template.html`（Renderer.ts 代替デモ）
- `demos/lib/*2D.js`（各エフェクトの Canvas 移植版）
- `elona_engine.js` の Canvas 接続部（計画済みロジックと統合）
- 削除: `src/render/Renderer.ts`、Pixi 依存、`vite` ビルド（最小化）
- 本計画: `plans/canvas_refactor_plan.md`

## 10. ロールアウト

1. Phase A 完了で `main` にマージ（旧実装はそのまま）。
2. Phase B/C で並行実装、Phase D で一斉切替。
3. 切替後 1 スプリント監視し、パフォーマンス regression がなければ旧コード完全削除。
