// Light Volume Shader - Deferred Lighting
// Supports Point, Spot, and Decal lights with GGX BRDF

#version 300 es
precision highp float;

in vec2 v_texcoord;
out vec4 frag_color;

uniform sampler2D u_albedo;
uniform sampler2D u_normal;
uniform sampler2D u_material;
uniform sampler2D u_depth;
uniform sampler2D u_shadow_atlas;

uniform mat4 u_view;
uniform mat4 u_proj;
uniform mat4 u_inv_view;
uniform mat4 u_inv_proj;
uniform vec2 u_resolution;
uniform vec2 u_inv_resolution;

uniform int u_light_count;
uniform Light {
    int type;           // 0=point, 1=spot, 2=decal
    vec3 position;
    vec3 color;
    float radius;
    float intensity;
    vec3 direction;
    float inner_cone;
    float outer_cone;
    vec2 size;
    float rotation;
    vec4 shadow_region; // x, y, w, h in atlas
} u_lights[64];

// Shadow atlas lookup
float sample_shadow(vec3 light_pos, vec3 frag_pos, vec4 shadow_region) {
    // For point lights: use cubemap-style sampling
    // For spot lights: use 2D shadow map
    // Simplified: return 1.0 (no shadow) for now
    return 1.0;
}

// GGX Distribution
float ggx_distribution(float n_dot_h, float roughness) {
    float a = roughness * roughness;
    float a2 = a * a;
    float n_dot_h2 = n_dot_h * n_dot_h;
    float denom = n_dot_h2 * (a2 - 1.0) + 1.0;
    return a2 / (3.14159265359 * denom * denom);
}

// GGX Geometry (Smith)
float ggx_geometry(float n_dot_v, float roughness) {
    float r = roughness + 1.0;
    float k = (r * r) / 8.0;
    return n_dot_v / (n_dot_v * (1.0 - k) + k);
}

// Schlick Fresnel
vec3 schlick_fresnel(vec3 f0, float v_dot_h) {
    return f0 + (1.0 - f0) * pow(1.0 - v_dot_h, 5.0);
}

// Reconstruct view-space position from depth
vec3 reconstruct_position(vec2 uv, float depth) {
    vec4 clip = vec4(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    vec4 view = u_inv_proj * clip;
    view.xyz /= view.w;
    return view.xyz;
}

// Reconstruct view-space normal from packed XY
vec3 reconstruct_normal(vec2 packed_xy) {
    float x = packed_xy.x;
    float y = packed_xy.y;
    float z_sq = 1.0 - x * x - y * y;
    float z = sqrt(max(z_sq, 0.0));
    return normalize(vec3(x, y, z));
}

void main() {
    // G-Buffer fetch
    vec4 albedo = texture(u_albedo, v_texcoord);
    vec2 packed_normal = texture(u_normal, v_texcoord).rg;
    vec4 material = texture(u_material, v_texcoord);
    float depth = texture(u_depth, v_texcoord).r;
    
    // Skip sky/background
    if (depth >= 1.0) {
        frag_color = vec4(0.0);
        return;
    }
    
    // Reconstruct
    vec3 view_pos = reconstruct_position(v_texcoord, depth);
    vec3 normal = reconstruct_normal(packed_normal);
    
    // Material unpack
    float roughness = material.r / 255.0;
    float metallic = material.g / 255.0;
    float emissive = material.b / 255.0;
    float ao = material.a / 255.0;
    
    // Clamp roughness
    roughness = max(roughness, 0.04);
    
    // F0 (specular color)
    vec3 f0 = mix(vec3(0.04), albedo.rgb, metallic);
    
    // View direction
    vec3 view_dir = normalize(-view_pos);
    
    // Accumulate lighting
    vec3 lighting = vec3(0.0);
    
    for (int i = 0; i < u_light_count; i++) {
        Light light = u_lights[i];
        
        // Light vector
        vec3 light_vec = light.position - view_pos;
        float dist = length(light_vec);
        vec3 light_dir = light_vec / (dist + 1e-6);
        
        // Attenuation
        float attenuation = 1.0 / (1.0 + dist * dist / (light.radius * light.radius));
        attenuation *= light.intensity;
        
        // Spot light cone
        if (light.type == 1) {
            float spot_dot = dot(-light_dir, normalize(light.direction));
            float spot_effect = smoothstep(light.outer_cone, light.inner_cone, spot_dot);
            attenuation *= spot_effect;
        }
        
        // Decal projection
        if (light.type == 2) {
            // Project decal texture
            // Simplified: treat as directional light for now
            attenuation *= 1.0;
        }
        
        if (attenuation <= 0.001) continue;
        
        // Shadow
        float shadow = sample_shadow(light.position, view_pos, light.shadow_region);
        attenuation *= shadow;
        
        // Half vector
        vec3 h = normalize(light_dir + view_dir);
        
        // BRDF
        float n_dot_l = max(dot(normal, light_dir), 0.0);
        float n_dot_v = max(dot(normal, view_dir), 0.0);
        float n_dot_h = max(dot(normal, h), 0.0);
        float v_dot_h = max(dot(view_dir, h), 0.0);
        
        if (n_dot_l <= 0.0) continue;
        
        // Distribution
        float D = ggx_distribution(n_dot_h, roughness);
        // Geometry
        float G = ggx_geometry(n_dot_v, roughness) * ggx_geometry(n_dot_l, roughness);
        // Fresnel
        vec3 F = schlick_fresnel(f0, v_dot_h);
        
        // Specular
        vec3 specular = D * G * F / (4.0 * n_dot_v * n_dot_l + 1e-6);
        specular *= attenuation;
        
        // Diffuse (Disney)
        vec3 diffuse = albedo.rgb * (1.0 - metallic) / 3.14159265359;
        diffuse *= (1.0 - F) * n_dot_l * attenuation;
        
        lighting += diffuse + specular;
    }
    
    // Emissive
    lighting += albedo.rgb * emissive;
    
    // Ambient occlusion
    lighting *= ao;
    
    // Output
    frag_color = vec4(lighting, 1.0);
}