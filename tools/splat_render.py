"""CPU EWA splat rasteriser for the .splat rows the viewer publishes.
Enough of Kerbl et al.'s forward pass to make honest figures: 3D covariance from
quaternion+scale, projected through the perspective Jacobian, alpha-composited
back to front. No GPU, no 3DGS install."""
import numpy as np

ROW = 32

def load(path):
    raw = np.fromfile(path, dtype=np.uint8).reshape(-1, ROW)
    xyz   = raw[:, 0:12].copy().view(np.float32).reshape(-1, 3)
    scale = raw[:, 12:24].copy().view(np.float32).reshape(-1, 3)
    rgba  = raw[:, 24:28].astype(np.float32)
    quat  = (raw[:, 28:32].astype(np.float32) - 128.0) / 128.0
    return xyz, scale, rgba[:, :3], rgba[:, 3] / 255.0, quat

def quat_mats(q):
    # the viewer stores (w, x, y, z) scaled into a byte each
    n = np.linalg.norm(q, axis=1, keepdims=True); n[n == 0] = 1
    w, x, y, z = (q / n).T
    return np.stack([
        1-2*(y*y+z*z), 2*(x*y-w*z),   2*(x*z+w*y),
        2*(x*y+w*z),   1-2*(x*x+z*z), 2*(y*z-w*x),
        2*(x*z-w*y),   2*(y*z+w*x),   1-2*(x*x+y*y)], axis=1).reshape(-1, 3, 3)

def render(path, view, W=1400, H=1000, fov_scale=1.0, bg=(0, 0, 0), max_r=48):
    xyz, scale, rgb, opa, quat = load(path)
    V = np.asarray(view, dtype=np.float64).reshape(4, 4).T     # column-major in
    P = (np.c_[xyz, np.ones(len(xyz))] @ V.T)[:, :3]
    f = 0.5 * W / np.tan(np.radians(55.0) / 2) * fov_scale
    keep = P[:, 2] > 0.15
    P, scale, rgb, opa, quat = P[keep], scale[keep], rgb[keep], opa[keep], quat[keep]

    R = quat_mats(quat)
    M = R * scale[:, None, :]                                   # R @ diag(s)
    S3 = M @ np.transpose(M, (0, 2, 1))                         # 3D covariance
    Rv = V[:3, :3]
    Sc = Rv @ S3 @ Rv.T                                         # into camera space

    tx, ty, tz = P.T
    J = np.zeros((len(P), 2, 3))
    J[:, 0, 0] = f / tz; J[:, 0, 2] = -f * tx / tz**2
    J[:, 1, 1] = f / tz; J[:, 1, 2] = -f * ty / tz**2
    S2 = J @ Sc @ np.transpose(J, (0, 2, 1))
    S2[:, 0, 0] += 0.3; S2[:, 1, 1] += 0.3                      # antialiasing floor

    det = S2[:, 0, 0]*S2[:, 1, 1] - S2[:, 0, 1]**2
    ok = det > 1e-9
    idx = np.where(ok)[0]
    inv = np.empty((len(idx), 3))                               # (a, b, c) of the inverse
    d = det[idx]
    inv[:, 0] =  S2[idx, 1, 1] / d
    inv[:, 1] = -S2[idx, 0, 1] / d
    inv[:, 2] =  S2[idx, 0, 0] / d
    rad = np.ceil(3.0 * np.sqrt(np.maximum(S2[idx, 0, 0], S2[idx, 1, 1]))).astype(int)
    rad = np.clip(rad, 1, max_r)
    u = (f * P[idx, 0] / P[idx, 2] + W / 2)
    v = (f * P[idx, 1] / P[idx, 2] + H / 2)

    order = np.argsort(-P[idx, 2])                              # far to near
    img = np.tile(np.array(bg, np.float32), (H, W, 1))
    for k in order:
        r = rad[k]; cu, cv = u[k], v[k]
        x0, x1 = int(cu - r), int(cu + r) + 1
        y0, y1 = int(cv - r), int(cv + r) + 1
        if x1 <= 0 or y1 <= 0 or x0 >= W or y0 >= H: continue
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, W), min(y1, H)
        gx = np.arange(x0, x1) - cu; gy = np.arange(y0, y1) - cv
        dx = gx[None, :]; dy = gy[:, None]
        a, b, c = inv[k]
        p = -0.5 * (a * dx * dx + 2 * b * dx * dy + c * dy * dy)
        al = opa[idx[k]] * np.exp(np.clip(p, -12, 0))
        al = al[..., None]
        img[y0:y1, x0:x1] = img[y0:y1, x0:x1] * (1 - al) + rgb[idx[k]] * al
    return np.clip(img, 0, 255).astype(np.uint8)

def look_at(eye, target, up=(0, -1, 0)):
    eye = np.asarray(eye, float); target = np.asarray(target, float)
    fwd = target - eye; fwd /= np.linalg.norm(fwd)
    up = np.asarray(up, float)
    right = np.cross(fwd, up)
    if np.linalg.norm(right) < 1e-6: right = np.cross(fwd, [0, 0, 1.0])
    right /= np.linalg.norm(right)
    trueup = np.cross(right, fwd)
    # the projection below treats camera +Y as image-DOWN, so the camera's
    # local Y must be -up, not up, or the render comes out vertically mirrored
    Rm = np.stack([right, -trueup, fwd])                         # world -> camera
    t = -Rm @ eye
    M = np.eye(4); M[:3, :3] = Rm; M[:3, 3] = t
    return M.T.reshape(-1)                                       # column-major out
