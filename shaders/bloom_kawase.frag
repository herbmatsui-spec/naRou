// Kawase Dual-Filter Bloom Shader
// Based on Kawase blur: "Practical Post-Process Depth of Field" (GDC 2017)

#version 300 es
precision highp float;

in vec2 v_texcoord;
out vec4 frag_color;

uniform sampler2D u_texture;
uniform vec2 u_resolution;
uniform vec2 u_inv_resolution;
uniform float u_threshold;
uniform float u_intensity;
uniform int u_pass;  // 0=extract, 1=downsample, 2=upsample+blur, 3=composite

// Kawase weights and offsets
const float weights[5] = float[5](0.227027, 0.194595, 0.121622, 0.054054, 0.016216);
const float offsets[5] = float[5](0.0, 1.384615, 3.230769, 5.076923, 7.0);

vec3 sample_bloom(sampler2D tex, vec2 uv, float radius) {
    vec3 result = texture(tex, uv).rgb * weights[0];
    float total_weight = weights[0];
    
    for (int i = 1; i < 5; i++) {
        float offset = offsets[i] * radius;
        
        vec2 dir[4] = vec2[4](
            vec2(1.0, 0.0),
            vec2(-1.0, 0.0),
            vec2(0.0, 1.0),
            vec2(0.0, -1.0)
        );
        
        for (int d = 0; d < 4; d++) {
            vec2 sample_uv = uv + dir[d] * offset * u_inv_resolution;
            if (sample_uv.x >= 0.0 && sample_uv.x <= 1.0 &&
                sample_uv.y >= 0.0 && sample_uv.y <= 1.0) {
                result += texture(tex, sample_uv).rgb * weights[i];
                total_weight += weights[i];
            }
        }
    }
    
    return result / total_weight;
}

void main() {
    vec4 tex_color = texture(u_texture, v_texcoord);
    vec3 hdr = tex_color.rgb;
    
    if (u_pass == 0) {
        // Pass 0: Extract bright pixels
        float luminance = dot(hdr, vec3(0.2126, 0.7152, 0.0722));
        if (luminance > u_threshold) {
            frag_color = vec4(hdr * u_intensity, 1.0);
        } else {
            frag_color = vec4(0.0);
        }
    } else if (u_pass == 1) {
        // Pass 1: Downsample (simple box filter)
        vec2 texel = u_inv_resolution;
        vec3 sum = hdr;
        int count = 1;
        
        for (int y = -1; y <= 1; y++) {
            for (int x = -1; x <= 1; x++) {
                if (x == 0 && y == 0) continue;
                vec2 offset = vec2(float(x), float(y)) * texel;
                vec2 sample_uv = v_texcoord + offset;
                if (sample_uv.x >= 0.0 && sample_uv.x <= 1.0 &&
                    sample_uv.y >= 0.0 && sample_uv.y <= 1.0) {
                    sum += texture(u_texture, sample_uv).rgb;
                    count++;
                }
            }
        }
        
        frag_color = vec4(sum / float(count), 1.0);
    } else if (u_pass == 2) {
        // Pass 2: Upsample + Kawase blur
        // u_radius should be passed as uniform
        float radius = 1.0;  // Will be overridden by uniform
        vec3 blurred = sample_bloom(u_texture, v_texcoord, radius);
        frag_color = vec4(blurred, 1.0);
    } else if (u_pass == 3) {
        // Pass 3: Composite bloom onto scene
        // This would be done in a separate composite shader
        frag_color = tex_color;
    } else {
        frag_color = tex_color;
    }
}