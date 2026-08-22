// Light Volume Shader - WebGPU (WGSL)
// Equivalent to light_volume.frag for WebGPU backend

struct Light {
    type: u32,           // 0=point, 1=spot, 2=decal
    position: vec3<f32>,
    color: vec3<f32>,
    radius: f32,
    intensity: f32,
    direction: vec3<f32>,
    inner_cone: f32,
    outer_cone: f32,
    size: vec2<f32>,
    rotation: f32,
    shadow_region: vec4<f32>, // x, y, w, h in atlas
}

struct GBuffer {
    albedo: texture_2d<f32>,
    normal: texture_2d<f32>,
    material: texture_2d<f32>,
    depth: texture_depth_2d,
    shadow_atlas: texture_2d<f32>,
}

@group(0) @binding(0) var gbuffer: GBuffer;
@group(0) @binding(1) var sampler_linear: sampler;
@group(0) @binding(2) var<uniform> lights: array<Light, 64>;
@group(0) @binding(3) var<uniform> light_count: u32;
@group(0) @binding(4) var<uniform> view: mat4x4<f32>;
@group(0) @binding(5) var<uniform> proj: mat4x4<f32>;
@group(0) @binding(6) var<uniform> inv_view: mat4x4<f32>;
@group(0) @binding(7) var<uniform> inv_proj: mat4x4<f32>;
@group(0) @binding(8) var<uniform> resolution: vec2<f32>;
@group(0) @binding(9) var<uniform> inv_resolution: vec2<f32>;

@fragment
fn fs_main(@builtin(position) frag_coord: vec2<f32>) -> @location(0) vec4<f32> {
    let uv = frag_coord * inv_resolution;

    // G-Buffer fetch
    let albedo = textureSample(gbuffer.albedo, sampler_linear, uv);
    let packed_normal = textureSample(gbuffer.normal, sampler_linear, uv).rg;
    let material = textureSample(gbuffer.material, sampler_linear, uv);
    let depth = textureLoad(gbuffer.depth, vec2<u32>(frag_coord), 0);

    // Skip sky/background
    if (depth >= 1.0) {
        return vec4<f32>(0.0, 0.0, 0.0, 0.0);
    }

    // Reconstruct view-space position
    var clip = vec4<f32>(uv * 2.0 - 1.0, depth * 2.0 - 1.0, 1.0);
    var view_pos = (inv_proj * clip).xyz / (inv_proj * clip).w;

    // Reconstruct normal
    let normal = normalize(vec3<f32>(packed_normal.x, packed_normal.y,
        sqrt(max(1.0 - packed_normal.x * packed_normal.x - packed_normal.y * packed_normal.y, 0.0))));

    // Material unpack
    let roughness = max(material.r, 0.04);
    let metallic = material.g;
    let emissive = material.b;
    let ao = material.a;

    // F0
    let f0 = mix(vec3<f32>(0.04), albedo.rgb, metallic);
    let view_dir = normalize(-view_pos);

    // Accumulate lighting
    var lighting = vec3<f32>(0.0);

    for (var i: u32 = 0; i < light_count; i++) {
        let light = lights[i];

        // Light vector
        let light_vec = light.position - view_pos;
        let dist = length(light_vec);
        let light_dir = light_vec / (dist + 1e-6);

        // Attenuation
        var attenuation = 1.0 / (1.0 + dist * dist / (light.radius * light.radius));
        attenuation *= light.intensity;

        // Spot light cone
        if (light.type == 1u) {
            let spot_dot = dot(-light_dir, normalize(light.direction));
            let spot_effect = smoothstep(light.outer_cone, light.inner_cone, spot_dot);
            attenuation *= spot_effect;
        }

        // Decal
        if (light.type == 2u) {
            attenuation *= 1.0;
        }

        if (attenuation <= 0.001) { continue; }

        // Shadow (placeholder)
        let shadow = 1.0;
        attenuation *= shadow;

        // Half vector
        let h = normalize(light_dir + view_dir);

        // BRDF
        let n_dot_l = max(dot(normal, light_dir), 0.0);
        let n_dot_v = max(dot(normal, view_dir), 0.0);
        let n_dot_h = max(dot(normal, h), 0.0);
        let v_dot_h = max(dot(view_dir, h), 0.0);

        if (n_dot_l <= 0.0) { continue; }

        // GGX Distribution
        let a = roughness * roughness;
        let a2 = a * a;
        let n_dot_h2 = n_dot_h * n_dot_h;
        let denom = n_dot_h2 * (a2 - 1.0) + 1.0;
        let D = a2 / (3.14159265359 * denom * denom);

        // GGX Geometry (Smith)
        let r = roughness + 1.0;
        let k = (r * r) / 8.0;
        let G_v = n_dot_v / (n_dot_v * (1.0 - k) + k);
        let G_l = n_dot_l / (n_dot_l * (1.0 - k) + k);
        let G = G_v * G_l;

        // Schlick Fresnel
        let F = f0 + (1.0 - f0) * pow(1.0 - v_dot_h, 5.0);

        // Specular
        var specular = D * G * F / (4.0 * n_dot_v * n_dot_l + 1e-6);
        specular *= attenuation;

        // Diffuse (Disney)
        let diffuse = albedo.rgb * (1.0 - metallic) / 3.14159265359;
        let diffuse_val = diffuse * (1.0 - F) * n_dot_l * attenuation;

        lighting += diffuse_val + specular;
    }

    // Emissive
    lighting += albedo.rgb * emissive;

    // AO
    lighting *= ao;

    return vec4<f32>(lighting, 1.0);
}
