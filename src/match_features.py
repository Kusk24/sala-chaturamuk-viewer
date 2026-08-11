#!/usr/bin/env python3
"""Stage 3: SIFT correspondences between ADJACENT frames only.

    python src/match_features.py --frames data/selected/ --out output/matches.json

This is a quality-control stage, not a reconstruction stage. It answers one
question: are consecutive captures close enough together to be interpolated?
A pair with few RANSAC inliers means the angular gap there is too large (or the
frames are mismatched), and interpolate.py will produce visible tearing across
that gap.

Two things this deliberately does NOT do:

  * It never matches globally across the whole set. Sala Chaturamuk Phaichit is
    four-porched and close to rotationally symmetric, so views ~90 deg apart
    look alike and match strongly but wrongly. Matching is restricted to
    adjacent pairs. Use --symmetry-stride to measure that failure on purpose.
  * It never recovers pose or 3D structure. The fundamental matrix here is used
    only as a RANSAC model to reject outlying correspondences -- nothing is
    decomposed out of it, and no geometry leaves this script. Per CLAUDE.md the
    project stays inside image-based rendering (Szeliski Ch. 14).
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


def match_pair(sift, flann, gray_a, gray_b, args):
    """SIFT + Lowe ratio test + RANSAC. Returns a stats dict and the inlier mask."""
    kp_a, des_a = sift.detectAndCompute(gray_a, None)
    kp_b, des_b = sift.detectAndCompute(gray_b, None)

    stats = {
        "keypoints_a": len(kp_a),
        "keypoints_b": len(kp_b),
        "good_matches": 0,
        "inliers": 0,
        "inlier_ratio": 0.0,
    }
    if des_a is None or des_b is None or len(kp_a) < 2 or len(kp_b) < 2:
        return stats, kp_a, kp_b, []

    # Lowe's ratio test (Szeliski Ch. 7.1.3) -- same form as Week6.
    good = []
    for pair in flann.knnMatch(des_a, des_b, k=2):
        if len(pair) < 2:
            continue
        m, n = pair
        if m.distance < args.ratio * n.distance:
            good.append(m)
    stats["good_matches"] = len(good)

    if len(good) < 8:
        return stats, kp_a, kp_b, good

    src = np.float32([kp_a[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp_b[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

    if args.model == "homography":
        # Valid only if the scene were planar or the camera purely rotating.
        _, mask = cv2.findHomography(src, dst, cv2.RANSAC, args.ransac_thresh)
    else:
        # Walking an arc induces real parallax, so epipolar geometry is the
        # honest outlier model here.
        _, mask = cv2.findFundamentalMat(src, dst, cv2.FM_RANSAC, args.ransac_thresh, 0.99)

    if mask is None:
        return stats, kp_a, kp_b, good

    mask = mask.ravel().astype(bool)
    stats["inliers"] = int(mask.sum())
    stats["inlier_ratio"] = round(float(mask.sum()) / len(good), 4)
    return stats, kp_a, kp_b, [m for m, keep in zip(good, mask) if keep]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--frames", required=True, help="directory of captured frames")
    p.add_argument("--out", required=True, help="output JSON path")
    p.add_argument("--ratio", type=float, default=0.7, help="Lowe ratio threshold (default: 0.7)")
    p.add_argument("--model", choices=["fundamental", "homography"], default="fundamental",
                   help="RANSAC outlier model (default: fundamental)")
    p.add_argument("--ransac-thresh", type=float, default=3.0, help="RANSAC reprojection threshold in px")
    p.add_argument("--min-inliers", type=int, default=30,
                   help="warn below this many inliers per adjacent pair (default: 30)")
    p.add_argument("--debug-dir", default=None, help="if set, write match visualisations here")
    p.add_argument("--symmetry-stride", type=int, default=None,
                   help="also match each frame against frame i+STRIDE to measure false "
                        "matches between the pavilion's symmetric faces (diagnostic only)")
    args = p.parse_args()

    if not os.path.isdir(args.frames):
        sys.exit(f"No such directory: {args.frames}")
    names = list_frames(args.frames)
    if len(names) < 2:
        sys.exit(f"Need at least 2 frames in {args.frames}, found {len(names)}")

    sift = cv2.SIFT_create()
    flann = cv2.FlannBasedMatcher(dict(algorithm=1, trees=5), dict(checks=50))  # KD-tree for SIFT

    if args.debug_dir:
        os.makedirs(args.debug_dir, exist_ok=True)

    grays = {}

    def gray(name):
        if name not in grays:
            img = cv2.imread(os.path.join(args.frames, name), cv2.IMREAD_GRAYSCALE)
            if img is None:
                sys.exit(f"Could not read {name}")
            grays[name] = img
        return grays[name]

    pairs, warnings = [], []
    # Adjacent pairs only, and no wraparound: the lake bounds the capture path,
    # so frame[-1] is NOT a neighbour of frame[0].
    for i in range(len(names) - 1):
        a, b = names[i], names[i + 1]
        stats, kp_a, kp_b, inliers = match_pair(sift, flann, gray(a), gray(b), args)
        record = {"index_a": i, "index_b": i + 1, "file_a": a, "file_b": b, **stats}
        pairs.append(record)

        flag = ""
        if stats["inliers"] < args.min_inliers:
            msg = (f"{a} -> {b}: only {stats['inliers']} inliers "
                   f"(< {args.min_inliers}); angular gap is probably too large to interpolate")
            warnings.append(msg)
            flag = "  <-- WEAK"
        print(f"[{i:3d}] {a} -> {b}: {stats['good_matches']:4d} good, "
              f"{stats['inliers']:4d} inliers ({stats['inlier_ratio']:.2f}){flag}")

        if args.debug_dir:
            vis = cv2.drawMatches(
                gray(a), kp_a, gray(b), kp_b, inliers[:80], None,
                flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS,
            )
            cv2.imwrite(os.path.join(args.debug_dir, f"pair_{i:04d}.jpg"), vis)

    symmetry = []
    if args.symmetry_stride:
        print(f"\nSymmetry check at stride {args.symmetry_stride} "
              f"(these pairs are NOT used for interpolation):")
        for i in range(len(names) - args.symmetry_stride):
            a, b = names[i], names[i + args.symmetry_stride]
            stats, _, _, _ = match_pair(sift, flann, gray(a), gray(b), args)
            symmetry.append({"index_a": i, "index_b": i + args.symmetry_stride,
                             "file_a": a, "file_b": b, **stats})
            print(f"[{i:3d}] {a} -> {b}: {stats['good_matches']:4d} good, "
                  f"{stats['inliers']:4d} inliers ({stats['inlier_ratio']:.2f})")

    result = {
        "frames_dir": args.frames,
        "n_frames": len(names),
        "wraparound": False,
        "params": {
            "ratio": args.ratio,
            "model": args.model,
            "ransac_thresh": args.ransac_thresh,
            "min_inliers": args.min_inliers,
        },
        "pairs": pairs,
        "symmetry_check": symmetry,
        "warnings": warnings,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(result, fh, indent=2)

    counts = [pr["inliers"] for pr in pairs]
    print(f"\n{len(pairs)} adjacent pairs -> {args.out}")
    print(f"  inliers: min {min(counts)}, median {int(np.median(counts))}, max {max(counts)}")
    for msg in warnings:
        print(f"  WARNING: {msg}")


if __name__ == "__main__":
    main()
