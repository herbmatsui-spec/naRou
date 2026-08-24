// DecalSystem2D.js - Simple persistent decal manager for Canvas 2D
// Stores decal objects (e.g., blood splatter, footprints) and draws them each frame.

export class DecalSystem2D {
  /**
   * @param {HTMLCanvasElement} canvas - Target canvas.
   * @param {Object} [options]
   */
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.width = canvas.width;
    this.height = canvas.height;
    this.decals = [];
  }

  /** Stamp a decal at (x, y) of a given type.
   * Supported types: 'blood', 'footprint'. Extend as needed.
   */
  stamp(x, y, type = 'blood') {
    this.decals.push({ x, y, type });
  }

  /** Render all decals. */
  render() {
    const ctx = this.ctx;
    for (const d of this.decals) {
      ctx.save();
      ctx.translate(d.x, d.y);
      if (d.type === 'blood') {
        ctx.fillStyle = 'rgba(150,0,0,0.6)';
        ctx.beginPath();
        ctx.arc(0, 0, 8, 0, Math.PI * 2);
        ctx.fill();
      } else if (d.type === 'footprint') {
        ctx.fillStyle = 'rgba(30,30,30,0.5)';
        ctx.beginPath();
        ctx.arc(0, 0, 6, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }
  }

  /** Clear all decals. */
  clear() {
    this.decals.length = 0;
  }
}
