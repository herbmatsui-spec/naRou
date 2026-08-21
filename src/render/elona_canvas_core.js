// elona_canvas_core.js - Minimal HTML5 Canvas 2D Tile Renderer
// Provides TileRenderer2D class to load a tileset atlas PNG + JSON metadata and draw tiles.

export class TileRenderer2D {
  /**
   * @param {HTMLCanvasElement} canvas - Target canvas element.
   * @param {Object} [options]
   * @param {number} [options.tileSize=16]   - Size of a tile in source atlas (pixels).
   * @param {number} [options.renderScale=2] - Scale factor for rendering (destination pixels per source pixel).
   */
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    // Disable smoothing for crisp pixel art.
    this.ctx.imageSmoothingEnabled = false;
    this.tileSize = options.tileSize || 16;
    this.renderScale = options.renderScale || 2;
    this.atlasImg = new Image();
    this.tileset = null; // JSON metadata loaded via fetch.
    this.loaded = false;
  }

  /**
   * Load atlas image and JSON metadata.
   * @param {string} atlasPath - Path to tileset PNG.
   * @param {string} jsonPath  - Path to tileset JSON (tileset_def format).
   * @returns {Promise<void>}
   */
  async load(atlasPath, jsonPath) {
    const imgPromise = new Promise((resolve, reject) => {
      this.atlasImg.onload = () => resolve();
      this.atlasImg.onerror = (e) => reject(e);
      this.atlasImg.src = atlasPath;
    });
    const jsonPromise = fetch(jsonPath).then(r => r.json());
    const [, json] = await Promise.all([imgPromise, jsonPromise]);
    this.tileset = json;
    this.loaded = true;
  }

  /** Get tile definition from ID.
   * @param {string} tileId
   * @returns {Object} Tile definition from JSON.
   */
  getTileDef(tileId) {
    if (!this.tileset) throw new Error('Tileset not loaded');
    const td = this.tileset.tiles[tileId];
    if (!td) throw new Error(`Tile ID not found: ${tileId}`);
    return td;
  }

  /** Draw a tile at grid coordinates.
   * @param {string} tileId - Tile ID from tileset_def.json (e.g., "TR_WALL_01").
   * @param {number} gridX - X position in tile units.
   * @param {number} gridY - Y position in tile units.
   * @param {Object} [opts] - Currently unused, placeholder for future variants.
   */
  drawTile(tileId, gridX, gridY, opts = {}) {
    if (!this.loaded) return; // Guard against premature calls.
    const td = this.getTileDef(tileId);
    const srcX = td.x;
    const srcY = td.y;
    const srcW = td.width;
    const srcH = td.height;
    const dstX = gridX * this.tileSize * this.renderScale;
    const dstY = gridY * this.tileSize * this.renderScale;
    const dstW = srcW * this.renderScale;
    const dstH = srcH * this.renderScale;
    this.ctx.drawImage(this.atlasImg, srcX, srcY, srcW, srcH, dstX, dstY, dstW, dstH);
  }

  /** Clear the entire canvas. */
  clear() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }
}
