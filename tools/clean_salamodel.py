"""Clean the trained sala-model splat for the viewer: remove the haze and the board,
lift the midtones, and reframe the opening view. Works on the trained result only;
nothing is retrained and the held-out scores are NOT recomputed afterwards.

    python tools/clean_salamodel.py [out.js]

Input is the notebook's own export in kaggle_out (the trained, cropped, upright model
and its packed viewer JS). Frame: upright, world up = [0, -1, 0].
"""
import base64, re, sys, os
import numpy as np

ROOT = '/Users/kusk/Desktop/Computer Vision/Term-Project'
SRC  = f'{ROOT}/kaggle_out/salamodel/out_salamodel/salamodel_final.splat'
JSIN = f'{ROOT}/kaggle_out/salamodel/out_salamodel/splat_salamodel.js'
OUT  = sys.argv[1] if len(sys.argv) > 1 else f'{ROOT}/sala-chaturamuk-viewer/viewer/splat_salamodel.js'

UP    = np.array([0, -1.0, 0])
AXIS  = np.array([-0.621, 1.100, -0.013])  # median of the model's solid Gaussians above the board
HZ    = 0.90    # keep within this horizontal distance of the model's axis   -> removes haze
HTOP  = -2.06   # keep above the top of the board (height along UP)          -> removes board, cloth
HHIGH = 0.00    # keep below this height (model top is about -0.22)          -> removes haze above
SCMAX = 0.05    # largest Gaussian axis                                      -> removes floaters
AMIN  = 0.15    # minimum opacity
GAMMA = 1.9     # midtone lift; clips 0.27% of channels
AZ, EL, DIST = 40.0, 14.0, 2.15   # opening view about AXIS

def view_matrix(target, az_deg, el_deg, dist):
    e1 = np.cross(UP, [0, 0, 1.0]); e1 /= np.linalg.norm(e1); e2 = np.cross(UP, e1)
    a, el = np.radians(az_deg), np.radians(el_deg)
    C = target + dist * (np.cos(el) * (np.cos(a) * e1 + np.sin(a) * e2) + np.sin(el) * UP)
    f = target - C; f /= np.linalg.norm(f)
    r = np.cross(f, UP); r /= np.linalg.norm(r)
    R = np.stack([r, np.cross(f, r), f])           # rows: right, image-down, forward
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = -R @ C
    return M.T.reshape(16)                          # column-major, as the viewer reads it

raw = np.fromfile(SRC, dtype=np.uint8); n = len(raw) // 32; R = raw.reshape(n, 32).copy()
xyz = R[:, 0:12].copy().view(np.float32).reshape(n, 3).astype(np.float64)
big = R[:, 12:24].copy().view(np.float32).reshape(n, 3).astype(np.float64).max(1)
alpha = R[:, 27] / 255.0
h = xyz @ UP
d = xyz - AXIS; hz = np.linalg.norm(d - np.outer(d @ UP, UP), axis=1)
keep = (hz < HZ) & (h > HTOP) & (h < HHIGH) & (big < SCMAX) & (alpha > AMIN)
K = R[keep]
rgb = np.power(K[:, 24:27] / 255.0, 1.0 / GAMMA)
K[:, 24:27] = np.clip(rgb * 255.0, 0, 255).astype(np.uint8)

js = open(JSIN).read()
js = re.sub(r'window\.SPLAT_COUNT\s*=\s*\d+;', f'window.SPLAT_COUNT = {len(K)};', js, count=1)
js = re.sub(r'window\.SPLAT_DATA_B64\s*=\s*"[^"]*";',
            lambda _: f'window.SPLAT_DATA_B64 = "{base64.b64encode(K.tobytes()).decode()}";', js, count=1)
vm = view_matrix(AXIS, AZ, EL, DIST)
js = re.sub(r'window\.SPLAT_VIEW_MATRIX\s*=\s*\[[^\]]*\];',
            lambda _: 'window.SPLAT_VIEW_MATRIX = [' + ', '.join(f'{x:.9f}' for x in vm) + '];', js, count=1)
js = js.replace('5 Sep 2026 capture', '12 September 2026 capture', 1)
open(OUT, 'w').write(js)
print(f'kept {len(K):,} of {n:,} ({100 * len(K) / n:.1f}%), clipped {100 * (rgb >= 0.999).mean():.2f}% -> {OUT}')
