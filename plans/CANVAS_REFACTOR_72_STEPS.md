# 実装計画書: HTML5 Canvas 2D への統合（全72ステップ）

- **目的**: 既存の Elona（naRou）の描画技術（WebGL, PixiJS, 生DOM等）の断片化を解消し、単一の HTML5 Canvas 2D レイヤーに統合する。
- **対象**: 低性能なLLMでも1ステップずつ確実に実装・検証できるよう、各ステップを「1つの小さな変更 ＋ 決まった検証」に分割。
- **前提知識**: JavaScript (Canvas 2D API), 既存コード (`demos/lib/*.js`, `src/render/Renderer.ts`)。
- **規約**: 各ステップは「独立してコンパイル/動作する」こと。前のステップが成功してから次へ進むこと。

---

## フェーズA: コア確立（非破壊） 〔ステップ1〜18〕

### Step 1 — `elona_canvas_core.js` の新規作成
- **変更ファイル**: `elona_canvas_core.js`（新規）
- **実装**: 空のファイルを作成し、先頭に `"use strict";` と簡単な説明コメントを記述する。
- **検証**: ファイルが作成され、構文エラーがない。

### Step 2 — コアクラス `CanvasCore` の定義
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: `class CanvasCore { constructor(canvasId) { this.canvas = document.getElementById(canvasId); this.ctx = this.canvas.getContext('2d'); } }` を追加。
- **検証**: `new CanvasCore('test')` がコンテキスト取得でエラーを出さない（IDが存在する場合）。

### Step 3 — `canvas_template.html` の作成
- **変更ファイル**: `canvas_template.html`（新規）
- **実装**: `<canvas id="gameCanvas" width="800" height="600"></canvas>` を持ち、`elona_canvas_core.js` を読み込む最小のHTMLを作成。
- **検証**: ブラウザで開き、800x600のキャンバスが存在する。

### Step 4 — デバイスピクセル比 (dpr) の対応
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: `CanvasCore` 内で `const dpr = Math.min(window.devicePixelRatio || 1, 2);` とし、canvasのwidth/heightをdpr倍し、`ctx.scale(dpr, dpr)` を適用。
- **検証**: 高DPI環境でキャンバスがぼやけず描画される。

### Step 5 — `TileRenderer2D` クラスの枠組み定義
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: `class TileRenderer2D { constructor(ctx) { this.ctx = ctx; } }` を追加。
- **検証**: スクリプトロード時に構文エラーがない。

### Step 6 — アトラス画像ロードの実装
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: `TileRenderer2D` に `async loadAtlas(url)` メソッドを追加し、`Image` オブジェクトをロードして `this.atlas` に保持。
- **検証**: `loadAtlas('test.png')` を呼び出し、画像がロードされる。

### Step 7 — タイル単体の描画ロジック実装
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: `TileRenderer2D` に `drawTile(sx, sy, sw, sh, dx, dy, dw, dh)` を追加し、`ctx.drawImage` を呼ぶ。
- **検証**: 指定した矩形の画像片がキャンバスの指定位置に描画される。

### Step 8 — `TilesetData` 形式のマッピング解析
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: JSON形式の `TilesetData` を受け取り、タイルIDから `sx, sy` を引く `setTileData(json)` メソッドを実装。
- **検証**: タイルIDを渡すと正しいアトラス座標が返る。

### Step 9 — カメラオフセット（viewport）の適用
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: `TileRenderer2D` に `setCamera(x, y)` を追加し、描画前に `ctx.translate(-x, -y)` を適用（描画後にリストア）。
- **検証**: `setCamera(10, 10)` 適用後、描画位置がずれること。

### Step 10 — 床レイヤーの一括描画
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: マップの2次元配列を受け取り、ループで `drawTile` を連続で呼ぶ `renderFloor(map)` を実装。
- **検証**: マップ配列の通りに床タイルが敷き詰められて描画される。

### Step 11 — オフスクリーンキャッシュ（床用）の実装
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 床レイヤー専用の `OffscreenCanvas`（または非表示canvas）を作成し、静的な床を描画してキャッシュ。メイン描画時はそれを一発転送。
- **検証**: `renderFloor` が初回のみループを回し、以後はキャッシュを描画する。

