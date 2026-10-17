/**
 * ボス戦専用演出ディレクター (T18 案3)
 *
 * ボス出現時に起動する演出を PIXI (スプライト/暗転) と DOM (テロップ/HPバー) の
 * 併用で再生する。FF6風の「暗転 → ボス出現ズーム → 名前テロップ → 専用HPバー →
 * フェード復帰」シーケンスと、撃破時の「スローモーション崩壊 → 勝利テロップ」を担う。
 *
 * 使い方:
 *   const director = new BossBattleDirector(pixiApp);
 *   director.init();                       // FF6_BOSS アトラスを事前ロード (非同期)
 *   director.playEntrance("ヴォイドの覇者"); // 出現検知フレームで呼ぶ
 *   director.updateBossHp(hp, maxHp);      // 毎フレーム / state同期時に呼ぶ
 *   director.onDefeated();                 // ボスが消えた (撃破) フレームで呼ぶ
 *
 * ボススプライトは assets/tiles/tileset_def.json の FF6_BOSS TileDef
 * (anchor=(0.5,1.0), 64x64, 2フレーム) に準拠し、direction=0 (正面) を使用する。
 * アトラス読み込みに失敗した場合は描画フォールバック (Graphicsシルエット) に切り替える。
 */
export class BossBattleDirector {
  /**
   * @param {PIXI.Application} app - 演出オーバーレイを重ねる PIXI アプリ
   * @param {object} [options]
   * @param {number} [options.darkenMs] - 画面暗転の所要ms
   * @param {number} [options.slideMs] - スライドイン＋ズームアップの所要ms
   * @param {number} [options.holdMs] - テロップ/HPバーを静止表示するms
   * @param {number} [options.domZIndex] - DOMテロップ/HPバーのz-index
   */
  constructor(app, options = {}) {
    this.app = app;
    this.darkenMs = options.darkenMs ?? 1000;
    this.slideMs = options.slideMs ?? 1200;
    this.holdMs = options.holdMs ?? 1600;
    this.domZIndex = options.domZIndex ?? 2600;

    this._overlay = null;      // 演出用 PIXI コンテナ (stage 最前面に都度追加)
    this._curtain = null;      // 暗転用黒幕
    this._bossSprite = null;   // 出現演出用ボススプライト
    this._bossTextures = null; // FF6_BOSS フレームテクスチャ配列 (direction=0)
    this._initPromise = null;

    this._hpBarDom = null;     // 専用HPバー (DOM・戦闘中表示を維持)
    this._telopDom = null;     // ボス名テロップ帯 (DOM)
    this._victoryDom = null;   // 勝利テロップ (DOM)
    this._fragmentLayer = null; // 撃破崩壊フラグメント (PIXI)

    this._entrancePlaying = false;
    this._defeatedPlaying = false;
  }

  /** 入場演出が再生中かどうか */
  get isEntrancePlaying() {
    return this._entrancePlaying;
  }

  /**
   * FF6_BOSS のアトラス/TileDef を事前ロードする (冪等・失敗時はフォールバック)
   * @returns {Promise<void>}
   */
  init() {
    if (this._initPromise) return this._initPromise;
    this._initPromise = this._loadBossTextures().catch((err) => {
      console.warn("BossBattleDirector: ボスアトラス読み込み失敗、フォールバック描画を使用します", err);
      this._bossTextures = null;
    });
    return this._initPromise;
  }

