#!/usr/bin/env python3
"""Measure the recovered camera path from a COLMAP sparse model.

    python recon/analyze_path.py salathai_version2

Writes recon/<version>/camera_path.json and a plot of the path seen from above.

Why this exists: the capture's start angle, end angle and mean angular spacing
were recorded on site as `[To record]` because no instrument measured them.
Structure-from-motion recovers the camera positions, so those angles can now be
*measured* rather than estimated -- from the reconstruction, which is how they
must be described in the paper.

It also answers a question the photographs alone cannot: whether the walk truly
closed back onto its starting point. Two photographs can match strongly and
still have been taken from different positions -- standing further back at a
slightly different bearing gives a similar view. Only the recovered geometry
settles it.

Note the reconstruction is up to an arbitrary similarity transform, so
distances here are in COLMAP units, not metres. Angles and ratios are
meaningful; absolute lengths are not.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np


def read_camera_centres(model_dir):
    """Return [(image_name, centre)] from a COLMAP images.txt.

    Each image contributes two lines; the first holds the world-from-camera
    rotation as a quaternion and the translation. The camera centre in world
    coordinates is C = -R^T t.
    """
    path = os.path.join(model_dir, "images.txt")
    if not os.path.isfile(path):
        sys.exit(f"No images.txt in {model_dir}. Convert first:\n"
                 f"  colmap model_converter --input_path {model_dir} "
                 f"--output_path {model_dir} --output_type TXT")
    with open(path) as fh:
        lines = [l for l in fh if not l.startswith("#") and l.strip()]

    out = []
    for i in range(0, len(lines), 2):     # skip each image's 2D-point line
        p = lines[i].split()
        qw, qx, qy, qz = map(float, p[1:5])
        t = np.array(list(map(float, p[5:8])))
        R = np.array([
            [1 - 2*(qy*qy + qz*qz), 2*(qx*qy - qz*qw),     2*(qx*qz + qy*qw)],
            [2*(qx*qy + qz*qw),     1 - 2*(qx*qx + qz*qz), 2*(qy*qz - qx*qw)],
            [2*(qx*qz - qy*qw),     2*(qy*qz + qx*qw),     1 - 2*(qx*qx + qy*qy)],
        ])
        out.append((p[9], -R.T @ t))
    out.sort(key=lambda r: r[0])          # capture order == filename order
    return out


def main():
    version = sys.argv[1] if len(sys.argv) > 1 else sys.exit(
        "usage: analyze_path.py <version-name>")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    work = os.path.join(root, "recon", version)
    model = os.path.join(work, "sparse", "0")

    names, centres = zip(*read_camera_centres(model))
    C = np.array(centres)

    # The walk is one ring at one height, so the camera centres are nearly
    # coplanar: two large singular values and one small one. Work in that plane.
    centroid = C.mean(0)
    _, sv, vt = np.linalg.svd(C - centroid)
    plane = (C - centroid) @ vt[:2].T
    out_of_plane = (C - centroid) @ vt[2]

    radius = np.linalg.norm(plane, axis=1)
    ang = np.unwrap(np.arctan2(plane[:, 1], plane[:, 0]))
    total_arc = abs(float(np.degrees(ang[-1] - ang[0])))
    step = np.abs(np.diff(np.degrees(ang)))
    neighbour = np.linalg.norm(np.diff(C, axis=0), axis=1)
    end_gap = float(np.linalg.norm(C[0] - C[-1]))

    # A genuinely closed walk ends roughly one normal step from where it began.
    closes = end_gap <= 3 * float(neighbour.mean())

    result = {
        "version": version,
        "n_cameras": len(C),
        "planarity_singular_values": [round(float(s), 3) for s in sv],
        "out_of_plane_sd": round(float(out_of_plane.std()), 3),
        "radius": {"mean": round(float(radius.mean()), 3),
                   "min": round(float(radius.min()), 3),
                   "max": round(float(radius.max()), 3),
                   "sd": round(float(radius.std()), 3)},
        "total_arc_deg": round(total_arc, 1),
        "angular_step_deg": {"mean": round(float(step.mean()), 2),
                             "median": round(float(np.median(step)), 2),
                             "max": round(float(step.max()), 2)},
        "neighbour_distance": {"mean": round(float(neighbour.mean()), 3),
                               "max": round(float(neighbour.max()), 3)},
        "first_to_last_distance": round(end_gap, 3),
        "walk_closes_onto_start": bool(closes),
        "units": "COLMAP units (arbitrary scale); angles are in degrees",
    }

    with open(os.path.join(work, "camera_path.json"), "w") as fh:
        json.dump(result, fh, indent=2)
    print(json.dumps(result, indent=2))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(6, 6), dpi=150)
    ax.plot(plane[:, 0], plane[:, 1], "-", lw=1, color="#bbb", zorder=1)
    sc = ax.scatter(plane[:, 0], plane[:, 1], c=np.arange(len(plane)),
                    cmap="viridis", s=20, zorder=3)
    ax.scatter(*plane[0], marker="*", s=250, color="#d62728", zorder=4, label="first photograph")
    ax.scatter(*plane[-1], marker="X", s=140, color="#1f77b4", zorder=4, label="last photograph")
    ax.scatter(0, 0, marker="+", s=180, color="k", zorder=4, label="pavilion (centroid)")
    ax.set_aspect("equal")
    ax.set_title(f"Recovered camera path — {version}\n"
                 f"{len(C)} cameras, {total_arc:.0f}° arc", fontsize=11)
    ax.legend(fontsize=8, loc="center")
    fig.colorbar(sc, ax=ax, label="capture order", shrink=.8)
    fig.tight_layout()
    fig.savefig(os.path.join(work, "camera_path.png"))
    print("\nplot:", os.path.join(work, "camera_path.png"))


if __name__ == "__main__":
    main()
