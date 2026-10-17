/**
 * レアドロップ演出ディレクター (FF6案7)
 *
 * アイテム獲得時の3段演出を再生する DOM オーバーレイ。
 * 「スロット風リール → レアリティ別光柱 → アイテム名テロップ」を一気通貫で見せる。
 *
 * 使い方:
 *   const director = new RareDropDirector();
 *   director.playDrop("絹のローブ", "epic");
 *
 * レアリティは common / uncommon / rare / epic / legendary を想定し、
 * 色は .rarity-* クラス (components.css) と同一トーンで統一している。
 * common はリール省略 (テロップのみ) で静かに表示する。
 */
export class RareDropDirector {
  /**
   * @param {object} [options]
   * @param {number} [options.zIndex] - オーバーレイのz-index (HUDより上・カットシーンより下)
   * @param {number} [options.reelSpinMs] - スロットリールの回転時間ms
   * @param {number} [options.pillarMs] - 光柱の点灯時間ms
   */
  constructor(options = {}) {
    this.zIndex = options.zIndex ?? 1500;
    this.reelSpinMs = options.reelSpinMs ?? 900;
    this.pillarMs = options.pillarMs ?? 1400;
    this._root = null;
    this._playing = false;

    // レアリティ → 表示色 (design_tokens.json の color.semantic.* と同一)
    this._rarityColor = {
      common: "#6b7280",
      uncommon: "#10b981",
      rare: "#3b82f6",
      epic: "#a855f7",
      legendary: "#d4af37",
    };
    // リールに流れるアイコン (FF6風の装飾記号)
    this._reelIcons = ["🗡", "🛡", "💍", "📜", "🧪", "⚔️", "💎", "🔮", "👑", "🍀"];
  }

  /** 再生中かどうか */
  get isPlaying() {
    return this._playing;
  }

  /**
   * レアドロップ演出を再生する
   * @param {string} itemName - アイテム名
   * @param {string} rarity - common/uncommon/rare/epic/legendary
   */
  async playDrop(itemName, rarity = "common") {
    if (this._playing) return;
    const color = this._rarityColor[rarity] || this._rarityColor.common;
    this._playing = true;
    try {
      this._ensureDom();
      this._root.style.opacity = "1";

      // 段1: スロット風リール (common は省略して静かに)
      if (rarity !== "common") {
        await this._playReel(color, rarity);
      }

      // 段2: レアリティ別光柱 (common は控えめなフラッシュのみ)
      this._playPillar(color, rarity === "common" ? 0.35 : 1.0);
      await this._wait(this.pillarMs * 0.6);

      // 段3: アイテム名テロップ
      this._showTelop(itemName, color, rarity);
      await this._wait(this.pillarMs * 0.8);

      // フェード復帰
      this._root.style.opacity = "0";
      await this._wait(400);
    } finally {
      this._teardownDom();
      this._playing = false;
    }
  }

  // ==================== 内部処理 ====================

  /** スロット風リール: アイコンが高速で切り替わり、レアリティが高いほど長く回る */
  async _playReel(color, rarity) {
    this._ensureDom();
    const reel = this._reel;
    if (!reel) return;
    reel.style.display = "flex";
    reel.style.borderColor = color;
    // 終盤ほど遅く (スロットの減速感)。spins は回転数の目安としてのみ利用
    const spins = raritySpinCount(rarity, this.reelSpinMs);
    void spins;
    const start = Date.now();
    let i = 0;
    while (Date.now() - start < this.reelSpinMs) {
      reel.textContent = this._reelIcons[i % this._reelIcons.length];
      // 終盤ほど遅く (スロットの減速感)
      const elapsed = (Date.now() - start) / this.reelSpinMs;
      const interval = 40 + elapsed * elapsed * 160;
      await this._wait(interval);
      i += 1;
    }
    await this._wait(150);
    reel.style.display = "none";
  }

  /** レアリティ別光柱: 中心から立ち上る光の柱をCSSグローで表現 */
  _playPillar(color, intensity) {
    const pillar = this._pillar;
    if (!pillar) return;
    pillar.style.display = "block";
    pillar.style.background = `linear-gradient(to top, ${color}00 0%, ${color}${Math.round(intensity * 200)
      .toString(16)
      .padStart(2, "0")} 60%, ${color}ff 100%)`;
    pillar.style.opacity = String(intensity);
    pillar.style.animation = "none";
    void pillar.offsetWidth; // リフロー強制でアニメーションを確実に再始動
    pillar.style.animation = `rareDropPillar ${this.pillarMs}ms ease-out both`;
  }

  /** アイテム名テロップ表示 */
  _showTelop(itemName, color, rarity) {
    const telop = this._telop;
    if (!telop) return;
    telop.style.display = "block";
    telop.style.borderColor = color;
    telop.style.color = color;
    telop.style.textShadow = `0 0 12px ${color}88`;
    telop.innerHTML = `<span style="font-size:.65rem; letter-spacing:.3em; display:block; margin-bottom:6px; opacity:.75;">${rarity.toUpperCase()}</span>${escapeHtml(itemName)}`;
  }

  /** オーバーレイDOMを生成する (未生成時のみ) */
  _ensureDom() {
    if (this._root) return;
    const root = document.createElement("div");
    root.className = "rare-drop-overlay";
    root.style.cssText = `position:fixed; inset:0; z-index:${this.zIndex}; pointer-events:none; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:18px; opacity:0; transition:opacity .35s ease; background:rgba(4,6,12,.35);`;
    root.innerHTML = `
      <div class="rare-drop-reel" style="display:none; width:88px; height:88px; border:2px solid #fff; border-radius:10px; background:rgba(8,10,18,.9); align-items:center; justify-content:center; font-size:2.6rem;"></div>
      <div class="rare-drop-pillar" style="display:none; position:absolute; bottom:0; left:50%; transform:translateX(-50%); width:120px; height:70vh; opacity:0; pointer-events:none;"></div>
      <div class="rare-drop-telop" style="display:none; position:relative; padding:14px 34px; border:2px solid #fff; border-radius:8px; background:rgba(8,10,18,.92); font-family:var(--font-title, 'Cinzel', serif); font-size:1.25rem; font-weight:700; text-align:center;"></div>
      <style>@keyframes rareDropPillar { 0% { opacity:0; transform:translateX(-50%) scaleY(.2); } 30% { opacity:1; } 100% { opacity:0; transform:translateX(-50%) scaleY(1.1); } }</style>`;
    this._root = root;
    this._reel = root.querySelector(".rare-drop-reel");
    this._pillar = root.querySelector(".rare-drop-pillar");
    this._telop = root.querySelector(".rare-drop-telop");
    document.body.appendChild(root);
  }

  /** DOMを撤去する */
  _teardownDom() {
    if (this._root && this._root.parentNode) {
      this._root.parentNode.removeChild(this._root);
    }
    this._root = null;
    this._reel = null;
    this._pillar = null;
    this._telop = null;
  }

  /** 単純待機 */
  _wait(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

/** レアリティに応じたリール回転数の目安 (legendaryほど長く回る) */
function raritySpinCount(rarity, reelSpinMs) {
  const table = { uncommon: 1.0, rare: 1.3, epic: 1.6, legendary: 2.0 };
  return Math.round(reelSpinMs * (table[rarity] ?? 0.8));
}

/** HTMLエスケープ */
function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