  /**
   * ボス出現演出を再生する (暗転 → スライドイン+ズーム → 名前テロップ → HPバー → フェード復帰)
   * 再生中の2度目の呼び出しは無視される。
   * @param {string} bossName - テロップ/HPバーに表示するボス名
   */
  async playEntrance(bossName) {
    if (this._entrancePlaying || this._defeatedPlaying) return;
    this._entrancePlaying = true;
    try {
      await this.init();
      this._buildOverlay();

      const screen = this.app.screen;
      const baseScale = 1.0;
      const targetScale = 2.2;
      const footY = screen.height * 0.55;

      // --- 1. 画面暗転 (1秒) ---
      this._curtain.alpha = 0;
      await this._tween(this.darkenMs * 0.6, (t) => {
        this._curtain.alpha = t;
      });

      // --- 2. ボススプライト: 右端からスライドイン + ズームアップ (1.2秒) ---
      this._bossSprite = this._createBossSprite();
      this._bossSprite.anchor.set(0.5, 1.0); // FF6_BOSS TileDef 準拠 (下端基準)
      this._bossSprite.x = screen.width + 80;
      this._bossSprite.y = footY;
      this._bossSprite.scale.set(baseScale);
      this._bossSprite.alpha = 0;
      this._overlay.addChild(this._bossSprite);

      await this._tween(this.slideMs, (t) => {
        const ease = 1 - Math.pow(1 - t, 3); // easeOutCubic
        this._bossSprite.x = (screen.width + 80) + ((screen.width / 2) - (screen.width + 80)) * ease;
        this._bossSprite.scale.set(baseScale + (targetScale - baseScale) * ease);
        this._bossSprite.alpha = Math.min(1, t * 3);
      });

      // --- 3. ボス名テロップ (FF6風: 左からスライドする帯 + Cinzel) ---
      this._showNameTelop(bossName || "？？？");

      // --- 4. 専用HPバー (金枠 + 赤ゲージ, DOM) を画面上部へ固定表示 ---
      this._showHpBar(bossName || "？？？");

      // テロップを静止表示
      await this._wait(this.holdMs);
      this._hideNameTelop();

      // --- 5. フェードでゲームへ復帰 (HPバーは表示維持) ---
      await this._tween(600, (t) => {
        this._curtain.alpha = 1 - t;
        if (this._bossSprite) this._bossSprite.alpha = 1 - t;
      });
      this._teardownOverlay();
    } finally {
      this._entrancePlaying = false;
    }
  }

  /**
   * 専用HPバーのゲージを更新する (未表示なら表示する)
   * @param {number} current
   * @param {number} max
   */
  updateBossHp(current, max) {
    if (!this._hpBarDom) {
      // 出現演出をスキップされた場合でもHPバーだけは表示する
      this._showHpBar("？？？");
    }
    if (max <= 0) return;
    const ratio = Math.max(0, Math.min(1, current / max));
    const gauge = this._hpBarDom.querySelector(".boss-hp-gauge");
    if (gauge) gauge.style.width = `${(ratio * 100).toFixed(1)}%`;
  }

  /**
   * ボス撃破演出を再生する (スローモーション + 崩壊エフェクト + 勝利テロップ)
   */
  async onDefeated() {
    if (this._defeatedPlaying) return;
    this._defeatedPlaying = true;
    try {
      // HPバーを閉じる
      this._hideHpBar();

      // --- 崩壊エフェクト: ボス体内からフラグメントが慢速で飛散・崩落 ---
      await this.init();
      const screen = this.app.screen;
      const cx = screen.width / 2;
      const cy = screen.height * 0.5;

      // 勝利の白フラッシュ (一瞬)
      this._overlay = new PIXI.Container();
      this.app.stage.addChild(this._overlay);
      const flash = new PIXI.Graphics();
      flash.beginFill(0xfff8e0);
      flash.drawRect(0, 0, screen.width, screen.height);
      flash.endFill();
      flash.alpha = 0.85;
      this._overlay.addChild(flash);
      await this._tween(400, (t) => {
        flash.alpha = 0.85 * (1 - t);
      });

      // フラグメント生成 (ボススプライトの一部を写した破片)
      this._fragmentLayer = new PIXI.Container();
      this._overlay.addChild(this._fragmentLayer);
      const fragments = [];
      const srcTexture = this._bossTextures ? this._bossTextures[0] : null;
      const COUNT = 14;
      for (let i = 0; i < COUNT; i++) {
        let tex;
        if (srcTexture) {
          // 元テクスチャからランダムな 12〜20px の破片を切り出す
          const fw = 12 + Math.random() * 8;
          const fh = 12 + Math.random() * 8;
          const fx = Math.random() * (srcTexture.width - fw);
          const fy = Math.random() * (srcTexture.height - fh);
          tex = new PIXI.Texture(srcTexture.baseTexture, new PIXI.Rectangle(fx, fy, fw, fh));
        }
        const frag = tex ? new PIXI.Sprite(tex) : this._createFallbackFragment();
        frag.anchor.set(0.5, 0.5);
        frag.x = cx + (Math.random() - 0.5) * 90;
        frag.y = cy + (Math.random() - 0.5) * 70;
        frag.rotation = Math.random() * Math.PI * 2;
        frag.scale.set(0.9 + Math.random() * 0.8);
        frag._vx = (Math.random() - 0.5) * 120; // 水平初速
        frag._vy = -(20 + Math.random() * 60);  // わずかに舞い上がってから落下
        frag._vr = (Math.random() - 0.5) * 3.0;
        this._fragmentLayer.addChild(frag);
        fragments.push(frag);
      }

      // スローモーション崩壊 (2.4秒かけて緩やかに崩れ落ちる)
      await this._tween(2400, (t) => {
        const slow = Math.pow(t, 0.6); // 前半だけ速く、後半はゆったり動く
        for (const frag of fragments) {
          frag.x += frag._vx * 0.016;
          frag._vy += 55 * 0.016; // 弱い重力 = ゆっくり落下
          frag.y += frag._vy * 0.016;
          frag.rotation += frag._vr * 0.016;
          frag.alpha = 1 - slow;
        }
      });

      // --- 勝利テロップ ---
      this._showVictoryTelop();
      await this._wait(2000);
      this._hideVictoryTelop();
      await this._wait(400);
      this._teardownOverlay();
    } finally {
      this._defeatedPlaying = false;
    }
  }

