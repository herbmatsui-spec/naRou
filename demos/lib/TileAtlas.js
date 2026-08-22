/**
 * TileAtlas - Unified tile atlas for naRou Web client.
 * Loads tileset_def.json and atlas metadata (16x16, 32x32, 64x64).
 * Provides UV lookup, sprite creation, autotiling, and animation support.
 */
export class TileAtlas {
    /**
     * @param {Object} baseTextures - Map of scale -> PIXI.BaseTexture
     * @param {Object} metadatas - Map of scale -> atlas metadata
     * @param {Object} defs - Tile definitions from tileset_def.json
     */
    constructor(baseTextures, metadatas, defs) {
        this.baseTextures = baseTextures;  // scale -> PIXI.BaseTexture
        this.metadatas = metadatas;        // scale -> metadata
        this.defs = defs;                  // tile_id -> TileDef
        this.defaultScale = "16";

        // Sprite caches
        this.staticSpriteCache = new Map();      // key -> PIXI.Sprite
        this.animatedSpriteCache = new Map();    // key -> PIXI.AnimatedSprite

        // 4-bit autotile mapping: bit0=up, bit1=right, bit2=down, bit3=left
        this.AUTOTILE_MAP = {
            0b0000: 0, 0b0001: 1, 0b0010: 2, 0b0100: 4, 0b1000: 8,
            0b0011: 3, 0b0110: 6, 0b1100: 12, 0b1001: 9, 0b0101: 5,
            0b1010: 10, 0b0111: 7, 0b1110: 14, 0b1101: 13, 0b1011: 11,
            0b1111: 15,
        };
    }

    /**
     * Load all tile data asynchronously.
     * @param {Array<string>} scales - Scales to load (default: ["16", "32", "64"])
     * @returns {Promise<Object>} { baseTextures, metadatas, defs }
     */
    static async loadAll(scales = ["16", "32", "64"]) {
        // 1. Load tileset_def.json
        const defRes = await fetch('assets/tiles/tileset_def.json');
        const defData = await defRes.json();
        const defs = defData.tiles || {};

        // 2. Load metadata for each scale in parallel
        const metaPromises = scales.map(s =>
            fetch(`assets/tiles/tileset_${s}x${s}.json`).then(r => r.json())
        );
        const metas = await Promise.all(metaPromises);
        const metadatas = Object.fromEntries(scales.map((s, i) => [s, metas[i]]));

        // 3. Load images for each scale in parallel
        const imgPromises = scales.map(s => {
            const img = new Image();
            img.src = `assets/tiles/tileset_${s}x${s}.png`;
            return new Promise((resolve, reject) => {
                img.onload = () => resolve({ scale: s, image: img });
                img.onerror = reject;
            });
        });
        const images = await Promise.all(imgPromises);

        // 4. Create PIXI.BaseTextures
        const baseTextures = {};
        for (const { scale, image } of images) {
            baseTextures[scale] = new PIXI.BaseTexture(image);
        }

        return { baseTextures, metadatas, defs };
    }

    /**
     * Get UV coordinates for a tile configuration.
     * @param {string} tileId - Tile ID (e.g., "TILE_WALL")
     * @param {number} variant - Variant index
     * @param {number} frame - Animation frame index
     * @param {number} direction - Direction index (0-3)
     * @param {string} state - Animation state ("idle", "walk", "attack")
     * @param {string} scale - Atlas scale ("16", "32", "64")
     * @returns {Object} { x, y, w, h, scale }
     */
    getTileUV(tileId, variant = 0, frame = 0, direction = 0, state = "idle", scale = "16") {
        const td = this.defs[tileId];
        if (!td) throw new Error(`TileDef not found: ${tileId}`);

        const meta = this.metadatas[scale];
        if (!meta) throw new Error(`Atlas metadata not loaded for scale: ${scale}`);

        const fileKey = td.file;
        if (!meta.tiles || !meta.tiles[fileKey]) {
            throw new Error(`Tile '${fileKey}' not found in ${scale} atlas metadata`);
        }

        const base = meta.tiles[fileKey];
        const bx = base.x, by = base.y;
        const bw = base.width, bh = base.height;
        const vw = td.variant_width || bw;
        const fw = td.frame_width || vw;

        const vx = variant * vw;
        const fx = frame * fw;
        const dy = direction * bh;

        return { x: bx + vx + fx, y: by + dy, w: fw, h: bh, scale };
    }

    /**
     * Get PIXI.Texture for a tile configuration.
     * @param {Object} uv - UV from getTileUV
     * @returns {PIXI.Texture}
     */
    _getTexture(uv) {
        const baseTex = this.baseTextures[uv.scale];
        return new PIXI.Texture(baseTex, new PIXI.Rectangle(uv.x, uv.y, uv.w, uv.h));
    }

