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
        this.fogDensity = 0.35;

        // Step 1 & 2: SDF & Volumetric Fog Shaders & Textures
        this.sdfTexture = PIXI.RenderTexture.create({ width, height, resolution: 1 });
        this.giTexture = PIXI.RenderTexture.create({ width, height, resolution: 1 });
        this.giSprite = new PIXI.Sprite(this.giTexture);
        this.giSprite.blendMode = PIXI.BLEND_MODES.SCREEN;

        this.initShaders();
    }

    /**
     * Step 1: シェーダー定義
     */
    initShaders() {
        const volumeLightFrag = `
            precision mediump float;
            varying vec2 vTextureCoord;
            uniform sampler2D uSampler;
            uniform sampler2D uSDFTexture;
            uniform vec2 uLightPos;
            uniform vec3 uLightColor;
            uniform float uLightIntensity;
            uniform float uFogDensity;
            uniform float uTime;

            void main(void) {
                vec4 baseColor = texture2D(uSampler, vTextureCoord);
                vec2 rayDir = normalize(uLightPos - vTextureCoord);
                float dist = length(uLightPos - vTextureCoord);

                float lightAccum = 0.0;
                const int STEPS = 12;
                for (int i = 0; i < STEPS; i++) {
                    float t = float(i) / float(STEPS);
                    vec2 samplePos = vTextureCoord + rayDir * dist * t;
                    float shadow = texture2D(uSDFTexture, samplePos).r;
                    if (shadow > 0.1) {
                        lightAccum += (1.0 - t) * (1.0 + 0.1 * sin(uTime * 5.0 + samplePos.x * 20.0));
                    }
                }
                lightAccum = clamp((lightAccum / float(STEPS)) * uFogDensity * uLightIntensity, 0.0, 1.0);
                vec3 fog = uLightColor * lightAccum;
                gl_FragColor = vec4(baseColor.rgb + fog, baseColor.a);
            }
        `;
        this.volumeLightFilter = new PIXI.Filter(null, volumeLightFrag, {
            uSDFTexture: this.sdfTexture,
            uLightPos: [0.5, 0.5],
            uLightColor: [1.0, 0.9, 0.6],
            uLightIntensity: 1.0,
            uFogDensity: this.fogDensity,
            uTime: 0.0
        });

        // Step 11 & 13: 2.5D ノーマルマップ陰影計算シェーダー
        const normalMapFrag = `
            precision mediump float;
            varying vec2 vTextureCoord;
            uniform sampler2D uSampler;
            uniform sampler2D uNormalSampler;
            uniform vec2 uLightPos;
            uniform vec3 uLightColor;
            uniform vec3 uAmbientColor;
            uniform vec2 uResolution;
            uniform float uLightRadius;
            uniform float uLightZ;

            void main(void) {
                vec4 diffuseColor = texture2D(uSampler, vTextureCoord);
                if (diffuseColor.a < 0.01) discard;

                vec3 normalRaw = texture2D(uNormalSampler, vTextureCoord).rgb;
                vec3 N = normalize(normalRaw * 2.0 - 1.0);

                vec2 pixelPos = vTextureCoord * uResolution;
                vec2 lightPixelPos = uLightPos * uResolution;

                vec3 lightDir = vec3(lightPixelPos - pixelPos, uLightZ);
                float dist = length(lightDir.xy);
                float attenuation = clamp(1.0 - dist / uLightRadius, 0.0, 1.0);
                attenuation = attenuation * attenuation;

                vec3 L = normalize(lightDir);
                float NdotL = max(dot(N, L), 0.0);

                vec3 diffuse = uLightColor * NdotL * attenuation;
                vec3 finalLight = uAmbientColor + diffuse;

                gl_FragColor = vec4(diffuseColor.rgb * finalLight, diffuseColor.a);
            }
        `;

        this.normalMapFilter = new PIXI.Filter(null, normalMapFrag, {
            uNormalSampler: PIXI.Texture.WHITE,
            uLightPos: [0.5, 0.5],
            uLightColor: [1.2, 1.1, 0.9],
            uAmbientColor: [0.35, 0.35, 0.45],
            uResolution: [this.width, this.height],
            uLightRadius: 300.0,
            uLightZ: 40.0
        });
    }

    /**
     * Step 11 & 15: ノーマルマップライティングの Uniform 更新
     * @param {number} px プレイヤー/光源Xピクセル
     * @param {number} py プレイヤー/光源Yピクセル
     * @param {PIXI.Texture} normalTexture
     */
    updateNormalLighting(px, py, normalTexture) {
        if (!this.normalMapFilter) return;
        this.normalMapFilter.uniforms.uLightPos = [px / this.width, py / this.height];
        if (normalTexture) {
            this.normalMapFilter.uniforms.uNormalSampler = normalTexture;
        }
    }

    /**
     * Step 3: Jump Flood / SDF 更新
     * @param {Array<Array<number>>} blockedGrid 障害物マップ (1=壁, 0=空間)
     */
    updateSDF(blockedGrid) {
        if (!blockedGrid || blockedGrid.length === 0) return;
        const h = blockedGrid.length;
        const w = blockedGrid[0].length;
        const tilePx = Math.max(1, Math.floor(this.width / w));
        const g = new PIXI.Graphics();

        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                if (blockedGrid[y][x] === 1) {
                    g.beginFill(0x000000); // 遮蔽物は黒
                } else {
                    g.beginFill(0xffffff); // 通過可能空間は白
                }
                g.drawRect(x * tilePx, y * tilePx, tilePx, tilePx);
                g.endFill();
            }
        }
        this.app.renderer.render(g, { renderTexture: this.sdfTexture, clear: true });
        g.destroy();
    }

    /**
     * Step 4 & 6: 2D GI & ボリューメトリックフォグ描画
     * @param {number} time
     */
    renderGI(time = 0) {
        if (!this.lightSources || this.lightSources.length === 0) return;
        const mainLight = this.lightSources[0];
        const nx = (mainLight.x * 24) / this.width;
        const ny = (mainLight.y * 24) / this.height;
        const col = mainLight.color || [255, 220, 140];
        const fog = (typeof window !== 'undefined' && window.fogDensity !== undefined) ? window.fogDensity : this.fogDensity;

        this.volumeLightFilter.uniforms.uLightPos = [nx, ny];
        this.volumeLightFilter.uniforms.uLightColor = [col[0] / 255, col[1] / 255, col[2] / 255];
        this.volumeLightFilter.uniforms.uLightIntensity = mainLight.intensity || 1.0;
        this.volumeLightFilter.uniforms.uFogDensity = fog;
        this.volumeLightFilter.uniforms.uTime = time;
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
