/**
 * 永続的デカール＆スプラッターシステム
 * 足跡、焦げ跡、血痕をレンダーテクスチャに直接焼き付けて半永久的に残す
 */

export class DecalSystem {
    /**
     * @param {PIXI.Application} app
     * @param {number} width
     * @param {number} height
     */
    constructor(app, width, height) {
        this.app = app;
        this.width = width;
        this.height = height;

        // Step 49 & 50: デカール焼き付け用レンダーテクスチャ
        this.renderTexture = PIXI.RenderTexture.create({
            width: this.width,
            height: this.height,
            resolution: 1
        });
        this.sprite = new PIXI.Sprite(this.renderTexture);
        this.sprite.blendMode = PIXI.BLEND_MODES.NORMAL;

        // 一時描画用スプライト・グラフィック
        this.tempGraphics = new PIXI.Graphics();
        this.stepCount = 0;
        this.lastStampTime = 0;

        // デカールテクスチャの生成
        this.textures = {
            footprint: this._createFootprintTexture(),
            scorch: this._createScorchTexture(),
            blood: this._createBloodSplatterTexture()
        };
    }

    /**
     * 足跡テクスチャの生成
     */
    _createFootprintTexture() {
        const g = new PIXI.Graphics();
        g.beginFill(0x0a0c10, 0.4);
        g.drawEllipse(4, 8, 3, 6); // 踵
        g.drawCircle(4, 2, 2);     // つま先
        g.endFill();
        return this.app.renderer.generateTexture(g);
    }

    /**
     * 焦げ跡テクスチャの生成
     */
    _createScorchTexture() {
        const g = new PIXI.Graphics();
        g.beginFill(0x110804, 0.85);
        g.drawCircle(12, 12, 10);
        g.beginFill(0x2a1005, 0.6);
        g.drawCircle(12, 12, 14);
        g.endFill();
        return this.app.renderer.generateTexture(g);
    }

    /**
     * 血痕テクスチャの生成
     */
    _createBloodSplatterTexture() {
        const g = new PIXI.Graphics();
        g.beginFill(0x5a0a10, 0.75);
        g.drawCircle(8, 8, 6);
        g.drawCircle(3, 4, 2.5);
        g.drawCircle(13, 12, 2.0);
        g.drawCircle(12, 3, 1.8);
        g.endFill();
        return this.app.renderer.generateTexture(g);
    }

    /**
     * Step 51: スタンプをレンダーテクスチャに焼き付け
     * @param {number} x
     * @param {number} y
     * @param {string} type 'footprint' | 'scorch' | 'blood'
     * @param {number} rotation
     * @param {number} scale
     * @param {number} alpha
     */
    stamp(x, y, type = 'footprint', rotation = 0, scale = 1.0, alpha = 0.6) {
        const tex = this.textures[type] || this.textures.footprint;
        const stampSprite = new PIXI.Sprite(tex);
        stampSprite.anchor.set(0.5);
        stampSprite.x = x;
        stampSprite.y = y;
        stampSprite.rotation = rotation;
        stampSprite.scale.set(scale);
        stampSprite.alpha = alpha;

        // RenderTextureに直接レンダリング（加算/通常）
        this.app.renderer.render(stampSprite, {
            renderTexture: this.renderTexture,
            clear: false
        });
        stampSprite.destroy();
    }

    /**
     * Step 54: 歩行足跡スタンプ
     * @param {number} x
     * @param {number} y
     * @param {number} dirX
     * @param {number} dirY
     */
    stampFootprint(x, y, dirX = 0, dirY = 1) {
        this.stepCount++;
        const isLeft = this.stepCount % 2 === 0;
        const angle = Math.atan2(dirY, dirX) - Math.PI / 2;
        const sideOffset = isLeft ? -4 : 4;
        
        const sx = x + Math.cos(angle + Math.PI / 2) * sideOffset;
        const sy = y + Math.sin(angle + Math.PI / 2) * sideOffset;
        
        this.stamp(sx, sy, 'footprint', angle, 0.8, 0.4);
    }

    /**
     * Step 55: 階層移動時のデカールクリア
     */
    clear() {
        const g = new PIXI.Graphics();
        this.app.renderer.render(g, {
            renderTexture: this.renderTexture,
            clear: true
        });
        g.destroy();
    }

    destroy() {
        if (this.renderTexture) this.renderTexture.destroy();
        if (this.sprite) this.sprite.destroy();
        if (this.tempGraphics) this.tempGraphics.destroy();
    }
}

// グローバルスコープにもエクスポート
window.DecalSystem = DecalSystem;
