# The September re-capture: two reconstructions that worked, and what still limits them

**Results for Version 5 · Sala Chaturamuk Phaichit · CSX4213**
Compiled 8 September 2026 from the capture of 5 September and the Kaggle runs of 7 September 2026.
Companion to `version5_failure_analysis.md`, which explains why everything before this failed.

---

## 1. Summary

The re-capture worked. For the first time in this project a reconstruction ran end to end —
structure-from-motion, undistortion, 30,000 iterations of Gaussian splatting, held-out scoring and
export — without a single geometric failure. Two models came out of it.

| | Photographs | Registered | Gaussians (cropped) | PSNR | SSIM | LPIPS |
|---|---|---|---|---|---|---|
| **Sala** | 446 | 395 | 291,764 | **20.10 dB** | 0.739 | 0.342 |
| **Lamp** | 100 | 100 | 163,756 | **15.93 dB** | 0.707 | 0.314 |

Both are scored on held-out photographs the model never saw — every eighth frame, 50 for the sala
and 13 for the lamp — using the same protocol as the 146-image `version2` model reported in
Version 4 (22.09 dB, 0.785, 0.346 at 15,000 iterations), so the three are comparable.

**The single most transferable finding of this round:** the reported PSNR is dominated by parts of
the photograph that are not the subject. Sky that the mask blackened inconsistently, and distant
scenery no orbit could constrain, account for most of the loss. Measured on the same renders, the
sala scores 20.10 dB over the whole frame and **22.33 dB once mask-blackened pixels are excluded**;
the lamp scores 15.93 dB over the whole frame and **20.25 dB over the region the lamp occupies**.
A single headline number conceals a reconstruction that is good where it was photographed and
absent where it was not.

Three limits remain, and **none of them is a training limit**:

| # | Limit | Status |
|---|---|---|
| 1 | The sky mask fires on some frames and not others, so the same tree is black in one view and textured in the next | Measured, costs 2.2–2.4 dB, fixable in software |
| 2 | The interior never bound to the exterior; COLMAP filed it as a second reconstruction and it was never trained | Measured, 51 of 93 interior photographs unused |
| 3 | Not one photograph looks down at the pavilion — the highest viewpoint is −10° elevation | **Requires new photographs.** Predicted in Version 5 §9.3 and not acted on |

---

## 2. What the failure analysis asked for, and what happened

`version5_failure_analysis.md` §9 listed three actions in order of cost. Recording the outcome
honestly matters more than recording the plan.

| # | Recommended | Outcome |
|---|---|---|
| 1 | Re-run COLMAP on the 352-photograph set with `single_camera_per_folder 1` | **Not done, and correctly so.** Superseded by action 3, which removed the cause rather than working around it |
| 2 | Train and report whatever that produced | **Not applicable** — the combined set was abandoned |
| 3 | Re-shoot: one camera, one session, one focal length, unbroken chain, **elevated positions from floor 6 or higher of the main building's east facade** | **Done, except the elevated positions.** Every other clause was satisfied exactly. The elevation clause was not, and §9 had named it "the only route to an observed roof" |

The re-capture solved every cause the failure analysis identified — and reproduced, untouched, the
one cause it had flagged as needing height. Section 9 of this document treats that as the finding
it is rather than an oversight to be mentioned in passing.

---

## 3. The 5 September capture

724 photographs, one continuous 55-minute session, iPhone 16 Pro, ultra-wide 2.22 mm lens.

| Property | Combined Aug set (failed) | 5 Sep set |
|---|---|---|
| Cameras | 2 phones (iPhone 17 Pro, 16 Pro) | **1** |
| Lens configurations | 3 | **1** |
| 35 mm-equivalent focal length spread | **7×** (24–100 mm) | **1.00×** (14 mm on every frame) |
| Sessions | 2, six days apart | **1** |
| Frames with no EXIF | 131 | **0** |
| Frames slower than 1/60 s | not measurable | **1 of 724** |
| ISO range | not measurable | 50–250 |

This is the fix. Every mechanism in `version5_failure_analysis.md` §6.2 — one intrinsic forced
across incompatible sensors, invisible because downscaling to 1600 px gives different fields of
view identical pixel dimensions — is structurally impossible on a single-lens capture.

