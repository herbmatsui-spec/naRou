/**
 * 動的ライティングシステム
 * 光源とライトマップを使用して、ゲームシーンに動的照明を適用
 */
export class LightingSystem {
    /**
     * @param {PIXI.Application} app - PixiJSアプリケーション
     * @param {PIXI.Container} targetLayer - ライティングを適用するレイヤー
     * @param {number} width - ライティングマップの幅
     * @param {number} height - ライティングマップの高さ
     */
    constructor(app, targetLayer, width, height) {
        this.app = app;
        this.targetLayer = targetLayer;
        this.width = width;
        this.height = height;
        
        // ライトレンダーテクスチャを作成
        this.renderTexture = PIXI.RenderTexture.create({
            width: width,
            height: height,
            resolution: 1
        });
        
        // ライトマップスプライト
        this.lightMapSprite = new PIXI.Sprite(this.renderTexture);
        this.lightMapSprite.width = width;
        this.lightMapSprite.height = height;
        
        // ライトソースコンテナ
        this.lightSourcesContainer = new PIXI.Container();
        
        // 光源データ
        this.lightSources = [];
        
        // パーティクルシステムへの参照
        this.particleSystem = null;
        
        // 設定
        this.ambientLight = 0.1; // 環境光
        this.lightBlendMode = PIXI.BLEND_MODES.MULTIPLY;
        
        // 初期化
        this._initLightingOverlay();
    }
    
    /**
     * ライティングオーバーレイを初期化
     */
    _initLightingOverlay() {
        // ダークオーバーレイ（暗闇用）
        this.darkOverlay = new PIXI.Graphics();
        this.darkOverlay.beginFill(0x000000, 1 - this.ambientLight);
        this.darkOverlay.drawRect(0, 0, this.width, this.height);
        this.darkOverlay.endFill();
        
        // ライトマップスプライトのブレンドモードを設定
        this.lightMapSprite.blendMode = PIXI.BLEND_MODES.ADD;
    }
    
    /**
     * 光源を追加
     * @param {Object} source - 光源データ {x, y, radius, color, intensity}
     */
    addLightSource(source) {
        const lightGraphic = new PIXI.Graphics();
        
        // 光源の色を解析
        const color = source.color || [255, 220, 140];
        const radius = source.radius || 7.5;
        const intensity = source.intensity || 1.0;
        
        // 放射グラデーションを描画（簡易版：円の重ね合わせ）
        const centerX = source.x * 24; // TILE_SIZE
        const centerY = source.y * 24;
        const steps = 20;
        
        for (let i = steps; i > 0; i--) {
            const stepRadius = (radius * 24 * i) / steps;
            const alpha = (intensity / steps) * 0.15;
            
            lightGraphic.beginFill(
                (color[0] << 16) | (color[1] << 8) | color[2],
                alpha
            );
            lightGraphic.drawCircle(centerX, centerY, stepRadius);
            lightGraphic.endFill();
        }
        
        // 光源をコンテナに追加
        this.lightSourcesContainer.addChild(lightGraphic);
        
        // 光源データを保存
        this.lightSources.push({
            graphic: lightGraphic,
            data: source
        });
        
        return lightGraphic;
    }
    
    /**
     * すべての光源をクリア
     */
    clearLightSources() {
        // グラフィックを破棄
        for (const source of this.lightSources) {
            if (source.graphic && source.graphic.parent) {
                source.graphic.parent.removeChild(source.graphic);
            }
            if (source.graphic && source.graphic.destroy) {
                source.graphic.destroy();
            }
        }
        
        this.lightSources = [];
        this.lightSourcesContainer.removeChildren();
    }
    
