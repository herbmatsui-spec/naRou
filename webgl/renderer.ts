interface TileDrawCall {
    texture_id: number;
    x: number;
    y: number;
    width: number;
    height: number;
    u0: number;
    v0: number;
    u1: number;
    v1: number;
    color: [number, number, number, number];
    rotation: number;
    scale: number;
}

interface TextDrawCall {
    text: string;
    x: number;
    y: number;
    font_size: number;
    color: [number, number, number, number];
    alignment: string;
    max_width?: number;
}

interface Viewport {
    x: number;
    y: number;
    width: number;
    height: number;
}

interface GlyphMetrics {
    advance: number;
    bearing_x: number;
    bearing_y: number;
    width: number;
    height: number;
    u0: number;
    v0: number;
    u1: number;
    v1: number;
}

class MSDFAtlas {
    texture: WebGLTexture | null = null;
    glyphs: Map<string, GlyphMetrics> = new Map();
    font_size: number = 0;
    chars: string = "";
    atlas_size: number = 4096;
    padding: number = 2;

    async generate_atlas(gl: WebGL2RenderingContext, font_path: string, chars: string, size: number, padding: number = 2): Promise<void> {
        this.font_size = size;
        this.chars = chars;
        this.padding = padding;

        const response = await fetch(font_path);
        const font_buffer = await response.arrayBuffer();
        
        const font = new FontFace('MSDF', font_buffer);
        await font.load();
        document.fonts.add(font);

        const glyphs_data: Array<[string, ImageData | null, number, number, number, number, number]> = [];
        let max_width = 0;
        let max_height = 0;

        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d')!;
        ctx.font = `${size}px MSDF`;

        for (const ch of chars) {
            const metrics = ctx.measureText(ch);
            const w = Math.ceil(metrics.actualBoundingBoxRight - metrics.actualBoundingBoxLeft);
            const h = Math.ceil(metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent);
            
            if (w > 0 && h > 0) {
                max_width = Math.max(max_width, w);
                max_height = Math.max(max_height, h);
                
                canvas.width = w + padding * 2;
                canvas.height = h + padding * 2;
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.font = `${size}px MSDF`;
                ctx.fillStyle = 'white';
                ctx.fillText(ch, padding - metrics.actualBoundingBoxLeft, padding + metrics.actualBoundingBoxAscent);
                
                const image_data = ctx.getImageData(0, 0, canvas.width, canvas.height);
                const sdf = this.compute_sdf(image_data);
                
                const advance = metrics.width;
                const bearing_x = -metrics.actualBoundingBoxLeft;
                const bearing_y = h + metrics.actualBoundingBoxDescent;
                
                glyphs_data.push([ch, sdf, advance, bearing_x, bearing_y, w, h]);
            } else {
                glyphs_data.push([ch, null, 0, 0, 0, 0, 0]);
            }
        }

        const cols = Math.floor(Math.sqrt(chars.length)) + 1;
        const rows = Math.ceil(chars.length / cols);
        const cell_w = max_width + padding * 2;
        const cell_h = max_height + padding * 2;
        
        const atlas_w = Math.min(cols * cell_w, this.atlas_size);
        const atlas_h = Math.min(rows * cell_h, this.atlas_size);
        
        const final_cols = Math.floor(atlas_w / cell_w);
        const final_rows = Math.floor(atlas_h / cell_h);
        
        const atlas_canvas = document.createElement('canvas');
        atlas_canvas.width = atlas_w;
        atlas_canvas.height = atlas_h;
        const atlas_ctx = atlas_canvas.getContext('2d')!;
        
        let x = 0;
        let y = 0;
        
        for (const [ch, sdf, advance, bearing_x, bearing_y, w, h] of glyphs_data) {
            if (sdf) {
                const dst_x = x * cell_w + padding;
                const dst_y = y * cell_h + padding;
                
                atlas_ctx.putImageData(sdf, dst_x, dst_y);
                
                const u0 = dst_x / atlas_w;
                const v0 = dst_y / atlas_h;
                const u1 = (dst_x + w) / atlas_w;
                const v1 = (dst_y + h) / atlas_h;
                
                this.glyphs.set(ch, {
                    advance,
                    bearing_x,
                    bearing_y,
                    width: w,
                    height: h,
                    u0, v0, u1, v1
                });
            } else {
                this.glyphs.set(ch, {
                    advance: 0, bearing_x: 0, bearing_y: 0,
                    width: 0, height: 0, u0: 0, v0: 0, u1: 0, v1: 0
                });
            }
            
            x += 1;
            if (x >= final_cols) {
                x = 0;
                y += 1;
            }
        }

        this.texture = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, this.texture);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, atlas_canvas);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    }

    private compute_sdf(image_data: ImageData): ImageData {
        const data = image_data.data;
        const w = image_data.width;
        const h = image_data.height;
        
        const inside = new Float32Array(w * h);
        for (let i = 0; i < w * h; i++) {
            inside[i] = data[i * 4] > 128 ? 1 : 0;
        }
        
        const dist_in = this.distance_transform(inside, w, h, true);
        const dist_out = this.distance_transform(inside, w, h, false);
        
        let max_dist = 0;
        for (let i = 0; i < w * h; i++) {
            max_dist = Math.max(max_dist, dist_in[i], dist_out[i]);
        }
        
        const sdf = new ImageData(w, h);
        const sdf_data = sdf.data;
        for (let i = 0; i < w * h; i++) {
            const d = dist_out[i] - dist_in[i];
            const val = max_dist > 0 ? 128 + (d / max_dist) * 127 : 128;
            const clamped = Math.max(0, Math.min(255, val));
            sdf_data[i * 4] = clamped;
            sdf_data[i * 4 + 1] = clamped;
            sdf_data[i * 4 + 2] = clamped;
            sdf_data[i * 4 + 3] = 255;
        }
        
        return sdf;
    }

    private distance_transform(input: Float32Array, w: number, h: number, inside: boolean): Float32Array {
        const output = new Float32Array(w * h);
        const INF = 1e9;
        
        for (let y = 0; y < h; y++) {
            for (let x = 0; x < w; x++) {
                output[y * w + x] = (inside ? input[y * w + x] : 1 - input[y * w + x]) > 0 ? 0 : INF;
            }
        }
        
        for (let y = 0; y < h; y++) {
            let d = INF;
            for (let x = 0; x < w; x++) {
                d = output[y * w + x] > 0 ? 0 : d + 1;
                output[y * w + x] = Math.min(output[y * w + x], d);
            }
            d = INF;
            for (let x = w - 1; x >= 0; x--) {
                d = output[y * w + x] > 0 ? 0 : d + 1;
                output[y * w + x] = Math.min(output[y * w + x], d);
            }
        }
        
        for (let x = 0; x < w; x++) {
            let d = INF;
            for (let y = 0; y < h; y++) {
                d = output[y * w + x] > 0 ? 0 : d + 1;
                output[y * w + x] = Math.min(output[y * w + x], d);
            }
            d = INF;
            for (let y = h - 1; y >= 0; y--) {
                d = output[y * w + x] > 0 ? 0 : d + 1;
                output[y * w + x] = Math.min(output[y * w + x], d);
            }
        }
        
        return output;
    }

    async load_atlas(gl: WebGL2RenderingContext, texture_url: string, meta_url: string): Promise<void> {
        const meta_res = await fetch(meta_url);
        const meta = await meta_res.json();
        
        this.font_size = meta.font_size;
        this.chars = meta.chars;
        this.padding = meta.padding;
        this.atlas_size = meta.atlas_size || 4096;
        this.glyphs.clear();
        
        for (const [ch, gm] of Object.entries(meta.glyphs as Record<string, any>)) {
            this.glyphs.set(ch, {
                advance: gm.advance,
                bearing_x: gm.bearing_x,
                bearing_y: gm.bearing_y,
                width: gm.width,
                height: gm.height,
                u0: gm.u0,
                v0: gm.v0,
                u1: gm.u1,
                v1: gm.v1,
            });
        }
        
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = "anonymous";
            img.onload = () => {
                this.texture = gl.createTexture();
                gl.bindTexture(gl.TEXTURE_2D, this.texture);
                gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
                gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
                resolve();
            };
            img.onerror = (err) => reject(err);
            img.src = texture_url;
        });
    }

    get_glyph(ch: string): GlyphMetrics | undefined {
        return this.glyphs.get(ch);
    }
}

