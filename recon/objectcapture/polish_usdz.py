"""Presentation polish for the masked photogrammetry mesh.

Two documented post-processing steps, both cosmetic and both reported in the
paper as such (the reconstruction itself is untouched):

1. Roof repair. Faces the capture never saw from above (single-height ring)
   came out sky-white. Above y=1.45 the white faces are free-hanging flaps
   suspended over the building (they outnumber real geometry there) and are
   deleted; white faces on the roof itself are inpainted from surrounding
   texture (cv2, Telea). A radius guard keeps the white balustrade lanterns
   (low, far out) untouched.
2. Ground trim. The terrain sheet's ragged outer fringe is cut to a clean
   edge: low faces beyond a tighter radius are dropped, same face-filtering
   machinery as crop_usdz.py.

  python3 polish_usdz.py <in.usdz> <out.usdz> [ground-radius]
"""
import sys, os, zipfile, shutil, tempfile
import numpy as np, cv2
from pxr import Usd, UsdGeom, UsdUtils, Sdf, Vt

src, dst = sys.argv[1], sys.argv[2]
GROUND_R = float(sys.argv[3]) if len(sys.argv) > 3 else 1.55
GROUND_Y = 0.30          # below this height, the tighter radius applies
FLAP_Y = 1.45            # white above this height: delete (hanging flaps)
WHITE_LUM, WHITE_SAT = 0.55, 0.30

work = tempfile.mkdtemp()
with zipfile.ZipFile(src) as z:
    z.extractall(work)
usdc = [os.path.join(r, f) for r, _, fs in os.walk(work) for f in fs if f.endswith('.usdc')][0]
stage = Usd.Stage.Open(usdc)
mesh = next(p for p in stage.Traverse() if p.IsA(UsdGeom.Mesh))
m = UsdGeom.Mesh(mesh)
pts = np.array(m.GetPointsAttr().Get())
faces = np.array(m.GetFaceVertexIndicesAttr().Get()).reshape(-1, 3)
tri = pts[faces]
cent = tri.mean(1)
nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9

api = UsdGeom.PrimvarsAPI(mesh)
st = api.GetPrimvar('st')
uv_vals = np.array(st.Get())
uv_idx = np.array(st.GetIndices()).reshape(-1, 3)      # per-corner, per-face

tex_path = [os.path.join(r, f) for r, _, fs in os.walk(work) for f in fs if f.endswith('_tex0.png')][0]
tex = cv2.imread(tex_path)
H, W = tex.shape[:2]
print(f'faces {len(faces):,}   texture {W}x{H}')

def px(uv):
    """st (origin bottom-left) -> pixel coords."""
    x = np.clip((uv[..., 0] * (W - 1)).astype(int), 0, W - 1)
    y = np.clip(((1 - uv[..., 1]) * (H - 1)).astype(int), 0, H - 1)
    return x, y

# --- classify white sky-cap faces: sample corners + centroid ------------------
uv_c = uv_vals[uv_idx]                                  # (F,3,2)
samples = np.concatenate([uv_c, uv_c.mean(1, keepdims=True)], 1)  # (F,4,2)
sx, sy = px(samples)
cols = tex[sy, sx].astype(np.float32) / 255             # BGR, (F,4,3)
colf = np.median(cols, axis=1)
lum = colf.mean(1)
sat = colf.max(1) - colf.min(1)
white = (lum > WHITE_LUM) & (sat < WHITE_SAT)
cx, cz = np.median(cent[:, 0]), np.median(cent[:, 2])
r = np.hypot(cent[:, 0] - cx, cent[:, 2] - cz)
y = cent[:, 1]
# The 0.45-0.7 band holds the white balustrade lanterns at large radius --
# only central white there is roof valley; above 0.7 it is all roof.
paint = white & (((y > 0.45) & (y <= 0.7) & (r < 1.1)) | ((y > 0.7) & (y <= FLAP_Y)))
flap = white & (y > FLAP_Y)
print(f'white roof faces to inpaint: {paint.sum():,}   flaps to delete: {flap.sum():,}')

