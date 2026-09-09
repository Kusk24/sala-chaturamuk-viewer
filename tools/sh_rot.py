"""Rotate a 3DGS model so its true vertical becomes +Y, including the spherical
harmonics. Positions and quaternions are easy; the SH need a per-band rotation
matrix or view-dependent shading ends up pointing the wrong way.

The band matrices are recovered numerically by least squares against 3DGS's own
SH basis, so the convention is guaranteed to match sh_utils.eval_sh rather than
a re-derivation of it."""
import numpy as np

C0 = 0.28209479177387814
C1 = 0.4886025119029199
C2 = [1.0925484305920792, -1.0925484305920792, 0.31539156525252005,
      -1.0925484305920792, 0.5462742152960396]
C3 = [-0.5900435899266435, 2.890611442640554, -0.4570457994644658,
      0.3731763325901154, -0.4570457994644658, 1.445305721320277,
      -0.5900435899266435]

def sh_basis(d):
    """Bands 1..3 of 3DGS's real SH basis, in its storage order. (S,3) -> (S,15)"""
    x, y, z = d[:, 0], d[:, 1], d[:, 2]
    xx, yy, zz = x*x, y*y, z*z
    xy, yz, xz = x*y, y*z, x*z
    return np.stack([
        -C1*y, C1*z, -C1*x,
        C2[0]*xy, C2[1]*yz, C2[2]*(2*zz-xx-yy), C2[3]*xz, C2[4]*(xx-yy),
        C3[0]*y*(3*xx-yy), C3[1]*xy*z, C3[2]*y*(4*zz-xx-yy),
        C3[3]*z*(2*zz-3*xx-3*yy), C3[4]*x*(4*zz-xx-yy),
        C3[5]*z*(xx-yy), C3[6]*x*(xx-3*yy)], axis=1)

BANDS = [(0, 3), (3, 8), (8, 15)]

def sh_rotation_matrices(R, n=4000, seed=0):
    """M[b] maps old coefficients to new ones so that colour(d) after rotation
    equals colour(R^-1 d) before it."""
    rng = np.random.default_rng(seed)
    d = rng.normal(size=(n, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
    A = sh_basis(d)
    B = sh_basis(d @ R)                  # d @ R == (R^T d) == R^-1 d for orthonormal R
    out = []
    for lo, hi in BANDS:
        M, *_ = np.linalg.lstsq(A[:, lo:hi], B[:, lo:hi], rcond=None)
        out.append(M)
    return out

def verify(R, tol=1e-6, n=500, seed=1):
    Ms = sh_rotation_matrices(R)
    rng = np.random.default_rng(seed)
    d = rng.normal(size=(n, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
    c = rng.normal(size=15)
    cnew = c.copy()
    for (lo, hi), M in zip(BANDS, Ms):
        cnew[lo:hi] = M @ c[lo:hi]
    lhs = sh_basis(d) @ cnew             # colour seen at d after rotating
    rhs = sh_basis(d @ R) @ c            # colour that direction had before
    err = np.abs(lhs - rhs).max()
    return err, err < tol

def quat_mul(q1, q2):
    """(w,x,y,z) Hamilton product, broadcasting q1 over q2."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2.T
    return np.stack([
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2], axis=1)

def mat_to_quat(R):
    t = np.trace(R)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2
        return np.array([0.25*s, (R[2,1]-R[1,2])/s, (R[0,2]-R[2,0])/s, (R[1,0]-R[0,1])/s])
    i = int(np.argmax(np.diag(R)))
    if i == 0:
        s = np.sqrt(1.0 + R[0,0] - R[1,1] - R[2,2]) * 2
        return np.array([(R[2,1]-R[1,2])/s, 0.25*s, (R[0,1]+R[1,0])/s, (R[0,2]+R[2,0])/s])
    if i == 1:
        s = np.sqrt(1.0 + R[1,1] - R[0,0] - R[2,2]) * 2
        return np.array([(R[0,2]-R[2,0])/s, (R[0,1]+R[1,0])/s, 0.25*s, (R[1,2]+R[2,1])/s])
    s = np.sqrt(1.0 + R[2,2] - R[0,0] - R[1,1]) * 2
    return np.array([(R[1,0]-R[0,1])/s, (R[0,2]+R[2,0])/s, (R[1,2]+R[2,1])/s, 0.25*s])
