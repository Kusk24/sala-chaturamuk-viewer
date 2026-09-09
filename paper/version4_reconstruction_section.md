# Reconstruction Comparison — rewritten section

*Draft for the Version 4 report. Every figure below is measured; anything not yet
computed is marked TBD rather than estimated.*

---

## 1. Why this section exists

The contribution of this project is **image-based rendering**: synthesizing novel viewpoints
directly from photographs, without ever recovering explicit 3D geometry (Szeliski, Ch. 14). At
the instructor's request we additionally produced 3D models, and this section reports them as a
**clearly-labelled comparison** rather than as a replacement. Same photographs, three methods,
compared on cost, coverage and quality. The image-based renderer remains geometry-free; no
reconstructed geometry is fed back into it.

Two reconstruction routes were completed:

| Route | Primitive | Where it ran |
|---|---|---|
| Apple Object Capture (photogrammetry) | textured triangle mesh | locally, Apple M2 |
| COLMAP → 3D Gaussian Splatting | radiance field of oriented Gaussians | Kaggle, NVIDIA T4 |

A third route, NeRF, is scaffolded on the same COLMAP output but **was not run**. We therefore
make no claim about it.

---

## 2. Route 1 — Photogrammetry

### 2.1 The sky problem, and the masking fix

The first reconstruction attempt turned the overcast sky into geometry: a white sheet draped
over the roof like a tarpaulin. Sky is bright, smooth and featureless, so the engine had no
texture to anchor depth against and invented a surface instead.

The fix was **per-image sky masking**. For each photograph a binary companion image marks which
pixels are sky, passed to the engine as `objectMask`, where 0 means *ignore*. Sky is detected
from three cues combined — high brightness, low saturation, and low gradient magnitude (Sobel) —
with the additional requirement that the region touches the top border of the frame. 146 masks
were generated, one per version-2 photograph.

### 2.2 Version 4

- Input: **146 photographs** (version 2, the close-range ring)
- Engine: Apple `PhotogrammetrySession`, detail `full`, sequential sample ordering
- Raw output: **249,999 faces**
- Post-processing: crop → polish → refine, giving a final **165,906 faces**

The roof required special handling. Every photograph was taken at approximately eye level, so
**no camera ever looked down on the ridge**. The reconstruction therefore had no data at the
top of the roof. A cross-gable surface *h(u,v) = H − s·min(|u|,|v|)* was fitted to the observed
roof planes and approximately **6,100 faces were generated** to close the gap, textured from a
tile swatch. The mesh was then Taubin-smoothed (λ = 0.5, μ = −0.53, 30 iterations).

**This is the section's most important caveat: that part of the model is synthesized, not
measured.** It is reported here rather than presented as reconstruction.

### 2.3 Version A — combining both capture sets

An earlier experiment had combined version 1 (206 photographs, shot from across the lake) with
version 2 and been **rejected**: COLMAP registered 351 of 352 images at 0.99 px mean
reprojection error, but the geometry was folded. The cause was the pavilion's four-fold
rotational symmetry — "chaturamuk" means four-faced — which makes views 90° apart nearly
identical, so exhaustive matching produced correspondences between *different* faces that the
mapper resolved into a self-consistent but globally wrong reconstruction. The sub-pixel
reprojection error is precisely why the failure was not visible in the numbers.

That result was, in retrospect, **over-generalized**. It is a property of COLMAP's exhaustive
matching, not of the photographs. Re-running the same combined set through Apple Object Capture
with unordered matching produced a correct, unfolded model:

- Input: **352 photographs** (version 1 + version 2), 351 registered
- Detail `medium`, no masks, no post-processing
- Output: **100,000 faces**

Version A has visibly better texture than Version 4 and a genuinely observed roof rather than a
generated one, at lower geometric resolution. **Version A has not been scored against held-out
photographs; that measurement is TBD.**

The same weakness appears in the mesh. Of the 40,472 faces inside the pavilion crop radius,
binned the same way, the weakest sectors run **18 % to 28 % of the median** density over a
contiguous arc of about 70°. The two models were reconstructed by different engines in different
arbitrary coordinate frames, so these azimuths cannot be compared directly and we do not claim
they describe the same physical face without registering the two frames. What can be said is
that **each reconstruction, independently, is thin over one contiguous arc of roughly 60–70°.**

The methodological point worth reporting: *a negative result from one algorithm does not
transfer to another*, and re-testing cost one 50-minute run.

---

## 3. Route 2 — 3D Gaussian Splatting

### 3.1 Method

Rather than triangles, the scene is represented as several hundred thousand oriented 3D
Gaussians, each carrying a position, a covariance, an opacity and a view-dependent colour
encoded in spherical harmonics. These parameters are optimized by gradient descent until the
rendered images match the input photographs. There is no mesh and no surface at any stage.

**It should not be described as a neural network.** There is no multilayer perceptron anywhere
in the method; it is gradient-based optimization of explicit primitives. It belongs to the
neural-rendering line of research, and that is the accurate phrasing.

### 3.2 Pipeline

1. COLMAP structure-from-motion, run locally on CPU. All **146 photographs registered** into a
   single model at **0.58 px mean reprojection error**. Matching was restricted to sequential
   neighbours for the four-fold-symmetry reason above.
