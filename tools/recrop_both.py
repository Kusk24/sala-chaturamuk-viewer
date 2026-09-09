"""Re-crop both models about the TRUE vertical (mean of the cameras' own up axes)
instead of COLMAP's arbitrary y-axis. Writes a PLY (for SuperSplat, keeps the
spherical harmonics) and a .splat (for the web viewer), matching the notebook's
export conventions exactly."""
import json, os, numpy as np
from plyfile import PlyData, PlyElement

K   = '/Users/kusk/Desktop/Computer Vision/Term-Project/kaggle_out'
SH_C0 = 0.28209479177387814

def ply_to_splat(v, dst):
    xyz    = np.stack([v['x'], v['y'], v['z']], 1).astype(np.float32)
    scales = np.exp(np.stack([v['scale_0'], v['scale_1'], v['scale_2']], 1)).astype(np.float32)
    rot    = np.stack([v['rot_0'], v['rot_1'], v['rot_2'], v['rot_3']], 1).astype(np.float32)
    rot   /= np.linalg.norm(rot, axis=1, keepdims=True)
    rgb    = 0.5 + SH_C0 * np.stack([v['f_dc_0'], v['f_dc_1'], v['f_dc_2']], 1)
    alpha  = 1.0 / (1.0 + np.exp(-np.asarray(v['opacity'], dtype=np.float64)))
    order  = np.argsort(-(scales.astype(np.float64).prod(1) * alpha))
    n = len(order); buf = np.zeros((n, 32), dtype=np.uint8)
    buf[:,  0:12] = xyz[order].view(np.uint8).reshape(n, 12)
    buf[:, 12:24] = scales[order].view(np.uint8).reshape(n, 12)
    buf[:, 24:27] = np.clip(rgb[order] * 255, 0, 255).astype(np.uint8)
    buf[:, 27:28] = np.clip(alpha[order, None] * 255, 0, 255).astype(np.uint8)
    buf[:, 28:32] = np.clip(rot[order] * 128 + 128, 0, 255).astype(np.uint8)
    buf.tofile(dst); return n

def run(sub, src_ply, keep_r_mult, keep_h_mult):
    cams = json.load(open(f'{K}/{sub}/out_{sub}/cameras.json'))
    R = np.array([c['rotation'] for c in cams]); P = np.array([c['position'] for c in cams])
    up = -R[:, :, 1].mean(0); up /= np.linalg.norm(up)
    centre = np.median(P, axis=0); ring = np.median(np.linalg.norm(P - centre, axis=1))

    v = PlyData.read(src_ply)['vertex']
    xyz = np.stack([v['x'], v['y'], v['z']], 1).astype(np.float64)
    d = xyz - centre
    h = d @ up
    rad = np.linalg.norm(d - np.outer(h, up), axis=1)
    KR, KH = keep_r_mult * ring, keep_h_mult * ring
    keep = (rad < KR) & (np.abs(h) < KH)

    out_dir = f'{K}/{sub}/out_{sub}'
    ply_out = f'{out_dir}/{sub}_cropped_v2.ply'
    PlyData([PlyElement.describe(v.data[keep], 'vertex')]).write(ply_out)
    n = ply_to_splat(v.data[keep], f'{out_dir}/{sub}_cropped_v2.splat')
    print(f'{sub}: ring {ring:.2f}  KEEP_R {KR:.2f}  KEEP_H {KH:.2f}  '
          f'tilt of old crop {np.degrees(np.arccos(abs(up@np.array([0,1.,0])))):.1f} deg')
    print(f'   kept {keep.sum():,} of {len(xyz):,} ({keep.mean()*100:.1f}%)  '
          f'PLY {os.path.getsize(ply_out)/1e6:.1f} MB  splat {os.path.getsize(out_dir+f"/{sub}_cropped_v2.splat")/1e6:.1f} MB')
    return n

run('lamp', f'{K}/lamp/out_lamp/lamp_full.ply', 0.40, 0.60)
run('sala', f'{K}/sala/out_sala/model/point_cloud/iteration_30000/point_cloud.ply', 0.55, 0.45)