### Step 12 — 壁レイヤーの一括描画
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 高さが伴う壁タイル用の `renderWalls(map)` を追加。奥から手前へYソートして描画。
- **検証**: 壁タイルが正しい重なり順で描画される。

### Step 13 — アニメーションフレーム計算式の実装
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: グローバル時間 `t` から `frame = Math.floor(t * fps) % frames` を返すヘルパー関数。
- **検証**: `t` の増加に伴い 0,1,2,0... と正しく循環する。

### Step 14 — アニメーションタイルの描画適用
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: アニメーション定義があるタイルに対し、Step 13 の `frame` を使ってアトラスの参照X座標をずらす処理を `drawTile` 呼び出し前に追加。
- **検証**: 時間経過とともにタイルの絵柄が切り替わる。

### Step 15 — エンティティ（動的オブジェクト）の描画枠
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: `renderEntities(entities)` を追加。各エンティティの `x, y` に基づき Yソートして `drawTile`。
- **検証**: エンティティがマップ上に表示され、Y座標に応じて前後関係が正しくなる。

### Step 16 — ダーティ矩形のスタブ実装
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 画面全体をクリアするのではなく、変更があった矩形リスト `dirtyRects` を受け取る準備。現状は全画面クリアのままでよい。
- **検証**: 構文エラーがない。

### Step 17 — `canvas_template.html` のシーンデモ構築
- **変更ファイル**: `canvas_template.html`
- **実装**: モックの `map` と `entities` データを定義し、`TileRenderer2D` に渡して初期画面を描画するスクリプトを記述。
- **検証**: HTMLを開くと、モックデータに基づくマップとエンティティが描画されている。

### Step 18 — 視覚 diff 検証（WebGL版との比較）
- **変更ファイル**: なし（検証のみ）
- **実装**: `canvas_template.html` と `webgl_template.html` (または相当するWebGLデモ) を並べて表示。
- **検証**: 色合いやタイルの配置がピクセルレベルでほぼ同一（許容差3%以内）であることを目視確認。

---

## フェーズB: エフェクト移植 〔ステップ19〜45〕

### Step 19 — `ParticleSystem2D` クラスの定義
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: `class ParticleSystem2D` を追加。初期化時に空のパーティクル配列を持つ。
- **検証**: スクリプトエラーがない。

### Step 20 — パーティクルプールの実装
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 毎フレームのGCを防ぐため、固定長（例:500個）のオブジェクト配列 `this.pool = Array(500).fill().map(()=>({...}))` を構築。
- **検証**: `pool` の長さが500であり、オブジェクトが格納されている。

### Step 21 — `Particle` 構造体の設計
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: プール内のオブジェクトが `x, y, vx, vy, life, maxLife, size, color, active` を持つよう定義。
- **検証**: プールの要素が指定のプロパティを持つ。

### Step 22 — `emit(x, y, options)` メソッド実装
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: `pool` から `active == false` のものを探し、引数の値で初期化して `active = true` にする。
- **検証**: `emit` 呼出後、該当パーティクルの `active` が true になる。

### Step 23 — パーティクル更新ロジック `update(dt)`
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 速度を位置に加算、`life` を `dt` 分減らし、0以下で `active = false` に戻す。
- **検証**: 時間経過とともに位置が移動し、寿命が尽きると非アクティブになる。

### Step 24 — パーティクル描画ロジック `render(ctx)`
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: アクティブなパーティクルに対して `ctx.fillStyle = color; ctx.fillRect()` または `ctx.arc()` を描画。
- **検証**: 画面に図形が表示される。

### Step 25 — 発光表現（lighterコンポジット）
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: パーティクル描画前に `ctx.globalCompositeOperation = 'lighter'` を設定し、描画後に `source-over` に戻す。
- **検証**: パーティクルが重なった部分が白く明るく光る。

