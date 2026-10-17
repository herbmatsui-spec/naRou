/**
 * マップ遷移演出ディレクター (FF6案9)
 *
 * 階段使用・フロア遷移時の3フェーズ演出を再生する DOM オーバーレイ。
 * 「暗転フェード → フロア名カード表示 → ホワイトアウト → フェード復帰」の順で流れ、
 * 暗転のピークで onMidpoint コールバックを呼ぶことで、新フロアのデータ再読込を
 * 画面が真っ暗な間に挟める。
 *
 * 使い方:
 *   const director = new TransitionDirector();
 *   director.playTransition("B2F", async () => { await refetchState(); });
 */
export class TransitionDirector {
  /**
   * @param {object} [options]
   * @param {number} [options.zIndex] - オーバーレイのz-index (カットシーンと同系統の2000)
   * @param {number} [options.fadeMs] - 各フェードの所要ms
   * @param {number} [options.cardMs] - フロア名カードの表示ms
   */
  constructor(options = {}) {
    this.zIndex = options.zIndex ?? 2000;
    this.fadeMs = options.fadeMs ?? 400;
    this.cardMs = options.cardMs ?? 1200;
    this._root = null;
    this._card = null;
    this._playing = false;
  }

  /** 再生中かどうか */
  get isPlaying() {
    return this._playing;
  }

  /**
   * フロア遷移演出を再生する
   * @param {string} floorName - フロア名 (例: "B2F", "地上", "最深部")
   * @param {Function} [onMidpoint] - 暗転ピーク時に呼ばれるコールバック (データ再読込用)
   * @returns {Promise<boolean>} 再生を実行したらtrue
   */
  async playTransition(floorName, onMidpoint) {
    if (this._playing) return false;
    this._playing = true;
    try {
      this._ensureDom();
      if (this._card) {
        this._card.textContent = floorName || "";
      }

      // フェーズ1: 暗転フェードイン
      this._root.style.background = "rgba(2,3,8,1)";
      this._root.style.opacity = "1";
      await this._wait(this.fadeMs);

      // 暗転ピーク: 新フロアデータの再読込を行う
      if (typeof onMidpoint === "function") {
        try {
          await onMidpoint();
        } catch (err) {
          console.warn("TransitionDirector: midpoint callback failed:", err);
        }
      }

      // フェーズ2: フロア名カード表示 (FF6風: 装飾枠 + ゆっくりフェードイン)
      if (this._card) {
        this._card.style.opacity = "1";
        this._card.style.transform = "translateX(-50%) translateY(0)";
      }
      await this._wait(this.cardMs);
      if (this._card) {
        this._card.style.opacity = "0";
        this._card.style.transform = "translateX(-50%) translateY(-12px)";
      }
      await this._wait(250);

      // フェーズ3: ホワイトアウト → 復帰
      this._root.style.background = "rgba(240,244,252,1)";
      await this._wait(220);
      this._root.style.opacity = "0";
      await this._wait(this.fadeMs);
    } finally {
      this._teardownDom();
      this._playing = false;
    }
    return true;
  }

  /** 即時中断 (強制フロア移動など) */
  cancel() {
    this._teardownDom();
    this._playing = false;
  }

  // ==================== 内部処理 ====================

  /** オーバーレイDOMを生成する (未生成時のみ) */
  _ensureDom() {
    if (this._root) return;
    const root = document.createElement("div");
    root.className = "floor-transition-overlay";
    root.style.cssText = `position:fixed; inset:0; z-index:${this.zIndex}; pointer-events:none; background:rgba(2,3,8,1); opacity:0; transition:opacity ${this.fadeMs}ms ease, background .22s ease;`;
    root.innerHTML = `
      <div class="floor-transition-card" style="position:absolute; left:50%; top:44%; transform:translateX(-50%) translateY(-12px); padding:16px 48px; border:2px solid rgba(229,169,59,.85); border-radius:8px; background:rgba(8,10,18,.94); font-family:var(--font-title, 'Cinzel', serif); font-size:1.6rem; font-weight:700; letter-spacing:.28em; color:#e5a93b; text-shadow:0 0 14px rgba(229,169,59,.55); opacity:0; transition:opacity .35s ease, transform .35s ease;"></div>`;
    this._root = root;
    this._card = root.querySelector(".floor-transition-card");
    document.body.appendChild(root);
  }

  /** DOMを撤去する */
  _teardownDom() {
    if (this._root && this._root.parentNode) {
      this._root.parentNode.removeChild(this._root);
    }
    this._root = null;
    this._card = null;
  }

  /** 単純待機 */
  _wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
