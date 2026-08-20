// canvas2d_renderer.ts - Step 54: WebGL2 が使えない環境向けの最小 Canvas2D レンダラ。
// タイルを色付き矩形、テキストを fillText で描画する。GPU シェーダー不要。

interface TileDraw {
    texture_id: number;
    x: number;
    y: number;
    width: number;
    height: number;
    color: [number, number, number, number];
}

interface TextDraw {
    text: string;
    x: number;
    y: number;
    font_size: number;
    color: [number, number, number, number];
}

function rgba(c: [number, number, number, number]): string {
    const a = c.length > 3 ? c[3] : 255;
    return `rgba(${c[0]},${c[1]},${c[2]},${a / 255})`;
}

export class Canvas2DRenderer {
    canvas: HTMLCanvasElement;
    ctx: CanvasRenderingContext2D;
    webgl2_supported = false;

    constructor(canvas: HTMLCanvasElement) {
        this.canvas = canvas;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
            throw new Error("Canvas2D not supported");
        }
        this.ctx = ctx;
    }

    draw_tile(d: TileDraw): void {
        const [r, g, b] = d.color;
        this.ctx.fillStyle = `rgb(${r},${g},${b})`;
        this.ctx.fillRect(d.x, d.y, d.width, d.height);
    }

    draw_text(d: TextDraw): void {
        this.ctx.fillStyle = rgba(d.color);
        this.ctx.font = `${d.font_size}px sans-serif`;
        this.ctx.fillText(d.text, d.x, d.y);
    }

    clear(color: [number, number, number] = [0, 0, 0]): void {
        this.ctx.fillStyle = `rgb(${color[0]},${color[1]},${color[2]})`;
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    }

    present(): void {
        // Canvas2D は即時描画のため何もしない（互換用）
    }
}

export function create_canvas2d_renderer(canvas: HTMLCanvasElement): Canvas2DRenderer {
    return new Canvas2DRenderer(canvas);
}