### Step 26 — 既存 PixiJS パーティクルの一部の置換
- **変更ファイル**: `demos/demo_skill_eater_showcase.html` (または該当デモ)
- **実装**: 既存の `ParticleSystem` (PixiJS) の呼び出しを `ParticleSystem2D` に差し替える。
- **検証**: デモ上でパーティクルがCanvas2Dで描画される。

### Step 27 — `FluidRenderer2D` クラスの定義
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 流体表現用の `class FluidRenderer2D` を追加。
- **検証**: スクリプトエラーがない。

### Step 28 — 流体用オフスクリーンキャンバス
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: メタボール計算用に半分の解像度の `OffscreenCanvas` を用意し、高速化を図る。
- **検証**: オフスクリーンキャンバスが正しい解像度で生成される。

### Step 29 — 流体パーティクル描画（ぼかし円）
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: オフスクリーン上に `createRadialGradient` を用いて、中心が濃く外縁が透明な円を描画。
- **検証**: オフスクリーンにぼやけた円が描画される。

### Step 30 — アルファ閾値（Cutoff）フィルタ実装
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: オフスクリーンのピクセルデータを `getImageData` で取得し、アルファ値が閾値以下なら0、以上なら255にする処理。
- **検証**: ぼやけた円が、くっきりしたメタボール形状に変換される。

### Step 31 — メインキャンバスへの流体合成
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 処理済みの流体オフスクリーンをメインキャンバスに `drawImage` する。
- **検証**: ゲーム画面上に毒沼や水たまりがメタボール状に描画される。

### Step 32 — 既存 FluidRenderer の置換
- **変更ファイル**: `demos/demo_skill_eater_showcase.html`
- **実装**: 流体エフェクトのPixi依存を剥がし、`FluidRenderer2D` へ移行。
- **検証**: Pixiなしで流体が動作する。

### Step 33 — `LightingSystem2D` クラスの定義
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 影と光を管理する `class LightingSystem2D` を追加。
- **検証**: スクリプトエラーがない。

### Step 34 — 影レイヤーキャンバス
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 画面全体を覆う暗色（例: `rgba(0,0,0,0.8)`）を塗るオフスクリーンを用意。
- **検証**: 真っ暗なレイヤーが作成される。

### Step 35 — 光源のくり抜き描画
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 影レイヤーに対し `globalCompositeOperation = 'destination-out'` を用いて、光源位置に放射状グラデーションを描画。
- **検証**: 光源の周囲だけ暗闇が丸く切り取られる。

### Step 36 — 乗算合成によるライティング適用
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 影レイヤーをメインキャンバスへ `globalCompositeOperation = 'multiply'` (または 'source-over') で合成。
- **検証**: 画面全体が暗くなり、光源周辺だけ明るくマップが見える。

### Step 37 — 既存 LightingSystem の置換
- **変更ファイル**: `demos/demo_skill_eater_showcase.html`
- **実装**: Pixiのライティングを `LightingSystem2D` に置換。
- **検証**: ライティングがCanvas2Dで動作する。

### Step 38 — `BoidSystem2D` クラスの定義
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 鳥の群れや敵群のステアリング用 `class BoidSystem2D` を追加。
- **検証**: スクリプトエラーがない。

### Step 39 — ボイドの物理ロジック移植
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 既存の `BoidSystem.js` から Separation, Alignment, Cohesion のロジックをコピーし調整。
- **検証**: 座標配列が群れの動きとして正しく更新される。

### Step 40 — ボイドの描画処理
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 向き（角度）に合わせて三角形や簡単なスプライトをCanvasに `ctx.rotate` して描画。
- **検証**: 群れが向いている方向を向いて描画される。

### Step 41 — `ScreenShake2D` 実装
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: カメラのオフセット値に対し、ランダムなノイズ（減衰つき）を加算するクラス。
- **検証**: シェイク発動時に描画全体が揺れる。

### Step 42 — `DecalSystem2D` 実装
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 血痕などを永続的に残すため、床オフスクリーンキャンバスに直接描き込む関数群。
- **検証**: エフェクト終了後も床にデカールが残る。

