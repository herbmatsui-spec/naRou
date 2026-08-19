// Particle Simulation Compute Shader - WebGPU (WGSL)

struct Particle {
    position: vec3<f32>,
    velocity: vec3<f32>,
    life: vec4<f32>,      // x=current, y=max, z=padding, w=padding
    color: vec4<f32>,
    size: vec4<f32>,      // x=start, y=end, z=current, w=padding
    rotation: vec4<f32>,  // x=start, y=speed, z=current, w=padding
    flags: u32,
    material_id: u32,
    emitter_id: u32,
    prev_position: vec3<f32>,
    ribbon_length: f32,
}

@group(0) @binding(0) var<storage, read_write> particles: array<Particle>;
@group(0) @binding(1) var<storage, read_write> alive_indices: array<u32>;
@group(0) @binding(2) var<storage, read_write> alive_count: u32;
@group(0) @binding(3) var<storage, read_write> free_list: array<u32>;
@group(0) @binding(4) var<storage, read_write> free_count: u32;
@group(0) @binding(5) var<storage, read> sdf_grid: array<f32>;
@group(0) @binding(6) var<uniform> sdf_dims: vec3<u32>;
@group(0) @binding(7) var<uniform> sdf_bounds_min: vec3<f32>;
@group(0) @binding(8) var<uniform> sdf_bounds_max: vec3<f32>;
@group(0) @binding(9) var<uniform> cell_size: f32;
@group(0) @binding(10) var<storage, read> perm: array<u32>;

struct Uniforms {
    dt: f32,
    time: f32,
    gravity: vec3<f32>,
    wind: vec3<f32>,
    max_particles: u32,
    flags_curl_noise: u32,
    flags_sdf_collision: u32,
    flags_ribbon: u32,
}
@group(0) @binding(11) var<uniform> uniforms: Uniforms;

fn fade(t: f32) -> f32 {
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0);
}

fn grad(hash: u32, x: f32, y: f32, z: f32) -> f32 {
    let h = hash & 15u;
    let u = select(y, x, h < 8u);
    let v = select(z, select(x, y, h < 4u), h == 12u || h == 14u);
    return select(-u, u, (h & 1u) == 0u) + select(-v, v, (h & 2u) == 0u);
}

fn noise3d(p: vec3<f32>) -> f32 {
    let ip = vec3<i32>(floor(p)) & 255;
    let fp = fract(p);
    let f = fade(fp);
    
    let aaa = perm[perm[perm[u32(ip.x)] + u32(ip.y)] + u32(ip.z)];
    let aba = perm[perm[perm[u32(ip.x)] + u32(ip.y)] + u32(ip.z) + 1u];
    let aab = perm[perm[perm[u32(ip.x)] + u32(ip.y) + 1u] + u32(ip.z)];
    let abb = perm[perm[perm[u32(ip.x)] + u32(ip.y) + 1u] + u32(ip.z) + 1u];
    let baa = perm[perm[perm[u32(ip.x) + 1u] + u32(ip.y)] + u32(ip.z)];
    let bba = perm[perm[perm[u32(ip.x) + 1u] + u32(ip.y)] + u32(ip.z) + 1u];
    let bab = perm[perm[perm[u32(ip.x) + 1u] + u32(ip.y) + 1u] + u32(ip.z)];
    let bbb = perm[perm[perm[u32(ip.x) + 1u] + u32(ip.y) + 1u] + u32(ip.z) + 1u];
    
    let x1 = mix(f32(grad(aaa, fp.x, fp.y, fp.z)), f32(grad(baa, fp.x - 1.0, fp.y, fp.z)), f.x);
    let x2 = mix(f32(grad(aba, fp.x, fp.y - 1.0, fp.z)), f32(grad(bba, fp.x - 1.0, fp.y - 1.0, fp.z)), f.x);
    let y1 = mix(x1, x2, f.y);
    
    let x1b = mix(f32(grad(aab, fp.x, fp.y, fp.z - 1.0)), f32(grad(bab, fp.x - 1.0, fp.y, fp.z - 1.0)), f.x);
    let x2b = mix(f32(grad(abb, fp.x, fp.y - 1.0, fp.z - 1.0)), f32(grad(bbb, fp.x - 1.0, fp.y - 1.0, fp.z - 1.0)), f.x);
    let y2 = mix(x1b, x2b, f.y);
    
    return mix(y1, y2, f.z) * 2.0;
}

fn curl_noise(p: vec3<f32>, eps: f32) -> vec3<f32> {
    let n_x = noise3d(p);
    let n_y = noise3d(p + vec3<f32>(1000.0, 0.0, 0.0));
    let n_z = noise3d(p + vec3<f32>(2000.0, 0.0, 0.0));
    
    let n_x_eps_y = noise3d(p + vec3<f32>(0.0, eps, 0.0));
    let n_y_eps_y = noise3d(p + vec3<f32>(1000.0, eps, 0.0));
    let n_z_eps_y = noise3d(p + vec3<f32>(2000.0, eps, 0.0));
    
    let n_x_eps_z = noise3d(p + vec3<f32>(0.0, 0.0, eps));
    let n_y_eps_z = noise3d(p + vec3<f32>(1000.0, 0.0, eps));
    let n_z_eps_z = noise3d(p + vec3<f32>(2000.0, 0.0, eps));
    
    let n_x_eps_x = noise3d(p + vec3<f32>(eps, 0.0, 0.0));
    let n_y_eps_x = noise3d(p + vec3<f32>(1000.0 + eps, 0.0, 0.0));
    let n_z_eps_x = noise3d(p + vec3<f32>(2000.0 + eps, 0.0, 0.0));
    
    return vec3<f32>(
        (n_z_eps_y - n_z) / eps - (n_y_eps_z - n_y) / eps,
        (n_x_eps_z - n_x) / eps - (n_z_eps_x - n_z) / eps,
        (n_y_eps_x - n_y) / eps - (n_x_eps_y - n_x) / eps
    );
}