# --- inpaint their UV triangles ----------------------------------------------
mask = np.zeros((H, W), np.uint8)
tx, ty = px(uv_c[paint])                                # (Nw,3) each
for k in range(int(paint.sum())):
    cv2.fillPoly(mask, [np.stack([tx[k], ty[k]], 1)], 255)
mask = cv2.dilate(mask, np.ones((9, 9), np.uint8))
print(f'inpainting {mask.astype(bool).mean()*100:.2f}% of the texture')
tex = cv2.inpaint(tex, mask, 11, cv2.INPAINT_TELEA)
cv2.imwrite(tex_path, tex)

# --- trim ragged ground fringe, drop hanging flaps ----------------------------
low = cent[:, 1] < GROUND_Y
drop = (low & (r > GROUND_R)) | flap
keep = ~drop
print(f'dropping {drop.sum():,} faces (ground fringe + flaps), keep {keep.sum():,}')
m.GetFaceVertexCountsAttr().Set(Vt.IntArray([3] * int(keep.sum())))
m.GetFaceVertexIndicesAttr().Set(Vt.IntArray(faces[keep].ravel().tolist()))
corner_keep = np.repeat(keep, 3)
for pv in api.GetPrimvars():
    if pv.GetInterpolation() != UsdGeom.Tokens.faceVarying:
        continue
    if pv.IsIndexed():
        pidx = np.array(pv.GetIndices())
        pv.SetIndices(Vt.IntArray(pidx[corner_keep].tolist()))
    else:
        vals = np.array(pv.Get())
        pv.GetAttr().Set(type(pv.Get())(vals[corner_keep].tolist()))
na = m.GetNormalsAttr()
if na.Get() is not None and m.GetNormalsInterpolation() == UsdGeom.Tokens.faceVarying:
    nv = np.array(na.Get())
    if len(nv) == len(corner_keep):
        na.Set(Vt.Vec3fArray.FromNumpy(nv[corner_keep]))

# --- drop crumbs orphaned by the deletions ------------------------------------
# Before any faces were removed the mesh was one welded component, so a
# topological pass did nothing. After the flap/fringe cuts, leftover shreds
# are genuinely disconnected and can finally be swept up.
kept_faces = faces[keep]
parent = np.arange(len(pts))
def find(a):
    root = a
    while parent[root] != root: root = parent[root]
    while parent[a] != root: parent[a], a = root, parent[a]
    return root
for f in kept_faces:
    a, b, c = find(f[0]), find(f[1]), find(f[2])
    parent[a] = parent[b] = c
roots = np.array([find(f[0]) for f in kept_faces])
uniq, counts = np.unique(roots, return_counts=True)
big = set(uniq[counts >= counts.max() * 0.01])
solid = np.array([r in big for r in roots])
print(f'component sweep: {len(uniq)} components, dropping {(~solid).sum():,} crumb faces')
kept_faces = kept_faces[solid]
m.GetFaceVertexCountsAttr().Set(Vt.IntArray([3] * len(kept_faces)))
m.GetFaceVertexIndicesAttr().Set(Vt.IntArray(kept_faces.ravel().tolist()))
ck2 = np.repeat(solid, 3)
for pv in api.GetPrimvars():
    if pv.GetInterpolation() != UsdGeom.Tokens.faceVarying:
        continue
    if pv.IsIndexed():
        pidx = np.array(pv.GetIndices())
        pv.SetIndices(Vt.IntArray(pidx[ck2].tolist()))
    else:
        vals = np.array(pv.Get())
        pv.GetAttr().Set(type(pv.Get())(vals[ck2].tolist()))
na2 = m.GetNormalsAttr()
if na2.Get() is not None and m.GetNormalsInterpolation() == UsdGeom.Tokens.faceVarying:
    nv2 = np.array(na2.Get())
    if len(nv2) == len(ck2):
        na2.Set(Vt.Vec3fArray.FromNumpy(nv2[ck2]))

stage.Save()
if os.path.exists(dst):
    os.remove(dst)
ok = UsdUtils.CreateNewUsdzPackage(Sdf.AssetPath(usdc), dst)
print('wrote' if ok else 'FAILED', dst)
shutil.rmtree(work)
sys.exit(0 if ok else 1)
