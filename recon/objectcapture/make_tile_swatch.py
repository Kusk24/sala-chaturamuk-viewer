"""Cut a clean roof-tile swatch out of the source photographs.

Scans the capture set for the largest axis-aligned rectangle that lies fully
inside a roof region (red tile bands and their gold ridge trims), crops it
from the full-resolution photo, and writes a swatch resized to fit
SW x SH. polish_usdz.py pastes this swatch into a strip added to the texture
atlas and maps the roof cover onto it -- so the cover shows photographed
tiles, not paint.

  python3 make_tile_swatch.py <photo-dir> <out.png> [photo]

With no photo given, every photo is scanned and the largest rectangle wins.
The largest is not always the cleanest (an ornament can intrude at an edge),
so the photo actually used for the deliverable was picked by eye from the
six largest candidates: capture_0110.jpg -- tiles and two ridge bands only.
"""
import sys, os, numpy as np, cv2
src, out = sys.argv[1], sys.argv[2]
SW, SH = 2048, 1024

def red_mask(bgr):
    # Red tile only. The gold ridge lines crossing a slope are thin, so a
    # modest closing bridges them and a tile band merges into one region;
    # the wide gold eave trims and the ornaments below stay excluded (an
    # earlier red-OR-gold mask with a large closing pulled in the whole
    # eave, pillars included).
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    m = (((h < 12) | (h > 168)) & (s > 70) & (v > 40)).astype(np.uint8) * 255
    # No closing: the gold ridge lines must NOT be bridged. Visual QA showed
    # that any stripe projected onto the lumpy synthetic cover betrays its
    # swirl, scale and seams at once; a plain tile field hides all three,
    # and real trims only run along eaves, which the crossing has none of.
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
    return cv2.erode(m, np.ones((5, 5), np.uint8))

def max_rect(mask):
    R, C = mask.shape
    hist = np.zeros(C, int); best = 0; rect = None
    for r in range(R):
        hist = np.where(mask[r] > 0, hist + 1, 0); stack = []
        for c in range(C + 1):
            cur = hist[c] if c < C else 0; start = c
            while stack and stack[-1][1] > cur:
                s0, hh = stack.pop()
                if hh * (c - s0) > best:
                    best = hh * (c - s0); rect = (s0, r - hh + 1, c - 1, r)
                start = s0
            stack.append((start, cur))
    return best, rect

best = (0, None, None)
files = sorted(f for f in os.listdir(src) if f.lower().endswith(('.jpg', '.jpeg', '.png')))
if len(sys.argv) > 3:
    files = [sys.argv[3]]
for f in files:
    im = cv2.imread(os.path.join(src, f))
    small = cv2.resize(im, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    area, rect = max_rect(red_mask(small))
    if area > best[0]:
        best = (area, f, rect)
area, f, (x0, y0, x1, y1) = best
im = cv2.imread(os.path.join(src, f))
crop = im[y0 * 4:(y1 + 1) * 4, x0 * 4:(x1 + 1) * 4]
crop = crop[:int(crop.shape[0] * 0.92)]            # drop the eave/shadow strip at the bottom
# the crop reads a little lighter than the photogrammetry-textured tiles it
# sits next to: darken 6%, 5% toward grey (13% overshot in visual QA)
gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)[..., None].repeat(3, -1)
crop = np.clip(crop.astype(np.float32) * 0.88, 0, 255).astype(np.uint8)   # renders ~35% brighter than neighbours at 0.94 (QA); no desaturation
print(f'best swatch: {f}  rect {crop.shape[1]}x{crop.shape[0]} px at ({x0*4},{y0*4})')
# tile at NATIVE photo resolution (no upscaling -- keeps the grain crisp),
# mirror-repeated so the seams are continuous
crop = crop[:SH, :SW]
sw = np.zeros((SH, SW, 3), np.uint8)
for yy in range(0, SH, crop.shape[0]):
    for xx in range(0, SW, crop.shape[1]):
        tile = crop[:, ::-1] if (xx // crop.shape[1]) % 2 else crop
        tile = tile[::-1] if (yy // crop.shape[0]) % 2 else tile
        sw[yy:yy + tile.shape[0], xx:xx + tile.shape[1]] = tile[:SH - yy, :SW - xx]
cv2.imwrite(out, sw)
print('wrote', out, sw.shape[1], 'x', sw.shape[0])
