# Reconstruction comparison

3D reconstruction of the same pavilion, from the **same photographs** already used by the
image-based rendering pipeline in `src/`. Added at the course instructor's request for a
neural-network-produced 3D model.

This is a **comparison, not a replacement**. The IBR viewer synthesizes novel views without ever
recovering geometry; that remains the project's contribution. This directory answers the adjacent
question: what do you get, and what does it cost, if you *do* recover geometry from the same
input? See the amendment in `../CLAUDE.md`.

## Three routes, two of which share a first stage

| route | where | output | needs |
|---|---|---|---|
| COLMAP SfM → 3D Gaussian splatting | Kaggle / Colab | `.ply` splat cloud, browser-viewable | free cloud GPU |
| COLMAP SfM → NeRF (`nerfstudio`) | Kaggle / Colab | trained field, optional mesh | free cloud GPU |
| Apple `PhotogrammetrySession` | **this Mac** | `.usdz` **textured mesh** | nothing |

The first two need a GPU because both the splatting rasteriser and COLMAP's dense stage are
hand-written CUDA, which does not build on Apple silicon at any speed. The third runs on the M2's
own GPU and Neural Engine and is the only route that produces a conventional mesh — the thing most
people mean by "a 3D model".

They are also methodologically different, which is the point of running more than one: COLMAP is
classical, documented, and inspectable; Apple's engine is an undocumented commercial pipeline and
must be described as a black box rather than claimed to be classical MVS.

## The COLMAP stages

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

## Apple PhotogrammetrySession — `objectcapture/`

Runs entirely on this machine, no account and no quota:

```
swiftc -O recon/objectcapture/main.swift -o recon/objectcapture/photogrammetry
./recon/objectcapture/photogrammetry data/selected_salathai_version2 \
    recon/salathai_version2/sala_mesh.usdz medium
```

Swift, not Python, for one reason only: the engine lives in RealityKit, and Apple exposes it to
code alone — there is no shipped command and no Python binding. The tool is ~50 lines, compiled
once, then used like any other command.

It is told `sampleOrdering = .sequential` because the photographs are one ordered walk. That is the
same restriction applied to COLMAP's matching and the same one `src/match_features.py` already
documents: the pavilion is four-porched and nearly symmetric under 90° rotation, so comparing
frames out of order invites matches between different faces.

Detail levels are `preview | reduced | medium | full | raw`. `medium` is the useful middle; `full`
and `raw` produce very heavy meshes.

**Expected weakness:** the API is built for isolated objects on turntables, not buildings standing
in front of a lake and sky. A `stitchingIncomplete` warning means the mesh came out partial — the
tool surfaces that rather than swallowing it.

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
