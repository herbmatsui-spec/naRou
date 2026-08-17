/**
 * パーティクルシステム
 * ゲーム内の視覚効果（ほこり、火花、魔法エフェクトなど）を管理
 */
export class ParticleSystem {
    /**
     * @param {PIXI.Application} app - PixiJSアプリケーション
     * @param {PIXI.Container} container - パーティクルを描画するコンテナ
     */
    constructor(app, container) {
        this.app = app;
        this.container = container;
        this.particles = [];
        this.particlePools = new Map();
        
        // 設定
        this.maxParticles = 500;
        this.defaultLifetime = 2.0;
        this.defaultGravity = 0.1;
        
        // パーティクルタイプ定義
        this.particleTypes = {
            dust: {
                lifetime: 1.5,
                gravity: 0.05,
                colors: [0x8b9bb4, 0x6b7b94, 0x4b5b74],
                sizes: [1, 2, 3],
                speed: 0.5
            },
            spark: {
                lifetime: 0.8,
                gravity: 0.2,
                colors: [0xffaa00, 0xff6600, 0xff3300],
                sizes: [2, 3, 4],
                speed: 1.5
            },
            magic: {
                lifetime: 1.2,
                gravity: -0.05,
                colors: [0x9933ff, 0x66ccff, 0x33ff99],
                sizes: [2, 3, 4],
                speed: 0.8
            },
            heal: {
                lifetime: 1.5,
                gravity: -0.1,
                colors: [0x33ff33, 0x66ff66, 0x99ff99],
                sizes: [2, 3, 4],
                speed: 0.6
            },
            damage: {
                lifetime: 0.6,
                gravity: 0.0,
                colors: [0xff3333, 0xff6666, 0xff9999],
                sizes: [2, 3, 4],
                speed: 1.0
            }
        };
    }
    
    /**
     * パーティクルを発生させる
     * @param {Object} config - パーティクル設定
     * @param {string} config.type - パーティクルタイプ (dust, spark, magic, heal, damage)
     * @param {number} config.x - 開始X座標
     * @param {number} config.y - 開始Y座標
     * @param {number} config.count - 発生数 (default: 5)
     * @param {number} config.lifetime - 寿命 (秒)
     * @param {number} config.gravity - 重力
     * @param {Array} config.colors - 色配列
     * @param {Array} config.sizes - サイズ配列
     * @param {number} config.speed - 速度
     * @param {string} config.shape - 形状 (circle, square, triangle)
     */
    emit(config) {
        const typeConfig = this.particleTypes[config.type] || this.particleTypes.dust;
        const count = config.count || 5;
        
        for (let i = 0; i < count; i++) {
            // パーティクルプールから取得または新規作成
            let particle = this._getParticleFromPool(config.type);
            
            if (!particle) {
                particle = this._createParticle(config.type);
            }
            
            // パーティクルを初期化
            this._initParticle(particle, {
                ...typeConfig,
                ...config
            });
            
            // パーティクルをコンテナに追加
            this.container.addChild(particle.graphic);
            
            // アクティブパーティクルリストに追加
            this.particles.push(particle);
        }
        
        // パーティクル数制限を超えた場合は古いものを削除
        while (this.particles.length > this.maxParticles) {
            const oldParticle = this.particles.shift();
            this._destroyParticle(oldParticle);
        }
    }
    
    /**
     * パーティクルを作成
     * @param {string} type - パーティクルタイプ
     * @returns {Object} パーティクルオブジェクト
     */
    _createParticle(type) {
        const graphic = new PIXI.Graphics();
        
        return {
            type: type,
            graphic: graphic,
            x: 0,
            y: 0,
            vx: 0,
            vy: 0,
            life: 0,
            maxLife: 0,
            size: 0,
            color: 0xffffff,
            alpha: 1.0,
            rotation: 0,
            rotationSpeed: 0,
            gravity: 0.1,
            active: false
        };
    }
    
    /**
     * パーティクルをプールから取得
     * @param {string} type - パーティクルタイプ
     * @returns {Object|null} パーティクルオブジェクト
     */
    _getParticleFromPool(type) {
        const pool = this.particlePools.get(type);
        if (pool && pool.length > 0) {
            return pool.pop();
        }
        return null;
    }
    
