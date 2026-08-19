// LPV (Light Propagation Volumes) Compute Shader
// WebGPU fallback for GI

struct LPVCell {
    flux: vec3<f32>,
    incoming: vec3<f32>,
    geometry: f32,
}

@group(0) @binding(0) var<storage, read_write> lpv_grid: array<LPVCell>;
@group(0) @binding(1) var<uniform> lpv_dims: vec3<u32>;
@group(0) @binding(2) var<uniform> lpv_world_bounds: vec4<f32>; // min_x, max_x, min_y, max_y (z in w)

@group(0) @binding(3) var<storage, read> rsm_depth: texture_2d<f32>;
@group(0) @binding(4) var<storage, read> rsm_normal: texture_2d<f32>;
@group(0) @binding(5) var<storage, read> rsm_flux: texture_2d<f32>;
@group(0) @binding(6) var<uniform> rsm_resolution: u32;
@group(0) @binding(7) var<uniform> light_vp: mat4x4<f32>; // Light view-projection

@group(0) @binding(8) var<uniform> params: LPVParams;
struct LPVParams {
    propagation_iterations: u32,
    injection_intensity: f32,
    cell_size: f32,
}

fn inject_rsm() {
    // Project RSM texels into LPV grid
    // This would be a separate compute pass
}

@compute @workgroup_size(8, 8, 8)
fn propagate(@builtin(global_invocation_id) idx: vec3<u32>) {
    let gx = lpv_dims.x;
    let gy = lpv_dims.y;
    let gz = lpv_dims.z;
    
    if (idx.x >= gx || idx.y >= gy || idx.z >= gz) { return; }
    
    let cell_idx = idx.z * gy * gx + idx.y * gx + idx.x;
    var cell = lpv_grid[cell_idx];
    
    // Propagate from 6 neighbors
    let dirs = array<vec3<i32>, 6>(
        vec3<i32>(1, 0, 0), vec3<i32>(-1, 0, 0),
        vec3<i32>(0, 1, 0), vec3<i32>(0, -1, 0),
        vec3<i32>(0, 0, 1), vec3<i32>(0, 0, -1)
    );
    
    var new_flux = cell.flux;
    var new_incoming = cell.incoming;
    
    for (var d = 0u; d < 6u; d++) {
        let neighbor_idx = vec3<i32>(idx) + dirs[d];
        
        if (all(neighbor_idx >= vec3<i32>(0)) && 
            all(neighbor_idx < vec3<i32>(lpv_dims))) {
            
            let n_idx = neighbor_idx.z * gy * gx + neighbor_idx.y * gx + neighbor_idx.x;
            let neighbor = lpv_grid[n_idx];
            
            let occlusion = 1.0 - cell.geometry;
            new_flux += neighbor.flux * occlusion * 0.25;
            new_incoming += neighbor.incoming * occlusion * 0.25;
        }
    }
    
    cell.flux = new_flux * params.injection_intensity;
    cell.incoming = new_incoming * params.injection_intensity;
    
    lpv_grid[cell_idx] = cell;
}

@compute @workgroup_size(8, 8, 8)
fn query_irradiance(
    @builtin(global_invocation_id) idx: vec3<u32>,
    @builtin(position) world_pos: vec3<f32>,
    @builtin(front_facing) is_front: bool,
    @builtin(frag_depth) depth: f32
) -> @location(0) vec3<f32> {
    // Trilinear interpolation of LPV incoming radiance
    let gx = lpv_dims.x;
    let gy = lpv_dims.y;
    let gz = lpv_dims.z;
    
    let min_x = lpv_world_bounds.x;
    let max_x = lpv_world_bounds.y;
    let min_y = lpv_world_bounds.z;
    let max_y = lpv_world_bounds.w;
    // min_z, max_z would be in another uniform
    
    let nx = (world_pos.x - min_x) / (max_x - min_x) * f32(gx - 1);
    let ny = (world_pos.y - min_y) / (max_y - min_y) * f32(gy - 1);
    // nz similar
    
    // Simplified - just return cell value
    let ix = min(u32(nx), gx - 1);
    let iy = min(u32(ny), gy - 1);
    let iz = min(u32(0), gz - 1); // Simplified
    
    let cell = lpv_grid[iz * gy * gx + iy * gx + ix];
    return cell.incoming;
}