Prepared to JPEG at 1600 px in `Term-Project/CV_Photos_prepared/`; seven 16:9 frames dropped.

| Subject | Frames | Size | Segments |
|---|---|---|---|
| `sala` | 446 | 1600×1200 | Sala 360 (264), Sala 360 Near (89), Sala Inside (93) |
| `lamp` | 100 | 1200×1600 | Higher (30), Middle (33), Lower (37) |
| `far` | 171 | 1600×1200 | not yet trained |

---

## 4. Attempt log

| # | Date | Subject | Outcome |
|---|---|---|---|
| 1 | 7 Sep | lamp | **Failed at training.** `FileNotFoundError: sparse/0/images.bin` — see §5 |
| 2 | 7 Sep | lamp | **Succeeded.** 1 h 35 m 35 s wall clock, 1.97 GB output |
| 3 | 7 Sep | sala | **Succeeded.** 1 h 43 m 16 s of training alone |

No run in this round produced a folded or geometrically wrong reconstruction. That is the
difference between this week and the five attempts documented in the failure analysis.

The fold diagnostic — maximum consecutive-camera step divided by the median step, scale-invariant,
with a healthy reference of 7.0 established by the clean 146-image `version2` capture — reports:

| Capture | Segment | Frames | max/median | Jumps > 5× |
|---|---|---|---|---|
| Sala | Sala 360 | 264 | 10.0 | 2 (0.8%) |
| Sala | Sala 360 Near | 89 | 14.3 | 17 (19.3%) |
| Sala | Sala Inside | 42 | 2.4 | 0 |
| Lamp | Higher | 30 | 3.7 | 0 |
| Lamp | Middle | 33 | 2.9 | 0 |
| Lamp | Lower | 37 | 2.4 | 0 |

Against the 102.2 and 36.0 of the failed combined runs, these are healthy. **Sala 360 Near is the
one number to keep an eye on:** at 14.3 with 19.3% of its steps beyond five times the median it sits
just under the 15.0 gate, and it passed on a threshold the failure analysis itself called arbitrary
(§6.2, defect 2). It is a near-orbit of a large building where the photographer's distance changes
sharply, so a genuine walk break is the likelier explanation than a fold — but it was not
independently verified, and it should not be quoted as if it had been.

---

## 5. The defect that stopped the first run

`colmap image_undistorter --output_type COLMAP` writes its output as
`sparse/{cameras,images,points3D}.bin`, flat. 3DGS's `readColmapSceneInfo` reads `sparse/0/`, a
path it hardcodes. The undistorted scene was therefore invisible to the trainer and the run died
three hours in, after all the expensive work had completed.

The reason this was not caught earlier is worth stating plainly: **the undistort-to-train path had
never once executed in this project.** Every earlier attempt died at the fold check before reaching
it, and the one model that did train (the `version2` model in Version 4) used a pre-made pinhole
dataset that bypassed undistortion entirely. The defect was not a regression. It was a section of
the pipeline that had never run.

The fix is to move the files into `sparse/0/` after undistortion, which is what the 3DGS
repository's own `convert.py` does. It was verified locally before re-running — COLMAP 4.1.1 over
all 100 real lamp photographs, then loaded back through 3DGS's own `colmap_loader.py`: 100 images,
one PINHOLE camera at 1191×1588, 45,393 points at 0.434 px mean reprojection error. An assertion
now fails at undistortion rather than three hours later.

---

## 6. Results

### 6.1 Sala

395 of 446 photographs, 30,000 iterations, NVIDIA T4 ×2, 1 h 43 m 16 s.

| Metric | Value |
|---|---|
| PSNR | 20.096 dB |
| SSIM | 0.7392 |
| LPIPS | 0.3418 |
| Held-out views | 50 |
| Per-view PSNR range | 10.45 to 25.61 dB, median 20.49 |
| Gaussians, full field | 653,917 |
| Gaussians after object crop | 291,764 |

### 6.2 Lamp

100 of 100 photographs, 30,000 iterations, NVIDIA T4 ×2, 1 h 35 m 35 s including SfM.

