/**
 * 戦闘バックドロップ (T11 案5)
 * フロアテーマ別の遠景を描画する: グラデーション地平線 + 遠景シルエット + 夜空の星
 */

export class BattleBackdrop {
    // フロアテーマ定義 (dungeon_themes.yaml の SkillEater 深度帯に対応)
    static THEMES = {
        slums: { skyTop: 0x1a1420, skyMid: 0x2a1e28, horizon: 0x4a2e24, ground: 0x140f12, silhouette: 0x120e14, starRatio: 0.35 },
        sewers: { skyTop: 0x0e1622, skyMid: 0x14202e, horizon: 0x1e3448, ground: 0x0c1016, silhouette: 0x0a1018, starRatio: 0.5 },
        labs: { skyTop: 0x1c1016, skyMid: 0x30141a, horizon: 0x582018, ground: 0x140a0c, silhouette: 0x140a0c, starRatio: 0.25 },
        tower: { skyTop: 0x0c1024, skyMid: 0x141a38, horizon: 0x243058, ground: 0x0a0c1c, silhouette: 0x0a0c1c, starRatio: 0.9 },
    };

    // T24 案4: dungeon_themes.yaml のテーマ名 (theme_id) → バックドロップテーマ対応表
    // (WeatherSystem.THEME_WEATHER と同じテーマ名を受け取る)
    static THEME_BY_WORLD = {
        industrial_ruins: 'slums',   // 廃工場跡 (スラム)
        neon_sewers: 'sewers',       // ネオン下水道
        midas_labs: 'labs',          // ミダス研究棟
        babel_core: 'tower',         // バベル核心 (塔)
        goblin_cave: 'slums',        // ゴブリンの洞窟
        ancient_ruins: 'tower',      // 古代遺跡
    };

    /**
     * ダンジョン階層からテーマ名を決定する
     * @param {number} level - ダンジョン階層 (0=街/地上)
     * @returns {string} テーマ名
     */
    static selectTheme(level) {
        if (level >= 51) return 'tower';
        if (level >= 31) return 'labs';
        if (level >= 16) return 'sewers';
        return 'slums';
    }

    /**
     * @param {PIXI.Application} app
     * @param {PIXI.Container} container - 親コンテナ (backgroundLayer)
     * @param {number} width
     * @param {number} height
     */
    constructor(app, container, width, height) {
        this.app = app;
        this.width = width;
        this.height = height;
        this.themeName = '';
        this._time = 0;
        this._drawnLevel = -1;
        this._drawnWorldTheme = null;

        // 描画レイヤー (下から: 空 → シルエット → 星)
        this.sky = new PIXI.Graphics();
        this.silhouette = new PIXI.Graphics();
        this.stars = new PIXI.Container();
        container.addChild(this.sky);
        container.addChild(this.silhouette);
        container.addChild(this.stars);

        // 星スプライト (2px 円テクスチャを使い回す)
        this._starTexture = app.renderer.generateTexture(this._createStarGraphics());
        this.starSprites = [];
        this._buildStars(90);

        this.setTheme(0);
    }

    /**
     * 星テクスチャ用の円グラフィック
     */
    _createStarGraphics() {
        const g = new PIXI.Graphics();
        g.beginFill(0xffffff);
        g.drawCircle(1, 1, 1);
        g.endFill();
        return g;
    }

    /**
     * 星フィールドを構築する (位置は固定、テーマで表示数を制御)
     */
    _buildStars(count) {
        for (let i = 0; i < count; i++) {
            const sprite = new PIXI.Sprite(this._starTexture);
            sprite.x = Math.random() * this.width;
            // 地平線 (高さ75%) より上にのみ配置
            sprite.y = Math.random() * this.height * 0.72;
            sprite.alpha = 0;
            sprite.phase = Math.random() * Math.PI * 2;
            sprite.twinkleSpeed = 1.0 + Math.random() * 2.5;
            this.stars.addChild(sprite);
            this.starSprites.push(sprite);
        }
    }

    /**
     * フロアテーマを適用する (同一階層の再描画はスキップ)
     * @param {number} level - ダンジョン階層
     */
    setTheme(level) {
        const name = BattleBackdrop.selectTheme(level);
        if (name === this.themeName && level === this._drawnLevel) return;
        this.themeName = name;
        this._drawnLevel = level;
        this._redraw();
    }

    /**
     * ワールドテーマ名からバックドロップを適用する (T24 案4: setTheme の実データ版)
     * dungeon_themes.yaml のテーマ名をサーバーから受け取って直指定する。
     * 未知のテーマ名は従来どおり階層 0 (スラム) 扱いにフォールバックする。
     * @param {string} themeName - dungeon_themes.yaml のテーマ名 (例: 'industrial_ruins')
     */
    setThemeByName(themeName) {
        const name = BattleBackdrop.THEME_BY_WORLD[themeName] || BattleBackdrop.selectTheme(0);
        if (name === this.themeName && themeName === this._drawnWorldTheme) return;
        this.themeName = name;
        this._drawnWorldTheme = themeName;
        this._redraw();
    }

    /**
     * 空のグラデーション地平線を描画する (帯補間でレトロ感を出す)
     */
    _drawSky(theme) {
        const g = this.sky;
        g.clear();
        const horizonY = Math.floor(this.height * 0.75);
        const bands = 24;
        for (let i = 0; i < bands; i++) {
            const t = i / (bands - 1);
            const y0 = Math.floor((horizonY * i) / bands);
            const y1 = Math.floor((horizonY * (i + 1)) / bands);
            g.beginFill(this._lerpColor3(theme.skyTop, theme.skyMid, theme.horizon, t));
            g.drawRect(0, y0, this.width, Math.max(1, y1 - y0));
            g.endFill();
        }
        // 地平線より下 (地面: 暗色の単調グラデーション)
        for (let i = 0; i < 8; i++) {
            const y0 = horizonY + Math.floor(((this.height - horizonY) * i) / 8);
            const shade = this._shade(theme.ground, -i * 0.08);
            g.beginFill(shade);
            g.drawRect(0, y0, this.width, this.height - y0);
            g.endFill();
        }
    }

