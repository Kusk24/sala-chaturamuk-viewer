# Why the combined 352-photograph reconstruction failed

**Failure analysis for Version 5 · Sala Chaturamuk Phaichit · CSX4213**
Compiled 5 September 2026 from five reconstruction attempts run between 29 August and 5 September 2026.

---

## 1. Summary

We tried five times to reconstruct the pavilion from all 352 photographs — 206 in
`salathai_version1` plus 146 in `salathai_version2` — and every attempt produced camera poses
that were internally consistent and geometrically wrong. The final attempt still could not be
trained on.

Three causes were identified. **One is solved**, one is a known defect we have not yet paid the
compute cost to fix, and one cannot be fixed without new photographs.

| # | Cause | Status |
|---|---|---|
| 1 | Vocabulary-tree loop closure matching views 90° apart on a four-faced pavilion | **Solved** — `loop_detection 0` |
| 2 | One camera intrinsic forced across three different lens/sensor configurations | **Identified, not fixed** — costs a full 2 h 12 m re-run |
| 3 | The roof was never photographed from above; captures differ in light and height | **Requires a new capture** |

The single most transferable finding: **a sub-pixel reprojection error is not evidence of correct
geometry.** Every failed attempt reported 0.66–0.99 px and registered 351 of 352 images. Those
numbers look like success and are not.

---

## 2. What we were trying to do

The project's contribution is image-based rendering in the sense of Szeliski Chapter 14 —
synthesising novel views from photographs *without* recovering explicit geometry. Structure-from-
motion and Gaussian splatting are the comparison arm: what do you get, and what does it cost, if
you *do* recover geometry from the same photographs?

The 146-photograph `version2` reconstruction already worked (22.09 dB held-out PSNR at 15,000
iterations). Adding `version1` should have helped: it was shot from across the lake and from a
different distance, so it sees parts of the structure `version2` never does. More viewpoints and
two capture radii should improve triangulation.

It did the opposite, five times.

---

## 3. The data we actually had

This is the part we did not check early enough, and it explains most of what followed. All figures
below are read from EXIF and image headers on 5 September 2026.

### version1 — 206 files, not one capture

| Files | Count | Dimensions | Camera | Timestamp |
|---|---|---|---|---|
| `capture_0000–0130` | **131** | 4031×3023 and 4032×3024, alternating | **none recorded** | **no EXIF at all** |
| `capture_0131–0205` | **75** | **5712×4284 and 4032×3024, alternating** | iPhone 17 Pro | 15 Aug 2026, 12:29–12:40 |

Two things matter here.

**The first 131 files carry no metadata whatsoever** — no camera, no timestamp, no lens. They also
alternate between 4031×3023 and 4032×3024, a one-pixel difference that is the signature of
re-encoding rather than of a sensor. We cannot establish what took them, when, or in what order.

**The last 75 files alternate between 24 MP (5712×4284) and 12 MP (4032×3024) inside a single
eleven-minute walk.** That is what an iPhone records when the lens or zoom level changes. The
photographer zoomed during the capture — repeatedly. This is the concrete violation of the "never
change focal length mid-session" rule, and we can now prove it happened rather than suspect it.

### version2 — 146 files, one clean capture

| Files | Count | Dimensions | Camera | Timestamp |
|---|---|---|---|---|
| `capture_0000–0145` | 146 | 4032×3024 (144 of 146) | iPhone 16 Pro | 21 Aug 2026, 17:08–17:23 |

One session, one phone, one focal length, 15 minutes, median 3.0 s between frames, EXIF throughout.
Only two frames deviate (3640×2730 and 3121×2341 at 17:15 — two digitally zoomed shots).

**`version1` and `version2` were not even taken with the same phone** — iPhone 17 Pro versus
iPhone 16 Pro, six days apart, at different times of day.

### What this means

The 352 "photographs" are at least **four distinct camera configurations**: an unknown source
(131), an iPhone 17 Pro at 24 MP (54), the same phone at 12 MP (21), and an iPhone 16 Pro at
12 MP (146).

---

## 4. Attempt log

The pipeline downscales every image to 1600 px wide before COLMAP. That is important: 5712×4284
and 4032×3024 both become 1600×1200, so after downscaling the images are **the same pixel
dimensions while representing different fields of view.** COLMAP has no way to tell them apart.

| # | Host | Matching | Registered | Final cost | v1 ratio | v2 ratio | Wall time |
|---|---|---|---|---|---|---|---|
| 0 | local | *version2 alone* | 146/146 | 0.58 px | — | **7.0** | — |
| 1 | local | exhaustive | 351/352 | 0.99 px | 102.2 | 36.0 | ~90 min |
| 2 | Kaggle | sequential + loop detection | 351/352 | 0.662 px | 55.3 | 29.2 | 2 h 55 m |
| 3 | Kaggle | sequential, **loop detection off** | 351/352 | 0.666 px | 27.4 | **5.4** | 1 h 54 m |
| 4 | Kaggle | same, v1 split for analysis | 351/352 | 0.667 px | v1a **16.1** / v1b **14.8** | 6.2 | 2 h 02 m |