| Metric | Value |
|---|---|
| PSNR | 15.932 dB |
| SSIM | 0.7068 |
| LPIPS | 0.3140 |
| Held-out views | 13 |
| Per-view PSNR range | 10.07 to 22.34 dB |
| Gaussians, full field | 1,053,976 |
| Gaussians after object crop | 163,756 |

The lamp registered every photograph and produced the cleanest fold ratios in the project, yet
scores nearly 4.2 dB below the sala. Section 7 explains why, and the explanation is not that the
lamp reconstructed worse.

---

## 7. Where the score is actually lost

Recomputing PSNR over sub-regions of the *same* renders, with no retraining:

| Region | Sala | Lamp |
|---|---|---|
| Whole frame | 20.10 dB | 15.93 dB |
| Excluding pixels the sky mask blackened | **22.33 dB** (+2.40) | **18.14 dB** (+2.21) |
| Central region — the subject | 20.89 dB | **20.25 dB** |
| Best single held-out view, central region | 25.56 dB | **30.01 dB** |
| Blackened pixels, share of average frame | 11.8% | 17.4% |

Two things follow.

**The lamp's low headline number is a framing artefact.** Over the region the lamp occupies it
scores 20.25 dB and reaches 30.01 dB on its best view — comparable to the sala, and on its best
view better than anything else in the project. Its whole-frame number is low because a small object
photographed from 3.6 m leaves most of the frame filled with a lake, a treeline and buildings a
hundred metres away, which a 3.6 m orbit gives no parallax on and therefore cannot constrain. The
model renders them as smear, and PSNR counts every one of those pixels.

**The sky mask costs more than any hyperparameter.** The HSV-and-gradient mask fires on some frames
and not on others: in held-out views `00007` and `00009` the ground truth shows open sky, while in
`00012` the same sky is black. The model cannot satisfy both, so it learns a compromise and is
penalised in both. This is worth 2.2–2.4 dB — roughly forty times what doubling the training
budget would buy (§10) — and it is fixable in software, without new photographs.

Inspection of the held-out pairs (`lamp_heldout_gt_vs_render.png`) confirms the reading directly:
the lamp itself renders with sharp mouldings and correct colour in every view; what fails is the
sky behind it. A person walks through roughly a third of the lamp frames and contributes a further
ghost at the base.

**Implication for the paper.** A single whole-frame PSNR is not a measure of how well the subject
reconstructed. Where the subject occupies a minority of the frame, the number is mostly reporting
the background. This parallels the finding of the previous round — that sub-pixel reprojection
error is not evidence of correct geometry — and has the same moral: the standard summary statistic
answers a different question than the one being asked.

---

## 8. The interior never joined the exterior

COLMAP produced **two disconnected sub-models** for the sala, and 3DGS trained only the larger.

| Sub-model | Images | Trained |
|---|---|---|
| `sparse/0` | 395 | yes |
| `sparse/1` | 71 | **no** |
| In both | 20 | — |
| **Exclusive to `sparse/1`** | **51** | **no** |

Those 51 photographs are not a random scatter. Cross-referenced against the capture manifest,
**every one of them belongs to the `Sala Inside` folder.** Of 93 interior photographs, 42 bound to
the exterior walk and 51 did not.

The cause is ordinary and worth naming: standing under the roof, the camera sees painted ceiling
and columns and almost nothing it saw from the terrace. Without frames that observe both at once,
sequential matching finds no bridge, and COLMAP correctly reports two reconstructions rather than
inventing a link between them. The model published as "the sala" is therefore **the exterior**.

The fix is cheap and belongs in the next capture: a handful of deliberate transition frames taken
standing in the doorway, turning slowly from outside to inside, so the two halves share features.
The 71 images in `sparse/1` are already reconstructed and could be trained as a separate interior
model at any time for roughly 40 minutes of GPU.

---

## 9. The roof was never photographed — again

Measuring the elevation of every camera about the centre of the reconstructed object, using a world
up-vector derived from the cameras' own up axes (mean agreement 0.97, i.e. the capture was level):

| Elevation | Sala | Lamp |
|---|---|---|
| −90° to −30° | 21 | 15 |
| −30° to 0° | **374** | 27 |
| 0° to +30° | **0** | 37 |
| +30° to +60° | **0** | 21 |
| +60° to +90° | **0** | 0 |
| **Highest viewpoint** | **−10°** | **+43°** |

