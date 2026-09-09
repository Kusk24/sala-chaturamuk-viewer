"""Apply exactly the September cleanup to the August version2 model so the two
can be compared fairly: crop about true vertical, upright with SH rotation,
drop oversized floaters. Same parameters as sala (0.55 / 1.5 / size<0.15)."""
import json, os, sys, numpy as np
from plyfile import PlyData, PlyElement
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sh_rot
from make_upright import align, to_splat

SRC = '/Users/kusk/Desktop/Computer Vision/Term-Project/sala/output/output/sala_v2'
OUT = '/Users/kusk/Desktop/Computer Vision/Term-Project/sala'
cams = json.load(open(f'{SRC}/cameras.json'))
Rc = np.array([c['rotation'] for c in cams]); P = np.array([c['position'] for c in cams])
up = -Rc[:, :, 1].mean(0); up /= np.linalg.norm(up)
agree = np.abs((-Rc[:, :, 1]) @ up).mean()
centre = np.median(P, axis=0); ring = np.median(np.linalg.norm(P - centre, axis=1))
tilt = np.degrees(np.arccos(abs(up @ np.array([0, 1., 0]))))

d = PlyData.read(f'{OUT}/sala_v2_15000.ply')['vertex'].data.copy()
xyz = np.stack([d['x'], d['y'], d['z']], 1).astype(np.float64)
n0 = len(xyz)

# 1. crop about the TRUE vertical
rel = xyz - centre; h = rel @ up; rad = np.linalg.norm(rel - np.outer(h, up), axis=1)
keep = (rad < 0.55 * ring) & (np.abs(h) < 1.5 * ring)
d = d[keep]; xyz = xyz[keep]; n1 = len(d)

# 2. upright: positions, quaternions, spherical harmonics
R = align(up, np.array([0, -1., 0]))
err, ok = sh_rot.verify(R); assert ok
new = (xyz - centre) @ R.T
d['x'], d['y'], d['z'] = new[:, 0], new[:, 1], new[:, 2]
q = np.stack([d[f'rot_{i}'] for i in range(4)], 1).astype(np.float64)
q /= np.linalg.norm(q, axis=1, keepdims=True)
qn = sh_rot.quat_mul(sh_rot.mat_to_quat(R), q)
for i in range(4): d[f'rot_{i}'] = qn[:, i]
rest = np.stack([d[f'f_rest_{i}'] for i in range(45)], 1).astype(np.float64).reshape(-1, 3, 15)
for (lo, hi), M in zip(sh_rot.BANDS, sh_rot.sh_rotation_matrices(R)):
    rest[:, :, lo:hi] = rest[:, :, lo:hi] @ M.T
rest = rest.reshape(-1, 45)
for i in range(45): d[f'f_rest_{i}'] = rest[:, i]

# 3. floater filter
sc = np.exp(np.stack([d['scale_0'], d['scale_1'], d['scale_2']], 1))
small = sc.max(1) < 0.15
vol_all = (4/3*np.pi*sc.prod(1)).sum(); vol_keep = (4/3*np.pi*sc[small].prod(1)).sum()
d = d[small]; n2 = len(d)

PlyData([PlyElement.describe(d, 'vertex')]).write(f'{OUT}/sala_v2_final.ply')
to_splat(d, f'{OUT}/sala_v2_final.splat')
print(f'August v2:  up agreement {agree:.3f}   tilt {tilt:.1f} deg   ring {ring:.2f}')
print(f'   raw {n0:,}  ->  crop {n1:,} ({n1/n0*100:.1f}%)  ->  filter {n2:,}')
print(f'   floaters removed: {n1-n2:,} gaussians holding {(1-vol_keep/vol_all)*100:.0f}% of the cropped volume')
print(f'   -> sala_v2_final.ply  {os.path.getsize(OUT+"/sala_v2_final.ply")/1e6:.1f} MB')
