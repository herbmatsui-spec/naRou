/**
 * 動的ライティングシステム (Phase 2-A 改修版)
 *
 * - サーバーが送る light_map（強度 0..1, -1=未探索）と light_color（"r,g,b"）を
 *   乗算ブレンド用のライトマップテクスチャに変換し、シーンを暗くする。
 * - 光源リスト（松明など）は加算ブレンドのハローとして描画し、ノイズで揺らぎ
 *   （flicker）を持たせる。
 * - 敵の視界コーンを加算ブレンドで描画する。
 */
export class LightingSystem {
    /**
     * @param {PIXI.Application} app
     * @param {PIXI.Container} targetLayer
     * @param {number} width  ライティングマップのピクセル幅
     * @param {number} height ライティングマップのピクセル高さ
     */
    constructor(app, targetLayer, width, height) {
        this.app = app;
        this.targetLayer = targetLayer;
        this.width = width;
        this.height = height;

        // 乗算ブレンド用のライトマップ（暗闇を表現）
        this.tintTexture = PIXI.RenderTexture.create({ width, height, resolution: 1 });
        this.tintSprite = new PIXI.Sprite(this.tintTexture);
        this.tintSprite.width = width;
        this.tintSprite.height = height;
        this.tintSprite.blendMode = PIXI.BLEND_MODES.MULTIPLY;

        // 光源ハロー（加算ブレンド）
        this.glowContainer = new PIXI.Container();

        // 敵視界コーン（加算ブレンド）
        this.enemyConesContainer = new PIXI.Container();

        // 光源データ（フリッカー用に seed を保持）
        this.lightSources = [];
        this.enemyCones = [];

        this.ambientLight = 0.08;
    }

