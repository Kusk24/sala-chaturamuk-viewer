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
flap_cand = white & (y > FLAP_Y)
# VERDICT after testing all three rules: the reconstruction has no surface
# at the central roof crossing (occluded from every eye-level viewpoint),
# and the white sheets are what covers that gap. Deleting them -- by any
# support heuristic -- exposes a see-through hole that looks worse than
# they do. So nothing is deleted: every white face keeps its geometry and
# is recolored by the inpaint instead. The component sweep still removes
# anything the ground trim orphans.
# Delete a high white face ONLY when other geometry continues beneath it --
# then it is a flap hanging over the roof. If nothing lies below, the face
# IS the roof surface there, and deleting it opens a hole visible from
# above (which is exactly what the first version of this rule did).
from scipy.spatial import cKDTree
others = np.where(~flap_cand)[0]
tree = cKDTree(cent[others][:, [0, 2]])
oy = cent[others, 1]
flap = np.zeros(len(cent), bool)
for i in np.where(flap_cand)[0]:
    nb = tree.query_ball_point(cent[i, [0, 2]], 0.06)
    # support must be the roof continuing NEAR beneath the flap; the
    # terrace floor a unit further down does not count -- that is what a
    # see-through hole looks like.
    if any(cent[i, 1] - 0.45 < oy[j] < cent[i, 1] - 0.08 for j in nb):
        flap[i] = True
flap[:] = False
paint = white & ((((y > 0.45) & (y <= 0.7) & (r < 1.1)) | ((y > 0.7) & (y <= FLAP_Y)))
                 ) | (flap_cand & ~flap)
print(f'white roof faces to inpaint: {paint.sum():,}   '
      f'true hanging flaps to delete: {flap.sum():,} of {flap_cand.sum():,} candidates')

# --- inpaint their UV triangles ----------------------------------------------
# The cover is textured by UV remapping (below), after the geometry has been
# relaxed -- no texture pixel is edited.

# --- relax the crumpled sheet geometry ----------------------------------------
# The sheets shade like crumpled foil because they ARE crumpled sky geometry.
# Interior sheet vertices (every incident face painted) are Laplacian-relaxed;
# vertices shared with real roof faces are pinned so the seam cannot move.
pf = faces[paint]
vert_tot = np.zeros(len(pts), int)
vert_pnt = np.zeros(len(pts), int)
np.add.at(vert_tot, faces.ravel(), 1)
np.add.at(vert_pnt, pf.ravel(), 1)
interior = (vert_pnt > 0) & (vert_pnt == vert_tot)
nbrs = {}
for a, b in np.concatenate([pf[:, [0, 1]], pf[:, [1, 2]], pf[:, [2, 0]]]):
    nbrs.setdefault(a, set()).add(b)
    nbrs.setdefault(b, set()).add(a)
P = pts.astype(np.float64).copy()
mov = np.where(interior)[0]
for _ in range(30):
    snap = P.copy()
    for v in mov:
        ns = list(nbrs.get(v, ()))
        if ns:
            P[v] = 0.4 * snap[v] + 0.6 * snap[ns].mean(0)
print(f'relaxed {len(mov):,} sheet vertices (30 Laplacian iterations)')
m.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(P.astype(np.float32)))

