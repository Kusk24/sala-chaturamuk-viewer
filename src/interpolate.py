#!/usr/bin/env python3
"""Stage 4: synthesize in-between viewpoints by optical-flow view interpolation.

    python src/interpolate.py --frames data/selected/ --out output/sequence/ --n-between 2

For each ADJACENT pair (A, B) we compute dense Farneback flow both ways and
produce --n-between intermediate frames at t = k/(n+1). This is Chen & Williams
view interpolation: the in-between views come from warping and cross-dissolving
photographs, never from geometry. No depth, no pose, no 3D.

The warp, for output time t in (0, 1):

    warped_A = remap(A, grid +     t * flow_BA)     # A pulled toward B's layout
    warped_B = remap(B, grid + (1-t) * flow_AB)     # B pulled toward A's layout
    I_t      = (1-t) * warped_A + t * warped_B      # cross-dissolve

At t=0 this is exactly A and at t=1 exactly B, so the sequence stays consistent
with the captured frames at its endpoints.

Note on wording: the paper describes this as "forward warping". It is
implemented as *backward* warping (cv2.remap pulls from the source) because
forward scatter leaves unfilled holes wherever the flow diverges. The result is
the same interpolated view; only the resampling direction differs. Worth fixing
in the paper text rather than in the code.

Output naming keeps real and synthetic distinguishable on disk:

    frame_0007.jpg      <- real captured frame (copied through)
    frame_0007_i1.jpg   <- synthesized, t = 1/3
    frame_0007_i2.jpg   <- synthesized, t = 2/3
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import cv2
import numpy as np

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")


def list_frames(directory):
    return sorted(
        name for name in os.listdir(directory)
        if name.lower().endswith(IMAGE_EXTS)
    )


def farneback(gray_from, gray_to, args):
    return cv2.calcOpticalFlowFarneback(
        gray_from, gray_to, None,
        pyr_scale=args.pyr_scale,
        levels=args.levels,
        winsize=args.winsize,
        iterations=args.iterations,
        poly_n=args.poly_n,
        poly_sigma=args.poly_sigma,
        flags=0,
    )


def warp(img, flow, scale, grid_x, grid_y):
    """Backward-warp img along `flow` scaled by `scale`."""
    map_x = (grid_x + scale * flow[..., 0]).astype(np.float32)
    map_y = (grid_y + scale * flow[..., 1]).astype(np.float32)
    return cv2.remap(img, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def interpolate_pair(img_a, img_b, flow_ab, flow_ba, t, grid_x, grid_y):
    warped_a = warp(img_a, flow_ba, t, grid_x, grid_y)
    warped_b = warp(img_b, flow_ab, 1.0 - t, grid_x, grid_y)
    blended = (1.0 - t) * warped_a.astype(np.float32) + t * warped_b.astype(np.float32)
    return np.clip(blended, 0, 255).astype(np.uint8)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--frames", required=True, help="directory of captured frames")
    p.add_argument("--out", required=True, help="output sequence directory")
    p.add_argument("--n-between", type=int, default=2, help="synthesized frames per pair (default: 2)")
    p.add_argument("--quality", type=int, default=95, help="JPEG quality (default: 95)")
    p.add_argument("--wraparound", action="store_true",
                   help="also interpolate from the last captured frame back to the first. Only "
                        "pass this if a full revolution was genuinely walked")
    # Farneback parameters, exposed so they can be tuned against the roof tiling.
    p.add_argument("--pyr-scale", type=float, default=0.5)
    p.add_argument("--levels", type=int, default=3)
    p.add_argument("--winsize", type=int, default=15)
    p.add_argument("--iterations", type=int, default=3)
    p.add_argument("--poly-n", type=int, default=5)
    p.add_argument("--poly-sigma", type=float, default=1.2)
    args = p.parse_args()

    if args.n_between < 0:
        sys.exit("--n-between must be >= 0")
    if not os.path.isdir(args.frames):
        sys.exit(f"No such directory: {args.frames}")

    names = list_frames(args.frames)
    if len(names) < 2:
        sys.exit(f"Need at least 2 frames in {args.frames}, found {len(names)}")

    os.makedirs(args.out, exist_ok=True)

    first = cv2.imread(os.path.join(args.frames, names[0]))
    if first is None:
        sys.exit(f"Could not read {names[0]}")
    h, w = first.shape[:2]
    grid_y, grid_x = np.mgrid[0:h, 0:w].astype(np.float32)

    records = []

    def emit_real(index, img):
        name = f"frame_{index:04d}.jpg"
        cv2.imwrite(os.path.join(args.out, name), img, [cv2.IMWRITE_JPEG_QUALITY, args.quality])
        records.append({"file": name, "kind": "real", "source_file": names[index],
                        "pair_a": index, "pair_b": None, "t": 0.0})

    def synthesize(img_a, img_b, i):
        """Write the --n-between views that sit between captured frames i and i+1."""
        gray_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
        gray_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)
        flow_ab = farneback(gray_a, gray_b, args)
        flow_ba = farneback(gray_b, gray_a, args)
        for k in range(1, args.n_between + 1):
            t = k / (args.n_between + 1)
            out = interpolate_pair(img_a, img_b, flow_ab, flow_ba, t, grid_x, grid_y)
            name = f"frame_{i:04d}_i{k}.jpg"
            cv2.imwrite(os.path.join(args.out, name), out, [cv2.IMWRITE_JPEG_QUALITY, args.quality])
            records.append({"file": name, "kind": "synth", "source_file": None,
                            "pair_a": i, "pair_b": (i + 1) % len(names), "t": round(t, 6)})

    img_a = first
    # Adjacent pairs only. The capture is normally a partial arc, so by default
    # the last frame is NOT joined back to the first.
    for i in range(len(names) - 1):
        img_b = cv2.imread(os.path.join(args.frames, names[i + 1]))
        if img_b is None:
            sys.exit(f"Could not read {names[i + 1]}")
        if img_b.shape[:2] != (h, w):
            sys.exit(f"{names[i + 1]} is {img_b.shape[1]}x{img_b.shape[0]}, "
                     f"expected {w}x{h}; re-run extract_frames.py with --width")

        emit_real(i, img_a)
        if args.n_between:
            synthesize(img_a, img_b, i)

        print(f"[{i:3d}/{len(names) - 2}] {names[i]} -> {names[i + 1]}: "
              f"+{args.n_between} synthesized")
        img_a = img_b

    emit_real(len(names) - 1, img_a)  # final captured frame

    if args.wraparound and args.n_between:
        # Only reached when a full revolution was genuinely walked.
        synthesize(img_a, first, len(names) - 1)
        print(f"[wrap] {names[-1]} -> {names[0]}: +{args.n_between} synthesized")

    meta = {
        "frames_dir": args.frames,
        "n_captured": len(names),
        "n_between": args.n_between,
        "n_total": len(records),
        "wraparound": args.wraparound,
        "method": "farneback-flow view interpolation (backward warp + cross-dissolve)",
        "farneback": {
            "pyr_scale": args.pyr_scale, "levels": args.levels, "winsize": args.winsize,
            "iterations": args.iterations, "poly_n": args.poly_n, "poly_sigma": args.poly_sigma,
        },
        "frames": records,
    }
    with open(os.path.join(args.out, "interpolation.json"), "w") as fh:
        json.dump(meta, fh, indent=2)

    n_synth = sum(1 for r in records if r["kind"] == "synth")
    print(f"\n{len(records)} frames to {args.out} "
          f"({len(names)} real + {n_synth} synthesized)")


if __name__ == "__main__":
    main()