  /** 全リソースを破棄する */
  destroy() {
    this._teardownOverlay();
    this._hideHpBar();
    this._hideVictoryTelop();
    this._initPromise = null;
    this._bossTextures = null;
  }

  // ==================== 内部処理 ====================

  /**
   * FF6_BOSS TileDef + アトラスから direction=0 のフレームテクスチャ列を構築する
   */
  async _loadBossTextures() {
    const defRes = await fetch("assets/tiles/tileset_def.json");
    const defData = await defRes.json();
    const def = (defData.tiles || {})["FF6_BOSS"];
    if (!def) throw new Error("FF6_BOSS TileDef が見つかりません");

    const metaRes = await fetch("assets/tiles/tileset_ff6_actors_16x16.json");
    const meta = await metaRes.json();
    const region = (meta.tiles || {})["FF6_BOSS"];
    if (!region) throw new Error("FF6_BOSS がアトラスメタデータに存在しません");

    const image = await new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = "assets/tiles/tileset_ff6_actors_16x16.png";
    });

    const baseTexture = new PIXI.BaseTexture(image);
    const frameW = def.frame_width || 64;
    const frameH = region.height / (def.directions || 1);
    const dy = region.y; // direction=0 (正面) のみ使用
    const textures = [];
    for (let f = 0; f < (def.frames || 1); f++) {
      textures.push(new PIXI.Texture(
        baseTexture,
        new PIXI.Rectangle(region.x + f * frameW, dy, frameW, frameH)
      ));
    }
    this._bossTextures = textures;
  }

  /** ボススプライトを生成する (テクスチャ未取得時は Graphics シルエット) */
  _createBossSprite() {
    if (this._bossTextures && this._bossTextures.length > 0) {
      const sprite = new PIXI.Sprite(this._bossTextures[0]);
      // 暗転に負けないよう僅かに発光色を重ねる
      sprite.tint = 0xfff2e0;
      return sprite;
    }
    // フォールバック: 64x64 の悪魔的シルエットを描く
    const g = new PIXI.Graphics();
    g.beginFill(0x3a1f4d);
    g.drawRoundedEllipse(0, 0, 40, 52);
    g.endFill();
    g.beginFill(0x2a1436);
    g.drawPolygon([-30, -18, -14, -44, -8, -18]);
    g.drawPolygon([30, -18, 14, -44, 8, -18]);
    g.endFill();
    g.beginFill(0xff3030);
    g.drawCircle(-9, -14, 4);
    g.drawCircle(9, -14, 4);
    g.endFill();
    return new PIXI.Sprite(this.app.renderer.generateTexture(g));
  }

  /** 撃破崩壊のフォールバック破片 ( Graphics ) */
  _createFallbackFragment() {
    const g = new PIXI.Graphics();
    g.beginFill(0x4a2a5e);
    g.drawPolygon([-6, -5, 6, -4, 4, 6, -5, 5]);
    g.endFill();
    return new PIXI.Sprite(this.app.renderer.generateTexture(g));
  }

  /** 演出オーバーレイ (黒幕) を stage 最前面に構築する */
  _buildOverlay() {
    this._teardownOverlay();
    const screen = this.app.screen;
    this._overlay = new PIXI.Container();
    this._curtain = new PIXI.Graphics();
    this._curtain.beginFill(0x000000);
    this._curtain.drawRect(0, 0, screen.width, screen.height);
    this._curtain.endFill();
    this._overlay.addChild(this._curtain);
    this.app.stage.addChild(this._overlay); // 都度最前面へ
  }

  /** 演出オーバーレイ (PIXI) を破棄する */
  _teardownOverlay() {
    if (this._overlay && this._overlay.parent) {
      this._overlay.parent.removeChild(this._overlay);
    }
    this._overlay = null;
    this._curtain = null;
    this._bossSprite = null;
    this._fragmentLayer = null;
  }

  /** ボス名テロップ帯 (DOM) を表示する */
  _showNameTelop(bossName) {
    this._hideNameTelop(true);
    const root = document.createElement("div");
    root.className = "boss-telop-root";
    root.style.cssText = [
      "position:fixed",
      "left:0",
      "top:16%",
      "width:100%",
      "z-index:" + this.domZIndex,
      "pointer-events:none",
      "overflow:hidden",
    ].join(";");

    const band = document.createElement("div");
    band.style.cssText = [
      "display:inline-flex",
      "align-items:center",
      "gap:14px",
      "padding:10px 48px 10px 32px",
      "background:linear-gradient(90deg, rgba(10,8,4,.96) 0%, rgba(64,48,12,.88) 78%, rgba(64,48,12,0) 100%)",
      "border-top:2px solid #ffd700",
      "border-bottom:2px solid #ffd700",
      "transform:translateX(-105%)",
      "transition:transform .7s cubic-bezier(.22,1,.36,1)",
      "font-family:var(--font-title, 'Cinzel', serif)",
      "font-size:30px",
      "font-weight:800",
      "letter-spacing:.18em",
      "color:#ffd700",
      "text-shadow:0 0 14px rgba(255,120,40,.8), 0 2px 4px rgba(0,0,0,.9)",
      "white-space:nowrap",
    ].join(";");

    const ornament = document.createElement("span");
    ornament.textContent = "◆";
    ornament.style.cssText = "font-size:16px;color:#ff8c00;";
    const label = document.createElement("span");
    label.textContent = bossName;

    band.appendChild(ornament);
    band.appendChild(label);
    root.appendChild(band);
    document.body.appendChild(root);
    this._telopDom = root;

    // 左からスライドイン
    requestAnimationFrame(() => {
      band.style.transform = "translateX(0)";
    });
  }

  /** ボス名テロップ帯 (DOM) を退場させる */
  _hideNameTelop(immediate = false) {
    const root = this._telopDom;
    this._telopDom = null;
    if (!root) return;
    const band = root.firstChild;
    if (immediate || !band) {
      root.remove();
      return;
    }
    band.style.transform = "translateX(-105%)";
    setTimeout(() => root.remove(), 750);
  }

  /** 専用HPバー (DOM・金枠 + 赤ゲージ) を画面上部に固定表示する */
  _showHpBar(bossName) {
    if (this._hpBarDom) return;
    const root = document.createElement("div");
    root.className = "boss-hpbar-root";
    root.style.cssText = [
      "position:fixed",
      "top:22px",
      "left:50%",
      "transform:translateX(-50%)",
      "width:min(440px, 62vw)",
      "z-index:" + this.domZIndex,
      "pointer-events:none",
      "text-align:center",
    ].join(";");

    const label = document.createElement("div");
    label.textContent = bossName;
    label.style.cssText = [
      "font-family:var(--font-title, 'Cinzel', serif)",
      "font-size:13px",
      "font-weight:700",
      "letter-spacing:.22em",
      "color:#ffd700",
      "text-shadow:0 1px 3px rgba(0,0,0,.9)",
      "margin-bottom:4px",
    ].join(";");

    const frame = document.createElement("div");
    // 金枠 + 赤ゲージ
    frame.style.cssText = [
      "height:16px",
      "border:2px solid #ffd700",
      "border-radius:3px",
      "box-shadow:0 0 10px rgba(255,215,0,.35), inset 0 0 6px rgba(0,0,0,.9)",
      "background:rgba(12,8,4,.85)",
      "padding:2px",
      "overflow:hidden",
    ].join(";");

    const gauge = document.createElement("div");
    gauge.className = "boss-hp-gauge";
    gauge.style.cssText = [
      "height:100%",
      "width:100%",
      "background:linear-gradient(180deg, #ff6a5e 0%, #e02020 45%, #8f0f0f 100%)",
      "transition:width .25s ease-out",
      "box-shadow:0 0 8px rgba(255,60,40,.7)",
    ].join(";");

    frame.appendChild(gauge);
    root.appendChild(label);
    root.appendChild(frame);
    document.body.appendChild(root);
    this._hpBarDom = root;
  }

  /** 専用HPバー (DOM) を退場させる */
  _hideHpBar() {
    const root = this._hpBarDom;
    this._hpBarDom = null;
    if (!root) return;
    root.style.transition = "opacity .5s ease";
    root.style.opacity = "0";
    setTimeout(() => root.remove(), 520);
  }

  /** 勝利テロップ (DOM) を表示する */
  _showVictoryTelop() {
    const root = document.createElement("div");
    root.className = "boss-victory-root";
    root.style.cssText = [
      "position:fixed",
      "inset:0",
      "display:flex",
      "align-items:center",
      "justify-content:center",
      "z-index:" + this.domZIndex,
      "pointer-events:none",
      "background:radial-gradient(ellipse at center, rgba(0,0,0,0) 30%, rgba(0,0,0,.72) 100%)",
    ].join(";");

    const text = document.createElement("div");
    text.textContent = "VICTORY!";
    text.style.cssText = [
      "font-family:var(--font-title, 'Cinzel', serif)",
      "font-size:min(84px, 12vw)",
      "font-weight:800",
      "letter-spacing:.2em",
      "background:linear-gradient(135deg, #fff3b0, #ffd700 45%, #ff8c00)",
      "-webkit-background-clip:text",
      "background-clip:text",
      "-webkit-text-fill-color:transparent",
      "filter:drop-shadow(0 0 22px rgba(255,180,40,.85))",
      "transform:scale(.6)",
      "opacity:0",
      "transition:transform .55s cubic-bezier(.22,1.4,.36,1), opacity .4s ease",
    ].join(";");
    root.appendChild(text);
    document.body.appendChild(root);
    this._victoryDom = root;

    requestAnimationFrame(() => {
      text.style.transform = "scale(1)";
      text.style.opacity = "1";
    });
  }

  /** 勝利テロップ (DOM) を退場させる */
  _hideVictoryTelop() {
    const root = this._victoryDom;
    this._victoryDom = null;
    if (!root) return;
    root.style.transition = "opacity .45s ease";
    root.style.opacity = "0";
    setTimeout(() => root.remove(), 480);
  }

  /** rAF ベースの簡易トゥイーン (0→1 を onUpdate へ渡す) */
  _tween(durationMs, onUpdate) {
    return new Promise((resolve) => {
      const start = performance.now();
      const step = (now) => {
        const t = Math.min(1, (now - start) / Math.max(1, durationMs));
        onUpdate(t);
        if (t < 1) requestAnimationFrame(step);
        else resolve();
      };
      requestAnimationFrame(step);
    });
  }

  /** setTimeout の Promise ラッパー (CutsceneDirector._wait と同型) */
  _wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

// グローバルスコープにもエクスポート（後方互換性のため）
window.BossBattleDirector = BossBattleDirector;
