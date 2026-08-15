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


def ransac_mask(src, dst, args):
    """RANSAC outlier mask. Returns (mask, model_actually_used).

    The fundamental matrix is the honest model while walking an arc, because
    the motion produces real parallax. But it is degenerate when the matched
    points are near-coplanar or the camera barely translates -- a flat facade
    shot head-on, or a stretch where you pivoted more than you walked. OpenCV
    does not fail gracefully there: it raises. So catch that and fall back to a
    homography, which is the correct model for exactly those cases, and record
    which one was used per pair.
    """
    order = ["homography"] if args.model == "homography" else ["fundamental", "homography"]
    for model in order:
        try:
            if model == "fundamental":
                matrix, mask = cv2.findFundamentalMat(
                    src, dst, cv2.FM_RANSAC, args.ransac_thresh, 0.99)
            else:
                matrix, mask = cv2.findHomography(src, dst, cv2.RANSAC, args.ransac_thresh)
        except cv2.error:
            continue
        if matrix is None or mask is None or len(mask) != len(src):
            continue
        degenerate = model != order[0]
        return mask.ravel().astype(bool), model + (" (fell back)" if degenerate else "")
    return None, "none succeeded"


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
        "model_used": None,
        "median_disp_px": None,
        "median_disp_pct": None,
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

    mask, model_used = ransac_mask(src, dst, args)
    stats["model_used"] = model_used
    if mask is None:
        return stats, kp_a, kp_b, good

    stats["inliers"] = int(mask.sum())
    stats["inlier_ratio"] = round(float(mask.sum()) / len(good), 4)

    # How far the scene actually moves between these two frames, as a fraction
    # of frame width. This -- not the inlier count -- is what predicts whether
    # interpolate.py can produce a real in-between view.
    #
    # SIFT is designed to be robust to large viewpoint change, so two frames
    # 30 degrees apart can still return a thousand confident inliers. Dense
    # optical flow has no such robustness: past roughly a tenth of the frame
    # width it stops finding the correspondence at all, the warp collapses to
    # no-op, and the cross-dissolve blends two unaligned images into a ghost.
    # A high inlier count therefore does NOT mean a pair is interpolatable.
    disp = np.linalg.norm(src[mask] - dst[mask], axis=2).ravel()
    median_disp = float(np.median(disp))
    stats["median_disp_px"] = round(median_disp, 1)
    stats["median_disp_pct"] = round(100.0 * median_disp / gray_a.shape[1], 2)
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
    p.add_argument("--max-displacement", type=float, default=8.0,
                   help="warn when the scene moves more than this %% of frame width between "
                        "adjacent frames — past it, optical flow ghosts instead of warping "
                        "(default: 8)")
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
            warnings.append(f"{a} -> {b}: only {stats['inliers']} inliers "
                            f"(< {args.min_inliers}); these frames barely match at all")
            flag = "  <-- WEAK MATCH"
        elif (stats["median_disp_pct"] or 0) > args.max_displacement:
            warnings.append(
                f"{a} -> {b}: scene moves {stats['median_disp_pct']:.1f}% of frame width "
                f"(> {args.max_displacement}%). SIFT still matches these, but optical flow "
                f"will not track that far — expect a ghosted blend, not a synthesized view. "
                f"Shoot this stretch of the arc closer together.")
            flag = "  <-- TOO FAR APART"
        disp = stats["median_disp_pct"]
        print(f"[{i:3d}] {a} -> {b}: {stats['inliers']:5d} inliers, scene moves "
              f"{'   n/a' if disp is None else f'{disp:5.1f}%'} of width{flag}")

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
    fell_back = sum(1 for pr in pairs if (pr["model_used"] or "").endswith("(fell back)"))
    if fell_back:
        print(f"  note: {fell_back}/{len(pairs)} pairs used a homography instead — near-planar "
              f"view, or you pivoted more than you walked across those frames")
    for msg in warnings:
        print(f"  WARNING: {msg}")


if __name__ == "__main__":
    main()
