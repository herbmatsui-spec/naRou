/**
 * ポストプロセスマネージャー
 * ブルーム、グレイン、VHSノイズなどのポストエフェクトを管理
 */
export class PostProcessManager {
    /**
     * @param {PIXI.Application} app - PixiJSアプリケーション
     */
    constructor(app) {
        this.app = app;

        // ポストプロセス用のレンダーテクスチャ
        this.renderTexture = PIXI.RenderTexture.create({
            width: app.screen.width,
            height: app.screen.height,
            resolution: app.renderer.resolution
        });

        // ポストプロセス用スプライト
        this.postProcessSprite = new PIXI.Sprite(this.renderTexture);
        this.postProcessSprite.width = app.screen.width;
        this.postProcessSprite.height = app.screen.height;

        // エフェクトコンテナ
        this.effectsContainer = new PIXI.Container();
        this.effectsContainer.addChild(this.postProcessSprite);

        // エフェクト状態
        this.bloomEnabled = true;
        this.bloomIntensity = 0.3;
        this.bloomThreshold = 0.6;
        this.grainEnabled = true;
        this.grainIntensity = 0.05;
        this.vignetteEnabled = true;
        this.vignetteIntensity = 0.4;
        this.chromaticEnabled = true;
        this.cinematicMode = true;

        // 衝撃波（Shockwaves）と熱歪み（Heat Haze）
        this.shockwaves = []; // [{x, y, radius, maxRadius, progress, duration}]
        this.heatHazeTime = 0;

        // ブルーム用のグラフィック
        this.bloomGraphics = new PIXI.Graphics();

        // グレイン用のノイズテクスチャ
        this.noiseTexture = this._createNoiseTexture();
        this.rippleTexture = this._createRippleTexture();

        // ビネット用のグラフィック
        this.vignetteGraphics = new PIXI.Graphics();

        // 深度別カラーグレーディング（フェーズ2-A）
        this.colorGradeEnabled = false;
        this.colorMatrix = null;
        if (PIXI.filters && PIXI.filters.ColorMatrixFilter) {
            this.colorMatrix = new PIXI.filters.ColorMatrixFilter();
            this.colorGradeEnabled = true;
        }

        // 初期化
        this._initEffects();
    }

