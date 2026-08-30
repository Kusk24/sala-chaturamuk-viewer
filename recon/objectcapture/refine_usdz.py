"""Geometric refinement of the polished mesh -- the "make it smooth" pass.

Runs after polish_usdz.py. Three documented, cosmetic operations on the
reconstruction's geometry (texture untouched, so no photographic detail lost):

1. Spike removal. Photogrammetry bridges gaps with long thin slivers that
   read as spikes/torn edges. Faces with a corner angle under MIN_ANGLE
   degrees are dropped. Edge LENGTH is deliberately not a criterion: the
   flat terrace is legitimately built from large triangles, and a length
   rule punches holes straight through it (tested).
2. Hole closing (MeshLab). Small pinholes -- up to MAX_HOLE boundary edges,
   so the terrain sheet's outer boundary is never touched -- are filled.
   New faces borrow the UV corners of their nearest original face, so they
   take on the colour of the surface around them.
3. Taubin smoothing (MeshLab). TAUBIN_STEPS shape-preserving smoothing steps
   (lambda/mu) over every vertex: crumples and reconstruction noise relax,
   volume is preserved, texture detail rides along on the same UVs.

Normals are recomputed smooth at the end.

  python3 refine_usdz.py <in.usdz> <out.usdz> [taubin-steps]
"""
import sys, os, zipfile, shutil, tempfile
import numpy as np
import pymeshlab
from scipy.spatial import cKDTree
from pxr import Usd, UsdGeom, UsdUtils, Sdf, Vt

src, dst = sys.argv[1], sys.argv[2]
TAUBIN_STEPS = int(sys.argv[3]) if len(sys.argv) > 3 else 30
MIN_ANGLE, MAX_HOLE = 2.0, 40

work = tempfile.mkdtemp()
with zipfile.ZipFile(src) as z:
    z.extractall(work)
usdc = [os.path.join(r, f) for r, _, fs in os.walk(work) for f in fs if f.endswith('.usdc')][0]
stage = Usd.Stage.Open(usdc)
mesh = next(p for p in stage.Traverse() if p.IsA(UsdGeom.Mesh))
m = UsdGeom.Mesh(mesh)
P = np.array(m.GetPointsAttr().Get(), dtype=np.float64)
F = np.array(m.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
api = UsdGeom.PrimvarsAPI(mesh)
print(f'faces {len(F):,}   verts {len(P):,}')

# --- 1. spike removal ----------------------------------------------------------
tri = P[F]
e = np.stack([np.linalg.norm(tri[:, 1] - tri[:, 0], axis=1),
              np.linalg.norm(tri[:, 2] - tri[:, 1], axis=1),
              np.linalg.norm(tri[:, 0] - tri[:, 2], axis=1)], 1)
med = np.median(e)
def angle(a, b, c):
    u, v = b - a, c - a
    cosang = (u * v).sum(1) / (np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1) + 1e-12)
    return np.degrees(np.arccos(np.clip(cosang, -1, 1)))
amin = np.minimum.reduce([angle(tri[:, 0], tri[:, 1], tri[:, 2]),
                          angle(tri[:, 1], tri[:, 2], tri[:, 0]),
                          angle(tri[:, 2], tri[:, 0], tri[:, 1])])
spike = amin < MIN_ANGLE
keep = np.where(~spike)[0]
print(f'spike removal: dropping {spike.sum():,} sliver faces (median edge {med:.4f})')
F1 = F[keep]

# --- 2 + 3. MeshLab: close small holes, Taubin smooth ---------------------------
ms = pymeshlab.MeshSet()
ms.add_mesh(pymeshlab.Mesh(vertex_matrix=P, face_matrix=F1.astype(np.int32)))
n0 = ms.current_mesh().face_number()
try:
    ms.meshing_close_holes(maxholesize=MAX_HOLE, newfaceselected=False, selfintersection=True)
    print(f'hole closing: +{ms.current_mesh().face_number() - n0:,} faces')
except Exception as ex:
    print('hole closing skipped:', str(ex)[:120])
ms.apply_coord_taubin_smoothing(lambda_=0.5, mu=-0.53, stepsmoothnum=TAUBIN_STEPS)
print(f'taubin smoothing: {TAUBIN_STEPS} steps')
cm = ms.current_mesh()
P2 = cm.vertex_matrix()
F2 = cm.face_matrix()
assert len(P2) == len(P), 'vertex count changed -- UV mapping would break'

# --- map every output face back to an original face for its UV corners ---------
key = {tuple(sorted(f)): i for i, f in zip(keep, F1)}
src_face = np.empty(len(F2), int)
corner_perm = np.empty((len(F2), 3), int)       # which original corner each new corner is
newf = []
for j, f in enumerate(F2):
    i = key.get(tuple(sorted(f)))
    if i is None:
        newf.append(j); continue
    src_face[j] = i
    orig = F[i]
    corner_perm[j] = [int(np.where(orig == v)[0][0]) for v in f]
newf = np.array(newf, int)
if len(newf):
    ctree = cKDTree(P[F1].mean(1))
    _, nn = ctree.query(P2[F2[newf]].mean(1))
    src_face[newf] = keep[nn]
    corner_perm[newf] = [0, 1, 2]
print(f'output faces {len(F2):,}  ({len(newf):,} new hole-fill faces borrowing neighbour UVs)')

# --- write back ------------------------------------------------------------------
m.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(P2.astype(np.float32)))
m.GetFaceVertexIndicesAttr().Set(Vt.IntArray(F2.ravel().tolist()))
m.GetFaceVertexCountsAttr().Set(Vt.IntArray([3] * len(F2)))
gather = src_face[:, None] * 3 + corner_perm       # (F2,3) -> original corner slots
for pv in api.GetPrimvars():
    if pv.GetInterpolation() != UsdGeom.Tokens.faceVarying:
        continue
    if pv.IsIndexed():
        pidx = np.array(pv.GetIndices())
        pv.SetIndices(Vt.IntArray(pidx[gather.ravel()].tolist()))
    else:
        vals = np.array(pv.Get())
        pv.GetAttr().Set(type(pv.Get())(vals[gather.ravel()].tolist()))
fn = np.cross(P2[F2[:, 1]] - P2[F2[:, 0]], P2[F2[:, 2]] - P2[F2[:, 0]])
vn = np.zeros_like(P2)
for k in range(3):
    np.add.at(vn, F2[:, k], fn)
vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-12
na = m.GetNormalsAttr()
if na.Get() is not None:
    m.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)
    na.Set(Vt.Vec3fArray.FromNumpy(vn[F2.ravel()].astype(np.float32)))
stage.Save()
if os.path.exists(dst):
    os.remove(dst)
ok = UsdUtils.CreateNewUsdzPackage(Sdf.AssetPath(usdc), dst)
print('wrote' if ok else 'FAILED', dst)
shutil.rmtree(work)
sys.exit(0 if ok else 1)