    /**
     * パーティクルを初期化
     * @param {Object} particle - パーティクルオブジェクト
     * @param {Object} config - 設定
     */
    _initParticle(particle, config) {
        particle.x = config.x;
        particle.y = config.y;
        particle.vx = (Math.random() - 0.5) * config.speed * 2;
        particle.vy = (Math.random() - 0.5) * config.speed * 2;
        particle.life = config.lifetime || this.defaultLifetime;
        particle.maxLife = particle.life;
        particle.size = config.sizes ? config.sizes[Math.floor(Math.random() * config.sizes.length)] : 2;
        particle.color = config.colors ? config.colors[Math.floor(Math.random() * config.colors.length)] : 0xffffff;
        particle.alpha = 1.0;
        particle.rotation = Math.random() * Math.PI * 2;
        particle.rotationSpeed = (Math.random() - 0.5) * 0.2;
        particle.gravity = config.gravity !== undefined ? config.gravity : this.defaultGravity;
        particle.active = true;
        
        // グラフィックを更新
        particle.graphic.clear();
        particle.graphic.beginFill(particle.color, particle.alpha);
        
        // 形状に応じて描画
        const shape = config.shape || 'circle';
        if (shape === 'circle') {
            particle.graphic.drawCircle(0, 0, particle.size);
        } else if (shape === 'square') {
            particle.graphic.drawRect(-particle.size, -particle.size, particle.size * 2, particle.size * 2);
        } else if (shape === 'triangle') {
            particle.graphic.drawPolygon([
                0, -particle.size,
                -particle.size, particle.size,
                particle.size, particle.size
            ]);
        }
        
        particle.graphic.endFill();
        particle.graphic.x = particle.x;
        particle.graphic.y = particle.y;
        particle.graphic.rotation = particle.rotation;
        particle.graphic.alpha = particle.alpha;
        particle.graphic.visible = true;
    }
    
    /**
     * パーティクルを破棄
     * @param {Object} particle - パーティクルオブジェクト
     */
    _destroyParticle(particle) {
        if (particle.graphic) {
            if (particle.graphic.parent) {
                particle.graphic.parent.removeChild(particle.graphic);
            }
            particle.graphic.destroy();
        }
    }
    
    /**
     * パーティクルをプールに返却
     * @param {Object} particle - パーティクルオブジェクト
     */
    _returnParticleToPool(particle) {
        const pool = this.particlePools.get(particle.type) || [];
        pool.push(particle);
        this.particlePools.set(particle.type, pool);
    }
    
    /**
     * パーティクルシステムを更新
     * @param {number} deltaTime - 経過時間（秒）
     */
    update(deltaTime) {
        const toRemove = [];
        
        for (let i = this.particles.length - 1; i >= 0; i--) {
            const particle = this.particles[i];
            
            if (!particle.active) {
                toRemove.push(i);
                continue;
            }
            
            // 寿命を減らす
            particle.life -= deltaTime;
            
            if (particle.life <= 0) {
                // パーティクルを無効化
                particle.active = false;
                particle.graphic.visible = false;
                
                // プールに返却
                this._returnParticleToPool(particle);
                toRemove.push(i);
                continue;
            }
            
            // 物理演算
            particle.vy += particle.gravity * deltaTime;
            particle.x += particle.vx * deltaTime;
            particle.y += particle.vy * deltaTime;
            particle.rotation += particle.rotationSpeed * deltaTime;
            
            // ライフタイムに応じてアルファとサイズを変化
            const lifeRatio = particle.life / particle.maxLife;
            particle.alpha = lifeRatio;
            particle.size *= (1.0 - deltaTime * 0.5); // 徐々に小さく
            
            // グラフィックを更新
            particle.graphic.x = particle.x;
            particle.graphic.y = particle.y;
            particle.graphic.alpha = particle.alpha;
            particle.graphic.rotation = particle.rotation;
            particle.graphic.scale.set(particle.size / (particle.size || 1));
        }
        
        // 無効化されたパーティクルを削除
        for (const index of toRemove) {
            this.particles.splice(index, 1);
        }
    }
    
    /**
     * プリセットエフェクトを発生
     * @param {string} effect - エフェクト名
     * @param {number} x - X座標
     * @param {number} y - Y座標
     * @param {number} count - 数
     */
    emitEffect(effect, x, y, count = 5) {
        const effects = {
            'step': { type: 'dust', count: count, speed: 0.3, lifetime: 0.8 },
            'hit': { type: 'spark', count: count * 2, speed: 1.0, lifetime: 0.4 },
            'magic_cast': { type: 'magic', count: count * 3, speed: 0.5, lifetime: 1.0 },
            'heal': { type: 'heal', count: count * 2, speed: 0.4, lifetime: 1.2 },
            'damage': { type: 'damage', count: count, speed: 0.8, lifetime: 0.5 },
            'level_up': { type: 'magic', count: 20, speed: 1.0, lifetime: 2.0 }
        };
        
        const config = effects[effect] || effects['step'];
        this.emit({
            ...config,
            x: x,
            y: y
        });
    }
    
    /**
     * すべてのパーティクルをクリア
     */
    clear() {
        for (const particle of this.particles) {
            this._destroyParticle(particle);
        }
        
        this.particles = [];
        
        // プールもクリア
        for (const pool of this.particlePools.values()) {
            for (const particle of pool) {
                this._destroyParticle(particle);
            }
        }
        this.particlePools.clear();
    }
    
    /**
     * アクティブパーティクル数を取得
     * @returns {number} アクティブパーティクル数
     */
    getActiveCount() {
        return this.particles.filter(p => p.active).length;
    }
    
    /**
     * リソースを破棄
     */
    destroy() {
        this.clear();
        
        if (this.container) {
            this.container.removeChildren();
        }
    }
}