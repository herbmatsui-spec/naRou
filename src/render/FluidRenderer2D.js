// FluidRenderer2D.js - Simple metaball fluid effect using Canvas 2D
// Draws soft circles on an off‑screen canvas and composites them onto the main canvas.

export class FluidRenderer2D {
  /**
   * @param {HTMLCanvasElement} canvas - Target canvas.
   * @param {Object} [options]
   * @param {number} [options.particleRadius=20] - Base radius of fluid particles.
   */
  constructor(canvas, options = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.width = canvas.width;
    this.height = canvas.height;
    this.particleRadius = options.particleRadius || 20;
    this.particles = [];
    // off‑screen buffer for additive metaballs
    this.off = document.createElement('canvas');
    this.off.width = this.width;
    this.off.height = this.height;
    this.offCtx = this.off.getContext('2d');
    this.offCtx.imageSmoothingEnabled = false;
  }

  /** Add a fluid particle at (x, y). */
  addParticle(x, y, radius = this.particleRadius) {
    this.particles.push({ x, y, radius });
  }

  /** Update optional motion – simple wandering for demo purposes. */
  update(dt) {
    for (const p of this.particles) {
      // small random drift
      p.x += (Math.random() - 0.5) * 30 * dt;
      p.y += (Math.random() - 0.5) * 30 * dt;
    }
  }

  /** Render fluid onto the main canvas. */
  render() {
    const off = this.offCtx;
    // clear off‑screen
    off.clearRect(0, 0, this.width, this.height);
    // draw metaballs with additive blending
    off.globalCompositeOperation = 'lighter';
    off.fillStyle = 'white';
    for (const p of this.particles) {
      off.beginPath();
      off.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      off.fill();
    }
    // composite onto main canvas – simple approach: draw with globalAlpha for softness
    const ctx = this.ctx;
    ctx.save();
    // dark background (optional – keep existing background unchanged)
    // draw the off‑screen buffer with a soft multiply effect
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 0.7;
    ctx.drawImage(this.off, 0, 0);
    ctx.restore();
  }

  /** Clear all particles. */
  clear() {
    this.particles.length = 0;
  }
}
