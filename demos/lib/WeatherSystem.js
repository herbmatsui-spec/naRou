/**
 * 天候パーティクルシステム (T16 案6)
 * 雨・雪・霧・灰の 4 種の天候エフェクトを、effectLayer の直下に置いた
 * 専用レイヤー (weatherLayer) で描画する。
 * ParticleSystem.js と同じプーリングパターンを踏襲し、総パーティクル数は
 * maxParticles (400) 以下に制限する。
 * prefers-reduced-motion 環境では実効強度を 0 にして一切発生させない。
 *
 * フロアテーマとの連動 (dungeon_themes.yaml のテーマ名から判定):
 *   スラム系 (industrial_ruins) = 灰 / 下水道・深層 (neon_sewers, midas_labs) = 雨 /
 *   塔系 (babel_core, ancient_ruins) = 霧
 */
export class WeatherSystem {
    // dungeon_themes.yaml のテーマ名 (theme_id) → 天候種別の対応表
    static THEME_WEATHER = {
        industrial_ruins: 'ash',   // 廃工場跡 (スラム) = 灰
        neon_sewers: 'rain',       // ネオン下水道 = 雨
        midas_labs: 'rain',        // ミダス研究棟 (深層) = 雨
        babel_core: 'fog',         // バベル核心 (塔) = 霧
        ancient_ruins: 'fog',      // 古代遺跡 = 霧
        goblin_cave: null,         // ゴブリンの洞窟 = 天候なし
    };

    // dungeon_themes.yaml の深度帯 → テーマ名 (BattleBackdrop.selectTheme と同一区分)
    static selectTheme(level) {
        if (level >= 51) return 'babel_core';
        if (level >= 31) return 'midas_labs';
        if (level >= 16) return 'neon_sewers';
        return 'industrial_ruins';
    }

    // 天候タイプごとの発生設定 (速度は px/秒)
    static WEATHER_TYPES = {
        // 雨: 縦線短パーティクル多数落下 + 地面で跳ね (splash)
        rain: {
            baseCount: 240,
            spawnPerSecond: 720,
            colors: [0x9fc4e8, 0x7ea8d8, 0xc8def8],
            sizes: [1, 1, 2],
            vyMin: 420, vyMax: 600,
        },
        // 雪: 白円がゆらゆら落下
        snow: {
            baseCount: 160,
            spawnPerSecond: 180,
            colors: [0xffffff, 0xf0f6ff, 0xdce8f8],
            sizes: [1, 1.5, 2, 2.5],
            vyMin: 30, vyMax: 60,
        },
        // 霧: 半透明の大楕円がゆっくり横流し
        fog: {
            baseCount: 16,
            spawnPerSecond: 6,
            colors: [0xb8c8e0, 0xa0b0c8, 0xc8d4e8],
            sizes: [60, 80, 100],   // 楕円の半幅
            vyMin: -2, vyMax: 2,
        },
        // 灰: 灰白の小粒がゆらゆら落下
        ash: {
            baseCount: 140,
            spawnPerSecond: 140,
            colors: [0x9a9a96, 0xb8b8b0, 0x6e6e6a, 0x8a8a84],
            sizes: [0.8, 1, 1.2, 1.6],
            vyMin: 18, vyMax: 40,
        },
    };

    /**
     * @param {PIXI.Application} app - PixiJSアプリケーション
     * @param {PIXI.Container} container - 天候パーティクルを描画するコンテナ (weatherLayer)
     */
    constructor(app, container) {
        this.app = app;
        this.container = container;
        this.particles = [];
        this.particlePools = new Map();

        // 総パーティクル数の上限 (rain 本体 + splash + 雪 + 霧 + 灰 の合算)
        this.maxParticles = 400;

        // 現在の天候状態
        this.weatherType = null;   // 'rain' | 'snow' | 'fog' | 'ash' | null
        this.intensity = 1.0;      // 0.0 .. 1.0 (呼び出し側の指定強度)
        this.time = 0;

        // フロア切替の差分検知用 (setWeatherForLevel)
        this.currentLevel = null;

        // テーマ切替の差分検知用 (setWeatherTheme / T24 案4)
        this.currentTheme = null;

        // prefers-reduced-motion 環境では実効強度 0 (パーティクルを発生させない)
        const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
        this.reducedMotion = mediaQuery.matches;
        this._intensityScale = this.reducedMotion ? 0.0 : 1.0;
        if (this.reducedMotion) {
            console.info('WeatherSystem: prefers-reduced-motion を検出、天候エフェクトは無効化されました');
        }
    }

