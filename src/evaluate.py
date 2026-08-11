#!/usr/bin/env python3
"""Stage 6: hold-out validation of the synthesized views.

    python src/evaluate.py --synth output/sequence/ --truth data/frames/ --out output/metrics/

The idea (CLAUDE.md, "Evaluation"): extract every frame of the walk, keep only
every Nth as the capture set, interpolate between those, then compare each
synthesized frame against the REAL frame that was held out at that position.

Each synthesized frame is scored twice against the same ground truth:

    interp    the flow-interpolated frame
    baseline  the nearest captured frame, i.e. what a plain object-movie viewer
              would have shown at that angle

That pairing is what makes Table I of the paper a measurement rather than an
impression. Nothing here invents a number: if a ground-truth frame is missing,
the row is skipped and reported, not estimated.

The frame -> frame mapping is read from the index.json / interpolation.json
files the earlier stages wrote, so it stays correct even with an uneven capture.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import sys

import cv2
import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


def load_json(path, what):
    if not os.path.isfile(path):
        sys.exit(f"Missing {what}: {path}")
    with open(path) as fh:
        return json.load(fh)


def psnr_ssim(truth, test):
    psnr = peak_signal_noise_ratio(truth, test, data_range=255)
    ssim = structural_similarity(truth, test, channel_axis=2, data_range=255)
    return psnr, ssim


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--synth", required=True, help="sequence directory from interpolate.py")
    p.add_argument("--truth", required=True, help="directory of ALL extracted frames (ground truth)")
    p.add_argument("--out", required=True, help="output directory for metric CSVs")
    p.add_argument("--selected", default=None,
                   help="capture-set directory (default: read from interpolation.json)")
    p.add_argument("--angular-step", type=float, default=None,
                   help="measured degrees between captured frames; recorded in the CSV if given")
    p.add_argument("--resize-truth", action="store_true",
                   help="resize ground truth to the synthesized size instead of erroring")
    p.add_argument("--append-summary", action="store_true",
                   help="append to summary.csv instead of overwriting (for sweeping --every)")
    args = p.parse_args()

    interp = load_json(os.path.join(args.synth, "interpolation.json"), "interpolation.json")
    selected_dir = args.selected or interp["frames_dir"]
    selected = load_json(os.path.join(selected_dir, "index.json"), "capture-set index.json")
    truth = load_json(os.path.join(args.truth, "index.json"), "ground-truth index.json")

    # source_index is the frame number in the original capture, shared by both.
    truth_by_source = {entry["source_index"]: entry["file"] for entry in truth["frames"]}
    selected_entries = selected["frames"]

    os.makedirs(args.out, exist_ok=True)

    rows, skipped = [], []
    for rec in interp["frames"]:
        if rec["kind"] != "synth":
            continue
        a, b, t = rec["pair_a"], rec["pair_b"], rec["t"]
        if a >= len(selected_entries) or b >= len(selected_entries):
            skipped.append((rec["file"], "capture-set index out of range"))
            continue

        src_a = selected_entries[a]["source_index"]
        src_b = selected_entries[b]["source_index"]
        src_truth = round(src_a + t * (src_b - src_a))
        if src_truth not in truth_by_source:
            skipped.append((rec["file"], f"no ground-truth frame at source index {src_truth}"))
            continue
        if src_truth in (src_a, src_b):
            skipped.append((rec["file"], "would score against a captured frame; capture set is too dense"))
            continue

        truth_img = cv2.imread(os.path.join(args.truth, truth_by_source[src_truth]))
        synth_img = cv2.imread(os.path.join(args.synth, rec["file"]))
        baseline_name = selected_entries[a if t < 0.5 else b]["file"]
        baseline_img = cv2.imread(os.path.join(selected_dir, baseline_name))
        if truth_img is None or synth_img is None or baseline_img is None:
            skipped.append((rec["file"], "could not read one of the images"))
            continue

        if truth_img.shape != synth_img.shape:
            if not args.resize_truth:
                sys.exit(
                    f"Size mismatch: ground truth {truth_img.shape[1]}x{truth_img.shape[0]} vs "
                    f"synthesized {synth_img.shape[1]}x{synth_img.shape[0]}.\n"
                    f"Re-extract both at the same --width, or pass --resize-truth."
                )
            truth_img = cv2.resize(truth_img, (synth_img.shape[1], synth_img.shape[0]),
                                   interpolation=cv2.INTER_AREA)

        psnr_i, ssim_i = psnr_ssim(truth_img, synth_img)
        psnr_b, ssim_b = psnr_ssim(truth_img, baseline_img)
        rows.append({
            "synth_file": rec["file"],
            "truth_file": truth_by_source[src_truth],
            "baseline_file": baseline_name,
            "pair_a": a, "pair_b": b, "t": t,
            "source_a": src_a, "source_b": src_b, "source_truth": src_truth,
            "angular_gap_deg": args.angular_step if args.angular_step is not None else "",
            "psnr_interp_db": round(psnr_i, 4),
            "ssim_interp": round(ssim_i, 6),
            "psnr_baseline_db": round(psnr_b, 4),
            "ssim_baseline": round(ssim_b, 6),
        })
        print(f"{rec['file']} vs {truth_by_source[src_truth]}: "
              f"PSNR {psnr_i:6.2f} dB (baseline {psnr_b:6.2f}), "
              f"SSIM {ssim_i:.4f} (baseline {ssim_b:.4f})")

    for name, why in skipped:
        print(f"  skipped {name}: {why}")

    if not rows:
        sys.exit("\nNo synthesized frame could be scored -- nothing written. "
                 "Check that --truth holds every extracted frame and that the "
                 "capture set was subsampled from it.")

    metrics_path = os.path.join(args.out, "metrics.csv")
    with open(metrics_path, "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "n_scored": len(rows),
        "n_skipped": len(skipped),
        "n_captured": len(selected_entries),
        "n_between": interp["n_between"],
        "angular_gap_deg": args.angular_step if args.angular_step is not None else "",
        "psnr_interp_mean_db": round(statistics.fmean(r["psnr_interp_db"] for r in rows), 4),
        "psnr_interp_median_db": round(statistics.median(r["psnr_interp_db"] for r in rows), 4),
        "ssim_interp_mean": round(statistics.fmean(r["ssim_interp"] for r in rows), 6),
        "psnr_baseline_mean_db": round(statistics.fmean(r["psnr_baseline_db"] for r in rows), 4),
        "psnr_baseline_median_db": round(statistics.median(r["psnr_baseline_db"] for r in rows), 4),
        "ssim_baseline_mean": round(statistics.fmean(r["ssim_baseline"] for r in rows), 6),
    }
    summary_path = os.path.join(args.out, "summary.csv")
    exists = os.path.isfile(summary_path)
    mode = "a" if args.append_summary and exists else "w"
    with open(summary_path, mode, newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary.keys()))
        if mode == "w" or not exists:
            writer.writeheader()
        writer.writerow(summary)

    print(f"\nScored {len(rows)} synthesized frames ({len(skipped)} skipped)")
    print(f"  interp   PSNR {summary['psnr_interp_mean_db']:.2f} dB   "
          f"SSIM {summary['ssim_interp_mean']:.4f}")
    print(f"  baseline PSNR {summary['psnr_baseline_mean_db']:.2f} dB   "
          f"SSIM {summary['ssim_baseline_mean']:.4f}")
    print(f"  {metrics_path}\n  {summary_path}")


if __name__ == "__main__":
    main()