Azimuth coverage is complete for both — 12 of 12 sectors, thinnest 22 photographs for the sala and
4 for the lamp. The deficiency is entirely in elevation.

**Not one of the 446 sala photographs looks down at the pavilion.** The upper surfaces of the roof
were never observed, so no Gaussian was ever placed on them and no amount of optimisation can
create one. Viewed from above in the interactive viewer, the roof opens into a hollow shell — not
because the model is undertrained, but because a radiance field contains only what was seen.

The lamp is better served by its three orbits, spanning −43° to +43°, but has nothing overhead
either, so its finial thins out from above.

This is the same limitation reported in `version5_failure_analysis.md` §6.3, and §9.3 of that
document specified the remedy: elevated positions from floor 6 or higher of the main building's
east facade. The re-capture followed every other instruction and omitted this one. The honest
conclusion is that **the roof remains unobserved by choice of viewpoint, not by limitation of
method**, and that the project now has a direct measurement of the gap rather than an impression
of it.

---

## 10. Was 30,000 iterations enough?

Yes, and the question can be answered quantitatively rather than by eye. Mean training L1 loss per
5,000 iterations, read from the TensorBoard event files:

| | 0–5k | 5–10k | 10–15k | 15–20k | 20–25k | 25–30k |
|---|---|---|---|---|---|---|
| Lamp | 0.0911 | 0.0538 | 0.0438 | 0.0362 | 0.0335 | **0.0319** |
| Sala | 0.0919 | 0.0663 | 0.0564 | 0.0477 | 0.0447 | **0.0429** |

The final 5,000 iterations improved the loss by 4.8% (lamp) and 4.0% (sala). Fitting
`L(t) = c + A·t^−b` over the post-densification regime (16k–30k, after densification stops at
15,000) and extrapolating:

| Iterations | Lamp | Sala |
|---|---|---|
| 30,000 (measured) | 0.0319 | 0.0429 |
| 40,000 | 0.0302 (−4.3%) | 0.0413 (−3.0%) |
| 60,000 | 0.0291 (−7.8%) | 0.0404 (−5.1%) |
| ∞ (fitted asymptote) | **0.0278 (−11.7%)** | **0.0396 (−6.9%)** |

The asymptote is the important column: it bounds what *any* amount of further training could ever
achieve. For the sala that ceiling is 6.9%, worth on the order of +0.3 dB, and roughly half of it
would be reached by 40,000 iterations at a cost of about 2 h 20 m of additional GPU. For
comparison, fixing the sky mask is worth 2.40 dB and costs no GPU at all.

One implementation detail bears on any attempt to extend a run: 3DGS decays the position learning
rate over `position_lr_max_steps`, which defaults to 30,000. Resuming a finished 30,000-iteration
checkpoint therefore continues at the floor of that schedule, where Gaussians barely move, and
yields materially less than the extrapolation above. Reaching the predicted values requires a fresh
run with `--iterations 40000` so that the schedule stretches.

**Conclusion: 30,000 iterations was the correct stopping point.** Training is not the binding
constraint on any result in this report.

---

## 11. The viewer

Both models are published as interactive pages in `Term-Project/sala-chaturamuk-viewer/viewer/`,
alongside the existing image-based renderer and photogrammetry mesh, and linked from `index.html`:

| Page | Model |
|---|---|
| `sala.html` | September capture, 291,764 Gaussians, 395 poses |
| `lamp.html` | 163,756 Gaussians, 100 poses |
| `splat.html` | August `version2` capture, retained for comparison |

Each embeds its model as base64 in a JavaScript global and reads the renderer from
`vendor/splat.js` (antimatter15/splat, MIT), so the pages open from `file://` with no server and no
build step — the same constraint the rest of the viewer observes. The vendored renderer was
extended by six lines to accept per-page camera poses and an opening view matrix; pages that supply
neither are unaffected, so the existing `splat.html` renders exactly as before.

The published models are the **cropped** fields, not the full ones. This is deliberate and follows
directly from §7: the discarded Gaussians are the background that scores around 10 dB, and
including them would make the pages both heavier and worse. The sala page shows 291,764 of
653,917 Gaussians; the lamp page 163,756 of 1,053,976.

