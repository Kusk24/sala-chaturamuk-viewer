"""Sky masks for Apple PhotogrammetrySession.

The first reconstruction attempt turned the overcast sky into geometry -- a
white "tarp" draped over the pavilion roof (see the paper's reconstruction
section). The fix is to tell the engine which pixels are sky so they never
become geometry: PhotogrammetrySample.objectMask, where 0 = ignore.

Overcast sky is bright, unsaturated and smooth, and touches the top border.
That heuristic is checked visually in scratchpad/mask_check.png before any
long reconstruction run consumes it. Masks are computed at 1600px wide and
upscaled: the classification does not need full resolution, and the kernel
sizes below are tuned for that width.

  python3 recon/objectcapture/make_masks.py <image-dir> <mask-dir>
"""
import cv2, numpy as np, glob, os, sys

def sky_mask(img):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    S, V = hsv[..., 1], hsv[..., 2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    grad = cv2.magnitude(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3),
                         cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3))
    smooth = cv2.blur((grad < 25).astype(np.uint8), (9, 9)) > 0.7
    cand = ((S < 50) & (V > 140) & smooth).astype(np.uint8)
    cand = cv2.morphologyEx(cand, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, lab = cv2.connectedComponents(cand)
    top = set(np.unique(lab[: img.shape[0] // 20])) - {0}
    sky = np.isin(lab, list(top)).astype(np.uint8)
    # Shrink the sky 4-5px so building edges are never eaten -- a sliver of
    # leftover sky is harmless, a chewed roofline is not.
    sky = cv2.erode(sky, np.ones((9, 9), np.uint8))
    return (1 - sky) * 255  # 255 = object, 0 = sky

def main(src, dst):
    os.makedirs(dst, exist_ok=True)
    files = sorted(glob.glob(os.path.join(src, "*.jpg")))
    assert files, f"no jpgs in {src}"
    for k, p in enumerate(files):
        img = cv2.imread(p)
        h, w = img.shape[:2]
        small = cv2.resize(img, (1600, int(h * 1600 / w)))
        m = sky_mask(small)
        m = cv2.resize(m, (w, h), interpolation=cv2.INTER_NEAREST)
        out = os.path.join(dst, os.path.splitext(os.path.basename(p))[0] + ".png")
        cv2.imwrite(out, m)
        if k % 20 == 0:
            print(f"{k+1}/{len(files)}", flush=True)
    print(f"wrote {len(files)} masks to {dst}")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
