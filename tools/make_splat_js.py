# Pack the trained lamp model into a single JS file the viewer can load from
# file://: the .splat as base64, the COLMAP poses, and an opening view matrix
# aimed at the lamp. Mirrors what was done for splat_sala_v2.js.
import base64, json, os, sys
import numpy as np

SUB = sys.argv[1]
SRC = f'/Users/kusk/Desktop/Computer Vision/Term-Project/kaggle_out/{SUB}/out_{SUB}'
DST = f'/Users/kusk/Desktop/Computer Vision/Term-Project/sala-chaturamuk-viewer/viewer/splat_{SUB}.js'
SPLAT = f'{SRC}/{SUB}_cropped_v2.splat'

cams = json.load(open(f'{SRC}/cameras.json'))
P = np.array([c['position'] for c in cams])
ctr = np.median(P, axis=0)

# Open on the photograph that looks most squarely at the middle of the ring.
def facing(c):
    R = np.array(c['rotation']); p = np.array(c['position'])
    to = ctr - p
    return float(R[:, 2] @ (to / np.linalg.norm(to)))
# argv[2] names the opening photograph explicitly; otherwise take the most
# centre-facing one, which is the right choice for an object-scale orbit.
pick = sys.argv[2] if len(sys.argv) > 2 else None
start = next(c for c in cams if c['img_name'] == pick) if pick else max(cams, key=facing)

def view_matrix(c):                      # identical to getViewMatrix in splat.js
    R = np.array(c['rotation']).reshape(9)
    t = c['position']
    return [R[0], R[1], R[2], 0,
            R[3], R[4], R[5], 0,
            R[6], R[7], R[8], 0,
            -t[0]*R[0] - t[1]*R[3] - t[2]*R[6],
            -t[0]*R[1] - t[1]*R[4] - t[2]*R[7],
            -t[0]*R[2] - t[1]*R[5] - t[2]*R[8], 1]

raw = open(SPLAT, 'rb').read()
n = len(raw) // 32
assert len(raw) % 32 == 0, f'{len(raw)} is not a whole number of 32-byte rows'
b64 = base64.b64encode(raw).decode('ascii')

vm = [round(float(v), 9) for v in view_matrix(start)]
with open(DST, 'w') as f:
    f.write(f'''// Generated - 3D Gaussian Splatting model of the lamp (โคมไฟ) beside
// Sala Chaturamuk Phaichit. Trained on Kaggle (NVIDIA T4 x2) from the 100
// photographs of the 5 September 2026 capture, 30,000 iterations.
// {n:,} Gaussians after the object crop, 32 bytes each.
// Base64 because a file:// page cannot fetch().
window.SPLAT_COUNT = {n};
window.SPLAT_VIEW_MATRIX = {json.dumps(vm)};
window.SPLAT_CAMERAS = {json.dumps(cams, separators=(',', ':'))};
window.SPLAT_DATA_B64 = "{b64}";
''')
print(f'{n:,} Gaussians  ->  {os.path.getsize(DST)/1e6:.1f} MB  {DST}')
print(f'opening view: {start["img_name"]}  facing score {facing(start):.4f}')