Both pages state their own limitations, with the measured numbers, rather than presenting a
headline score without context.

---

## 12. Process failures, and what they cost

| Failure | Cost | Correction |
|---|---|---|
| A pipeline path — undistort to train — that had never been executed was assumed to work | One full Kaggle run, ~3 h | Verified locally end to end against 3DGS's own loader before re-running |
| The fold check was applied to captures whose frame ordering could not be verified | Two runs rejected on a test that did not apply to them | Gated to captures with verified continuous ordering; now warns rather than aborting |
| The sky mask was never checked for *consistency between views*, only for whether it ate the subject | 2.2–2.4 dB in every reported score | Measured this round; not yet fixed |
| §9.3 of the failure analysis specified elevated viewpoints; the capture plan did not carry the instruction through | The roof is unobserved for a second consecutive round | Must appear in the capture one-pager as a required segment, not a recommendation |
| Full-frame PSNR was quoted for four rounds without asking what share of the frame is subject | Understated every object-scale result | Region-decomposed scores reported alongside the headline from this round on |

The pattern across this round and the last is consistent: **the failures were in verification, not
in the method.** Every one was a case of a number or a stage being trusted without being checked
against what it actually measured.

---

## 13. What Version 6 should do

**In order of cost.**

1. **Fix the sky mask, retrain nothing.** Enforce view-consistency — either mask nothing and let
   the crop remove distant floaters, or segment the sky per-frame with a model that does not flip
   between adjacent views. Worth 2.2–2.4 dB, zero GPU. Re-score the existing renders first to
   confirm the gain before committing to a retrain.
2. **Constrain the viewer's camera** to the photographed envelope (−30° to 0° for the sala, −43° to
   +43° for the lamp) so unobserved directions cannot be flown into. No retraining; removes the
   most visible artefact in the published pages.
3. **Train the interior sub-model** from `sparse/1`. 71 photographs already reconstructed, ~40 min
   GPU, and it adds content that currently exists in no model.
4. **Train the `far` set** — 171 photographs, prepared and untouched, at a second capture radius.
5. **Re-shoot for elevation.** 40–60 frames between +30° and +60°, plus doorway transition frames
   so the interior binds. This is the only route to an observed roof and to a single connected
   model, and it is now the third round in which it has been the outstanding item.

**Do not** spend GPU on more iterations. §10 bounds the entire remaining benefit at 7–12% of
training loss, against a 2.4 dB gain available from a software fix.

---

## 14. Reproducing the numbers

| Claim | Source |
|---|---|
| Capture EXIF, focal-length spread, ISO, shutter | `PIL.Image.getexif()` over the 5 Sep HEIC originals; `pillow-heif` for decoding |
| Segment counts | `Term-Project/CV_Photos_prepared/{sala,lamp}_manifest.csv` |
| Registration counts, fold ratios | Kaggle run logs, cells 8 and 9 of `Term-Project/notebooks/KAGGLE_{sala,lamp}_sep05.ipynb` |
| Two sub-models, and which images are in each | COLMAP `sparse/{0,1}/images.bin`, decoded directly from the binary record format |
| Held-out scores | `results.json`, 3DGS `metrics.py`, every 8th frame held out via `--eval` |
| Per-view scores | `model/per_view.json` |
| Region-decomposed PSNR | Recomputed from `model/test/ours_30000/{gt,renders}/*.png`; background defined as pixels below value 18 in either image |
| Loss curves and extrapolation | `model/events.out.tfevents.*`, parsed directly from the TFRecord/protobuf stream |
| Camera elevation coverage | `cameras.json` positions against the median of the cropped model's Gaussian centres; world up from the mean of the cameras' own up axes |
| Gaussian counts | `.splat` file size ÷ 32 bytes per row |
| Figures | `lamp_heldout_gt_vs_render.png`, `lamp_cropped_preview.png`, `sala_view_candidates.png` |

Raw outputs are in `Term-Project/kaggle_out/{sala,lamp}/`. The notebooks are resumable: every
expensive stage banks to `/kaggle/working` and is restored before any work is redone, so
re-running the same file after a failure skips whatever already completed.