    /**
     * 天候を設定する
     * @param {string|null} type - 'rain' / 'snow' / 'fog' / 'ash' / null (解除)
     * @param {number} intensity - 強度 0.0 .. 1.0
     */
    setWeather(type, intensity = 1.0) {
        if (type !== null && !WeatherSystem.WEATHER_TYPES[type]) {
            console.warn(`WeatherSystem: 未知の天候タイプ '${type}' は無視されました`);
            return;
        }
        if (type === this.weatherType && intensity === this.intensity) return;

        this.weatherType = type;
        this.intensity = Math.max(0, Math.min(1, intensity));
        // 天候が切り替わったら既存パーティクルをクリアして作り直す
        this.clear();
    }

    /**
     * dungeon_level からフロアテーマを判定して天候を設定する (差分検知付き)
     * @param {number} level - ダンジョン階層 (0 = 街 / 地上)
     */
    setWeatherForLevel(level) {
        if (level === this.currentLevel) return;
        this.currentLevel = level;
        const theme = WeatherSystem.selectTheme(level);
        // T24 案4: テーマ名直指定 API へ委譲 (後方互換維持)
        this.setWeatherTheme(theme);
    }

    /**
     * dungeon_themes.yaml のテーマ名から天候を設定する (T24 案4、差分検知付き)
     * サーバー (web_server.py) が解決した world_theme を直指定する。
     * 未登録のテーマ名は天候なし (null) として扱う。
     * @param {string} themeName - テーマ名 (例: 'industrial_ruins')
     */
    setWeatherTheme(themeName) {
        if (themeName === this.currentTheme) return;
        this.currentTheme = themeName;
        const weather = WeatherSystem.THEME_WEATHER[themeName] || null;
        this.setWeather(weather, 1.0);
    }