### Step 43 — Git競合マーカーの解消 (`demos/lib`)
- **変更ファイル**: `demos/lib/*.js` (必要に応じて)
- **実装**: `<<<<<<< ours` などのGit競合マーカーが残っているファイルを検索し、2D移行に合わせて不要ならファイルごと削除準備、またはマージ済みにする。
- **検証**: `grep -r "<<<<<<<"` で該当ファイルが出ないこと。

### Step 44 — 統合テスト用モック更新
- **変更ファイル**: `canvas_template.html`
- **実装**: これまで作成したすべてのエフェクト（パーティクル、流体、光、ボイド、シェイク、デカール）を同時に起動するデモコードを記述。
- **検証**: 1つの画面で全エフェクトが破綻なく描画される。

### Step 45 — PixiJS系の不具合修正
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: Step 44 で生じた描画順やコンポジットモードの競合（光の切り抜きがおかしい等）を修正。
- **検証**: エフェクトが正しくブレンドされる。

---

## フェーズC: エンジン統合 〔ステップ46〜60〕

### Step 46 — `AnimationController2D` 定義
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: `requestAnimationFrame` を用いた単一のゲームループクラスを構築。
- **検証**: ループが毎フレーム実行され、コンソールに `dt` が出力される（一時的）。

### Step 47 — 各システムのループへの登録
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: `AnimationController2D` に `addSystem(sys)` を設け、ループ内で各 `update()` と `render()` を一斉呼び出し。
- **検証**: 登録したシステム群が自動で進行・描画される。

### Step 48 — `HUD2D` クラス定義
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 画面上のUI（HP/MPバー、ログ）を描画する `class HUD2D`。
- **検証**: スクリプトエラーがない。

### Step 49 — HUDバー描画実装
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: `HUD2D` に `drawBar(x, y, w, h, ratio, color)` を実装し、背景黒＋手前色の `fillRect` を行う。
- **検証**: ダメージに合わせてバーの長さが変わる。

### Step 50 — テキストログ描画実装
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 画面下部に文字列の配列を描画する `drawLog(messages)`。`ctx.font = '14px monospace'` 指定。
- **検証**: 文字列が下から上へ正しくスタックして描画される。

### Step 51 — テキストレイアウトの最適化
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: `ctx.measureText` を用いて、右端ガイドや文字列幅の計算結果をキャッシュする仕組み。
- **検証**: 大量テキスト描画時もFPSが低下しない。

### Step 52 — 計画中ロジックとの接続準備
- **変更ファイル**: `elona_engine.js`（既存または新規）
- **実装**: ゲームロジック側（シミュレーション）が、自身の状態をJSON等で出力できるインターフェースを整備。
- **検証**: `sim.getState()` がプレーンなオブジェクトを返す。

### Step 53 — `elona_canvas_core.js` とロジックのブリッジ
- **変更ファイル**: `elona_engine.js`
- **実装**: `AnimationController2D` のループ内で `sim.update(dt)` を呼び、その状態を各種Rendererに渡す。
- **検証**: ロジックの進行（座標変化など）が画面に反映される。

### Step 54 — 3分割動画デモ (video1) の Canvas2D 化
- **変更ファイル**: `elona_video1.html` (または相当ファイル)
- **実装**: 描画層を `elona_canvas_core.js` ベースに書き換える。
- **検証**: 動画デモ1がCanvas2Dで動作する。

### Step 55 — 3分割動画デモ (video2) の Canvas2D 化
- **変更ファイル**: `elona_video2.html`
- **実装**: 同上。
- **検証**: 動画デモ2が動作する。

### Step 56 — 3分割動画デモ (video3) の Canvas2D 化
- **変更ファイル**: `elona_video3.html`
- **実装**: 同上。
- **検証**: 動画デモ3が動作する。

### Step 57 — 複数キャンバス競合の回避
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: 状態をグローバルに持たず、クラスインスタンス（`this`）内に閉じることで、同一ページに複数のキャンバスを置けるように保証。
- **検証**: 1つのHTMLに2つのCanvasを置き、別々のシーンが独立して動く。

### Step 58 — リサイズ処理の対応
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: `window.addEventListener('resize')` でキャンバス幅を再設定し、アスペクト比を維持。
- **検証**: ブラウザのウィンドウ幅を変えても描画が極端に潰れない。

