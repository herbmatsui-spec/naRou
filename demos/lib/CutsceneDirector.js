/**
 * カットシーン演出ディレクター (FF6案6)
 *
 * DOMオーバーレイ式のカットシーン再生機構。
 * web_game_client.html の loading-overlay と同一系統の
 * z-index:2000 フルスクリーンオーバーレイを動的に生成し、
 * 「フェード暗転 → テロップ送り → 背景スライド → フェード復帰」を再生する。
 *
 * 使い方:
 *   const director = new CutsceneDirector();
 *   await director.play([
 *     { text: "★メインクエスト【運命の始まり】 完了！", background: "#000000", duration: 2600 },
 *   ]);
 *
 * 各ステップはテキスト (text)・背景色 (background)・表示時間ms (duration) を指定可能。
 * 表示中はテロップ部クリック / Enter / Space で次のテロップへ送り、
 * 「スキップ ▶」ボタンでシーケンス全体を即時中断できる。
 */
export class CutsceneDirector {
  /**
   * @param {object} [options]
   * @param {number} [options.fadeMs] - 暗転/復帰フェードの所要ms
   * @param {number} [options.autoAdvanceMs] - duration未指定テロップの既定表示時間ms
   * @param {number} [options.zIndex] - オーバーレイのz-index (loading-overlayと同じ2000)
   */
  constructor(options = {}) {
    this.fadeMs = options.fadeMs ?? 600;
    this.autoAdvanceMs = options.autoAdvanceMs ?? 2600;
    this.zIndex = options.zIndex ?? 2000;
    this._root = null;
    this._bgLayer = null;
    this._telop = null;
    this._playing = false;
    this._skipRequested = false;
    this._onAdvance = null;
    this._queue = [];
    this._keyHandler = null;
  }

  /** 再生中かどうか */
  get isPlaying() {
    return this._playing;
  }

  /**
   * カットシーンを再生する (フェード暗転 → テロップ送り → 背景スライド → フェード復帰)
   * @param {Array<{text: string, background?: string, duration?: number}>} sequence - ステップ配列
   * @returns {Promise<boolean>} 再生を実行したらtrue (空シーケンスはfalse)
   */
  async play(sequence) {
    if (!Array.isArray(sequence) || sequence.length === 0) {
      return false;
    }
    if (this._playing) {
      // 再生中は次のシーケンスを予約し、現在の再生終了後に続けて再生する
      this._queue.push(sequence);
      return true;
    }
    this._playing = true;
    try {
      await this._run(sequence);
      while (this._queue.length > 0 && !this._skipRequested) {
        await this._run(this._queue.shift());
      }
    } finally {
      this._playing = false;
      this._skipRequested = false;
      this._teardownDom();
    }
    return true;
  }

  /** 再生中のシーケンスを即時中断する (スキップボタンからも呼ばれる) */
  skip() {
    this._skipRequested = true;
    this._notifyAdvance();
  }

  /** 現在表示中のテロップを送り、次のステップへ進む */
  advance() {
    this._notifyAdvance();
  }

  /** リソースを破棄 */
  destroy() {
    this.skip();
    this._queue = [];
    this._teardownDom();
  }

  // ==================== 内部処理 ====================

  async _run(sequence) {
    this._ensureDom();
    this._skipRequested = false;

    // フェード暗転
    this._root.style.opacity = "1";
    await this._wait(this.fadeMs);

    // テロップ送り (背景スライドはCSS遷移で滑らかに切り替わる)
    for (const step of sequence) {
      if (this._skipRequested) break;
      if (this._bgLayer) {
        this._bgLayer.style.background = step.background || "#000000";
      }
      if (this._telop) {
        this._telop.textContent = step.text || "";
      }
      const duration = typeof step.duration === "number" ? step.duration : this.autoAdvanceMs;
      await this._waitForAdvance(Math.max(200, duration));
    }

    // フェード復帰
    if (this._root) this._root.style.opacity = "0";
    await this._wait(this.fadeMs);
  }

  /** タイムアウトまたは送り要求のどちらか早い方で解決する */
  _waitForAdvance(ms) {
    return new Promise((resolve) => {
      let settled = false;
      const finish = () => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        this._onAdvance = null;
        resolve();
      };
      const timer = setTimeout(finish, ms);
      this._onAdvance = finish;
    });
  }

  _notifyAdvance() {
    if (this._onAdvance) this._onAdvance();
  }

  _wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /** オーバーレイDOMを生成する (loading-overlayパターンを流用) */
  _ensureDom() {
    if (this._root) return;

    const root = document.createElement("div");
    root.id = "cutscene-overlay";
    root.style.cssText = [
      "position:fixed",
      "inset:0",
      `z-index:${this.zIndex}`,
      "display:flex",
      "align-items:center",
      "justify-content:center",
      "opacity:0",
      "transition:opacity .6s ease",
      "background:#000",
      "color:#fff",
      "font-family:sans-serif",
      "cursor:pointer",
    ].join(";");

    const bgLayer = document.createElement("div");
    bgLayer.style.cssText = [
      "position:absolute",
      "inset:0",
      "background:#000",
      "transition:background .8s ease",
    ].join(";");

    const telop = document.createElement("div");
    telop.style.cssText = [
      "position:relative",
      "max-width:80%",
      "padding:16px 28px",
      "font-size:20px",
      "line-height:1.8",
      "text-align:center",
      "text-shadow:0 0 12px rgba(255,215,0,.55)",
      "letter-spacing:.08em",
    ].join(":");

    const skipBtn = document.createElement("button");
    skipBtn.textContent = "スキップ ▶";
    skipBtn.style.cssText = [
      "position:absolute",
      "bottom:16px",
      "right:16px",
      "padding:8px 16px",
      "background:rgba(17,24,39,.92)",
      "color:#fff",
      "border:1px solid #4a7ae6",
      "border-radius:8px",
      "cursor:pointer",
      "font-size:13px",
    ].join(";");
    skipBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      this.skip();
    });

    root.appendChild(bgLayer);
    root.appendChild(telop);
    root.appendChild(skipBtn);

    // テロップ送り操作: 画面クリック / Enter / Space
    root.addEventListener("click", () => this.advance());
    this._keyHandler = (e) => {
      if (e.code === "Enter" || e.code === "Space") {
        e.preventDefault();
        this.advance();
      }
    };
    document.addEventListener("keydown", this._keyHandler);

    document.body.appendChild(root);
    this._root = root;
    this._bgLayer = bgLayer;
    this._telop = telop;
  }

  /** オーバーレイDOMを破棄する */
  _teardownDom() {
    if (this._keyHandler) {
      document.removeEventListener("keydown", this._keyHandler);
      this._keyHandler = null;
    }
    if (this._root && this._root.parentNode) {
      this._root.parentNode.removeChild(this._root);
    }
    this._root = null;
    this._bgLayer = null;
    this._telop = null;
    this._onAdvance = null;
  }
}

// グローバルスコープにもエクスポート（後方互換性のため）
window.CutsceneDirector = CutsceneDirector;