export class WebGLRenderer {
    private gl: WebGL2RenderingContext;
    // Step 53: WebGL2 が使えない場合のフォールバック検知フラグ
    webgl2_supported: boolean = true;
    private width: number;
    private height: number;
    private texture_cache: Map<number, WebGLTexture> = new Map();
    private next_texture_id: number = 1;
    private msdf_atlas: MSDFAtlas | null = null;
    private viewport: Viewport = { x: 0, y: 0, width: 0, height: 0 };
    
    private tile_program: WebGLProgram | null = null;
    private text_program: WebGLProgram | null = null;
    private tile_vao: WebGLVertexArrayObject | null = null;
    private text_vao: WebGLVertexArrayObject | null = null;
    
    private tile_buffer: WebGLBuffer | null = null;
    private text_buffer: WebGLBuffer | null = null;
    
    private tile_vertex_shader = `#version 300 es
        precision highp float;
        in vec2 a_position;
        in vec2 a_texcoord;
        in vec4 a_color;
        uniform mat4 u_projection;
        out vec2 v_texcoord;
        out vec4 v_color;
        void main() {
            gl_Position = u_projection * vec4(a_position, 0.0, 1.0);
            v_texcoord = a_texcoord;
            v_color = a_color;
        }
    `;
    
    private tile_fragment_shader = `#version 300 es
        precision highp float;
        in vec2 v_texcoord;
        in vec4 v_color;
        uniform sampler2D u_texture;
        out vec4 frag_color;
        void main() {
            vec4 tex = texture(u_texture, v_texcoord);
            frag_color = tex * v_color;
        }
    `;
    