    /**
     * 遠景シルエットを描画する (テーマ別の形)
     */
    _drawSilhouette(theme) {
        const g = this.silhouette;
        g.clear();
        const horizonY = Math.floor(this.height * 0.75);
        g.beginFill(theme.silhouette);
        const seedRandom = this._makeRandom(this.themeName.length * 7919 + horizonY);

        if (this.themeName === 'tower') {
            // 塔: 尖ったスパイラー列
            let x = 0;
            while (x < this.width) {
                const w = 24 + seedRandom() * 40;
                const h = 60 + seedRandom() * 130;
                const tipX = x + w / 2;
                g.moveTo(x, horizonY);
                g.lineTo(tipX, horizonY - h);
                g.lineTo(x + w, horizonY);
                x += w * (0.6 + seedRandom() * 0.6);
            }
        } else if (this.themeName === 'labs') {
            // 研究棟: 煙突・タンク列
            let x = 0;
            while (x < this.width) {
                const w = 30 + seedRandom() * 50;
                const h = 40 + seedRandom() * 110;
                g.drawRect(x, horizonY - h, w, h);
                if (seedRandom() < 0.4) {
                    // 煙突
                    g.drawRect(x + w * 0.3, horizonY - h - 30, w * 0.18, 30);
                }
                x += w * (0.8 + seedRandom() * 0.5);
            }
        } else if (this.themeName === 'sewers') {
            // 下水道: アーチ列
            let x = 0;
            while (x < this.width) {
                const w = 44 + seedRandom() * 30;
                const h = 36 + seedRandom() * 40;
                g.moveTo(x, horizonY);
                g.arc(x + w / 2, horizonY, w / 2, Math.PI, 0);
                g.lineTo(x + w, horizonY);
                x += w * 0.85;
            }
        } else {
            // スラム: 不揃いな屋根と配管
            let x = 0;
            while (x < this.width) {
                const w = 26 + seedRandom() * 46;
                const h = 30 + seedRandom() * 90;
                if (seedRandom() < 0.5) {
                    // のこぎり屋根
                    g.moveTo(x, horizonY);
                    g.lineTo(x + w / 2, horizonY - h);
                    g.lineTo(x + w, horizonY);
                } else {
                    g.drawRect(x, horizonY - h, w, h);
                }
                x += w * (0.7 + seedRandom() * 0.5);
            }
        }
        g.endFill();
    }

    /**
     * テーマの星表示率を反映する
     */
    _applyStarVisibility(theme) {
        const visibleCount = Math.floor(this.starSprites.length * theme.starRatio);
        this.starSprites.forEach((s, i) => {
            s.visible = i < visibleCount;
            s.baseAlpha = 0.35 + (i % 5) * 0.13;
        });
    }

    /**
     * 全レイヤーを再描画する
     */
    _redraw() {
        const theme = BattleBackdrop.THEMES[this.themeName] || BattleBackdrop.THEMES.slums;
        this._drawSky(theme);
        this._drawSilhouette(theme);
        this._applyStarVisibility(theme);
    }

    /**
     * 毎フレーム更新 (星の瞬き + リサイズ追従)
     * @param {number} dt - 経過秒
     */
    update(dt) {
        this._time += dt;
        // リサイズ検出 (renderer.resize に自動追従)
        if (this.app.screen.width !== this.width || this.app.screen.height !== this.height) {
            this.width = this.app.screen.width;
            this.height = this.app.screen.height;
            this._redraw();
        }
        for (const s of this.starSprites) {
            if (!s.visible) continue;
            s.alpha = s.baseAlpha * (0.55 + 0.45 * Math.sin(this._time * s.twinkleSpeed + s.phase));
        }
    }

    /**
     * 3色を補間する (0 <= t <= 1, skyTop → skyMid → horizon)
     */
    _lerpColor3(top, mid, bottom, t) {
        const [a, b, tt] = t < 0.5 ? [top, mid, t * 2] : [mid, bottom, (t - 0.5) * 2];
        const r = Math.round(this._lerp((a >> 16) & 0xff, (b >> 16) & 0xff, tt));
        const g = Math.round(this._lerp((a >> 8) & 0xff, (b >> 8) & 0xff, tt));
        const bl = Math.round(this._lerp(a & 0xff, b & 0xff, tt));
        return (r << 16) | (g << 8) | bl;
    }

    _lerp(a, b, t) {
        return a + (b - a) * Math.min(1, Math.max(0, t));
    }

    /**
     * 明度を比率分加減する
     */
    _shade(color, ratio) {
        const r = Math.min(255, Math.max(0, Math.round(((color >> 16) & 0xff) * (1 + ratio))));
        const g = Math.min(255, Math.max(0, Math.round(((color >> 8) & 0xff) * (1 + ratio))));
        const b = Math.min(255, Math.max(0, Math.round((color & 0xff) * (1 + ratio))));
        return (r << 16) | (g << 8) | b;
    }

    /**
     * 文字列シードから簡易乱数生成器を作る (シルエット形状の再現用)
     */
    _makeRandom(seed) {
        let s = seed >>> 0;
        return function () {
            s = (s * 1664525 + 1013904223) >>> 0;
            return s / 4294967296;
        };
    }
}

// グローバル公開 (web_game_client.html の非モジュールスクリプトから参照する)
window.BattleBackdrop = BattleBackdrop;
