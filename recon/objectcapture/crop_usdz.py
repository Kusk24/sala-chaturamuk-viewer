"""Crop background debris out of an Apple photogrammetry usdz, losslessly.

SceneKit could re-export the mesh but destroys the face-varying UV layout in
the process (textures come out white), so this edits the USD itself with
Pixar's usd-core: unzip, filter the faces, keep every primvar aligned, rezip.

Faces are dropped when their centroid is farther than <radius> from the
robust (median) horizontal centre -- the debris is welded to the pavilion by
thin skirts, so a spatial cut is the only separator.

  python3 crop_usdz.py <in.usdz> <out.usdz> <radius>
"""
import sys, os, zipfile, shutil, tempfile
import numpy as np
from pxr import Usd, UsdGeom, UsdUtils, Sdf, Vt

src, dst, radius = sys.argv[1], sys.argv[2], float(sys.argv[3])
work = tempfile.mkdtemp()
with zipfile.ZipFile(src) as z:
    z.extractall(work)
usdcs = [os.path.join(r, f) for r, _, fs in os.walk(work) for f in fs if f.endswith(('.usdc', '.usda'))]
assert len(usdcs) == 1, usdcs
stage = Usd.Stage.Open(usdcs[0])

mesh = next(p for p in stage.Traverse() if p.IsA(UsdGeom.Mesh))
m = UsdGeom.Mesh(mesh)
counts = np.array(m.GetFaceVertexCountsAttr().Get())
idx = np.array(m.GetFaceVertexIndicesAttr().Get())
pts = np.array(m.GetPointsAttr().Get())
assert (counts == 3).all(), "non-triangle faces"
tris = idx.reshape(-1, 3)
cent = pts[tris].mean(1)
cx, cz = np.median(cent[:, 0]), np.median(cent[:, 2])
keep = np.hypot(cent[:, 0] - cx, cent[:, 2] - cz) <= radius
print(f"faces: {len(tris):,} -> keeping {keep.sum():,} ({100*keep.mean():.1f}%)")

# corner k of face f lives at flat position 3f+k; every faceVarying primvar
# (and its index array, if indexed) must be filtered identically.
corner_keep = np.repeat(keep, 3)
m.GetFaceVertexCountsAttr().Set(Vt.IntArray([3] * int(keep.sum())))
m.GetFaceVertexIndicesAttr().Set(Vt.IntArray(tris[keep].ravel().tolist()))

api = UsdGeom.PrimvarsAPI(mesh)
for pv in api.GetPrimvars():
    if pv.GetInterpolation() != UsdGeom.Tokens.faceVarying:
        continue
    name = pv.GetPrimvarName()
    if pv.IsIndexed():
        pidx = np.array(pv.GetIndices())
        assert len(pidx) == len(corner_keep), (name, len(pidx))
        pv.SetIndices(Vt.IntArray(pidx[corner_keep].tolist()))
        print(f"  primvar {name}: filtered {len(pidx):,} indices")
    else:
        vals = np.array(pv.Get())
        assert len(vals) == len(corner_keep), (name, len(vals))
        arr = vals[corner_keep]
        pv.GetAttr().Set(type(pv.Get())(arr.tolist()))
        print(f"  primvar {name}: filtered {len(vals):,} values")

nattr = m.GetNormalsAttr()
if nattr.Get() is not None and m.GetNormalsInterpolation() == UsdGeom.Tokens.faceVarying:
    nv = np.array(nattr.Get())
    if len(nv) == len(corner_keep):
        nattr.Set(Vt.Vec3fArray.FromNumpy(nv[corner_keep]))
        print(f"  normals: filtered {len(nv):,} values")

stage.Save()
if os.path.exists(dst):
    os.remove(dst)
ok = UsdUtils.CreateNewUsdzPackage(Sdf.AssetPath(usdcs[0]), dst)
print("wrote" if ok else "FAILED to write", dst)
shutil.rmtree(work)
sys.exit(0 if ok else 1)
