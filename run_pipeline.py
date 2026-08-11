#!/usr/bin/env python3
"""Run the whole pipeline end to end.

Put the capture in data/raw/ and run:

    python run_pipeline.py

That is the whole workflow. Drop in a folder of photographs, or a video of the
walkaround, and this finds it, runs every stage in order, and leaves you with
viewer/index.html ready to open.

    python run_pipeline.py --angular-step 12         # record the measured capture step
    python run_pipeline.py --every 15                # hold out frames for evaluation
    python run_pipeline.py --resume                  # skip stages already done
    python run_pipeline.py --dry-run                 # print the commands, run nothing
    python run_pipeline.py --from interpolate        # re-run the tail after tuning flow

Each stage is invoked as its own subprocess and its exact command line is
printed, so any stage can be lifted out and re-run by hand while tuning. This
file only sequences them; the real work stays in src/.

Evaluation only runs when there are held-out frames to evaluate against, i.e.
when --every is greater than 1. With 30 photographs and nothing withheld there
is no ground truth, so the stage is skipped and says so rather than inventing
a comparison.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "src")

VIDEO_EXTS = (".mov", ".mp4", ".m4v", ".avi", ".mkv")
IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")

STAGE_ORDER = ["extract", "subsample", "match", "interpolate", "sequence", "evaluate"]


def rel(path):
    return os.path.relpath(path, ROOT)


def has_images(directory):
    return any(n.lower().endswith(IMAGE_EXTS) for n in os.listdir(directory))


def discover_input(raw_dir):
    """Find the capture in data/raw/. Returns (path, kind) or exits with advice."""
    if not os.path.isdir(raw_dir):
        sys.exit(f"No {rel(raw_dir)}/ directory. Create it and put the capture inside.")

    entries = sorted(os.listdir(raw_dir))
    videos = [os.path.join(raw_dir, n) for n in entries if n.lower().endswith(VIDEO_EXTS)]
    if len(videos) > 1:
        sys.exit("Several videos in {}:\n  {}\nPick one with --input.".format(
            rel(raw_dir), "\n  ".join(rel(v) for v in videos)))
    if videos:
        return videos[0], "video"

    if has_images(raw_dir):
        return raw_dir, "stills"

    subdirs = [os.path.join(raw_dir, n) for n in entries
               if os.path.isdir(os.path.join(raw_dir, n)) and has_images(os.path.join(raw_dir, n))]
    if len(subdirs) == 1:
        return subdirs[0], "stills"
    if len(subdirs) > 1:
        sys.exit("Several photo folders in {}:\n  {}\nPick one with --input.".format(
            rel(raw_dir), "\n  ".join(rel(d) for d in subdirs)))

    sys.exit(
        f"Nothing to process in {rel(raw_dir)}/.\n\n"
        f"Put the capture there, then run this again:\n"
        f"  - a folder of photographs, or the photographs directly, or\n"
        f"  - the walkaround video (.mov/.mp4)\n\n"
        f"Shot video and want PSNR/SSIM? Add --every 15 to hold frames out for evaluation."
    )


def run(stage, cmd, dry_run):
    printable = " ".join(("python" if c == sys.executable else rel(c) if os.path.isabs(c) else c)
                         for c in cmd)
    print(f"\n\033[1m$ {printable}\033[0m" if sys.stdout.isatty() else f"\n$ {printable}")
    if dry_run:
        return 0.0
    start = time.time()
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(f"\nStage '{stage}' failed (exit {result.returncode}). "
                 f"Fix it and re-run with --from {stage}")
    return time.time() - start


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", default=None, help="capture video or photo folder (default: find it in data/raw/)")
    p.add_argument("--every", type=int, default=None,
                   help="keep every Nth frame as the capture set. >1 holds the rest out for "
                        "evaluation. Default: 15 for video, 1 for photographs")
    p.add_argument("--n-between", type=int, default=2, help="synthesized views per pair (default: 2)")
    p.add_argument("--angular-step", type=float, default=None,
                   help="measured degrees between captured frames; recorded, never guessed")
    p.add_argument("--start-angle", type=float, default=0.0)
    p.add_argument("--width", type=int, default=None, help="resize frames to this width")
    p.add_argument("--min-inliers", type=int, default=30, help="warn below this many inliers per pair")
    p.add_argument("--from", dest="from_stage", choices=STAGE_ORDER, default=None,
                   help="start at this stage")
    p.add_argument("--only", choices=STAGE_ORDER, default=None, help="run just this stage")
    p.add_argument("--resume", action="store_true", help="skip stages whose output already exists")
    p.add_argument("--dry-run", action="store_true", help="print the commands without running them")
    p.add_argument("--debug-matches", action="store_true", help="write match visualisations for inspection")
    args = p.parse_args()

    raw = os.path.join(ROOT, "data", "raw")
    frames = os.path.join(ROOT, "data", "frames")
    selected = os.path.join(ROOT, "data", "selected")
    sequence = os.path.join(ROOT, "output", "sequence")
    metrics = os.path.join(ROOT, "output", "metrics")
    matches = os.path.join(ROOT, "output", "matches.json")
    manifest = os.path.join(ROOT, "viewer", "manifest.json")

    if args.input:
        source = os.path.abspath(args.input)
        if not os.path.exists(source):
            sys.exit(f"No such input: {args.input}")
        kind = "video" if os.path.isfile(source) else "stills"
    else:
        source, kind = discover_input(raw)

    every = args.every if args.every is not None else (15 if kind == "video" else 1)
    if every < 1:
        sys.exit("--every must be >= 1")
    holdout = every > 1

    print(f"Capture   {rel(source)}  ({kind})")
    print(f"Capture set   every {every} frame{'s' if every > 1 else ''}"
          f"{'  (rest held out for evaluation)' if holdout else '  (nothing held out)'}")
    print(f"Synthesis     {args.n_between} in-between view(s) per adjacent pair")
    if args.angular_step is None:
        print("Angles        not recorded — pass --angular-step to write real angles")
    else:
        print(f"Angles        {args.angular_step} deg between captured frames")

    py = sys.executable
    common = ["--width", str(args.width)] if args.width else []

    # When nothing is held out, the capture set IS the input: extract straight
    # into data/selected/ and skip the subsample and evaluate stages.
    first_out = frames if holdout else selected

    stages = [
        ("extract", [py, os.path.join(SRC, "extract_frames.py"),
                     "--input", source, "--out", first_out, "--every", "1"] + common,
         os.path.join(first_out, "index.json"), True, ""),

        ("subsample", [py, os.path.join(SRC, "extract_frames.py"),
                       "--input", frames, "--out", selected, "--every", str(every)],
         os.path.join(selected, "index.json"), holdout,
         "nothing held out (--every 1), capture set is the full input"),

        ("match", [py, os.path.join(SRC, "match_features.py"),
                   "--frames", selected, "--out", matches,
                   "--min-inliers", str(args.min_inliers)]
                  + (["--debug-dir", os.path.join(ROOT, "output", "debug")] if args.debug_matches else []),
         matches, True, ""),

        ("interpolate", [py, os.path.join(SRC, "interpolate.py"),
                         "--frames", selected, "--out", sequence,
                         "--n-between", str(args.n_between)],
         os.path.join(sequence, "interpolation.json"), True, ""),

        ("sequence", [py, os.path.join(SRC, "build_sequence.py"),
                      "--frames", sequence, "--out", manifest,
                      "--start-angle", str(args.start_angle)]
                     + (["--angular-step", str(args.angular_step)] if args.angular_step is not None else []),
         manifest, True, ""),

        ("evaluate", [py, os.path.join(SRC, "evaluate.py"),
                      "--synth", sequence, "--truth", frames, "--out", metrics]
                     + (["--angular-step", str(args.angular_step)] if args.angular_step is not None else []),
         os.path.join(metrics, "metrics.csv"), holdout,
         "no held-out frames to score against — re-run with --every 15 or higher"),
    ]

    if args.only:
        wanted = {args.only}
    else:
        start = STAGE_ORDER.index(args.from_stage) if args.from_stage else 0
        wanted = set(STAGE_ORDER[start:])

    timings, skipped = [], []
    for i, (name, cmd, marker, enabled, why) in enumerate(stages, 1):
        label = f"[{i}/{len(stages)}] {name}"
        if name not in wanted:
            continue
        if not enabled:
            print(f"\n{label}: skipped — {why}")
            skipped.append((name, why))
            continue
        if args.resume and os.path.exists(marker):
            print(f"\n{label}: skipped — {rel(marker)} already exists (--resume)")
            skipped.append((name, "already done"))
            continue
        print(f"\n{label}")
        timings.append((name, run(name, cmd, args.dry_run)))

    if args.dry_run:
        print("\nDry run — nothing was executed.")
        return

    record = {
        "input": rel(source),
        "kind": kind,
        "every": every,
        "holdout": holdout,
        "n_between": args.n_between,
        "angular_step_deg": args.angular_step,
        "start_angle_deg": args.start_angle,
        "width": args.width,
        "stages_run": [name for name, _ in timings],
        "stages_skipped": [{"stage": n, "reason": w} for n, w in skipped],
        "seconds": {name: round(secs, 2) for name, secs in timings},
    }
    os.makedirs(os.path.join(ROOT, "output"), exist_ok=True)
    with open(os.path.join(ROOT, "output", "pipeline_run.json"), "w") as fh:
        json.dump(record, fh, indent=2)

    print("\n" + "-" * 60)
    for name, secs in timings:
        print(f"  {name:<12} {secs:6.1f}s")
    print(f"  {'total':<12} {sum(s for _, s in timings):6.1f}s")
    for name, why in skipped:
        print(f"  {name:<12} skipped — {why}")
    print("-" * 60)
    print(f"\nParameters recorded in {rel(os.path.join(ROOT, 'output', 'pipeline_run.json'))}")
    if os.path.exists(manifest):
        print(f"Open {rel(manifest).replace('manifest.json', 'index.html')} to view the result.")
    if not holdout:
        print("No metrics measured: nothing was held out. Re-run with --every 15 for PSNR/SSIM.")


if __name__ == "__main__":
    main()
