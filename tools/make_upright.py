"""Write an upright copy of a cropped model: true vertical -> -Y, which is what a
normal, level 3DGS capture looks like, so any viewer treats it the way it treats
every other 3DGS file. Positions, quaternions AND spherical harmonics rotated."""
import json, os, numpy as np
from plyfile import PlyData, PlyElement
import sh_rot

K = '/Users/kusk/Desktop/Computer Vision/Term-Project/kaggle_out'
SH_C0 = 0.28209479177387814

def align(a, b):
    a = a/np.linalg.norm(a); b = b/np.linalg.norm(b)
    v = np.cross(a, b); c = a @ b
    if np.linalg.norm(v) < 1e-9: return np.eye(3) * (1 if c > 0 else -1)
    Kx = np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
    return np.eye(3) + Kx + Kx @ Kx * (1/(1+c))

def to_splat(v, dst):
    xyz = np.stack([v['x'],v['y'],v['z']],1).astype(np.float32)
    sc  = np.exp(np.stack([v['scale_0'],v['scale_1'],v['scale_2']],1)).astype(np.float32)
    rt  = np.stack([v['rot_0'],v['rot_1'],v['rot_2'],v['rot_3']],1).astype(np.float32)
    rt /= np.linalg.norm(rt,axis=1,keepdims=True)
    rgb = 0.5 + SH_C0*np.stack([v['f_dc_0'],v['f_dc_1'],v['f_dc_2']],1)
    al  = 1/(1+np.exp(-np.asarray(v['opacity'],dtype=np.float64)))
    o   = np.argsort(-(sc.astype(np.float64).prod(1)*al))
    n = len(o); buf = np.zeros((n,32),np.uint8)
    buf[:, 0:12] = xyz[o].view(np.uint8).reshape(n,12)
    buf[:,12:24] = sc[o].view(np.uint8).reshape(n,12)
    buf[:,24:27] = np.clip(rgb[o]*255,0,255).astype(np.uint8)
    buf[:,27:28] = np.clip(al[o,None]*255,0,255).astype(np.uint8)
    buf[:,28:32] = np.clip(rt[o]*128+128,0,255).astype(np.uint8)
    buf.tofile(dst); return n

def upright(sub, src_ply):
    cams = json.load(open(f'{K}/{sub}/out_{sub}/cameras.json'))
    Rc = np.array([c['rotation'] for c in cams]); P = np.array([c['position'] for c in cams])
    up = -Rc[:,:,1].mean(0); up /= np.linalg.norm(up)
    R = align(up, np.array([0,-1.0,0]))
    err, ok = sh_rot.verify(R)
    assert ok, f'SH rotation failed verification ({err:.2e})'

    data = PlyData.read(src_ply)['vertex'].data.copy()
    centre = np.median(P, axis=0)
    xyz = np.stack([data['x'],data['y'],data['z']],1).astype(np.float64)
    new = (xyz - centre) @ R.T
    data['x'], data['y'], data['z'] = new[:,0], new[:,1], new[:,2]

    q = np.stack([data['rot_0'],data['rot_1'],data['rot_2'],data['rot_3']],1).astype(np.float64)
    q /= np.linalg.norm(q, axis=1, keepdims=True)
    qn = sh_rot.quat_mul(sh_rot.mat_to_quat(R), q)
    for i in range(4): data[f'rot_{i}'] = qn[:,i]

    Ms = sh_rot.sh_rotation_matrices(R)
    rest = np.stack([data[f'f_rest_{i}'] for i in range(45)],1).astype(np.float64).reshape(-1,3,15)
    for (lo,hi), M in zip(sh_rot.BANDS, Ms):
        rest[:,:,lo:hi] = rest[:,:,lo:hi] @ M.T
    rest = rest.reshape(-1,45)
    for i in range(45): data[f'f_rest_{i}'] = rest[:,i]

    out = f'{K}/{sub}/out_{sub}/{sub}_upright.ply'
    PlyData([PlyElement.describe(data,'vertex')]).write(out)
    n = to_splat(data, f'{K}/{sub}/out_{sub}/{sub}_upright.splat')
    # sanity: the model's own vertical extent should now run along Y
    h = new @ np.array([0,-1.0,0])
    print(f'{sub}: rotated {np.degrees(np.arccos(np.clip(up@np.array([0,-1.,0]),-1,1))):.1f} deg   '
          f'SH check {err:.1e}   {n:,} gaussians')
    print(f'   -> {os.path.basename(out)}  {os.path.getsize(out)/1e6:.1f} MB   '
          f'height along -Y now {h.min():.2f} .. {h.max():.2f}')

upright('lamp', f'{K}/lamp/out_lamp/lamp_cropped_v2.ply')
upright('sala', f'{K}/sala/out_sala/sala_cropped_v2.ply')
