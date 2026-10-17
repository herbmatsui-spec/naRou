/**
 * ワールドマップオーバーレイ (T11 案8)
 * Mキーで全画面表示する 9 世界のノード配置図。
 * 開閉時に pixiApp.stage の rotation/scale を操作した擬似モード7風の回転ズーム演出を行う。
 */

export class WorldMapOverlay {
    // 9世界のノード配置 (NAROU_9_WORLDS_DESIGN.md §4.1 の世界配置図に準拠、パネル内正規座標)
    static WORLDS = [
        { id: 'W1', name: '薬師錬金', x: 0.30, y: 0.86, start: true },
        { id: 'W2', name: '悪役令嬢', x: 0.42, y: 0.60 },
        { id: 'W3', name: 'ダンジョン', x: 0.78, y: 0.34 },
        { id: 'W4', name: 'スキル喰い', x: 0.62, y: 0.86 },
        { id: 'W5', name: '領地経営', x: 0.18, y: 0.60 },
        { id: 'W6', name: 'テイマー', x: 0.68, y: 0.60 },
        { id: 'W7', name: 'ループ', x: 0.22, y: 0.34 },
        { id: 'W8', name: 'NPC', x: 0.50, y: 0.34 },
        { id: 'W9', name: 'スマホ神', x: 0.50, y: 0.10 },
    ];

    // 世界間の接続線 (配置図の矢印に準拠)
    static CONNECTIONS = [
        ['W9', 'W7'], ['W9', 'W8'], ['W9', 'W3'],
        ['W7', 'W5'], ['W8', 'W2'], ['W3', 'W6'],
        ['W5', 'W1'], ['W2', 'W1'], ['W6', 'W4'], ['W1', 'W4'],
    ];

    /**
     * @param {PIXI.Application} app
     */
    constructor(app) {
        this.app = app;
        this._isOpen = false;
        this._animT = 0;       // オープン演出の進行 (0..1)
        this._time = 0;
        this._ticking = false;

        // 最前面に置くフルスクリーンコンテナ
        this.root = new PIXI.Container();
        this.root.visible = false;
        app.stage.addChild(this.root);

        this._buildPanel();
    }

    /**
     * パネル本体を構築する
     */
    _buildPanel() {
        // 画面暗転レイヤー
        this.dim = new PIXI.Graphics();
        this.root.addChild(this.dim);

        // 地図パネル (FF6風の深い青の海面)
        this.panel = new PIXI.Container();
        this.root.addChild(this.panel);

        this.panelBg = new PIXI.Graphics();
        this.panel.addChild(this.panelBg);

        // 接続線 → ノード → ラベルの順に重ねる
        this.lines = new PIXI.Graphics();
        this.panel.addChild(this.lines);

        this.nodes = new PIXI.Container();
        this.panel.addChild(this.nodes);

        for (const w of WorldMapOverlay.WORLDS) {
            const g = new PIXI.Graphics();
            g.beginFill(0x0a0c18);
            g.lineStyle(2, w.start ? 0xf0c860 : 0x8a9ac8);
            g.drawCircle(0, 0, w.start ? 9 : 7);
            g.endFill();
            g.x = w.x;
            g.y = w.y;
            g._circleMeta = { id: w.id, x: w.x, y: w.y };
            this.nodes.addChild(g);

            const label = new PIXI.Text(`${w.id}: ${w.name}`, {
                fontFamily: 'sans-serif',
                fontSize: 12,
                fill: w.start ? 0xf0c860 : 0xc8d0e8,
                align: 'center',
            });
            label.anchor.set(0.5, 0);
            label.x = w.x;
            label.y = w.y + 12;
            this.nodes.addChild(label);
        }

        this.titleText = new PIXI.Text('九世界転移譚 ― ワールドマップ', {
            fontFamily: 'sans-serif',
            fontSize: 18,
            fill: 0xf0e8d0,
            align: 'center',
        });
        this.panel.addChild(this.titleText);

        this.helpText = new PIXI.Text('M / Esc: 閉じる', {
            fontFamily: 'sans-serif',
            fontSize: 12,
            fill: 0x8a94b4,
            align: 'center',
        });
        this.panel.addChild(this.helpText);

        // スタート地点の脉動マーカー (W1)
        this.playerMarker = new PIXI.Graphics();
        this.playerMarker.beginFill(0xff5050);
        this.playerMarker.drawCircle(0, 0, 3);
        this.playerMarker.endFill();
        const start = WorldMapOverlay.WORLDS.find(w => w.start);
        this.playerMarker.x = start.x;
        this.playerMarker.y = start.y;
        this.panel.addChild(this.playerMarker);
    }