    /**
     * Step 26: 波紋（リップル）テクスチャを作成
     * @returns {PIXI.Texture}
     */
    _createRippleTexture() {
        const size = 128;
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        const cx = size / 2;
        const cy = size / 2;
        const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, cx);
        grad.addColorStop(0, 'rgba(128, 128, 255, 0)');
        grad.addColorStop(0.6, 'rgba(255, 128, 128, 1)');
        grad.addColorStop(0.8, 'rgba(0, 255, 128, 1)');
        grad.addColorStop(1, 'rgba(128, 128, 255, 0)');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, size, size);
        return PIXI.Texture.from(canvas);
    }

    /**
     * ノイズテクスチャを作成
     * @returns {PIXI.Texture} ノイズテクスチャ
     */
    _createNoiseTexture() {
        const size = 128;
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');

        const imageData = ctx.createImageData(size, size);
        for (let i = 0; i < imageData.data.length; i += 4) {
            const value = Math.random() * 255;
            imageData.data[i] = value;     // R
            imageData.data[i + 1] = value; // G
            imageData.data[i + 2] = value; // B
            imageData.data[i + 3] = 255;   // A
        }

        ctx.putImageData(imageData, 0, 0);

        const texture = PIXI.Texture.from(canvas);
        texture.baseTexture.wrapMode = PIXI.WRAP_MODES.REPEAT;

        return texture;
    }

    /**
     * エフェクトを初期化
     */
    _initEffects() {
        // ブルームエフェクト
        this.bloomFilter = new PIXI.filters.BloomFilter({
            threshold: this.bloomThreshold,
            bloomScale: this.bloomIntensity,
            quality: 4
        });

        // グレインフィルタ
        this.grainFilter = new PIXI.filters.NoiseFilter({
            noise: this.grainIntensity,
            seed: Math.random() * 1000
        });

        // Step 25 & 29: ディスプレイスメント（衝撃波・歪み）フィルター
        this.displacementSprite = new PIXI.Sprite(this.rippleTexture);
        this.displacementSprite.anchor.set(0.5);
        this.displacementSprite.visible = false;
        this.displacementFilter = new PIXI.filters.DisplacementFilter(this.displacementSprite);
        this.displacementFilter.scale.x = 0;
        this.displacementFilter.scale.y = 0;

        // Step 42, 44, 46: 色収差 & シネマティックビネット
        const chromaticFrag = `
            precision mediump float;
            varying vec2 vTextureCoord;
            uniform sampler2D uSampler;
            uniform float uRedShift;
            uniform float uBlueShift;
            uniform float uVignette;
            uniform vec3 uVignetteColor;

            void main(void) {
                vec2 dir = vTextureCoord - vec2(0.5);
                float dist = length(dir);

                float r = texture2D(uSampler, vTextureCoord - dir * uRedShift).r;
                float g = texture2D(uSampler, vTextureCoord).g;
                float b = texture2D(uSampler, vTextureCoord + dir * uBlueShift).b;
                float a = texture2D(uSampler, vTextureCoord).a;

                float vig = smoothstep(0.8, 0.25, dist * (1.0 + uVignette * 0.8));
                vec3 color = mix(uVignetteColor, vec3(r, g, b), vig);

                gl_FragColor = vec4(color, a);
            }
        `;
        this.cinematicFilter = new PIXI.Filter(null, chromaticFrag, {
            uRedShift: 0.003,
            uBlueShift: 0.003,
            uVignette: this.vignetteIntensity,
            uVignetteColor: [0.0, 0.0, 0.0]
        });

        // フィルタを適用
        this._applyFilters();
    }

    /**
     * フィルタを適用
     */
    _applyFilters() {
        const filters = [];

        if (this.cinematicMode) {
            if (this.displacementFilter) filters.push(this.displacementFilter);
            if (this.bloomEnabled) filters.push(this.bloomFilter);
            if (this.grainEnabled) filters.push(this.grainFilter);
            if (this.chromaticEnabled && this.cinematicFilter) filters.push(this.cinematicFilter);
            if (this.colorGradeEnabled && this.colorMatrix) filters.push(this.colorMatrix);
        }

        this.effectsContainer.filters = filters.length > 0 ? filters : null;
    }

    /**
     * Step 27 & 28: 衝撃波を追加
     * @param {number} x 画面X
     * @param {number} y 画面Y
     * @param {number} maxRadius 最大半径ピクセル
     * @param {number} duration 持続時間（秒）
     */
    addShockwave(x, y, maxRadius = 160, duration = 0.6) {
        this.shockwaves.push({
            x, y,
            maxRadius,
            radius: 0,
            progress: 0,
            duration
        });
    }

    /**
     * Step 46: ダメージ時の色収差・赤色ビネット演出
     * @param {number} intensity
     */
    triggerDamageDistortion(intensity = 1.0) {
        if (!this.cinematicFilter) return;
        this.cinematicFilter.uniforms.uRedShift = 0.015 * intensity;
        this.cinematicFilter.uniforms.uBlueShift = 0.015 * intensity;
        this.cinematicFilter.uniforms.uVignette = 0.8 * intensity;
        this.cinematicFilter.uniforms.uVignetteColor = [0.4 * intensity, 0.0, 0.0];
    }

    /**
     * ブルーム強度を設定
     * @param {number} intensity - ブルーム強度 (0.0 - 1.0)
     */
    setBloomIntensity(intensity) {
        this.bloomIntensity = Math.max(0, Math.min(1, intensity));
        this.bloomFilter.bloomScale = this.bloomIntensity;
    }

    /**
     * ブルーム閾値を設定
     * @param {number} threshold - ブルーム閾値 (0.0 - 1.0)
     */
    setBloomThreshold(threshold) {
        this.bloomThreshold = Math.max(0, Math.min(1, threshold));
        this.bloomFilter.threshold = this.bloomThreshold;
    }

    /**
     * グレイン強度を設定
     * @param {number} intensity - グレイン強度 (0.0 - 1.0)
     */
    setGrainIntensity(intensity) {
        this.grainIntensity = Math.max(0, Math.min(1, intensity));
        this.grainFilter.noise = this.grainIntensity;
    }

    /**
     * ビネット強度を設定
     * @param {number} intensity - ビネット強度 (0.0 - 1.0)
     */
    setVignetteIntensity(intensity) {
        this.vignetteIntensity = Math.max(0, Math.min(1, intensity));
        this.vignetteFilter.strength = this.vignetteIntensity;
    }

    /**
     * ブルームを有効/無効化
     * @param {boolean} enabled - 有効/無効
     */
    setBloomEnabled(enabled) {
        this.bloomEnabled = enabled;
        this._applyFilters();
    }

    /**
     * グレインを有効/無効化
     * @param {boolean} enabled - 有効/無効
     */
    setGrainEnabled(enabled) {
        this.grainEnabled = enabled;
        this._applyFilters();
    }

    /**
     * ビネットを有効/無効化
     * @param {boolean} enabled - 有効/無効
     */
    setVignetteEnabled(enabled) {
        this.vignetteEnabled = enabled;
        this._applyFilters();
    }

    /**
     * 深度別カラーグレーディングを設定（フェーズ2-A）。
     * @param {number} depth - ダンジョン深度（0=地上、深いほど強く冷暗トーン）
     */
    setColorGrade(depth = 0) {
        if (!this.colorGradeEnabled || !this.colorMatrix) return;
        const t = Math.max(0, Math.min(1, depth / 50)); // 0..1 に正規化
        this.colorMatrix.reset();
        // 深層：青み・緑がかった冷色シフト + わずかな暗化
        this.colorMatrix.tint((120 - t * 40) << 16 | (150 - t * 30) << 8 | (200 + t * 30), false);
        this.colorMatrix.brightness(1 - t * 0.15, true);
    }

    setCinematicMode(enabled) {
        this.cinematicMode = !!enabled;
        this._applyFilters();
    }

    /**
     * ポストプロセスを更新
     * @param {number} deltaTime - 経過時間（秒）
     */
    update(deltaTime = 0.016) {
        // グレインのシードを定期的に更新（ノイズの変動）
        if (this.grainEnabled && Math.random() < 0.1) {
            this.grainFilter.seed = Math.random() * 1000;
        }

        // ダメージ色収差の減衰
        if (this.cinematicFilter) {
            const curRed = this.cinematicFilter.uniforms.uRedShift || 0.003;
            if (curRed > 0.003) {
                this.cinematicFilter.uniforms.uRedShift = Math.max(0.003, curRed - deltaTime * 0.03);
                this.cinematicFilter.uniforms.uBlueShift = this.cinematicFilter.uniforms.uRedShift;
                this.cinematicFilter.uniforms.uVignette = Math.max(this.vignetteIntensity, (this.cinematicFilter.uniforms.uVignette || 0.4) - deltaTime * 0.8);
                const curCol = this.cinematicFilter.uniforms.uVignetteColor || [0, 0, 0];
                this.cinematicFilter.uniforms.uVignetteColor = [
                    Math.max(0, curCol[0] - deltaTime * 0.8),
                    0, 0
                ];
            }
        }

        // 衝撃波（Shockwaves）の拡大・減衰
        if (this.shockwaves.length > 0 && this.displacementSprite && this.displacementFilter) {
            const sw = this.shockwaves[0];
            sw.progress += deltaTime / sw.duration;
            if (sw.progress >= 1.0) {
                this.shockwaves.shift();
                this.displacementSprite.visible = false;
                this.displacementFilter.scale.x = 0;
                this.displacementFilter.scale.y = 0;
            } else {
                const curRadius = sw.maxRadius * sw.progress;
                const power = (1.0 - sw.progress) * 24.0;
                this.displacementSprite.visible = true;
                this.displacementSprite.x = sw.x;
                this.displacementSprite.y = sw.y;
                this.displacementSprite.width = curRadius * 2;
                this.displacementSprite.height = curRadius * 2;
                this.displacementFilter.scale.x = power;
                this.displacementFilter.scale.y = power;
            }
        }
    }

    /**
     * ポストプロセス用のレンダーターゲットを取得
     * @returns {PIXI.RenderTexture} レンダーテクスチャ
     */
    getRenderTexture() {
        return this.renderTexture;
    }

    /**
     * ポストプロセスコンテナを取得
     * @returns {PIXI.Container} エフェクトコンテナ
     */
    getEffectsContainer() {
        return this.effectsContainer;
    }

    /**
     * ポストプロセスをリセット
     */
    reset() {
        this.bloomEnabled = true;
        this.bloomIntensity = 0.3;
        this.bloomThreshold = 0.6;
        this.grainEnabled = true;
        this.grainIntensity = 0.05;
        this.vignetteEnabled = true;
        this.vignetteIntensity = 0.4;

        this._applyFilters();
    }

    /**
     * リソースを破棄
     */
    destroy() {
        if (this.renderTexture) {
            this.renderTexture.destroy();
        }

        if (this.noiseTexture) {
            this.noiseTexture.destroy();
        }

        if (this.effectsContainer) {
            this.effectsContainer.destroy();
        }
    }
}

// グローバルスコープにもエクスポート（後方互換性のため）
window.PostProcessManager = PostProcessManager;
