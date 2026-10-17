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
        this.scheduledEmits = []; // 遅延発生予定のパーティクル (emitSpellのレイヤー順再生用)

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
            blendMode: PIXI.BLEND_MODES.ADD,
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
        // スポーン位置: spawnRadius指定時は中心(x, y)周囲の円環上に配置 (emitSpellの集束/散布用)
        particle.x = config.x;
        particle.y = config.y;
        if (config.spawnRadius) {
            const angle = Math.random() * Math.PI * 2;
            particle.x += Math.cos(angle) * config.spawnRadius;
            particle.y += Math.sin(angle) * config.spawnRadius;
        }

        // 速度: radialMode指定時は中心基準の方向速度、未指定時は従来のランダム速度
        if (config.radialMode) {
            const dx = particle.x - config.x;
            const dy = particle.y - config.y;
            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
            const ux = dx / dist;
            const uy = dy / dist;
            // 0.75〜1.25倍の揺らぎで機械的な並びにならないよう調整
            const v = config.speed * (0.75 + Math.random() * 0.5);
            if (config.radialMode === 'converge') {
                // 中心へ収束
                particle.vx = -ux * v;
                particle.vy = -uy * v;
            } else if (config.radialMode === 'swirl') {
                // 接線方向＋わずかな内向速度で渦を描く (テレポート用)
                particle.vx = (-uy - ux * 0.4) * v;
                particle.vy = (ux - uy * 0.4) * v;
            } else if (config.radialMode === 'rise') {
                // 上昇 (回復エフェクト用)
                particle.vx = (Math.random() - 0.5) * v * 0.3;
                particle.vy = -v;
            } else {
                // 中心から放射
                particle.vx = ux * v;
                particle.vy = uy * v;
            }
        } else {
            particle.vx = (Math.random() - 0.5) * config.speed * 2;
            particle.vy = (Math.random() - 0.5) * config.speed * 2;
        }
        particle.life = config.lifetime || this.defaultLifetime;
        particle.maxLife = particle.life;
        particle.size = config.sizes ? config.sizes[Math.floor(Math.random() * config.sizes.length)] : 2;
        particle.color = config.colors ? config.colors[Math.floor(Math.random() * config.colors.length)] : 0xffffff;
        particle.alpha = 1.0;
        particle.rotation = Math.random() * Math.PI * 2;
        particle.rotationSpeed = (Math.random() - 0.5) * 0.2;
        particle.gravity = config.gravity !== undefined ? config.gravity : this.defaultGravity;
        particle.active = true;

        // 光条・稲妻形状は進行方向へ回転を固定する
        if (config.shape === 'streak' || config.shape === 'zigzag') {
            particle.rotation = Math.atan2(particle.vy, particle.vx);
            particle.rotationSpeed = 0;
        }

        // グラフィックを更新
        particle.graphic.clear();
        // 加算ブレンド (案4: フレア/アルテマ級の発光表現)
        particle.graphic.blendMode = particle.blendMode || PIXI.BLEND_MODES.ADD;

        // 形状に応じて描画
        const shape = config.shape || 'circle';
        if (shape === 'zigzag') {
            // ジグザグ: 雷光の稲妻ライン (ストローク描画)
            particle.graphic.lineStyle(Math.max(1, particle.size * 0.5), particle.color, particle.alpha);
            const seg = particle.size * 1.6;
            const jit = particle.size * 1.1;
            particle.graphic.moveTo(-seg * 1.5, 0);
            particle.graphic.lineTo(-seg * 0.5, -jit);
            particle.graphic.lineTo(seg * 0.5, jit);
            particle.graphic.lineTo(seg * 1.5, 0);
        } else {
            particle.graphic.beginFill(particle.color, particle.alpha);
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
            } else if (shape === 'streak') {
                // 長尺線状: 進行方向に沿った光条
                const len = particle.size * 6;
                const wid = Math.max(1, particle.size * 0.6);
                particle.graphic.drawRect(-len / 2, -wid / 2, len, wid);
            }
            particle.graphic.endFill();
        }

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
        // 遅延発生予定のエフェクトを処理 (emitSpellのレイヤー順再生)
        if (this.scheduledEmits.length > 0) {
            const ready = [];
            for (const scheduled of this.scheduledEmits) {
                scheduled.delay -= deltaTime;
                if (scheduled.delay <= 0) {
                    ready.push(scheduled.config);
                }
            }
            if (ready.length > 0) {
                this.scheduledEmits = this.scheduledEmits.filter(s => s.delay > 0);
                for (const config of ready) {
                    this.emit(config);
                }
            }
        }

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
     * 遅延発生を予約 (emitSpellのレイヤー順再生用)
     * @param {Object} config - emit()に渡すパーティクル設定
     * @param {number} delay - 遅延時間 (秒)
     */
    _scheduleEmit(config, delay) {
        this.scheduledEmits.push({ config, delay });
    }

    /**
     * FF6フレア/アルテマ級の多層魔法エフェクトを発生 (バッチ2案2)
     * 4レイヤー構成: L1集束円 → L2粒子散布 → L3光条 → L4残像リング
     * 速度の単位はpx/s (update()に秒単位のdeltaTimeを渡すWebクライアント向け)
     * @param {string} name - 呪文属性 (fire, ice, lightning, heal, teleport)
     * @param {number} x - 中心X座標 (px)
     * @param {number} y - 中心Y座標 (px)
     */
    emitSpell(name, x, y) {
        // 属性別のカラーパレット・速度・レイヤー挙動
        const spells = {
            fire: {
                colors: [0xff6600, 0xff3300, 0xffaa00],
                ringColors: [0xffcc66, 0xff8833],
                gravity: 30.0,
                scatterMode: 'radial', scatterSpeed: 160.0,
                streakShape: 'streak', streakSpeed: 340.0
            },
            ice: {
                colors: [0x66ccff, 0x3399ff, 0xaaeeff],
                ringColors: [0xccf5ff, 0x66ccff],
                gravity: -20.0,
                scatterMode: 'radial', scatterSpeed: 140.0,
                streakShape: 'streak', streakSpeed: 300.0
            },
            lightning: {
                colors: [0xffffcc, 0xffff66, 0xffffff],
                ringColors: [0xffffff, 0xffff99],
                gravity: 0.0,
                scatterMode: 'radial', scatterSpeed: 200.0,
                streakShape: 'zigzag', streakSpeed: 420.0
            },
            heal: {
                colors: [0x33ff33, 0x66ff66, 0x99ff99],
                ringColors: [0x99ff99, 0x33ff66],
                gravity: -60.0,
                scatterMode: 'rise', scatterSpeed: 90.0,
                streakShape: 'streak', streakSpeed: 200.0
            },
            teleport: {
                colors: [0xffffff, 0xcc99ff, 0x9966ff],
                ringColors: [0xe6ccff, 0xcc99ff],
                gravity: 0.0,
                scatterMode: 'swirl', scatterSpeed: 130.0,
                streakShape: 'streak', streakSpeed: 260.0
            },
            magic: {
                colors: [0x9933ff, 0x66ccff, 0x33ff99],
                ringColors: [0xcc99ff, 0x66ccff],
                gravity: -10.0,
                scatterMode: 'radial', scatterSpeed: 150.0,
                streakShape: 'streak', streakSpeed: 320.0
            }
        };
        const spell = spells[name] || spells.magic;

        // L1: 集束円 — 周囲から中心へ収束する円形パーティクル (0.3秒)
        this.emit({
            type: 'magic', x: x, y: y,
            count: 24, lifetime: 0.3, gravity: 0.0,
            colors: spell.colors, sizes: [2, 3],
            speed: 120.0, spawnRadius: 36.0, radialMode: 'converge'
        });

        // L2: 粒子散布 — 収束後に中心から散布 (加算ブレンド)
        this._scheduleEmit({
            type: 'magic', x: x, y: y,
            count: 32, lifetime: 0.8, gravity: spell.gravity,
            colors: spell.colors, sizes: [2, 3, 4],
            speed: spell.scatterSpeed, spawnRadius: 4.0, radialMode: spell.scatterMode
        }, 0.3);

        // L3: 光条 — 長尺線状パーティクルを放射
        this._scheduleEmit({
            type: 'magic', x: x, y: y,
            count: 12, lifetime: 0.45, gravity: 0.0,
            colors: spell.colors, sizes: [2, 3],
            speed: spell.streakSpeed, spawnRadius: 6.0,
            radialMode: spell.scatterMode === 'rise' ? 'rise' : 'radial',
            shape: spell.streakShape
        }, 0.32);

        // L4: 残像リング — 半径拡大するリングを3連発
        for (let i = 0; i < 3; i++) {
            this._scheduleEmit({
                type: 'magic', x: x, y: y,
                count: 24, lifetime: 0.55, gravity: 0.0,
                colors: spell.ringColors, sizes: [2, 3],
                speed: 90.0 + i * 45.0, spawnRadius: 4.0, radialMode: 'radial'
            }, 0.4 + i * 0.15);
        }
    }

    /**
     * すべてのパーティクルをクリア
     */
    clear() {
        for (const particle of this.particles) {
            this._destroyParticle(particle);
        }

        this.particles = [];
        this.scheduledEmits = [];

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

// グローバルスコープにもエクスポート（後方互換性のため）
window.ParticleSystem = ParticleSystem;