    private text_vertex_shader = `#version 300 es
        precision highp float;
        in vec2 a_position;
        in vec2 a_texcoord;
        in vec4 a_color;
        uniform mat4 u_projection;
        out vec2 v_texcoord;
        out vec4 v_color;
        void main() {
            gl_Position = u_projection * vec4(a_position, 0.0, 1.0);
            v_texcoord = a_texcoord;
            v_color = a_color;
        }
    `;
    
    private text_fragment_shader = `#version 300 es
        precision highp float;
        in vec2 v_texcoord;
        in vec4 v_color;
        uniform sampler2D u_msdf_atlas;
        out vec4 frag_color;
        void main() {
            float msdf = texture(u_msdf_atlas, v_texcoord).r;
            float alpha = smoothstep(0.4, 0.6, msdf);
            frag_color = v_color * vec4(1.0, 1.0, 1.0, alpha);
        }
    `;

    constructor(canvas: HTMLCanvasElement) {
        this.width = canvas.width;
        this.height = canvas.height;
        
        const gl = canvas.getContext('webgl2', {
            alpha: true,
            antialias: false,
            preserveDrawingBuffer: true,
        });
        
        if (!gl) {
            // Step 53: 例外を投げず、Canvas2D レンダラへのフォールバックを通知
            console.warn('WebGL2 not supported; falling back to Canvas2D renderer.');
            this.webgl2_supported = false;
            this.gl = null as unknown as WebGL2RenderingContext;
            this.viewport = { x: 0, y: 0, width: this.width, height: this.height };
            return;
        }

        this.gl = gl;
        this.viewport = { x: 0, y: 0, width: this.width, height: this.height };
        
        this.init_shaders();
        this.init_buffers();
    }

    private init_shaders(): void {
        const gl = this.gl;
        
        this.tile_program = this.create_program(this.tile_vertex_shader, this.tile_fragment_shader);
        this.text_program = this.create_program(this.text_vertex_shader, this.text_fragment_shader);
    }

    private create_program(vs_src: string, fs_src: string): WebGLProgram {
        const gl = this.gl;
        
        const vs = gl.createShader(gl.VERTEX_SHADER)!;
        gl.shaderSource(vs, vs_src);
        gl.compileShader(vs);
        if (!gl.getShaderParameter(vs, gl.COMPILE_STATUS)) {
            throw new Error('Vertex shader compile error: ' + gl.getShaderInfoLog(vs));
        }
        
        const fs = gl.createShader(gl.FRAGMENT_SHADER)!;
        gl.shaderSource(fs, fs_src);
        gl.compileShader(fs);
        if (!gl.getShaderParameter(fs, gl.COMPILE_STATUS)) {
            throw new Error('Fragment shader compile error: ' + gl.getShaderInfoLog(fs));
        }
        
        const program = gl.createProgram()!;
        gl.attachShader(program, vs);
        gl.attachShader(program, fs);
        gl.linkProgram(program);
        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
            throw new Error('Program link error: ' + gl.getProgramInfoLog(program));
        }
        
