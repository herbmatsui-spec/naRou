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
        
        // ブルーム用のグラフィック
        this.bloomGraphics = new PIXI.Graphics();
        
        // グレイン用のノイズテクスチャ
        this.noiseTexture = this._createNoiseTexture();
        
        // ビネット用のグラフィック
        this.vignetteGraphics = new PIXI.Graphics();
        
        // 初期化
        this._initEffects();
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
        
        // ビネットフィルタ
        this.vignetteFilter = new PIXI.filters.VignetteFilter({
            radius: 0.5,
            strength: this.vignetteIntensity
        });
        
        // フィルタを適用
        this._applyFilters();
    }
    
    /**
     * フィルタを適用
     */
    _applyFilters() {
        const filters = [];
        
        if (this.bloomEnabled) {
            filters.push(this.bloomFilter);
        }
        
        if (this.grainEnabled) {
            filters.push(this.grainFilter);
        }
        
        if (this.vignetteEnabled) {
            filters.push(this.vignetteFilter);
        }
        
        this.effectsContainer.filters = filters.length > 0 ? filters : null;
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
     * ポストプロセスを更新
     * @param {number} deltaTime - 経過時間（秒）
     */
    update(deltaTime) {
        // グレインのシードを定期的に更新（ノイズの変動）
        if (this.grainEnabled && Math.random() < 0.1) {
            this.grainFilter.seed = Math.random() * 1000;
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