Attempt 0 is the control: the 146 `version2` photographs on their own.

Note that **registration count and reprojection error are flat across every attempt** — 351/352
and 0.66–0.99 px — while the actual geometry ranges from catastrophic (102.2) to clean (5.4).
Those two headline metrics carry no signal about whether the reconstruction is correct.

---

## 5. The diagnostic

Reprojection error cannot detect this failure, so we used a different test.

**A walk photographed in order should have consecutive cameras close together.** Take the
reconstructed camera centres in filename order, compute the distance between each consecutive
pair, and report

> **fold ratio = max(step) / median(step)**

This is scale-invariant, so it works despite COLMAP's arbitrary units. On a clean capture it is
small: `version2` alone scores **7.0** with 2 steps above 5× the median. On a folded model the
same photographs score 36.0 with 8 such steps.

### Where the test is valid, and where it is not

The test assumes **consecutive filenames are consecutive footsteps.** That holds for `version2`:
one session, EXIF on all 146 frames, median 3.0 s apart, filename order matching chronological
order.

It does **not** hold for `version1`. The first 131 files have no timestamps at all, so we cannot
confirm they form a single ordered walk. A high ratio there is genuinely ambiguous — it could be
folded geometry, or it could be a capture that was never one continuous walk. **We used this test
to reject two runs before recognising it was not valid for that half of the data.** The final
notebook gates only on captures whose ordering is verifiable and reports the rest as diagnostics.

A secondary caution: the pass/fail threshold of 15.0 is arbitrary. In attempt 4 the two halves of
`version1` scored 16.1 and 14.8 — statistically indistinguishable, on opposite sides of the line.

---

## 6. Root causes

### 6.1 Four-fold rotational symmetry — SOLVED

The pavilion is *chaturamuk*, four-faced. Views 90° apart are nearly identical. Any matcher that
proposes non-adjacent image pairs will therefore match one face to another, and the mapper resolves
those false correspondences into a self-consistent but globally wrong reconstruction — which is
exactly why the reprojection error stays sub-pixel.

- **Exhaustive matching** compares every pair, so it proposes the bad pairs by construction: 102.2 / 36.0.
- **Sequential + vocabulary-tree loop detection** proposes a bounded number of appearance-similar
  candidates per image. Better, but the vocabulary tree retrieves on appearance, and the four faces
  *look the same*: 55.3 / 29.2.
- **Sequential with loop detection off** proposes only temporally adjacent pairs, which cannot be
  90° apart: 27.4 / **5.4**.

`version2` at 5.4 is *better than its own standalone score of 7.0*. The symmetry problem is solved.

The cost is that nothing now links the two walks, and the ring no longer closes onto itself, so
drift accumulates. Drift is far less damaging than a fold.

This mirrors a decision already made elsewhere in the project: `src/match_features.py` restricts
optical-flow matching to adjacent frames for the same reason. The same failure reproduced in
structure-from-motion, an independent algorithm — which is the more interesting way to report it.

### 6.2 One camera model across three configurations — IDENTIFIED, NOT FIXED

Feature extraction ran with:

```
--ImageReader.single_camera 1 --ImageReader.camera_model SIMPLE_RADIAL
```

This forces **a single shared intrinsic across all 351 images** — across two different iPhones and
across a 24 MP and a 12 MP lens on one of them. Because everything is downscaled to 1600×1200 first,
nothing crashes; the images merely have different true fields of view and one fitted focal length
between them.

`version2`'s 146 frames are the largest homogeneous group, so the fitted focal length is
effectively *version2's camera*. Both halves of `version1` then carry the wrong focal length, and
their poses bend to compensate.

This is consistent with every observation: in attempt 4, `version2` scores 6.2 while both halves of
`version1` sit at 15–16, despite all three being reconstructed by the same matcher in the same
model.

**The fix is `--ImageReader.single_camera_per_folder 1`** with the captures separated into
folders — one per camera configuration, so four rather than two. It invalidates the feature
database and therefore costs a full re-run: extraction (~25 min) + matching (~38 min) + mapper
(~67 min) ≈ **2 h 12 m** before training starts. We ran out of GPU quota before paying it.

**This is the first thing Version 5 should do**, because it is cheap relative to a re-shoot and it
tells you whether the remaining error is fixable in software at all.

### 6.3 The capture itself — REQUIRES NEW PHOTOGRAPHS

Even with perfect poses, this data has ceilings no processing removes:

