// LightingSystem2D.js - Simple ambient lighting using radial gradients on Canvas 2D
// Each light is a colored radial gradient blended additively over a dark overlay.

export class LightingSystem2D {
  /**
   * @param {HTMLCanvasElement} canvas - Target canvas.
   * @param {Object} [options]
   * @param {string} [options.overlayColor='rgba(0,0,0,0.6)'] - Base darkness.
   */
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.width = canvas.width;
    this.height = canvas.height;
    this.overlayColor = options.overlayColor || 'rgba(0,0,0,0.6)';
    this.lights = [];
  }

  /** Add a light source.
   * @param {number} x - X coordinate (canvas space).
   * @param {number} y - Y coordinate.
   * @param {number} radius - Light radius.
   * @param {string} color - CSS color (e.g., '#ffcc66' or 'rgba(255,200,100,0.8)').
   */
  addLight(x, y, radius = 80, color = '#ffffff') {
    this.lights.push({ x, y, radius, color });
  }

  /** Remove all lights. */
  clearLights() {
    this.lights.length = 0;
  }

  /** Render the lighting overlay. */
  render() {
    const ctx = this.ctx;
    ctx.save();
    // Dark overlay
    ctx.fillStyle = this.overlayColor;
    ctx.fillRect(0, 0, this.width, this.height);
    // Additive blend for lights
    ctx.globalCompositeOperation = 'lighter';
    for (const l of this.lights) {
      const grad = ctx.createRadialGradient(l.x, l.y, 0, l.x, l.y, l.radius);
      grad.addColorStop(0, l.color);
      grad.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(l.x, l.y, l.radius, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }
}