2. Undistortion to a pinhole camera model.
3. Training on Kaggle: **30,000 iterations, ≈ 1 h 36 min on an NVIDIA T4**, holding out every
   8th photograph for evaluation.

### 3.3 Problems encountered

**No local GPU path.** Both the Gaussian rasterizer and COLMAP's dense stage are hand-written
CUDA and do not build on Apple silicon at any usable speed. The entire route therefore had to be
moved to a free cloud GPU, which is the single largest cost difference between this route and
photogrammetry — the latter runs on the laptop's own hardware with no setup.

**GPU selection silently breaks training.** Kaggle offers both the P100 and the T4. The P100 is
compute capability 6.0, which the runtime's PyTorch build no longer supports. The CUDA
extensions *compile successfully* on it and training then aborts — a failure that costs roughly
an hour before it surfaces. `TORCH_CUDA_ARCH_LIST` is set explicitly to `7.5` and an assertion
checks the device before any long step runs.

**Read-only input mount.** `/kaggle/input/` cannot be written to, but the training code writes
`points3D.ply` beside the COLMAP binaries on first load. The scene must be copied into
`/kaggle/working/` first or the run fails immediately.

**The output is not a conventional 3D model.** `point_cloud.ply` holds Gaussians, not geometry.
It cannot be opened by Preview, Quick Look, or any mesh viewer, and it cannot be imported into
the project's existing three.js page. Viewing it requires a dedicated splat renderer.

**Model retrieval.** Only the evaluation outputs — metrics and rendered views — were initially
retrieved from Kaggle; the trained model itself was left behind, so for a period the result
existed only as images. On re-download, the **30,000-iteration checkpoint returns 0 bytes on
every attempt**, and the recovered model is therefore the **15,000-iteration checkpoint
(554,618 Gaussians)**. The quoted scores below belong to the 30,000-iteration checkpoint and do
not describe the model currently in hand.

**One side of the pavilion reconstructs thinly.** Counting Gaussians in the inner 40 % of the
model by radius — 221,847 of them, the pavilion itself rather than the surrounding lawn — and
binning them by azimuth in 10° sectors weighted by opacity, the arc from roughly **100° to 160°
is persistently sparse**: 29 %, 36 %, 45 % and 55 % of the median sector density, with the
weakest sector at 140–160°. The rest of the ring sits near the median. The capture's single
largest angular gap, 9.8° between 152.6° and 162.4°, falls at the edge of that same arc, so
thinner photographic coverage is the plausible cause. Visually this reads as one face of the
building failing to close, with the structure breaking up rather than forming a continuous
surface.

**Quality falls off away from the capture path.** The capture is a single-height ring at roughly
2.4° mean angular spacing. Near those camera positions the model is sharp; away from them it
interpolates confidently and incorrectly. The roof is the worst case, for the same reason it is
worst in photogrammetry: nothing ever looked down on it.

### 3.4 Result

Scored against **19 held-out photographs** the model never saw during training:

| Metric | Value |
|---|---|
| PSNR | **22.09 dB** |
| SSIM | **0.785** |
| LPIPS | **0.346** |

---

## 4. Comparison

| | Image-based rendering | Photogrammetry | Gaussian splatting |
|---|---|---|---|
| Output primitive | photographs | triangle mesh | oriented Gaussians |
| Explicit geometry | none | yes | none |
| Hardware | laptop CPU | laptop GPU | cloud GPU required |
| Training time | none | ≈ 50 min | ≈ 1 h 36 min |
| Held-out PSNR | **13.88 dB** | TBD | **22.09 dB** |
| Held-out SSIM | **0.491** | TBD | **0.785** |
| Roof coverage | n/a — never claims 3D | synthesized (~6,100 faces) | unresolved |

**These PSNR figures are not directly comparable and should not be presented as a ranking.** The
image-based renderer is scored on interpolated viewpoints *between* captured frames against a
frame-switching baseline of 13.27 dB, over 144 scored frames; the splatting model is scored on
every 8th photograph held out from training, over 19 frames. They measure different things on
different splits. What can be said is that each beats the trivial alternative in its own setting.

---

## 5. What the comparison shows

1. **Neither reconstruction route recovers the roof.** Both fail in the same place and for the
   same reason — the capture is a single eye-level ring, and no photograph looks down on the
   ridge. This is a limitation of the capture, not of either method. A follow-up capture from
   the upper floors of the adjacent building is planned to address it.

2. **Appearance survives better without geometry.** The splatting result is visually far closer
   to the photographs than either mesh, because a mesh must commit to one shape and one colour
   per patch, while Gaussians carry view-dependent colour. The gilded ornament and the dark
   interior are reproduced by the radiance field and lost by the mesh.

3. **Both reconstructions thin out over one arc, not just at the roof.** Measured by azimuthal
   density, each model is sparse over a contiguous 60–70° sector at 18–55 % of its median
   density elsewhere. In the splatting model that arc coincides with the capture's largest
   angular gap. This is a second coverage limit alongside the roof, and it argues that the
   re-capture should not merely add elevation but also even out the spacing around the ring.

4. **A failure in one algorithm does not generalize to another.** The combined capture set was
   rejected on COLMAP evidence and was later shown to reconstruct correctly in a different
   engine. The cost of not re-testing was a model built from 146 photographs when 352 were
   available.