        return program;
    }

    private init_buffers(): void {
        const gl = this.gl;
        
        this.tile_vao = gl.createVertexArray()!;
        gl.bindVertexArray(this.tile_vao);
        
        this.tile_buffer = gl.createBuffer()!;
        gl.bindBuffer(gl.ARRAY_BUFFER, this.tile_buffer);
        gl.bufferData(gl.ARRAY_BUFFER, 1024 * 4 * 4, gl.DYNAMIC_DRAW);
        
        const pos_loc = gl.getAttribLocation(this.tile_program!, 'a_position');
        const tex_loc = gl.getAttribLocation(this.tile_program!, 'a_texcoord');
        const col_loc = gl.getAttribLocation(this.tile_program!, 'a_color');
        
        gl.enableVertexAttribArray(pos_loc);
        gl.vertexAttribPointer(pos_loc, 2, gl.FLOAT, false, 4 * 8, 0);
        gl.enableVertexAttribArray(tex_loc);
        gl.vertexAttribPointer(tex_loc, 2, gl.FLOAT, false, 4 * 8, 2 * 4);
        gl.enableVertexAttribArray(col_loc);
        gl.vertexAttribPointer(col_loc, 4, gl.FLOAT, false, 4 * 8, 4 * 4);
        
        this.text_vao = gl.createVertexArray()!;
        gl.bindVertexArray(this.text_vao);
        
        this.text_buffer = gl.createBuffer()!;
        gl.bindBuffer(gl.ARRAY_BUFFER, this.text_buffer);
        gl.bufferData(gl.ARRAY_BUFFER, 1024 * 4 * 4, gl.DYNAMIC_DRAW);
        
        const t_pos_loc = gl.getAttribLocation(this.text_program!, 'a_position');
        const t_tex_loc = gl.getAttribLocation(this.text_program!, 'a_texcoord');
        const t_col_loc = gl.getAttribLocation(this.text_program!, 'a_color');
        
        gl.enableVertexAttribArray(t_pos_loc);
        gl.vertexAttribPointer(t_pos_loc, 2, gl.FLOAT, false, 4 * 8, 0);
        gl.enableVertexAttribArray(t_tex_loc);
        gl.vertexAttribPointer(t_tex_loc, 2, gl.FLOAT, false, 4 * 8, 2 * 4);
        gl.enableVertexAttribArray(t_col_loc);
        gl.vertexAttribPointer(t_col_loc, 4, gl.FLOAT, false, 4 * 8, 4 * 4);
        
        gl.bindVertexArray(null);
    }

    async load_msdf_atlas(font_path: string, chars: string, size: number, padding: number = 2): Promise<void> {
        this.msdf_atlas = new MSDFAtlas();
        await this.msdf_atlas.generate_atlas(this.gl, font_path, chars, size, padding);
    }

    async load_msdf_atlas_from_url(texture_url: string, meta_url: string): Promise<void> {
        this.msdf_atlas = new MSDFAtlas();
        await this.msdf_atlas.load_atlas(this.gl, texture_url, meta_url);
    }

    begin_frame(): void {
        const gl = this.gl;
        gl.viewport(0, 0, this.width, this.height);
        gl.clearColor(0, 0, 0, 1);
        gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
    }

    end_frame(): void {
    }

    draw_tile(call: TileDrawCall): void {
        const gl = this.gl;
        const texture = this.texture_cache.get(call.texture_id);
        if (!texture) return;
        
        gl.useProgram(this.tile_program!);
        gl.bindVertexArray(this.tile_vao!);
        
        const projection = this.get_projection_matrix();
        gl.uniformMatrix4fv(gl.getUniformLocation(this.tile_program!, 'u_projection'), false, projection);
        
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.uniform1i(gl.getUniformLocation(this.tile_program!, 'u_texture'), 0);
        
        const x = call.x;
        const y = call.y;
        const w = call.width * call.scale;
        const h = call.height * call.scale;
        
        const vertices = new Float32Array([
            x, y, call.u0, call.v0, call.color[0], call.color[1], call.color[2], call.color[3],
            x + w, y, call.u1, call.v0, call.color[0], call.color[1], call.color[2], call.color[3],
            x, y + h, call.u0, call.v1, call.color[0], call.color[1], call.color[2], call.color[3],
            x + w, y + h, call.u1, call.v1, call.color[0], call.color[1], call.color[2], call.color[3],
        ]);
        
        gl.bindBuffer(gl.ARRAY_BUFFER, this.tile_buffer!);
        gl.bufferSubData(gl.ARRAY_BUFFER, 0, vertices);
        
        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }

    draw_text(call: TextDrawCall): void {
        const gl = this.gl;
        
        if (!this.msdf_atlas || !this.msdf_atlas.texture) {
            console.warn('MSDF atlas not loaded, skipping text render');
            return;
        }
        
        gl.useProgram(this.text_program!);
        gl.bindVertexArray(this.text_vao!);
        
        const projection = this.get_projection_matrix();
        gl.uniformMatrix4fv(gl.getUniformLocation(this.text_program!, 'u_projection'), false, projection);
        
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, this.msdf_atlas.texture);
        gl.uniform1i(gl.getUniformLocation(this.text_program!, 'u_msdf_atlas'), 0);
        
        let x = call.x;
        const y = call.y;
        const scale = call.font_size / this.msdf_atlas.font_size;
        
        for (const ch of call.text) {
            const glyph = this.msdf_atlas.get_glyph(ch);
            if (glyph && glyph.width > 0) {
                const w = glyph.width * scale;
                const h = glyph.height * scale;
                
                const vertices = new Float32Array([
                    x, y, glyph.u0, glyph.v0, call.color[0], call.color[1], call.color[2], call.color[3],
                    x + w, y, glyph.u1, glyph.v0, call.color[0], call.color[1], call.color[2], call.color[3],
                    x, y + h, glyph.u0, glyph.v1, call.color[0], call.color[1], call.color[2], call.color[3],
                    x + w, y + h, glyph.u1, glyph.v1, call.color[0], call.color[1], call.color[2], call.color[3],
                ]);
                
                gl.bindBuffer(gl.ARRAY_BUFFER, this.text_buffer!);
                gl.bufferSubData(gl.ARRAY_BUFFER, 0, vertices);
                gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
                
                x += glyph.advance * scale;
            } else {
                x += call.font_size * 0.5;
            }
        }
    }

    set_viewport(viewport: Viewport): void {
        this.viewport = viewport;
    }

    get_viewport(): Viewport {
        return this.viewport;
    }

    create_texture(path: string): number {
        const gl = this.gl;
        const texture = gl.createTexture()!;
        
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        
        const texture_id = this.next_texture_id++;
        this.texture_cache.set(texture_id, texture);
        
        const img = new Image();
        img.onload = () => {
            gl.bindTexture(gl.TEXTURE_2D, texture);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img);
        };
        img.src = path;
        
        return texture_id;
    }

    destroy_texture(texture_id: number): void {
        const texture = this.texture_cache.get(texture_id);
        if (texture) {
            this.gl.deleteTexture(texture);
            this.texture_cache.delete(texture_id);
        }
    }

    get_texture_size(texture_id: number): [number, number] {
        const texture = this.texture_cache.get(texture_id);
        if (texture) {
            return [0, 0];
        }
        return [0, 0];
    }

    clear(color: [number, number, number, number] = [0, 0, 0, 1]): void {
        const gl = this.gl;
        gl.clearColor(color[0], color[1], color[2], color[3]);
        gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    }

    present(): void {
    }

    resize(width: number, height: number): void {
        this.width = width;
        this.height = height;
        const canvas = this.gl.canvas as HTMLCanvasElement;
        canvas.width = width;
        canvas.height = height;
        this.viewport = { x: 0, y: 0, width, height };
    }

    get_framebuffer_size(): [number, number] {
        return [this.width, this.height];
    }

    private get_projection_matrix(): Float32Array {
        const left = this.viewport.x;
        const right = this.viewport.x + this.viewport.width;
        const bottom = this.viewport.y + this.viewport.height;
        const top = this.viewport.y;
        
        const matrix = new Float32Array(16);
        matrix[0] = 2 / (right - left);
        matrix[5] = 2 / (top - bottom);
        matrix[10] = -1;
        matrix[12] = -(right + left) / (right - left);
        matrix[13] = -(top + bottom) / (top - bottom);
        matrix[15] = 1;
        return matrix;
    }
}

export function create_renderer(canvas: HTMLCanvasElement): WebGLRenderer {
    return new WebGLRenderer(canvas);
}