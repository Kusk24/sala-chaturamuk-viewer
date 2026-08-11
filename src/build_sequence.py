#!/usr/bin/env python3
"""Stage 5: order the frames and write the viewer manifest.

    python src/build_sequence.py --frames output/sequence/ --out viewer/manifest.json

Real and synthesized frames are ordered by capture angle and tagged, so the
viewer can show either the full interpolated sequence or just the captured
frames (the object-movie baseline) without rebuilding anything.

Angles come from what you measured on site. Preferred form is the measured arc:

    --start-angle 0 --end-angle 214

from which the mean angular step is DERIVED against the real frame count,
rather than assumed uniform. --angular-step is still accepted for the case
where you only have a nominal step. Supply neither and frames carry angle: null
and the viewer shows an index -- this script will not guess an arc.

The run prints the four values the paper's Table I asks for (displayed frames
and mean angular step, for the captured-only baseline and the interpolated
sequence), all derived from the measurement rather than assumed.

--wraparound closes the last captured frame back onto the first. Leave it off
unless a full revolution was genuinely walked; the lake normally prevents one,
and a partial arc that pretends to loop will tear at the seam.

Two files are written next to each other:

    manifest.json   canonical output
    manifest.js     same data as `window.SALA_MANIFEST = {...}`

The .js copy exists because browsers block fetch() of local .json over file://,
and CLAUDE.md requires the viewer to open straight from file:// with no server.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

IMAGE_EXTS = (".jpg", ".jpeg", ".png")
# frame_0007.jpg  or  frame_0007_i2.jpg
PATTERN = re.compile(r"^frame_(\d+)(?:_i(\d+))?\.(?:jpg|jpeg|png)$", re.IGNORECASE)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--frames", required=True, help="sequence directory from interpolate.py")
    p.add_argument("--out", required=True, help="output manifest path (.json)")
    p.add_argument("--start-angle", type=float, default=0.0,
                   help="measured angle of the FIRST captured frame (default: 0)")
    p.add_argument("--end-angle", type=float, default=None,
                   help="measured angle of the LAST captured frame. Preferred: the mean angular "
                        "step is then derived from the real frame count instead of assumed")
    p.add_argument("--angular-step", type=float, default=None,
                   help="nominal degrees between captured frames; use --end-angle instead "
                        "once you have measured the arc")
    p.add_argument("--wraparound", action="store_true",
                   help="close the last captured frame back onto the first. Only pass this if a "
                        "full revolution was genuinely walked")
    args = p.parse_args()

    if args.end_angle is not None and args.angular_step is not None:
        sys.exit("Pass either --end-angle (measured arc) or --angular-step (nominal), not both.")

    if not os.path.isdir(args.frames):
        sys.exit(f"No such directory: {args.frames}")

    # Prefer the t values interpolate.py recorded; fall back to even spacing.
    recorded = {}
    n_between = None
    meta_path = os.path.join(args.frames, "interpolation.json")
    if os.path.isfile(meta_path):
        with open(meta_path) as fh:
            meta = json.load(fh)
        n_between = meta.get("n_between")
        recorded = {r["file"]: r for r in meta.get("frames", [])}
    else:
        print(f"note: no interpolation.json in {args.frames}; inferring spacing from filenames")

    entries = []
    for name in os.listdir(args.frames):
        if not name.lower().endswith(IMAGE_EXTS):
            continue
        m = PATTERN.match(name)
        if not m:
            print(f"  skipped unrecognised filename: {name}")
            continue
        base = int(m.group(1))
        sub = int(m.group(2)) if m.group(2) else 0
        entries.append((base, sub, name))

    if not entries:
        sys.exit(f"No frames matching frame_NNNN[_iK].jpg in {args.frames}")
    entries.sort()

    if n_between is None:
        n_between = max(sub for _, sub, _ in entries)

    n_captured = max(base for base, _, _ in entries) + 1
    # A closed revolution has one interval more than a partial arc, because the
    # last captured frame closes back onto the first.
    spans = n_captured if args.wraparound else n_captured - 1
    if spans < 1:
        sys.exit("Need at least 2 captured frames to define an arc.")

    step = args.angular_step
    arc = None
    if args.end_angle is not None:
        arc = args.end_angle - args.start_angle
        step = arc / spans          # derived from the measurement, not assumed
    elif step is not None:
        arc = step * spans

    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    rel_root = os.path.relpath(os.path.abspath(args.frames), out_dir).replace(os.sep, "/")

    frames = []
    for i, (base, sub, name) in enumerate(entries):
        rec = recorded.get(name)
        if rec is not None:
            t = rec["t"]
            real = rec["kind"] == "real"
        else:
            t = sub / (n_between + 1) if n_between else 0.0
            real = sub == 0
        angle = None if step is None else round(args.start_angle + (base + t) * step, 4)
        frames.append({
            "index": i,
            "file": f"{rel_root}/{name}",
            "real": real,
            "captured_index": base,
            "t": round(t, 6),
            "angle_deg": angle,
        })

    n_real = sum(1 for f in frames if f["real"])
    displayed_spans = len(frames) if args.wraparound else len(frames) - 1
    manifest = {
        "generated_by": "build_sequence.py",
        "sequence_dir": args.frames,
        "n_frames": len(frames),
        "n_captured": n_real,
        "n_synthesized": len(frames) - n_real,
        "n_between": n_between,
        # The pavilion sits on the lake edge, so the accessible path is normally
        # a partial arc and the viewer clamps at both ends. Only a genuinely
        # walked full revolution sets this true.
        "wraparound": args.wraparound,
        "start_angle_deg": args.start_angle,
        "end_angle_deg": args.end_angle if args.end_angle is not None else (
            None if arc is None else round(args.start_angle + arc, 4)),
        "total_arc_deg": None if arc is None else round(arc, 4),
        "angle_source": "measured arc" if args.end_angle is not None else (
            "nominal step" if args.angular_step is not None else "not recorded"),
        # Table I of the paper: displayed frames and mean angular step, for the
        # captured-only baseline and for the interpolated sequence.
        "angular_step_deg": None if step is None else round(step, 4),
        "mean_step_baseline_deg": None if step is None else round(step, 4),
        "mean_step_interpolated_deg": None if arc is None else round(arc / displayed_spans, 4),
        "frames": frames,
    }

    with open(args.out, "w") as fh:
        json.dump(manifest, fh, indent=2)

    js_path = os.path.splitext(args.out)[0] + ".js"
    with open(js_path, "w") as fh:
        fh.write("// Generated by build_sequence.py -- do not edit.\n")
        fh.write("// Loaded via <script> so the viewer works over file:// too.\n")
        fh.write("window.SALA_MANIFEST = ")
        json.dump(manifest, fh, indent=2)
        fh.write(";\n")

    print(f"{len(frames)} frames ({n_real} captured + {len(frames) - n_real} synthesized)")
    print(f"  {args.out}")
    print(f"  {js_path}")
    print(f"  arc: {'closed revolution' if args.wraparound else 'partial (no wraparound)'}")

    if step is None:
        print("\n  angles: null — pass --start-angle/--end-angle once the arc is measured")
        return

    print(f"  angles: {frames[0]['angle_deg']} .. {frames[-1]['angle_deg']} deg "
          f"({manifest['angle_source']}, {manifest['total_arc_deg']} deg total)")
    print("\n  Table I — measured, ready for the paper:")
    print(f"    {'':<34}{'Baseline':>10}{'Interp.':>10}")
    print(f"    {'Displayed frames':<34}{n_real:>10}{len(frames):>10}")
    print(f"    {'Mean angular step between frames':<34}"
          f"{manifest['mean_step_baseline_deg']:>9.2f}°{manifest['mean_step_interpolated_deg']:>9.2f}°")


if __name__ == "__main__":
    main()
