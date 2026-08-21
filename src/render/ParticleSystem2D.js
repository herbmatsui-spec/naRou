// ParticleSystem2D.js - Canvas 2D particle system (Pixi‑free version)
// Provides a lightweight particle manager that works with a 2D Canvas context.

export class ParticleSystem2D {
  /**
   * @param {CanvasRenderingContext2D} ctx - Canvas 2D context.
   * @param {Object} [options]
   * @param {number} [options.maxParticles=500]
   * @param {number} [options.defaultLifetime=2.0]
   * @param {number} [options.defaultGravity=0.1]
   */
  constructor(ctx, options = {}) {
    this.ctx = ctx;
    this.maxParticles = options.maxParticles || 500;
    this.defaultLifetime = options.defaultLifetime || 2.0;
    this.defaultGravity = options.defaultGravity || 0.1;
    this.particles = [];
    this.particlePools = new Map(); // type -> array of pooled particles

    // Pre‑defined particle type config (mirrors demo/lib/ParticleSystem.js)
    this.particleTypes = {
      dust: { lifetime: 1.5, gravity: 0.05, colors: [0x8b9bb4, 0x6b7b94, 0x4b5b74], sizes: [1, 2, 3], speed: 0.5, shape: 'circle' },
      spark: { lifetime: 0.8, gravity: 0.2, colors: [0xffaa00, 0xff6600, 0xff3300], sizes: [2, 3, 4], speed: 1.5, shape: 'square' },
      magic: { lifetime: 1.2, gravity: -0.05, colors: [0x9933ff, 0x66ccff, 0x33ff99], sizes: [2, 3, 4], speed: 0.8, shape: 'circle' },
      heal: { lifetime: 1.5, gravity: -0.1, colors: [0x33ff33, 0x66ff66, 0x99ff99], sizes: [2, 3, 4], speed: 0.6, shape: 'circle' },
      damage: { lifetime: 0.6, gravity: 0.0, colors: [0xff3333, 0xff6666, 0xff9999], sizes: [2, 3, 4], speed: 1.0, shape: 'circle' }
    };
  }

  /** Emit particles with a configuration object.
   * @param {Object} cfg
   *   {string} type   - particle type key (dust, spark, ...)
   *   {number} x     - origin X (canvas pixels)
   *   {number} y     - origin Y (canvas pixels)
   *   {number} [count=5]
   *   {number} [lifetime]
   *   {number} [gravity]
   *   {Array<number>} [colors]
   *   {Array<number>} [sizes]
   *   {number} [speed]
   *   {string} [shape]
   */
  emit(cfg) {
    const typeCfg = this.particleTypes[cfg.type] || this.particleTypes.dust;
    const count = cfg.count ?? 5;
    for (let i = 0; i < count; i++) {
      let particle = this._getFromPool(cfg.type);
      if (!particle) particle = this._createParticle(cfg.type);
      this._initParticle(particle, { ...typeCfg, ...cfg });
      this.particles.push(particle);
    }
    // Trim if over limit
    while (this.particles.length > this.maxParticles) {
      const old = this.particles.shift();
      this._returnToPool(old);
    }
  }

  _createParticle(type) {
    return {
      type,
      x: 0,
      y: 0,
      vx: 0,
      vy: 0,
      life: 0,
      maxLife: 0,
      size: 0,
      color: 0xffffff,
      alpha: 1,
      rotation: 0,
      rotationSpeed: 0,
      gravity: this.defaultGravity,
      shape: 'circle',
      active: false
    };
  }

  _getFromPool(type) {
    const pool = this.particlePools.get(type);
    if (pool && pool.length) return pool.pop();
    return null;
  }

  _returnToPool(particle) {
    const pool = this.particlePools.get(particle.type) || [];
    pool.push(particle);
    this.particlePools.set(particle.type, pool);
  }

  _initParticle(particle, cfg) {
    particle.x = cfg.x;
    particle.y = cfg.y;
    const speed = cfg.speed ?? 0.5;
    particle.vx = (Math.random() - 0.5) * speed * 2;
    particle.vy = (Math.random() - 0.5) * speed * 2;
    particle.life = cfg.lifetime ?? this.defaultLifetime;
    particle.maxLife = particle.life;
    particle.size = cfg.sizes ? cfg.sizes[Math.floor(Math.random() * cfg.sizes.length)] : 2;
    particle.color = cfg.colors ? cfg.colors[Math.floor(Math.random() * cfg.colors.length)] : 0xffffff;
    particle.alpha = 1;
    particle.rotation = Math.random() * Math.PI * 2;
    particle.rotationSpeed = (Math.random() - 0.5) * 0.2;
    particle.gravity = cfg.gravity !== undefined ? cfg.gravity : this.defaultGravity;
    particle.shape = cfg.shape || 'circle';
    particle.active = true;
  }

  /** Update all particles. dt in seconds. */
  update(dt) {
    const toRemove = [];
    for (let i = this.particles.length - 1; i >= 0; i--) {
      const p = this.particles[i];
      if (!p.active) { toRemove.push(i); continue; }
      p.life -= dt;
      if (p.life <= 0) {
        p.active = false;
        this._returnToPool(p);
        toRemove.push(i);
        continue;
      }
      // physics
      p.vy += p.gravity * dt;
      p.x += p.vx * dt;
      p.y += p.vy * dt;
      p.rotation += p.rotationSpeed * dt;
      // fade / shrink
      const lifeRatio = p.life / p.maxLife;
      p.alpha = lifeRatio;
      p.size *= (1.0 - dt * 0.5);
    }
    // remove dead particles from main array
    for (const idx of toRemove) {
      this.particles.splice(idx, 1);
    }
  }

  /** Render particles onto the stored canvas context. */
  render() {
    const ctx = this.ctx;
    for (const p of this.particles) {
      if (!p.active) continue;
      ctx.save();
      ctx.globalAlpha = p.alpha;
      // color as #RRGGBB
      const hex = p.color.toString(16).padStart(6, '0');
      ctx.fillStyle = `#${hex}`;
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rotation);
      const s = p.size;
      if (p.shape === 'circle') {
        ctx.beginPath();
        ctx.arc(0, 0, s, 0, Math.PI * 2);
        ctx.fill();
      } else if (p.shape === 'square') {
        ctx.fillRect(-s, -s, s * 2, s * 2);
      } else if (p.shape === 'triangle') {
        ctx.beginPath();
        ctx.moveTo(0, -s);
        ctx.lineTo(-s, s);
        ctx.lineTo(s, s);
        ctx.closePath();
        ctx.fill();
      }
      ctx.restore();
    }
  }

  /** Clear all particles (both active and pooled). */
  clear() {
    this.particles.length = 0;
    this.particlePools.clear();
  }

  /** Destroy – currently just clears resources. */
  destroy() {
    this.clear();
  }
}