fn sdf_query(pos: vec3<f32>) -> f32 {
    if (sdf_dims.x == 0u) { return 1e6; }
    
    let local = (pos - sdf_bounds_min) / cell_size;
    if (any(local < vec3<f32>(0.0)) || any(local > vec3<f32>(sdf_dims) - 1.0)) {
        return 1e6;
    }
    
    let idx = vec3<u32>(floor(local));
    let frac = fract(local);
    
    if (any(idx >= sdf_dims - 1u)) { return 1e6; }
    
    let i = idx;
    let f = frac;
    
    let stride_yz = sdf_dims.y * sdf_dims.x;
    let stride_z = sdf_dims.x;
    
    let c000 = sdf_grid[i.z * stride_yz + i.y * stride_z + i.x];
    let c100 = sdf_grid[i.z * stride_yz + i.y * stride_z + i.x + 1u];
    let c010 = sdf_grid[i.z * stride_yz + (i.y + 1u) * stride_z + i.x];
    let c110 = sdf_grid[i.z * stride_yz + (i.y + 1u) * stride_z + i.x + 1u];
    let c001 = sdf_grid[(i.z + 1u) * stride_yz + i.y * stride_z + i.x];
    let c101 = sdf_grid[(i.z + 1u) * stride_yz + i.y * stride_z + i.x + 1u];
    let c011 = sdf_grid[(i.z + 1u) * stride_yz + (i.y + 1u) * stride_z + i.x];
    let c111 = sdf_grid[(i.z + 1u) * stride_yz + (i.y + 1u) * stride_z + i.x + 1u];
    
    let c00 = mix(c000, c100, f.x);
    let c01 = mix(c010, c110, f.x);
    let c10 = mix(c001, c101, f.x);
    let c11 = mix(c011, c111, f.x);
    
    let c0 = mix(c00, c01, f.y);
    let c1 = mix(c10, c11, f.y);
    
    return mix(c0, c1, f.z);
}

fn sdf_gradient(pos: vec3<f32>, eps: f32) -> vec3<f32> {
    let d = sdf_query(pos);
    return vec3<f32>(
        sdf_query(pos + vec3<f32>(eps, 0.0, 0.0)) - d,
        sdf_query(pos + vec3<f32>(0.0, eps, 0.0)) - d,
        sdf_query(pos + vec3<f32>(0.0, 0.0, eps)) - d
    ) / eps;
}

@compute @workgroup_size(256)
fn main(@builtin(global_invocation_id) idx: vec3<u32>) {
    let i = idx.x;
    if (i >= uniforms.max_particles) { return; }
    
    if ((particles[i].flags & 1u) == 0u) { return; }
    
    // Update life
    particles[i].life.x += uniforms.dt;
    if (particles[i].life.x >= particles[i].life.y) {
        // Kill particle
        let free_idx = atomicAdd(&free_count, 1u);
        if (free_idx < uniforms.max_particles) {
            free_list[free_idx] = i;
        }
        particles[i].flags = 0u;
        return;
    }
    
    let life_ratio = particles[i].life.x / particles[i].life.y;
    var vel = particles[i].velocity;
    
    // Gravity
    vel += uniforms.gravity * uniforms.dt;
    
    // Wind
    vel += uniforms.wind * uniforms.dt;
    
    // Curl noise
    if ((uniforms.flags_curl_noise & 1u) != 0u) {
        let noise_vel = curl_noise(particles[i].position + uniforms.time, 0.01);
        vel += noise_vel * uniforms.dt * 5.0;
    }
    
    // Position update
    var new_pos = particles[i].position + vel * uniforms.dt;
    
    // SDF Collision
    if ((uniforms.flags_sdf_collision & 1u) != 0u) {
        let dist = sdf_query(new_pos);
        let radius = particles[i].size.z;
        
        if (dist < radius) {
            let grad = sdf_gradient(new_pos, 0.01);
            let grad_len = length(grad);
            if (grad_len > 1e-6) {
                let n = normalize(grad);
                new_pos += n * (radius - dist);
                
                let v_dot_n = dot(vel, n);
                if (v_dot_n < 0.0) {
                    vel -= n * (1.0 + 0.3) * v_dot_n;
                }
            }
        }
    }
    
    // Ribbon/Trail
    if ((uniforms.flags_ribbon & 1u) != 0u && (particles[i].flags & 2u) != 0u) {
        particles[i].prev_position = particles[i].position;
        particles[i].ribbon_length += length(new_pos - particles[i].position);
    }
    
    // Rotation
    particles[i].rotation.z += particles[i].rotation.y * uniforms.dt;
    
    // Size interpolation
    particles[i].size.z = mix(particles[i].size.x, particles[i].size.y, life_ratio);
    
    // Alpha fade
    particles[i].color.w *= (1.0 - life_ratio);
    
    // Commit
    particles[i].position = new_pos;
    particles[i].velocity = vel;
}