- **The roof was never observed from above.** `version2` shoots upward from the balustrade;
  `version1` shoots from across the lake at distance. No camera has ever looked down on the ridge.
  The reconstruction has to invent that surface.
- **`version2` is a single-height ring** covering 342° with one gap, all at eye level.
  Measured: mean angular step 2.42°, largest gap 12.36°, first-to-last distance 2.21 units where a
  normal step is 0.19 — the walk does not close.
- **The two captures were taken in different light** six days apart at different times of day.
  Even with correct geometry that bakes patchy appearance into a splatting model.
- **131 photographs have no provenance at all.**

---

## 7. Secondary findings worth reporting

**Sky floaters consume a third of the model.** In the 15,000-iteration `version2` splat,
**196,775 of 554,618 Gaussians (35.5 %) are bright and semi-transparent** — the sky-floater
signature — and the largest 1 % by scale sit at a median radius of 9.92 against a scene median of
2.30. Over a third of the model's capacity paints haze rather than the pavilion. This is the
concrete argument for sky masking, and it is the same failure as the sky sheet in the
photogrammetry mesh.

**"Sinking underground" in SuperSplat is not a training defect.** COLMAP never solves for a ground
plane, its origin and scale are arbitrary, and 3DGS inherits COLMAP's Y-down convention while
SuperSplat is Y-up — hence the automatic `Rotation Z 180` on import. Fix it with the transform.

---

## 8. Process failures, and what they cost

These are not reconstruction problems, but they consumed more time than the reconstruction did and
are worth recording.

| Failure | Cost | Lesson |
|---|---|---|
| Two Google Colab runtimes died mid-run | ~2 h of COLMAP, twice | Free Colab has no background execution; closing the laptop kills the run |
| First notebook only wrote results to Drive *after* the mapper | everything before it lost | Bank every expensive stage the moment it finishes, and check before recomputing |
| COLMAP aborted on Colab with `qt.qpa.xcb: could not connect to display` | one run | COLMAP links Qt; headless hosts need `QT_QPA_PLATFORM=offscreen` |
| GPU SIFT then failed for the same reason | one run | SiftGPU needs an OpenGL context, which comes from the display — use `use_gpu 0` |
| CPU matching at 27 s/image | ~2.6 h projected | Cap features (`max_num_features 8192`) when matching on CPU |
| Two notebook outputs attached at once | 69 min re-running the mapper | The cache lookup takes the alphabetically first match — attach only the latest |

**Kaggle turned out to be the right host.** *Save & Run All (Commit)* runs detached on Kaggle's
servers, so closing the laptop cannot kill it. Output from a **failed** commit is retained, so
banked stages survive an assertion. It provides 4 CPU cores against Colab free's 2, roughly halving
the COLMAP stages. GPU quota is 30 h/week per account — and since COLMAP is entirely CPU, running
it with Accelerator = None costs none of it.

---

## 9. What Version 5 should do

**In order of cost.**

1. **Re-run COLMAP with per-configuration cameras.** ~2 h 12 m, no new data. Separate the four
   camera configurations into folders and use `single_camera_per_folder 1`. If the `version1`
   ratios drop toward `version2`'s 6, cause 6.2 was the remaining problem and the combined
   reconstruction becomes trainable. If they do not, the capture itself is the limit and we have
   proved it.
2. **Train and report whatever that produces**, held-out scored the same way as the 146-image model
   (22.09 dB PSNR, 0.785 SSIM, 0.346 LPIPS at 15,000 iterations) so the two are comparable.
3. **Re-shoot, following `SalaThai_Capture_OnePager.pdf`.** One camera, one session, one focal
   length, unbroken chain of frames, elevated positions from floor 6 or higher of the main
   building's east facade. This is the only route to an observed roof.

**Do not** present an invented roof surface as measured. Reporting the roof as unobserved, and
explaining why, is the honest and more interesting result.

---

## 10. Reproducing the numbers

| Claim | Source |
|---|---|
| EXIF, dimensions, camera models | `PIL.Image.getexif()` over `data/raw_versions/salathai_version{1,2}/*.jpg` |
| Fold ratios | Cell 8 of `Term-Project/notebooks/KAGGLE_sala_splat_352.ipynb`, from COLMAP `images.txt` |
| Registration counts, reprojection cost | COLMAP mapper output, Kaggle run logs |
| Attempt 1 | `recon/combined_capture_finding.json` |
| Attempt 0 control | `recon/salathai_version2/camera_path.json` |
| Sky-floater fraction | Direct analysis of `Term-Project/sala/sala_v2_15000.ply` |
| Held-out scores | `results.json`, 3DGS `metrics.py`, every 8th frame held out via `--eval` |

The notebook is resumable: every expensive stage banks to `/kaggle/working/out` and is restored
before any work is redone, so re-running the same file after a failure is safe and skips whatever
already completed.