    /**
     * パーティクルを作成 (ParticleSystem.js と同型の構造)
     * @param {string} type - パーティクルタイプ (rain / splash / snow / fog / ash)
     * @returns {Object} パーティクルオブジェクト
     */
    _createParticle(type) {
        return {
            type: type,
            graphic: new PIXI.Graphics(),
            x: 0,
            y: 0,
            vx: 0,
            vy: 0,
            life: 0,
            maxLife: 0,
            size: 0,
            color: 0xffffff,
            alpha: 1.0,
            phase: 0,          // ゆらぎ位相 (雪 / 灰 / 霧)
            swayFreq: 0,       // ゆらぎ周波数
            splashY: 0,        // 雨の跳ね発生ライン
            active: false,
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
     * パーティクルを初期化して画面に配置する
     * @param {Object} particle - パーティクルオブジェクト
     * @param {string} type - パーティクルタイプ
     */
    _initParticle(particle, type) {
        const cfg = WeatherSystem.WEATHER_TYPES[type];
        const width = this.app.screen.width;
        const height = this.app.screen.height;
        particle.type = type;
        particle.active = true;
        particle.size = cfg.sizes[Math.floor(Math.random() * cfg.sizes.length)];
        particle.color = cfg.colors[Math.floor(Math.random() * cfg.colors.length)];
        particle.phase = Math.random() * Math.PI * 2;
        particle.swayFreq = 1.0 + Math.random() * 2.0;

        if (type === 'rain') {
            // 画面上端外から斜めに落下 (風でわずかに左へ)
            particle.x = Math.random() * (width + 60) - 30;
            particle.y = Math.random() * -40;
            particle.vx = -30 - Math.random() * 20;
            particle.vy = cfg.vyMin + Math.random() * (cfg.vyMax - cfg.vyMin);
            particle.maxLife = (height + 60) / particle.vy + 0.5;
            particle.splashY = height - Math.random() * height * 0.25;
            particle.alpha = 0.5 + Math.random() * 0.3;
        } else if (type === 'splash') {
            // 雨粒の着地点から上向きに散る小粒
            particle.maxLife = 0.25 + Math.random() * 0.15;
            particle.vx = (Math.random() - 0.5) * 120;
            particle.vy = -(60 + Math.random() * 90);
            particle.alpha = 0.7;
        } else if (type === 'snow') {
            particle.x = Math.random() * width;
            particle.y = Math.random() * -20;
            particle.vx = 0; // update で sin 揺れを付与
            particle.vy = cfg.vyMin + Math.random() * (cfg.vyMax - cfg.vyMin);
            particle.maxLife = (height + 40) / particle.vy + 1.0;
            particle.alpha = 0.7 + Math.random() * 0.3;
        } else if (type === 'fog') {
            // 画面全域をゆっくり流れる大楕円 (横方向は wrap)
            particle.x = Math.random() * width;
            particle.y = Math.random() * height;
            particle.vx = 8 + Math.random() * 12;
            particle.vy = cfg.vyMin + Math.random() * (cfg.vyMax - cfg.vyMin);
            particle.maxLife = 30;
            particle.alpha = 0.04 + Math.random() * 0.06;
        } else if (type === 'ash') {
            particle.x = Math.random() * width;
            particle.y = Math.random() * -20;
            particle.vx = 0; // update で sin 揺れを付与
            particle.vy = cfg.vyMin + Math.random() * (cfg.vyMax - cfg.vyMin);
            particle.maxLife = (height + 40) / particle.vy + 1.0;
            particle.alpha = 0.5 + Math.random() * 0.3;
        }

        particle.life = particle.maxLife;
        this._drawParticle(particle);
        particle.graphic.x = particle.x;
        particle.graphic.y = particle.y;
        particle.graphic.alpha = particle.alpha;
        particle.graphic.visible = true;
        this.container.addChild(particle.graphic);
    }

    /**
     * パーティクルの形を描画する (天候タイプ別)
     * @param {Object} particle - パーティクルオブジェクト
     */
    _drawParticle(particle) {
        const g = particle.graphic;
        g.clear();
        // 天候は自然物のため加算ブレンドにせず NORMAL で描画する
        g.blendMode = PIXI.BLEND_MODES.NORMAL;

        if (particle.type === 'rain') {
            // 縦線の短パーティクル (落下方向に細長い)
            const len = 6 + particle.size * 3;
            g.beginFill(particle.color, particle.alpha);
            g.drawRect(-0.5, -len, 1, len);
            g.endFill();
        } else if (particle.type === 'splash') {
            g.beginFill(particle.color, particle.alpha);
            g.drawCircle(0, 0, particle.size || 1);
            g.endFill();
        } else if (particle.type === 'fog') {
            // 半透明の大楕円
            g.beginFill(particle.color, particle.alpha);
            g.drawEllipse(0, 0, particle.size, particle.size * 0.3);
            g.endFill();
        } else {
            // 雪・灰: 白 / 灰白の小円
            g.beginFill(particle.color, particle.alpha);
            g.drawCircle(0, 0, particle.size);
            g.endFill();
        }
    }

    /**
     * 現在の天候で目標パーティクル数に足りない分を発生させる
     * @param {number} dt - 経過時間 (秒)
     */
    _spawnParticles(dt) {
        if (!this.weatherType) return;
        const effectiveIntensity = this.intensity * this._intensityScale;
        if (effectiveIntensity <= 0) return;

        const cfg = WeatherSystem.WEATHER_TYPES[this.weatherType];
        const target = Math.floor(cfg.baseCount * effectiveIntensity);
        let activeCount = 0;
        for (const p of this.particles) {
            if (p.type === this.weatherType) activeCount++;
        }

        // 1 フレームの発生数を spawnPerSecond で制限し、上限も超えないようにする
        let budget = Math.ceil(cfg.spawnPerSecond * effectiveIntensity * dt);
        while (activeCount < target && budget > 0 && this.particles.length < this.maxParticles) {
            let particle = this._getParticleFromPool(this.weatherType);
            if (!particle) particle = this._createParticle(this.weatherType);
            this._initParticle(particle, this.weatherType);
            this.particles.push(particle);
            activeCount++;
            budget--;
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
     * 天候パーティクルシステムを更新
     * @param {number} deltaTime - 経過時間 (秒)
     */
    update(deltaTime) {
        this.time += deltaTime;
        this._spawnParticles(deltaTime);

        const width = this.app.screen.width;
        const height = this.app.screen.height;

        for (let i = this.particles.length - 1; i >= 0; i--) {
            const particle = this.particles[i];
            if (!particle.active) {
                this.particles.splice(i, 1);
                continue;
            }

            particle.life -= deltaTime;

            if (particle.type === 'rain') {
                particle.x += particle.vx * deltaTime;
                particle.y += particle.vy * deltaTime;
                // 地面ラインに到達したら跳ね (splash) を発生させて消す
                if (particle.y >= particle.splashY || particle.life <= 0) {
                    this._emitSplash(particle.x, particle.splashY);
                    particle.active = false;
                    particle.graphic.visible = false;
                    this._returnParticleToPool(particle);
                    this.particles.splice(i, 1);
                    continue;
                }
            } else if (particle.type === 'splash') {
                particle.vy += 400 * deltaTime; // 重力で減速・落下
                particle.x += particle.vx * deltaTime;
                particle.y += particle.vy * deltaTime;
                if (particle.life <= 0) {
                    particle.active = false;
                    particle.graphic.visible = false;
                    this._returnParticleToPool(particle);
                    this.particles.splice(i, 1);
                    continue;
                }
                particle.alpha = Math.max(0, particle.life / particle.maxLife) * 0.8;
            } else if (particle.type === 'fog') {
                // 大楕円を横流しし、画面外に出たら左端へ折り返す
                particle.x += particle.vx * deltaTime;
                particle.y += particle.vy * deltaTime;
                particle.x += Math.sin(this.time * particle.swayFreq + particle.phase) * 4 * deltaTime;
                if (particle.x - particle.size > width) {
                    particle.x = -particle.size;
                    particle.y = Math.random() * height;
                }
                if (particle.life <= 0) {
                    particle.life = particle.maxLife; // 霧は寿命で消さず更新し続ける
                }
            } else {
                // 雪・灰: sin 揺れでゆらゆら落下
                particle.y += particle.vy * deltaTime;
                particle.x += Math.sin(this.time * particle.swayFreq + particle.phase) * 12 * deltaTime;
                if (particle.y > height + 20 || particle.life <= 0) {
                    particle.active = false;
                    particle.graphic.visible = false;
                    this._returnParticleToPool(particle);
                    this.particles.splice(i, 1);
                    continue;
                }
            }

            particle.graphic.x = particle.x;
            particle.graphic.y = particle.y;
            particle.graphic.alpha = particle.alpha;
        }
    }

    /**
     * 雨粒の着地点に跳ね (splash) を 2 個発生させる
     * @param {number} x - 着地点 X
     * @param {number} y - 着地点 Y
     */
    _emitSplash(x, y) {
        if (this.particles.length >= this.maxParticles) return;
        for (let n = 0; n < 2; n++) {
            if (this.particles.length >= this.maxParticles) return;
            let particle = this._getParticleFromPool('splash');
            if (!particle) particle = this._createParticle('splash');
            this._initParticle(particle, 'splash');
            particle.x = x + (Math.random() - 0.5) * 3;
            particle.y = y;
            particle.graphic.x = particle.x;
            particle.graphic.y = particle.y;
            this.particles.push(particle);
        }
    }

    /**
     * すべてのパーティクルをクリア (プールへ返却)
     */
    clear() {
        for (const particle of this.particles) {
            particle.active = false;
            particle.graphic.visible = false;
            this._returnParticleToPool(particle);
        }
        this.particles = [];
    }

    /**
     * アクティブパーティクル数を取得
     * @returns {number} アクティブパーティクル数
     */
    getActiveCount() {
        return this.particles.length;
    }

    /**
     * リソースを破棄
     */
    destroy() {
        this.clear();
        // プールも破棄する
        for (const pool of this.particlePools.values()) {
            for (const particle of pool) {
                this._destroyParticle(particle);
            }
        }
        this.particlePools.clear();

        if (this.container) {
            this.container.removeChildren();
        }
    }
}

// グローバルスコープにもエクスポート (ParticleSystem.js と同じ後方互換パターン)
window.WeatherSystem = WeatherSystem;
