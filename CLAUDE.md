# Sala Viewer — Project Instructions

## What this is

A Computer Vision term project (CSX4213 / ITX4283, Assumption University of Thailand) implementing
**image-based rendering (IBR)** for Sala Chaturamuk Phaichit, the four-porched Thai pavilion on the
Suvarnabhumi campus.

The deliverable is an interactive web viewer that lets a user rotate around the pavilion, where the
in-between viewpoints are **synthesized from photographs** rather than rendered from geometry.

Team: Win Yu Maung, Myat Bhone Thet, Min Pyae Hein.
The paper draft lives at `paper/CSX4213_Sala_Thai.docx`.

---

## The hard constraint — read this before proposing any approach

This project follows **Szeliski, *Computer Vision: Algorithms and Applications*, Chapter 14
(Image-Based Rendering)**. The academic point is synthesizing novel views **without recovering
explicit 3D geometry**.

**Do not** substitute any of these for the IBR pipeline in `src/`:

- COLMAP / OpenMVG / Meshroom or any full structure-from-motion + MVS reconstruction
- Photogrammetry producing a mesh or textured 3D model
- NeRF, Gaussian splatting, or any learned radiance-field method
- Anything that outputs a point cloud or mesh as the rendering primitive

These are all *better* at making a nice 3D demo, and that is exactly why the IBR result must not
quietly become one of them. The viewer in `viewer/` and the pipeline in `src/` stay geometry-free.

**Amendment (2026-08-29):** the course instructor has asked for a 3D model produced with neural
methods, so reconstruction is now in scope **as a separate, clearly-labelled comparison** living in
`recon/` — never as a replacement for, or silent upgrade to, the IBR pipeline. The paper keeps
image-based rendering as its contribution and reports reconstruction alongside it: same
photographs, two approaches, compared on cost, coverage and quality. If a task would blur the two
(e.g. feeding reconstructed geometry back into the viewer, or describing the IBR result as a 3D
model), say so and stop.

Feature matching (SIFT/ORB) is used **only** to establish 2D correspondences between adjacent frames
for warping. It is not a step toward reconstruction.

**In scope:** view interpolation (Chen & Williams), view morphing (Seitz & Dyer), optical-flow-based
warping and cross-dissolve, object-movie frame sequencing.

---

## Pipeline

1. **Capture** — photographs (or video walked along an arc) around the pavilion. Phone at 1x in
   landscape, constant distance and height, aimed at the pavilion's centre, targeting 5–8° between
   adjacent shots, with exposure/white balance/focus locked. Start angle, end angle, total arc and
   photograph count are recorded on site; every angle downstream derives from those measurements.
2. **Frame extraction / selection** — if video, extract frames and subsample to a capture set.
3. **Correspondence** — SIFT keypoints matched between *adjacent* frames only, RANSAC-filtered.
4. **Interpolation** — dense optical flow (Farneback baseline) between adjacent pairs; backward-warp
   (cv2.remap, to avoid the holes forward scatter leaves) and cross-dissolve to synthesize
   intermediate views.
5. **Sequencing** — order real + synthesized frames by angle, export as an indexed sequence.
6. **Viewer** — drag-to-rotate web viewer over that sequence.
7. **Evaluation** — see below.

### Two site-specific problems to respect

- **Partial arc.** The pavilion sits at the edge of the campus lake, and site boundaries may prevent
  a continuous constant-radius path around all four sides. The pipeline represents the **measured
  accessible arc** and must not assume wraparound. Do not hardcode 360° or assume `frame[n]`
  neighbours `frame[0]`. The last frame is joined back to the first only when `--wraparound` is
  passed, which is only legitimate if a full revolution was genuinely walked.
- **Four-fold symmetry.** "Chaturamuk" means four-faced; views ~90° apart look nearly identical.
  This causes **false feature matches between different faces**. Always restrict matching to adjacent
  frames and filter with RANSAC. Never match globally across the whole set.

---

## Evaluation — how we get real numbers

Preferred method (requires video capture): **hold-out validation.**

1. Extract all frames from the walk.
2. Subsample every Nth frame → "captured set".
3. Interpolate between captured frames.
4. Compare synthesized frames against the **real held-out frames** at those angles.
5. Report **PSNR** and **SSIM**, and plot error against angular spacing.

This turns the paper's subjective smoothness rating into a real measurement. Write metrics to
`output/metrics/` as CSV so they can go straight into the paper's Table I.

---

## Rules for writing results

**Never invent, estimate, or placeholder a number as if it were measured.** No example PSNR values,
no "typical" SSIM, no illustrative timings. If a metric hasn't been computed from real data, leave
it explicitly empty or `TBD`.

This applies to code comments, README tables, notebook markdown, and any text written toward the
paper. The paper currently carries `[To record]` markers exactly for this reason — they get replaced
by measured output, never by plausible-sounding prose.

If asked to "fill in" results, produce the script that computes them instead.

---

## Structure

```
sala-chaturamuk-viewer/
├── CLAUDE.md
├── README.md
├── requirements.txt
├── run_pipeline.py   # runs every stage in order; the normal entry point
├── data/
│   ├── raw/          # source video / original photos (gitignored — large)
│   ├── frames/       # extracted frames        + index.json
│   └── selected/     # subsampled capture set  + index.json
├── src/
│   ├── extract_frames.py
│   ├── match_features.py
│   ├── interpolate.py
│   ├── build_sequence.py
│   └── evaluate.py
├── viewer/
│   ├── index.html
│   ├── app.js
│   ├── manifest.json # generated by build_sequence.py
│   └── manifest.js   # same data, <script>-loadable so file:// works
├── output/
│   ├── matches.json       # adjacent-pair inlier counts (QC)
│   ├── pipeline_run.json  # parameters and timings of the last full run
│   ├── sequence/          # final ordered frames + interpolation.json
│   └── metrics/           # PSNR/SSIM CSVs (committed — these feed the paper)
└── paper/
    └── CSX4213_Sala_Thai.docx
```

The `index.json` / `interpolation.json` files are how stages hand context to each other — in
particular they let `evaluate.py` work out which real frame each synthesized frame should be scored
against. Keep writing them if you change a stage.

## Conventions

- Python 3.11+, OpenCV (`opencv-python`), NumPy, scikit-image (for SSIM).
- Each `src/` script is runnable standalone with argparse; no notebook-only logic.
- Frames named zero-padded by index: `frame_0042.jpg`. Synthesized frames carry a suffix
  (`frame_0042_i1.jpg`) so real and synthetic are always distinguishable on disk.
- Viewer is vanilla HTML/JS — no build step, no framework. It must open from `file://`.
- Do not commit anything in `data/raw/`.

## Working style

- Ask before adding a dependency.
- Prefer small, inspectable steps over one large pipeline script — each stage's output should be
  visually checkable.
- When something can't be done within the IBR constraint, say so plainly rather than working around it.