    /**
     * パネルを現在の画面サイズに再配置する
     */
    _layout() {
        const w = this.app.screen.width;
        const h = this.app.screen.height;

        this.dim.clear();
        this.dim.beginFill(0x000000, 0.72);
        this.dim.drawRect(0, 0, w, h);
        this.dim.endFill();

        const panelW = Math.min(640, w * 0.8);
        const panelH = Math.min(480, h * 0.8);
        const px = (w - panelW) / 2;
        const py = (h - panelH) / 2;

        this.panelBg.clear();
        this.panelBg.beginFill(0x183868, 0.94);
        this.panelBg.lineStyle(3, 0x8a7a54);
        this.panelBg.drawRect(px, py, panelW, panelH);
        this.panelBg.endFill();
        // 内側の縁取り
        this.panelBg.lineStyle(1, 0x4a6090);
        this.panelBg.drawRect(px + 5, py + 5, panelW - 10, panelH - 10);

        this.panel.x = 0;
        this.panel.y = 0;
        this.panel.pivot = { x: 0, y: 0 };

        // ノードはパネル矩形に内接させて配置する
        const inner = { x: px + 20, y: py + 46, w: panelW - 40, h: panelH - 92 };
        for (const child of this.nodes.children) {
            const world = WorldMapOverlay.WORLDS.find(
                wd => `${wd.id}: ${wd.name}` === child.text
            );
            if (world) {
                child.x = inner.x + world.x * inner.w;
                child.y = inner.y + world.y * inner.h - 5;
            } else if (child._circleMeta) {
                child.x = inner.x + child._circleMeta.x * inner.w;
                child.y = inner.y + child._circleMeta.y * inner.h;
            }
        }

        // 接続線をノード座標に追従させて描く
        this.lines.clear();
        this.lines.lineStyle(2, 0x5a78b0, 0.8);
        const nodePos = (id) => {
            const world = WorldMapOverlay.WORLDS.find(wd => wd.id === id);
            const circle = this.nodes.children.find(c => c._circleMeta && c._circleMeta.id === id);
            if (circle) return { x: circle.x, y: circle.y };
            return { x: inner.x + world.x * inner.w, y: inner.y + world.y * inner.h };
        };
        for (const [a, b] of WorldMapOverlay.CONNECTIONS) {
            const pa = nodePos(a);
            const pb = nodePos(b);
            this.lines.moveTo(pa.x, pa.y);
            this.lines.lineTo(pb.x, pb.y);
        }

        this.titleText.x = w / 2;
        this.titleText.y = py + 12;
        this.titleText.anchor.set(0.5, 0);
        this.helpText.x = w / 2;
        this.helpText.y = py + panelH - 26;
        this.helpText.anchor.set(0.5, 0);

        const start = WorldMapOverlay.WORLDS.find(wd => wd.start);
        this.playerMarker.x = inner.x + start.x * inner.w;
        this.playerMarker.y = inner.y + start.y * inner.h;
    }

    /**
     * 擬似モード7風の回転ズーム演出 (stage操作)
     * @param {number} t - 進行 0(開始)..1(収束)
     */
    _applyStageEffect(t) {
        const stage = this.app.stage;
        const w = this.app.screen.width;
        const h = this.app.screen.height;
        // オープン時: 回転 0.14rad→0、ズーム 1.22→1 の慣性的な収束
        stage.pivot.set(w / 2, h / 2);
        stage.rotation = (1 - t) * 0.14;
        const scale = 1 + (1 - t) * 0.22;
        stage.scale.set(scale);
        // 開いている間は微揺れでモード7の浮遊感を残す
        if (t >= 1) {
            stage.rotation = 0.008 * Math.sin(this._time * 1.4);
        }
    }

    _resetStage() {
        const stage = this.app.stage;
        stage.rotation = 0;
        stage.scale.set(1);
        stage.pivot.set(0, 0);
    }

    /**
     * オーバーレイを開く
     */
    open() {
        if (this._isOpen) return;
        this._isOpen = true;
        this._animT = 0;
        this._time = 0;
        this._layout();
        this.root.visible = true;
        // 最前面へ移動 (ポストプロセスコンテナより上にする)
        this.app.stage.addChild(this.root);
        if (!this._ticking) {
            this.app.ticker.add(this._tick, this);
            this._ticking = true;
        }
    }

    /**
     * オーバーレイを閉じる
     */
    close() {
        if (!this._isOpen) return;
        this._isOpen = false;
        this.root.visible = false;
        this._resetStage();
        if (this._ticking) {
            this.app.ticker.remove(this._tick, this);
            this._ticking = false;
        }
    }

    toggle() {
        this._isOpen ? this.close() : this.open();
    }

    isOpen() {
        return this._isOpen;
    }

    /**
     * 毎フレーム更新 (演出進行 + マーカー脉動 + リサイズ追従)
     */
    _tick(delta) {
        this._time += this.app.ticker.deltaMS / 1000;
        if (this._animT < 1) {
            // ease-out cubic で収束させる
            this._animT = Math.min(1, this._animT + (this.app.ticker.deltaMS / 1000) / 0.6);
            const t = 1 - Math.pow(1 - this._animT, 3);
            this._applyStageEffect(t);
        } else {
            this._applyStageEffect(1);
        }
        const pulse = 1 + 0.35 * Math.sin(this._time * 4);
        this.playerMarker.scale.set(pulse);
        // リサイズ検出
        if (this.root.visible && this._lastW !== this.app.screen.width) {
            this._lastW = this.app.screen.width;
            this._layout();
        }
    }
}

// グローバル公開 (web_game_client.html の非モジュールスクリプトから参照する)
window.WorldMapOverlay = WorldMapOverlay;
