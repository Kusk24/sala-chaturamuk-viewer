# The tabletop model: the first capture that registered completely, and what it does not prove

**Results for Version 6 · Sala Chaturamuk Phaichit · CSX4213**
Compiled 13 September 2026 from the capture of 12 September and the Kaggle run of 12–13 September 2026.
Companion to `version5_results.md`, whose §13 set the agenda this round was measured against.

---

## 1. Summary

A carved **miniature** of the pavilion was photographed indoors on a wooden board and reconstructed
end to end. Every photograph registered.

| | Photographs | Registered | Gaussians (trained) | PSNR | SSIM | LPIPS |
|---|---|---|---|---|---|---|
| **Sala model** (12 Sep) | 301 | **301** | 222,199 | **25.08 dB** | **0.851** | 0.371 |
| Sala, sky trained (7 Sep) | 446 | 395 | 593,708 | 23.45 dB | 0.769 | 0.333 |
| Lamp (7 Sep) | 100 | 100 | 154,729 | 20.87 dB | 0.784 | 0.306 |

Scored on held-out photographs the model never saw — every eighth frame, 38 of them — by the same
protocol as every previous round, so the numbers are produced the same way.

**They are not, however, measuring the same difficulty, and the headline must not be read as
progress in method.** This is a 15-centimetre object on a table in even indoor light, photographed
from six complete orbits at a fixed focal length. The pavilion is a building beside a lake with sky
behind it and no viewpoint above −10°. A tabletop object is an easier reconstruction problem than a
building, and the correct conclusion from 25.08 dB is *that the capture was good*, not that the
pipeline improved. LPIPS, which is perceptual rather than per-pixel, is **worse** here (0.371
against the pavilion's 0.333) — the plain cloth backdrop flatters PSNR and SSIM while adding
nothing a perceptual metric rewards.

**The transferable finding of this round is about matching, not about scores.** Sequential matching
with loop detection off — the setting that rescued every previous run — would have been the wrong
choice here, and the evidence said so before any GPU time was spent. §4.

Three results worth carrying forward:

| # | Finding | Status |
|---|---|---|
| 1 | 301 of 301 registered into **one** model; no second sub-model, no fold | Measured. First complete registration in the project |
| 2 | Cross-orbit links sit ~60 frames apart, far outside any sequential window; the four-fold symmetry trap does **not** spring on this subject | Measured before the run, §4 |
| 3 | The trained model is fogged; **41.0% of the opening frame is haze** and the notebook's own floater filter removed 0.1% of it | Measured, fixed without retraining, §8 |

---

## 2. What Version 5 asked for, and what happened

`version5_results.md` §13 listed five actions in order of cost.

| # | Recommended | Outcome |
|---|---|---|
| 1 | Fix the sky mask, retrain nothing — *"either mask nothing and let the crop remove distant floaters"* | **Done, on this subject.** Trained with no mask at all; the floaters were then removed geometrically. §8 shows the crop lever works and by how much |
| 2 | Constrain the viewer's camera to the photographed envelope | **Not done** |
| 3 | Train the interior sub-model from `sparse/1` | **Not done** |
| 4 | Train the far set (171 photographs) | **Not done** |
| 5 | Re-shoot for elevation — *"the only route to an observed roof"* | **Done on the model, not on the building.** Orbits 5 and 6 look down onto the roof. That answers the question for the miniature and leaves it open for the pavilion |

Action 1 was named as worth 2.2–2.4 dB for zero GPU. This round did not re-run the pavilion, so that
figure is still untested on the pavilion; what it did establish is that training with no mask and
cropping afterwards produces a usable model, and that the crop threshold shipped in the notebook is
far too loose to do the job. §8.

---

## 3. The 12 September capture

301 photographs, 08:14–08:42, a single 28-minute session.

| Property | Value |
|---|---|
| Camera | iPhone 17 Pro, all 301 frames |
| Focal length | 24 mm equivalent (6.765 mm), **spread 1.00×** — zero variation |
| Dimensions | 5712 × 4284, identical on all 301 |
| EXIF | Present on all 301 |
| Orbits | view1 61, view2 65, view3 44, view4 45, view5 45, view6 41 |
| Filenames | IMG_2069 – IMG_2373, unbroken |

Every clause of the capture rule that earlier rounds violated is satisfied: one camera, one session,
one focal length, EXIF intact. For comparison, the August set was three camera configurations across
two phones six days apart, and one of its walks alternated 24 MP and 12 MP mid-capture.

**The camera moves; the object does not.** This matters, because a turntable capture — object
rotating, camera fixed — cannot be solved by structure-from-motion without masking the background.
Mean absolute difference between consecutive frames, measured on the frame corners (background) and
the centre (subject): **13.88 corners, 20.58 centre**. A static camera would put the corners near
zero. The background moves, so the camera moved.

Adjacent-frame overlap, SIFT with Lowe's ratio test and a RANSAC fundamental matrix, sampled across
all six orbits: **172–962 good matches per pair at 65–96% inlier ratio**.

---

## 4. Why the matching had to change

Every previous run used `sequential_matcher` with `--SequentialMatching.loop_detection 0`. The
reasoning was sound and is recorded in `sala-colmap-fold-diagnosis`: the pavilion is four-faced,
vocabulary-tree retrieval pairs views 90° apart because they genuinely look alike, and turning it
off took the fold ratio from 29.2 to 5.4.

That reasoning does not transfer to this capture, and the measurements say so in both directions.

| Pair type | Frames apart | RANSAC inliers |
|---|---|---|
| Adjacent, within an orbit | 1 | **241** |
| Orbit seam (last of ring *n* → first of ring *n+1*) | 1 | **12–25** |
| Same azimuth, different orbit | **~60** | **78–91** |
| 90° apart, same orbit (the symmetry trap) | 15 | **9** |

Two conclusions follow:

1. **Sequential matching would have joined six rings by their weakest joints.** The strong
   cross-orbit links are ~60 frames apart in capture order; no sequential window of 10 or 14 reaches
   them. The only links it would have found are the seams, at 12–25 inliers.
2. **The four-fold symmetry trap does not spring here.** A 90°-apart pair scores 9 inliers, not
   hundreds. The wood grain and the folds of the cloth differ at every azimuth, so the background
   breaks a symmetry that sky and lake could not.

Exhaustive matching was therefore both safe and affordable — 301 frames is ~45,000 pairs, each
geometrically verified. The outcome was 301 of 301 registered into a single model. Under sequential
matching the plausible failure was a split reconstruction, which is exactly what the pavilion run
produced when 51 interior photographs were filed into a `sparse/1` that was never trained.

`tools/build_nb4.py` now carries a `matcher` key in `CFG`; `sequential` remains the default and the
matching cell branches on it. The sala and lamp notebooks regenerate with identical COLMAP commands —
verified by diff, not assumed.

---

## 5. The defect that nearly shipped: EXIF orientation

Preparation converts HEIC to JPEG at 1600 px long edge with `sips`. It wrote **landscape pixels
carrying EXIF orientation tag 6** — "rotate 90°". The two halves of the toolchain disagree about
what that file is: COLMAP and PIL read stored pixels and see landscape; anything honouring the tag
sees portrait. It was uniform across all 301 frames, so nothing crashed and `single_camera 1`
stayed valid — the failure mode was a model lying on its side, not an error message.

It was caught because `sips` and `mdls` reported different dimensions for the same file, and the
first contact sheet showed the pavilion pointing sideways. The fix bakes the rotation into the
pixels and clears the tag (`ImageOps.exif_transpose`, re-save), giving 1200 × 1600 portrait that
every reader agrees on. Undistortion then produces 1191 × 1600.

This is the same class of defect as every entry in Version 5 §12: a value trusted without being
checked against what it actually measured.

---

## 6. Results

Kernel `winyumg/sala-model`, GPU T4 ×2, **7 h 27 m** (26,853.7 s), 1.45 GB of output.
30,000 iterations, spherical harmonics degree 3, images on CPU, every eighth frame held out.

| Metric | Value |
|---|---|
| PSNR | **25.08 dB** |
| SSIM | **0.851** |
| LPIPS | 0.371 |
| Held-out views | 38 |
| Per-view PSNR | min **16.58**, median **25.93**, max **30.58** |

The spread is the honest picture. The good views reproduce the carving, the inlaid glass and the red
steps close to the photograph. The worst are veiled.

Gaussian budget as the notebook produced it:

| Stage | Count |
|---|---|
| Trained | 235,390 |
| After crop (`keep_r` = `keep_h` = 0.80 × ring = 2.937) | 225,756 |
| Floaters dropped (largest axis > 0.04 × ring = 0.147) | 3,557 |
| Final | **222,199** |

Camera ring radius 3.671. True vertical **25.35° off** COLMAP's y-axis, camera-up agreement 0.872.

---

## 7. Where the score is actually lost

The same pattern as every previous round, with cloth in the role of sky: the loss is dominated by
empty space the optimisation cannot constrain.

The white cloth backdrop is nearly textureless. Nothing pins down the volume between camera and
subject, and a large, semi-transparent Gaussian sitting in that volume costs the loss very little.
The result is a milky haze in front of the model, worst in the views that scored worst.

**The notebook's floater filter did not touch it.** Its threshold is 0.04 × ring = 0.147, inherited
from the outdoor scenes. On this model the largest-axis distribution is:

| Percentile | p50 | p90 | p95 | p99 | p99.9 |
|---|---|---|---|---|---|
| Largest axis | 0.019 | 0.052 | 0.071 | 0.115 | **0.143** |

A threshold of 0.147 sits above the 99.9th percentile: it removed 3,557 Gaussians, about 1.5%, and
left the haze untouched. A threshold tuned on one scene was carried to another without being
re-checked against that scene's distribution.

---

## 8. The geometric clean, and what it is honestly worth

Three cuts were applied to the trained `.splat` directly — **no retraining, no second GPU run**:

| Cut | Rule | Removes |
|---|---|---|
| Radius | horizontal distance from the model's own axis < 0.90 | the haze |
| Height | above the top of the board (h > −2.06 along up = [0, −1, 0]) | the board and the cloth it stood on |
| Size | largest Gaussian axis < 0.05, alpha > 0.15 | remaining floaters |

Followed by a **gamma 1.9 midtone lift** (0.27% of channels clipped), because the object was
photographed indoors and reads dark against a black page.

**77,626 of 222,199 Gaussians survive — 34.9%.** Rendered from the identical camera before and
after:

| | Frame lit | Classified as haze | Mean luminance |
|---|---|---|---|
| As trained | 95.9% | **41.0%** | 98.6 |
| After the clean | 11.4% | **0.5%** | 63.6 |

The board was located by profiling horizontal spread against height: the bottom two bands spread to
1.50–1.60 with mean colour (112, 94, 52) — wood — and the band immediately above collapses to 0.52.
The model is a narrow column standing on a wide slab, and the slab is separable.

**The scores in §6 were not re-measured after this, and must not be quoted as scores of what the
viewer shows.** They belong to the model the optimiser produced, haze included, scored against
held-out photographs the standard way. Cropping changes what is displayed, not what was learned, and
re-scoring a cropped model against photographs that still contain a board and a backdrop would
measure the crop rather than the reconstruction. The viewer page says so on its face.

---

## 9. What this capture cannot show

- **The underside.** The model stands on a board; its base was never photographed, and nothing in
  the reconstruction can invent it.
- **The backdrop.** Plain cloth carries little texture, so what survived the crop there is thin.
- **The building.** This is a model *of* the pavilion. It belongs beside the outdoor runs as a
  controlled comparison and not as a replacement for them. The roof problem is answered here and
  still open there.

---

## 10. The viewer

Nine pages. `viewer/salamodel.html` was added and one row appended to the `PAGES` array in
`viewer/nav.js`, which is the only place the navigation is defined; every page picks it up.
The page carries the per-view spread, the cleaning method and the caveat in §8 rather than the
headline alone.

Opening view: azimuth 40°, elevation 14°, radius 2.15 about the model's own centre, recomputed
because the pose the notebook exported had been framed around a board that no longer exists.
Verified in a browser at 60 fps with the orbit rig live.

---

## 11. What Version 7 should do

In order of cost.

- **Re-tune the floater threshold per subject, in the notebook.** §7 shows a constant carried
  between scenes is worthless. Derive it from the scene's own percentile distribution. Zero GPU.
- **Apply the same geometric clean to the pavilion runs.** The lever is now measured — haze 41.0% →
  0.5% — and the pavilion pages still show haze around the roofline. Zero GPU.
- **Constrain the viewer's camera** to the photographed envelope. Outstanding from Version 5 §13.
- **Train the interior sub-model** from `sparse/1`. Outstanding from Version 5 §13; 71 photographs
  already reconstructed, ~40 min GPU.
- **Re-shoot the pavilion for elevation.** Outstanding since Version 5 §9. The tabletop capture
  demonstrates what complete orbit coverage buys — 301 of 301 registered, roof observed — and is the
  argument for doing it on the building.

Do not spend GPU on more iterations; the Version 5 extrapolation bounding the remaining benefit at
7–12% of training loss has not been superseded.

---

## 12. Reproducing the numbers

| Claim | Source |
|---|---|
| Capture EXIF, focal spread, dimensions, timestamps | `mdls` over the 12 Sep HEIC originals in `Downloads/Sala_Model/view{1..6}` |
| Orbit counts | `CV_Photos_prepared/salamodel_manifest.csv` |
| Camera-moves-not-object test | Mean absolute difference of corner vs centre patches over 20 consecutive frames |
| Adjacency and cross-orbit inliers | OpenCV SIFT, Lowe ratio 0.75, `cv2.findFundamentalMat` RANSAC at 3.0 px, on the prepared JPEGs |
| Registration count | `cameras_final.json`, 301 entries |
| Held-out scores | `results.json`, 3DGS `metrics.py`, every 8th frame via `--eval` |
| Per-view scores | `per_view.json`, 38 entries |
| Gaussian counts, ring, tilt, crop bounds | `frame.json`; `.splat` size ÷ 32 bytes per row |
| Largest-axis percentiles | `salamodel_final.splat`, bytes 12:24 as three float32 scales |
| Before/after haze percentages | Both models rendered from the identical view matrix in the vendored WebGL renderer; haze = pixels with saturation < 22 and value < 190 |
| Training configuration | `cfg_args` |
| Run time | Kaggle log, 26,853.7 s |

Raw outputs are in `Term-Project/kaggle_out/salamodel/`. The notebook is
`notebooks/KAGGLE_salamodel_sep12.ipynb`; the cleaning script is `scratchpad/clean_salamodel.py`.