    /**
     * ライトマップを更新（乗算ブレンド用のカラーテクスチャを構築）。
     * @param {Array<Array<number>>} lightMapData 強度グリッド
     * @param {Array<Array<string>>} lightColorData "r,g,b" グリッド（省略可）
     */
    updateLightMap(lightMapData, lightColorData) {
        if (!lightMapData || lightMapData.length === 0) return;
        const h = lightMapData.length;
        const w = lightMapData[0] ? lightMapData[0].length : 0;
        if (w === 0 || h === 0) return;

        const tilePx = Math.max(1, Math.floor(this.width / w));
        const g = new PIXI.Graphics();

        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                const intensity = lightMapData[y][x];
                let r = 0, gr = 0, b = 0;
                const colStr = lightColorData && lightColorData[y] ? lightColorData[y][x] : null;
                if (colStr) {
                    const parts = colStr.split(",");
                    r = parseInt(parts[0], 10) || 0;
                    gr = parseInt(parts[1], 10) || 0;
                    b = parseInt(parts[2], 10) || 0;
                }
                if (intensity < 0) {
                    // 未探索：黒（タイル自体は描画されない）
                    r = 0; gr = 0; b = 0;
                } else if (intensity <= 0.001) {
                    // 探索済みだが視界外：サーバーが送る暗い色をそのまま使用
                    // （乗算ブレンドでわずかに見える Fog of War）
                } else {
                    // 可視：色 × 強度 で乗算用ティントを合成
                    r = Math.min(255, Math.round(r * intensity));
                    gr = Math.min(255, Math.round(gr * intensity));
                    b = Math.min(255, Math.round(b * intensity));
                }
                g.beginFill((r << 16) | (gr << 8) | b, 1);
                g.drawRect(x * tilePx, y * tilePx, tilePx, tilePx);
                g.endFill();
            }
        }

        this.app.renderer.render(g, { renderTexture: this.tintTexture, clear: true });
        g.destroy();
    }

    /**
     * 光源（松明など）を設定し、フリッカー付きのハローを描画。
     * @param {Array} sources [{x, y, radius, intensity, color:[r,g,b]}]
     * @param {number} time アニメーション時刻（秒）
     */
    setLightSources(sources, time = 0) {
        this.glowContainer.removeChildren();
        this.lightSources = Array.isArray(sources) ? sources : [];

        for (const src of this.lightSources) {
            const color = src.color || [255, 220, 140];
            const radiusTiles = src.radius || 7.5;
            const intensity = src.intensity == null ? 1.0 : src.intensity;
            const seed = (src.x * 13.13 + src.y * 7.7);
            // ノイズベースの揺らぎ（flicker）
            const flicker = 1 + 0.12 * Math.sin(time * 9 + seed) + 0.05 * Math.sin(time * 23 + seed * 2);
            const px = src.x * 24;
            const py = src.y * 24;
            const radiusPx = radiusTiles * 24 * flicker;
            const steps = 18;
            const glow = new PIXI.Graphics();
            for (let i = steps; i > 0; i--) {
                const t = i / steps;
                const rr = radiusPx * t;
                const alpha = (intensity / steps) * 0.18 * (1 - t * 0.6);
                glow.beginFill((color[0] << 16) | (color[1] << 8) | color[2], alpha);
                glow.drawCircle(px, py, rr);
                glow.endFill();
            }
            this.glowContainer.addChild(glow);
        }
    }

    /**
     * 敵の視界コーンを設定・描画。
     * @param {Array} cones [{x, y, angle, half_angle, range, color:"r,g,b"}]
     * @param {number} time アニメーション時刻（秒）
     */
    setEnemyCones(cones, time = 0) {
        this.enemyConesContainer.removeChildren();
        this.enemyCones = Array.isArray(cones) ? cones : [];

        for (const c of this.enemyCones) {
            const parts = (c.color || "255,60,60").split(",");
            const r = parseInt(parts[0], 10) || 255;
            const g = parseInt(parts[1], 10) || 60;
            const b = parseInt(parts[2], 10) || 60;
            const ox = c.x * 24 + 12;
            const oy = c.y * 24 + 12;
            const half = c.half_angle || 0.6;
            const range = (c.range || 6) * 24;
            const a0 = c.angle - half;
            const a1 = c.angle + half;
            const pulse = 0.12 + 0.06 * (0.5 + 0.5 * Math.sin(time * 4 + ox));
            const cone = new PIXI.Graphics();
            cone.beginFill((r << 16) | (g << 8) | b, pulse);
            cone.moveTo(ox, oy);
            const seg = 10;
            for (let i = 0; i <= seg; i++) {
                const a = a0 + (a1 - a0) * (i / seg);
                cone.lineTo(ox + Math.cos(a) * range, oy + Math.sin(a) * range);
            }
            cone.lineTo(ox, oy);
            cone.endFill();
            this.enemyConesContainer.addChild(cone);
        }
    }

    /**
     * ライティングをシーンに適用。
     * @param {PIXI.Container} sceneContainer
     */
    applyLighting(sceneContainer) {
        if (this.tintSprite.parent !== sceneContainer) {
            sceneContainer.addChild(this.tintSprite);
        }
        if (this.glowContainer.parent !== sceneContainer) {
            sceneContainer.addChild(this.glowContainer);
        }
        if (this.enemyConesContainer.parent !== sceneContainer) {
            sceneContainer.addChild(this.enemyConesContainer);
        }
    }

    removeLighting(sceneContainer) {
        for (const c of [this.tintSprite, this.glowContainer, this.enemyConesContainer]) {
            if (c.parent === sceneContainer) sceneContainer.removeChild(c);
        }
    }

    setAmbientLight(intensity) {
        this.ambientLight = Math.max(0, Math.min(1, intensity));
    }

    destroy() {
        if (this.tintTexture) this.tintTexture.destroy();
        if (this.tintSprite) this.tintSprite.destroy();
        if (this.glowContainer) this.glowContainer.destroy({ children: true });
        if (this.enemyConesContainer) this.enemyConesContainer.destroy({ children: true });
    }
}

// グローバルスコープにもエクスポート（後方互換性のため）
window.LightingSystem = LightingSystem;