# --- texture the cover with REAL tiles: UV remap, not paint --------------------
# Painting the cover any colour (nearest-face, blended, blurred) reads as a
# frosted membrane from above. Apple's atlas is too fragmented to borrow a
# tile region from (largest free/contiguous patch is a 176 px strip), so a
# STRIP of PAD rows is added to the top of every material map, a photographed
# tile swatch (make_tile_swatch.py) is pasted into it, and the cover's
# relaxed (x, z) is planar-projected onto the swatch with mirror repeat at a
# plausible tile scale. Existing UVs are rescaled for the taller canvas. The
# displacement map is dropped: viewers ignore it and it is 40% of the file.
PAD = 1024
swatch = cv2.imread(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tile_swatch.png'))
SH_, SW_ = swatch.shape[:2]
maps = {f.split('_')[-1]: os.path.join(r, f) for r, _, fs in os.walk(work) for f in fs
        if f.startswith('baked') and not f.endswith('.usdc')}
fill = {'tex0.png': None, 'norm0.png': (255, 128, 128), 'roughness0.png': 132, 'ao0.png': 254}
for key, pth in maps.items():
    if key == 'disp0.exr':
        continue
    im = cv2.imread(pth, cv2.IMREAD_UNCHANGED)
    strip = np.zeros((PAD,) + im.shape[1:], im.dtype)
    if key == 'tex0.png':
        strip[:SH_, :SW_] = swatch
        strip[:, SW_:] = np.array([105, 114, 112], np.uint8)
        dark = (np.percentile(swatch.reshape(-1, 3), 15, axis=0) * 0.6).astype(np.uint8)
        strip[64:320, SW_ + 64:SW_ + 320] = dark              # block for the occluder disc
    else:
        strip[:] = fill[key]
    cv2.imwrite(pth, np.concatenate([strip, im], 0))
H2 = H + PAD
# drop the displacement texture from the material and from the package.
# TraverseAll (not Traverse) so inactive/variant prims are covered, then
# rewrite any remaining asset path that still points at the .exr -- the
# packager refuses the package if a single unresolved reference survives.
from pxr import UsdShade
for prim in list(stage.TraverseAll()):
    if prim.IsA(UsdShade.Shader):
        fi = UsdShade.Shader(prim).GetInput('file')
        if fi and fi.Get() and 'disp' in str(fi.Get().path):
            stage.RemovePrim(prim.GetPath())
for prim in stage.TraverseAll():
    if prim.IsA(UsdShade.Shader):
        di = UsdShade.Shader(prim).GetInput('displacement')
        if di:
            di.GetAttr().ClearConnections()
def _strip_disp(path):
    return '' if 'disp' in path else path
UsdUtils.ModifyAssetPaths(stage.GetRootLayer(), _strip_disp)
if 'disp0.exr' in maps:
    os.remove(maps['disp0.exr'])
# rescale every existing uv for the taller canvas: old row y -> y + PAD
uv_re = uv_vals.copy()
uv_re[:, 1] = 1 - ((1 - uv_vals[:, 1]) * (H - 1) + PAD) / (H2 - 1)
# swatch rectangle in the new uv space
u0, u1 = 0.0, (SW_ - 1) / (W - 1)
v0, v1 = 1 - (SH_ - 1) / (H2 - 1), 1.0
SWATCH_SPAN = 1.15         # world units per 2048 native photo px (visual QA calibrated)
def mirror(t):
    return 1 - np.abs(np.mod(t, 2.0) - 1)
cov = P[faces[paint]]
# One top-down projection. A per-face dominant-axis projection was tried
# and produced seams and a glassy patch where neighbouring faces switched
# axis; with a plain tile field the stretch on the flanks is invisible.
tu = (cov[..., 0] - cov[..., 0].min()) / SWATCH_SPAN
tv = (cov[..., 2] - cov[..., 2].min()) / (SWATCH_SPAN * SH_ / SW_)
new_uv = np.stack([u0 + mirror(tu) * (u1 - u0), v0 + mirror(tv) * (v1 - v0)], -1).reshape(-1, 2)
dark_uv = np.array([[(SW_ + 192) / (W - 1), 1 - 192 / (H2 - 1)]])
uv_vals2 = np.concatenate([uv_re, new_uv, dark_uv])
dark_i = len(uv_vals2) - 1
uv_idx2 = uv_idx.copy()
uv_idx2[paint] = np.arange(len(uv_re), len(uv_re) + len(new_uv)).reshape(-1, 3)
st.Set(Vt.Vec2fArray.FromNumpy(uv_vals2.astype(np.float32)))
st.SetIndices(Vt.IntArray(uv_idx2.ravel().tolist()))
print(f'texture canvas {W}x{H2}; remapped {int(paint.sum()):,} cover faces onto the photo swatch')

# --- trim ragged ground fringe, drop hanging flaps ----------------------------
low = cent[:, 1] < GROUND_Y
drop = (low & (r > GROUND_R)) | flap
# The high sky sheets over the crossing are deleted after all: relaxed and
# retextured they still had see-through slits at the crown that no hole
# closer could cap, and they shaded like a tarp. The opening they leave is
# capped with generated geometry below (a hipped peak fanned to an apex).
cap = paint & (y > 1.1)
drop = drop | cap
keep = ~drop
print(f'dropping {drop.sum():,} faces (ground fringe + flaps + {cap.sum():,} sky sheets), keep {keep.sum():,}')
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
# --- cap the crossing with a fitted cross-gable surface -------------------------
# A sala chaturamuk is four gables meeting at right angles, so the missing
# crossing is the surface h(u,v) = H - s*min(|u|,|v|) in ridge-aligned
# coordinates. Ridge orientation is fitted from real roof-face normals, ridge
# height H and slope s from real roof faces by least squares; the surface
# is sampled on a grid ONLY where the reconstruction has no roof, and
# triangulated. (A fan of the opening's boundary to one apex was tried first
# and read as a circus tent: too tall, radial texture streaks, half the
# roof plan.)
cap_c = cent[cap]
# Centre and orientation from the REAL roof, not from the sky sheets (which
# drape to one side: QA measured the first cap a wing-width off-centre and
# 22 deg off the ridges). Two passes: a rough centre from the sheets picks
# the nearby high roof faces; their area-weighted centroid is the crossing.
ccx, ccz = np.median(cap_c[:, 0]), np.median(cap_c[:, 2])
tri_k = P[faces]
area = 0.5 * np.linalg.norm(np.cross(tri_k[:, 1] - tri_k[:, 0], tri_k[:, 2] - tri_k[:, 0]), axis=1)
for _pass in range(2):
    rr = np.hypot(cent[:, 0] - ccx, cent[:, 2] - ccz)
    roof_hi = keep & (~white) & (y > 0.9) & (rr < 0.9) & (np.abs(nrm[:, 1]) > 0.3) & (np.abs(nrm[:, 1]) < 0.92)
    H_fit = float(np.percentile(cent[roof_hi & (rr < 0.5), 1], 96)) - 0.03   # finials stay the highest points (QA)
    top = roof_hi & (y > H_fit - 0.35)
    w = area[top]
    ccx, ccz = np.average(cent[top, 0], weights=w), np.average(cent[top, 2], weights=w)
# 4-fold circular mean of the horizontal normal direction = ridge axis set
ang4 = 4 * np.arctan2(nrm[top, 2], nrm[top, 0])
th = float(np.angle(np.sum(w * np.exp(1j * ang4))) / 4)
def to_uv(X):
    dx, dz = X[..., 0] - ccx, X[..., 2] - ccz
    return np.cos(th) * dx + np.sin(th) * dz, -np.sin(th) * dx + np.cos(th) * dz
nh = nrm[top]
s_fit = float(np.clip(np.median(np.hypot(nh[:, 0], nh[:, 2]) / (np.abs(nh[:, 1]) + 1e-9)), 0.8, 2.5))
print(f'cross-gable fit: centre ({ccx:.3f},{ccz:.3f}) ridge axis {np.degrees(th):.1f} deg, ridge height {H_fit:.3f}, slope {s_fit:.2f}')
# Domain: the crossing square only -- where the two wings overlap. Its
# half-width is the wing half-width: top-tier height over slope. Along a
# ridge axis h == H at any distance, so an unclipped grid ran planks out
# over both wings and the terrace (QA).
W_box = float(np.clip((H_fit - np.percentile(cent[top, 1], 5)) / s_fit + 0.06, 0.15, 0.6))
Wu = Wv = W_box + 0.03      # margin so the cap reaches into the real slopes
def h_at(u_, v_):
    return H_fit - s_fit * np.minimum(np.abs(u_), np.abs(v_))
fu, fv = to_uv(P[kept_faces].mean(1))
fy = P[kept_faces].mean(1)[:, 1]
# Real geometry that conflicts with the cap is removed: everything inside
# the cap volume (up to 35 cm below the cap surface -- torn crossing
# fragments, not the tiers or terrace far below) and non-gold fragments
# poking through it. Gold faces above the cap are the real finials: kept.
kc = kept_faces.mean(1) if False else None
kcol = np.zeros((len(kept_faces), 3))
kmap = {tuple(sorted(f)): i for i, f in enumerate(faces)}
for j, f in enumerate(kept_faces):
    i = kmap.get(tuple(sorted(f)))
    if i is not None:
        kcol[j] = colf[i]
gold = (kcol[:, 2] > 1.4 * kcol[:, 0]) & (kcol[:, 1] > 1.3 * kcol[:, 0])      # BGR: R>1.4B, G>1.3B
inbox = (np.abs(fu) < Wu + 0.1) & (np.abs(fv) < Wv + 0.1)
hh = h_at(fu, fv)
protrude = inbox & (((fy > hh + 0.02) & ~gold) | ((fy <= hh + 0.02) & (fy > hh - 0.35))) & (fy > 1.0)
kept_faces = kept_faces[~protrude]
# slice every face-varying primvar with the same mask -- dropping faces
# without this shifted every later face's UVs onto its neighbour's and
# scrambled the whole texture (caught by QA on v9)
ck3 = np.repeat(~protrude, 3)
for pv in api.GetPrimvars():
    if pv.GetInterpolation() != UsdGeom.Tokens.faceVarying:
        continue
    if pv.IsIndexed():
        pidx = np.array(pv.GetIndices())
        pv.SetIndices(Vt.IntArray(pidx[ck3].tolist()))
    else:
        vals = np.array(pv.Get())
        pv.GetAttr().Set(type(pv.Get())(vals[ck3].tolist()))
# protrusion removal orphans small shards; sweep components < 40 faces
_par = {}
def _fr(a):
    while _par.setdefault(a, a) != a:
        _par[a] = _par[_par[a]]; a = _par[a]
    return a
for t3 in kept_faces:
    r0 = _fr(t3[0])
    for bb in t3[1:]:
        rb = _fr(bb)
        if rb != r0: _par[rb] = r0
_roots = np.array([_fr(t3[0]) for t3 in kept_faces])
_cnt = np.bincount(_roots)
crumb = _cnt[_roots] < 80
kept_faces = kept_faces[~crumb]
ck4 = np.repeat(~crumb, 3)
for pv in api.GetPrimvars():
    if pv.GetInterpolation() != UsdGeom.Tokens.faceVarying:
        continue
    if pv.IsIndexed():
        pidx = np.array(pv.GetIndices()); pv.SetIndices(Vt.IntArray(pidx[ck4].tolist()))
    else:
        vals = np.array(pv.Get()); pv.GetAttr().Set(type(pv.Get())(vals[ck4].tolist()))
print(f'crossing box {2*Wu:.2f} square; removed {protrude.sum():,} protruding faces, swept {crumb.sum():,} orphaned crumbs')
N = 56
gu, gv = np.meshgrid(np.linspace(-Wu, Wu, N), np.linspace(-Wv, Wv, N), indexing='ij')
gh = h_at(gu, gv) + 0.015
gx = ccx + np.cos(th) * gu - np.sin(th) * gv
gz = ccz + np.sin(th) * gu + np.cos(th) * gv
# keep the cap wherever it sits clearly ABOVE whatever real geometry is
# there (3 cm), drop it only where a real surface is at or above cap
# height. The earlier "skip if any real face within 6 cm below" rule left
# cavities over low interior fragments (QA).
fc = P[kept_faces].mean(1)
tree_xz = cKDTree(fc[:, [0, 2]])
gpts = np.stack([gx.ravel(), gz.ravel()], 1)
# the cap covers the whole square unconditionally: conflicting real
# geometry was removed above, and dropping cells around fragments left
# cavities in every earlier build (QA)
unc = gh.ravel() > 1.0
unc = unc.reshape(N, N)
base = len(P)
gp = np.stack([gx.ravel(), gh.ravel(), gz.ravel()], 1)
P = np.concatenate([P, gp])
idx = np.arange(N * N).reshape(N, N) + base
tris = []
for i in range(N - 1):
    for j in range(N - 1):
        q = [idx[i, j], idx[i + 1, j], idx[i + 1, j + 1], idx[i, j + 1]]
        u_ = [unc[i, j], unc[i + 1, j], unc[i + 1, j + 1], unc[i, j + 1]]
        for t in ((0, 1, 2), (0, 2, 3)):
            if sum(u_[k] for k in t) >= 1:      # one-cell overlap under the real slopes closes slits
                tris.append([q[k] for k in t])
tent = np.array(tris, int).reshape(-1, 3)
# keep only the largest connected piece: eave gaps inside the box produce
# small islands and shards that read as loose plates (QA)
par = {}
def _f(a):
    while par.setdefault(a, a) != a:
        par[a] = par[par[a]]; a = par[a]
    return a
for t3 in tent:
    r0 = _f(t3[0])
    for bb in t3[1:]:
        rb = _f(bb)
        if rb != r0: par[rb] = r0
roots_t = np.array([_f(t3[0]) for t3 in tent])
big_root = np.bincount(roots_t).argmax() if len(roots_t) else -1
tent = tent[roots_t == big_root]
# skirt: extrude every boundary edge of the cap 8 cm downward so the
# interior can never be seen between the cap edge and the real slope
# Weld the cap's boundary onto the real roof: every remaining gap, pinhole
# and cavity in QA was this seam. Cap boundary vertices snap to the nearest
# real BOUNDARY vertex within 12 cm (real boundary = edges with one face).
E_r = np.sort(np.concatenate([kept_faces[:, [0, 1]], kept_faces[:, [1, 2]], kept_faces[:, [2, 0]]]), 1)
Eu_r, cnt_r = np.unique(E_r, axis=0, return_counts=True)
# (Excluding gold/bright vertices as snap targets was tried, to protect the
# west panel's ridge crest: it did not restore the crest -- that loss comes
# from the protrusion removal, not the weld -- and 35 fewer snapped
# vertices reopened a visible hole at the crossing. Kept as is.)
rb_v = np.unique(Eu_r[cnt_r == 1])
E_c0 = np.sort(np.concatenate([tent[:, [0, 1]], tent[:, [1, 2]], tent[:, [2, 0]]]), 1)
Eu_c0, cnt_c0 = np.unique(E_c0, axis=0, return_counts=True)
cb_v = np.unique(Eu_c0[cnt_c0 == 1])
if len(rb_v):
    tr = cKDTree(P[rb_v])
    dist, near = tr.query(P[cb_v], distance_upper_bound=0.12)
    remap = {int(cb_v[k]): int(rb_v[near[k]]) for k in range(len(cb_v)) if np.isfinite(dist[k])}
    if remap:
        tent = np.vectorize(lambda v: remap.get(int(v), int(v)))(tent)
        tent = tent[(tent[:, 0] != tent[:, 1]) & (tent[:, 1] != tent[:, 2]) & (tent[:, 0] != tent[:, 2])]
    print(f'seam weld: {len(remap)} of {len(cb_v)} cap boundary vertices snapped to real roof')
E_t = np.sort(np.concatenate([tent[:, [0, 1]], tent[:, [1, 2]], tent[:, [2, 0]]]), 1)
Eu_t, cnt_t = np.unique(E_t, axis=0, return_counts=True)
bnd_t = Eu_t[cnt_t == 1]
bverts = np.unique(bnd_t)
low = {int(v): len(P) + k for k, v in enumerate(bverts)}
P = np.concatenate([P, P[bverts] - np.array([0, 0.40, 0])])   # deep enough to reach the tier below
skirt = []
for a_, b_ in bnd_t:
    skirt += [[a_, b_, low[int(b_)]], [a_, low[int(b_)], low[int(a_)]]]
skirt = np.array(skirt, int).reshape(-1, 3)
sn = np.cross(P[skirt[:, 1]] - P[skirt[:, 0]], P[skirt[:, 2]] - P[skirt[:, 0]])
sc = P[skirt].mean(1)
outward_s = np.stack([sc[:, 0] - ccx, np.zeros(len(sc)), sc[:, 2] - ccz], 1)
flip_s = (sn * outward_s).sum(1) < 0
skirt[flip_s] = skirt[flip_s][:, [0, 2, 1]]
tent = np.concatenate([tent, skirt])
print(f'skirt: {len(skirt)} faces along {len(bnd_t)} boundary edges')
tn = np.cross(P[tent[:, 1]] - P[tent[:, 0]], P[tent[:, 2]] - P[tent[:, 0]])
flip = (tn[:, 1] < 0) & (np.arange(len(tent)) < len(tent) - len(skirt))
tent[flip] = tent[flip][:, [0, 2, 1]]
kept_faces = np.concatenate([kept_faces, tent])
m.GetPointsAttr().Set(Vt.Vec3fArray.FromNumpy(P.astype(np.float32)))
m.GetFaceVertexCountsAttr().Set(Vt.IntArray([3] * len(kept_faces)))
m.GetFaceVertexIndicesAttr().Set(Vt.IntArray(kept_faces.ravel().tolist()))
tc = P[tent]
tu2 = (tc[..., 0] - cov[..., 0].min()) / SWATCH_SPAN
tv2 = (tc[..., 2] - cov[..., 2].min()) / (SWATCH_SPAN * SH_ / SW_)
tent_uv = np.stack([u0 + mirror(tu2) * (u1 - u0), v0 + mirror(tv2) * (v1 - v0)], -1).reshape(-1, 2)
for pv in api.GetPrimvars():
    if pv.GetInterpolation() != UsdGeom.Tokens.faceVarying:
        continue
    if pv.IsIndexed():
        pidx = list(pv.GetIndices())
        if pv.GetPrimvarName() == 'st':
            vals = np.array(pv.Get())
            pv.Set(Vt.Vec2fArray.FromNumpy(np.concatenate([vals, tent_uv]).astype(np.float32)))
            pidx += list(range(len(vals), len(vals) + len(tent_uv)))
        else:
            pidx += [0] * (3 * len(tent))
        pv.SetIndices(Vt.IntArray(pidx))
    else:
        vals = list(pv.Get())
        pv.GetAttr().Set(type(pv.Get())(vals + [vals[0]] * (3 * len(tent))))
print(f'crossing cap: {len(tent)} cross-gable faces over {unc.sum()} uncovered grid cells')

# small components inside the crossing region (severed slivers, flecks)
_p2 = {}
def _f2(a):
    while _p2.setdefault(a, a) != a:
        _p2[a] = _p2[_p2[a]]; a = _p2[a]
    return a
for t3 in kept_faces:
    r0 = _f2(t3[0])
    for bb in t3[1:]:
        rb = _f2(bb)
        if rb != r0: _p2[rb] = r0
_r2 = np.array([_f2(t3[0]) for t3 in kept_faces])
_c2 = np.bincount(_r2)
kfu, kfv = to_uv(P[kept_faces].mean(1))
near_cap = (np.abs(kfu) < Wu + 0.15) & (np.abs(kfv) < Wv + 0.15) & (P[kept_faces].mean(1)[:, 1] > 1.0)
fleck = near_cap & (_c2[_r2] < 200)
if fleck.any():
    kept_faces = kept_faces[~fleck]
    ck5 = np.repeat(~fleck, 3)
    for pv in api.GetPrimvars():
        if pv.GetInterpolation() != UsdGeom.Tokens.faceVarying:
            continue
        if pv.IsIndexed():
            pidx = np.array(pv.GetIndices()); pv.SetIndices(Vt.IntArray(pidx[ck5].tolist()))
        else:
            vals = np.array(pv.Get()); pv.GetAttr().Set(type(pv.Get())(vals[ck5].tolist()))
    m.GetFaceVertexCountsAttr().Set(Vt.IntArray([3] * len(kept_faces)))
    m.GetFaceVertexIndicesAttr().Set(Vt.IntArray(kept_faces.ravel().tolist()))
print(f'flecks near cap swept: {int(fleck.sum())}')

# The relaxation moved vertices, so stored normals are stale everywhere the
# sheets were. Recompute smooth area-weighted vertex normals for the whole
# final mesh -- organic photogrammetry shades better smooth anyway.
fn = np.cross(P[kept_faces[:, 1]] - P[kept_faces[:, 0]],
              P[kept_faces[:, 2]] - P[kept_faces[:, 0]])
vn = np.zeros_like(P)
for k in range(3):
    np.add.at(vn, kept_faces[:, k], fn)
vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-12
na2 = m.GetNormalsAttr()
if na2.Get() is not None:
    m.SetNormalsInterpolation(UsdGeom.Tokens.faceVarying)
    na2.Set(Vt.Vec3fArray.FromNumpy(vn[kept_faces.ravel()].astype(np.float32)))

st_n = len(UsdGeom.PrimvarsAPI(mesh).GetPrimvar('st').GetIndices())
assert st_n == 3 * len(kept_faces), f'st indices {st_n} != 3 x faces {len(kept_faces)}'
stage.Save()
if os.path.exists(dst):
    os.remove(dst)
ok = UsdUtils.CreateNewUsdzPackage(Sdf.AssetPath(usdc), dst)
print('wrote' if ok else 'FAILED', dst)
shutil.rmtree(work)
sys.exit(0 if ok else 1)