### Step 59 — UIイベントハンドリングの追加
- **変更ファイル**: `elona_canvas_core.js`
- **実装**: キャンバス上のクリック座標を拾い、ゲーム内座標へ逆変換してロジックへ渡すリスナー。
- **検証**: マップ上のタイルをクリックした際、正しい論理座標が取得できる。

### Step 60 — 統合後のパフォーマンスチェック
- **変更ファイル**: なし（検証のみ）
- **実装**: 動画デモ3種や `canvas_template.html` を動かし、Chrome DevTools で 60FPS を維持できるか確認。
- **検証**: 大幅なフレームドロップがない。

---

## フェーズD: 旧依存の削除（破壊的） 〔ステップ61〜72〕

### Step 61 — WebGLレンダラの削除
- **変更ファイル**: `src/render/Renderer.ts`
- **実装**: 不要になった three.js ベースの WebGL レンダラファイルを削除。
- **検証**: ファイルが存在しない。

### Step 62 — 旧WebGLデモの削除
- **変更ファイル**: `webgl_template.html` 等
- **実装**: WebGL に依存していた古いデモHTMLを削除。
- **検証**: ファイルが存在しない。

### Step 63 — Three.js 依存関係の排除
- **変更ファイル**: `package.json`
- **実装**: `dependencies` または `devDependencies` から `three` を削除し `npm install`。
- **検証**: `node_modules/three` が消える。

### Step 64 — 旧PixiJSエフェクト群の削除
- **変更ファイル**: `demos/lib/ParticleSystem.js`, `FluidRenderer.js` 等
- **実装**: Canvas2Dに移植完了した PixiJS ベースのエフェクトファイルを削除。
- **検証**: 該当ファイル群が存在しない。

### Step 65 — PixiJS 依存関係の排除
- **変更ファイル**: `package.json`
- **実装**: `pixi.js` を削除し `npm install`。
- **検証**: `node_modules/pixi.js` が消える。

### Step 66 — `vite.config.js` の整理
- **変更ファイル**: `vite.config.js`
- **実装**: Three.js や PixiJS のビルド最適化設定などが残っていれば削除。
- **検証**: Vite 起動時にエラーが出ない。

### Step 67 — `package.json` スクリプト整理
- **変更ファイル**: `package.json`
- **実装**: `scripts` 内の不要なビルドステップを整理し、単純なローカルサーバー起動を主とする。
- **検証**: `npm run dev` 等が正常に動作する。

### Step 68 — `file://` 再生テスト
- **変更ファイル**: なし（検証のみ）
- **実装**: `canvas_template.html` などをブラウザに直接ドラッグ＆ドロップして開く。
- **検証**: CORS エラーやビルドエラーなく、そのままゲーム・デモが実行される。

### Step 69 — Lighthouse による検証
- **変更ファイル**: なし（検証のみ）
- **実装**: デモページに対し Lighthouse を実行し、パフォーマンスと外部CDN依存ゼロ（ネットワークリクエスト減）を確認。
- **検証**: 外部JSの読み込みがなく、初期ロードが高速化されている。

### Step 70 — テストコードの修正
- **変更ファイル**: 既存の `test_*.py` または JSテスト
- **実装**: レンダリング層に関するテスト（スタブ生成など）が旧 WebGL クラスを参照していれば `CanvasCore` 系に修正。
- **検証**: 全てのテストが GREEN になる。

### Step 71 — README の更新
- **変更ファイル**: `README.md`
- **実装**: アーキテクチャの解説部分を「Three/Pixi から Canvas 2D へ完全統合。依存なしの file:// 再生可能」へ書き換え。
- **検証**: README が正しく更新されている。

### Step 72 — 最終動作確認とリリース
- **変更ファイル**: なし（検証のみ）
- **実装**: ルートからプロジェクト全体を見渡し、デモ、ゲームプレイ、ビルド全てが新 Canvas 2D エンジン上で動作していることを最終確認。
- **検証**: 全てのエラーログがなく、快適に動作する。
