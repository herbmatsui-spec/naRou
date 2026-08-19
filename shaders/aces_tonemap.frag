// ACES RRT + ODT Tonemapping Shader
// Based on ACES approximation from https://github.com/TheRealMJP/BakingLab/blob/master/ACES.hlsl

#version 300 es
precision highp float;

in vec2 v_texcoord;
out vec4 frag_color;

uniform sampler2D u_hdr_texture;
uniform float u_exposure;
uniform float u_gamma;
uniform int u_tonemap_mode;  // 0=ACES, 1=Reinhard, 2=Filmic
uniform int u_color_space;   // 0=sRGB, 1=P3, 2=Rec2020

// ACES RRT
vec3 aces_rrt(vec3 x) {
    const vec3 a = vec3(2.51);
    const vec3 b = vec3(0.03);
    const vec3 c = vec3(2.43);
    const vec3 d = vec3(0.59);
    const vec3 e = vec3(0.14);
    
    vec3 num = x * (a * x + b);
    vec3 den = x * (c * x + d) + e;
    return num / (den + 1e-6);
}

// ACES ODT (sRGB)
vec3 aces_odt_srgb(vec3 x) {
    // Simplified sRGB ODT
    x = pow(x, vec3(1.0 / 2.2));
    return x;
}

// Reinhard tonemapping
vec3 reinhard(vec3 x) {
    return x / (1.0 + x);
}

// Filmic tonemapping (Unreal-style)
vec3 filmic(vec3 x) {
    const float A = 0.22;
    const float B = 0.30;
    const float C = 0.10;
    const float D = 0.20;
    const float E = 0.01;
    const float F = 0.30;
    const float W = 11.2;
    
    vec3 num = x * (A * x + C * B) + D * E;
    vec3 den = x * (A * x + B) + D * F;
    vec3 white = vec3(W);
    float white_num = W * (A * W + C * B) + D * E;
    float white_den = W * (A * W + B) + D * F;
    float white_scale = white_num / white_den - E / F;
    
    return (num / (den + 1e-6) - E / F) / white_scale;
}

void main() {
    vec3 hdr = texture(u_hdr_texture, v_texcoord).rgb;
    
    // Exposure
    hdr *= u_exposure;
    
    // Tonemapping
    vec3 tonemapped;
    if (u_tonemap_mode == 0) {
        // ACES
        tonemapped = aces_rrt(hdr);
        tonemapped = aces_odt_srgb(tonemapped);
    } else if (u_tonemap_mode == 1) {
        // Reinhard
        tonemapped = reinhard(hdr);
    } else {
        // Filmic
        tonemapped = filmic(hdr);
    }
    
    // Gamma correction
    tonemapped = pow(max(tonemapped, 0.0), vec3(1.0 / u_gamma));
    
    // Clamp
    tonemapped = clamp(tonemapped, 0.0, 1.0);
    
    frag_color = vec4(tonemapped, 1.0);
}