    /**
     * ライトマップを更新
     * @param {Array<Array<number>>} lightMapData - 2Dライトマップ配列
     */
    updateLightMap(lightMapData) {
        if (!lightMapData || lightMapData.length === 0) return;
        
        const height = lightMapData.length;
        const width = lightMapData[0] ? lightMapData[0].length : 0;
        
        if (width === 0 || height === 0) return;
        
        // ライトマップグラフィックを作成
        const lightMapGraphic = new PIXI.Graphics();
        
        for (let y = 0; y < height; y++) {
            for (let x = 0; x < width; x++) {
                const lightValue = lightMapData[y][x];
                
                if (lightValue > 0) {
                    // 可視領域：明るさに応じて色を適用
                    const brightness = Math.min(1, lightValue);
                    const grayValue = Math.floor(255 * brightness);
                    const color = (grayValue << 16) | (grayValue << 8) | grayValue;
                    
                    lightMapGraphic.beginFill(color, brightness);
                    lightMapGraphic.drawRect(x * 24, y * 24, 24, 24);
                    lightMapGraphic.endFill();
                }
                // lightValue <= 0 の場合は描画しない（暗闇）
            }
        }
        
        // レンダーテクスチャに描画
        this.app.renderer.render(lightMapGraphic, { renderTexture: this.renderTexture, clear: true });
        
        // グラフィックを破棄
        lightMapGraphic.destroy();
    }
    
    /**
     * 光源データを設定
     * @param {Array} lightSourcesData - 光源データ配列
     */
    setLightSources(lightSourcesData) {
        // 既存の光源をクリア
        this.clearLightSources();
        
        // 新しい光源を追加
        if (lightSourcesData && Array.isArray(lightSourcesData)) {
            for (const source of lightSourcesData) {
                this.addLightSource(source);
            }
        }
    }
    
    /**
     * パーティクルシステムを設定
     * @param {Object} particleSystem - パーティクルシステムインスタンス
     */
    setParticleSystem(particleSystem) {
        this.particleSystem = particleSystem;
    }
    
    /**
     * ライティングを適用
     * @param {PIXI.Container} sceneContainer - シーンコンテナ
     */
    applyLighting(sceneContainer) {
        // 現在の実装では、シーンに直接ライトオーバーレイを追加
        // 将来的には、シェーダーベースのライティングに置き換え可能
        
        // ライトマップスプライトをシーンに追加
        if (this.lightMapSprite.parent !== sceneContainer) {
            sceneContainer.addChild(this.lightMapSprite);
        }
        
        // 光源コンテナをシーンに追加
        if (this.lightSourcesContainer.parent !== sceneContainer) {
            sceneContainer.addChild(this.lightSourcesContainer);
        }
    }
    
    /**
     * ライティングを解除
     * @param {PIXI.Container} sceneContainer - シーンコンテナ
     */
    removeLighting(sceneContainer) {
        if (this.lightMapSprite.parent === sceneContainer) {
            sceneContainer.removeChild(this.lightMapSprite);
        }
        
        if (this.lightSourcesContainer.parent === sceneContainer) {
            sceneContainer.removeChild(this.lightSourcesContainer);
        }
    }
    
    /**
     * 環境光を設定
     * @param {number} intensity - 環境光の強度 (0.0 - 1.0)
     */
    setAmbientLight(intensity) {
        this.ambientLight = Math.max(0, Math.min(1, intensity));
        
        // ダークオーバーレイを更新
        this.darkOverlay.clear();
        this.darkOverlay.beginFill(0x000000, 1 - this.ambientLight);
        this.darkOverlay.drawRect(0, 0, this.width, this.height);
        this.darkOverlay.endFill();
    }
    
    /**
     * リソースを破棄
     */
    destroy() {
        this.clearLightSources();
        
        if (this.renderTexture) {
            this.renderTexture.destroy();
        }
        
        if (this.lightMapSprite) {
            this.lightMapSprite.destroy();
        }
        
        if (this.darkOverlay) {
            this.darkOverlay.destroy();
        }
    }
}

// グローバルスコープにもエクスポート（後方互換性のため）
window.LightingSystem = LightingSystem;