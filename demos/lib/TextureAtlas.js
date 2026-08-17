/**
 * テクスチャアトラスローダー
 * アトラス画像とメタデータからグリフテクスチャを提供するクラス
 */
export class TextureAtlas {
    /**
     * @param {PIXI.Texture} baseTexture - アトラス画像のベーステクスチャ
     * @param {Object} metadata - アトラスメタデータオブジェクト
     */
    constructor(baseTexture, metadata) {
        if (!(baseTexture instanceof PIXI.Texture)) {
            throw new Error('baseTexture must be a PIXI.Texture object');
        }
        
        this.baseTexture = baseTexture;
        this.metadata = metadata;
        this.textures = new Map();
        
        // メタデータから個々のテクスチャを作成
        if (metadata && metadata.glyphs) {
            for (const [char, frame] of Object.entries(metadata.glyphs)) {
                // フレームデータの形式: { x, y, width, height, ... }
                const texture = new PIXI.Texture(baseTexture, new PIXI.Rectangle(
                    frame.x,
                    frame.y,
                    frame.width,
                    frame.height
                ));
                this.textures.set(char, texture);
            }
        }
    }
    
    /**
     * 指定された文字のテクスチャを取得
     * @param {string} char - 文字
     * @returns {PIXI.Texture|null} テクスチャ（見つからない場合はnull）
     */
    getTexture(char) {
        return this.textures.get(char) || null;
    }
    
    /**
     * すべてのテクスチャを取得（イテレータ）
     * @returns {Iterator<[string, PIXI.Texture]>}
     */
    *[Symbol.iterator]() {
        yield* this.textures.entries();
    }
    
    /**
     * テクスチャアトラスを破棄し、リソースを解放
     */
    destroy() {
        if (this.baseTexture) {
            this.baseTexture.destroy();
        }
        this.textures.clear();
    }
    
    /**
     * テクスチャアトラスの情報を取得
     * @returns {Object} テクスチャアトラスの情報
     */
    getInfo() {
        return {
            baseTexture: this.baseTexture,
            glyphCount: this.textures.size,
            metadata: this.metadata
        };
    }
}

// グローバルスコープにもエクスポート（後方互換性のため）
window.TextureAtlas = TextureAtlas;