    /**
     * Create a static sprite for a tile.
     * @param {string} tileId - Tile ID
     * @param {Object} options - { variant, frame, direction, state, scale, tint }
     * @returns {PIXI.Sprite}
     */
    createSprite(tileId, options = {}) {
        const {
            variant = 0, frame = 0, direction = 0, state = "idle",
            scale = this.defaultScale, tint = 0xFFFFFF
        } = options;

        const td = this.defs[tileId];
        if (!td) throw new Error(`TileDef not found: ${tileId}`);

        // Cache key
        const cacheKey = `${tileId}_${variant}_${frame}_${direction}_${state}_${scale}_${tint}`;
        if (this.staticSpriteCache.has(cacheKey)) {
            const sprite = this.staticSpriteCache.get(cacheKey);
            // Clone for independent use
            const clone = new PIXI.Sprite(sprite.texture);
            clone.tint = tint;
            clone.anchor.set(td.anchor_x || 0.5, td.anchor_y || 1.0);
            return clone;
        }

        const uv = this.getTileUV(tileId, variant, frame, direction, state, scale);
        const texture = this._getTexture(uv);
        const sprite = new PIXI.Sprite(texture);
        sprite.tint = tint;
        sprite.anchor.set(td.anchor_x || 0.5, td.anchor_y || 1.0);

        // Cache the prototype (don't add to scene)
        this.staticSpriteCache.set(cacheKey, sprite);
        return sprite;
    }

    /**
     * Create an animated sprite for a tile.
     * @param {string} tileId - Tile ID
     * @param {Object} options - { variant, direction, state, scale, fps, loop }
     * @returns {PIXI.AnimatedSprite}
     */
    createAnimatedSprite(tileId, options = {}) {
        const {
            variant = 0, direction = 0, state = "idle",
            scale = this.defaultScale, fps = 10, loop = true
        } = options;

        const td = this.defs[tileId];
        if (!td) throw new Error(`TileDef not found: ${tileId}`);

        // Cache key
        const cacheKey = `${tileId}_${variant}_${direction}_${state}_${scale}_${fps}_${loop}`;
        if (this.animatedSpriteCache.has(cacheKey)) {
            const anim = this.animatedSpriteCache.get(cacheKey);
            // Clone for independent playback
            const clone = new PIXI.AnimatedSprite(anim.textures.slice());
            clone.animationSpeed = fps / 60;
            clone.loop = loop;
            clone.anchor.set(td.anchor_x || 0.5, td.anchor_y || 1.0);
            clone.play();
            return clone;
        }

        const frames = [];
        for (let f = 0; f < (td.frames || 1); f++) {
            const uv = this.getTileUV(tileId, variant, f, direction, state, scale);
            frames.push(this._getTexture(uv));
        }

        const anim = new PIXI.AnimatedSprite(frames);
        anim.animationSpeed = fps / 60;
        anim.loop = loop;
        anim.anchor.set(td.anchor_x || 0.5, td.anchor_y || 1.0);
        anim.play();

        // Cache prototype
        this.animatedSpriteCache.set(cacheKey, anim);
        return anim;
    }

    /**
     * Get autotile variant from 4-bit neighbor mask.
     * @param {string} tileId - Tile ID
     * @param {number} neighborMask - 4-bit mask (up=1, right=2, down=4, left=8)
     * @returns {number} Variant index (0-15)
     */
    getAutotileVariant(tileId, neighborMask) {
        return this.AUTOTILE_MAP[neighborMask & 0xF] || 0;
    }

    /**
     * Calculate 4-bit neighbor mask for autotiling.
     * @param {Array<Array<string>>} tileMap - 2D array of tile IDs
     * @param {number} x - X coordinate
     * @param {number} y - Y coordinate
     * @param {string} targetTile - Tile ID to check neighbors for
     * @returns {number} 4-bit mask
     */
    calculateNeighborMask(tileMap, x, y, targetTile) {
        const h = tileMap.length;
        const w = h > 0 ? tileMap[0].length : 0;
        let mask = 0;
        if (y > 0 && tileMap[y-1][x] === targetTile) mask |= 1;      // up
        if (x < w - 1 && tileMap[y][x+1] === targetTile) mask |= 2;  // right
        if (y < h - 1 && tileMap[y+1][x] === targetTile) mask |= 4;  // down
        if (x > 0 && tileMap[y][x-1] === targetTile) mask |= 8;      // left
        return mask;
    }

    /**
     * Create a sprite with autotiling applied.
     * @param {string} tileId - Tile ID (must have autotile: true)
     * @param {Array<Array<string>>} tileMap - 2D array of tile IDs
     * @param {number} x - X coordinate in tileMap
     * @param {number} y - Y coordinate in tileMap
     * @param {Object} options - Additional sprite options
     * @returns {PIXI.Sprite}
     */
    createAutotileSprite(tileId, tileMap, x, y, options = {}) {
        const mask = this.calculateNeighborMask(tileMap, x, y, tileId);
        const variant = this.getAutotileVariant(tileId, mask);
        return this.createSprite(tileId, { ...options, variant });
    }

    /**
     * Clear all caches.
     */
    clearCaches() {
        for (const sprite of this.staticSpriteCache.values()) {
            sprite.texture.destroy(true);
        }
        for (const anim of this.animatedSpriteCache.values()) {
            for (const tex of anim.textures) {
                tex.destroy(true);
            }
            anim.destroy();
        }
        this.staticSpriteCache.clear();
        this.animatedSpriteCache.clear();
    }

    /**
     * Destroy the atlas and release resources.
     */
    destroy() {
        this.clearCaches();
        for (const tex of Object.values(this.baseTextures)) {
            tex.destroy();
        }
        this.baseTextures = {};
        this.metadatas = {};
        this.defs = {};
    }
}

// Global for backward compatibility
window.TileAtlas = TileAtlas;
