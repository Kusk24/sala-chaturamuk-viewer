# Reconstruction comparison

3D reconstruction of the same pavilion, from the **same photographs** already used by the
image-based rendering pipeline in `src/`. Added at the course instructor's request for a
neural-network-produced 3D model.

This is a **comparison, not a replacement**. The IBR viewer synthesizes novel views without ever
recovering geometry; that remains the project's contribution. This directory answers the adjacent
question: what do you get, and what does it cost, if you *do* recover geometry from the same
input? See the amendment in `../CLAUDE.md`.

## Two stages

Both reconstruction approaches need the same first stage, so it runs once:

**1. Structure-from-motion — `run_sfm.sh` (local, no GPU)**

```
./recon/run_sfm.sh salathai_version2
```

COLMAP recovers each photograph's camera pose and a sparse point cloud. Output lands in
`recon/<version>/sparse/`. Runs on CPU; the Apple-silicon Mac has no CUDA, and COLMAP's GPU SIFT is
CUDA-only.

Matching is **sequential, not exhaustive** — the same restriction `src/match_features.py` applies,
for the same documented reason: the pavilion is four-porched and nearly symmetric under 90° rotation,
so faces far apart on the walk look alike. Exhaustive matching invites correspondences between
*different* faces, which SfM resolves as a folded camera path. This project already measured that
risk; the reconstruction inherits the finding.

**2. Neural rendering — Kaggle or Colab (needs a GPU)**

3D Gaussian splatting, consuming the poses from stage 1. Nothing here runs on the laptop: the
splatting rasteriser and COLMAP's dense stage are both CUDA-only, and this is an Apple silicon Mac.

- `sala_gaussian_splatting_kaggle.ipynb` — **preferred.** Kaggle's session is guaranteed for hours
  and the 105 MB input is uploaded *once* as a Dataset, so an interrupted run costs nothing.
- `sala_gaussian_splatting.ipynb` — Colab. Easier Drive integration, but the free tier
  idle-disconnects, which can kill a 30–50 minute training run partway.

Both take the same input bundle, `sala_v2_colmap.zip` (gitignored; rebuild it by copying
`data/selected_<version>/*.jpg` into `images/` and the sparse model's three `.bin` files into
`sparse/0/`).

Both train with `--eval`, holding out every 8th photograph. That is deliberate: it yields PSNR/SSIM
against real photographs the model never saw, which is the same kind of held-out measurement
`src/evaluate.py` performs for the IBR pipeline — so the two approaches compare on one footing
rather than by eye.

## What to expect from this data

Both captures are **single-height rings**: every photograph was taken from roughly eye level while
walking around the pavilion. The sides should reconstruct well. The **roof will not** — nothing ever
looked down on it, so expect a hole or noise above the eaves. This is a coverage limitation of the
capture, not of the method, and is worth reporting rather than hiding.

- `salathai_version1` — 206 photographs, partial arc, merged from two walks, wider spacing
- `salathai_version2` — 146 photographs, **closed 360° loop**, tighter spacing

`version2` is the better reconstruction candidate: a genuinely closed loop constrains the camera
path far better than an open arc. `version1` adds coverage and baseline diversity if needed.

## Outputs

Databases, sparse/dense models and point clouds are gitignored — they are large and fully
regenerable from the photographs. Measured summaries (how many cameras registered, reprojection
error) are small facts and belong in the paper, so they stay tracked.
