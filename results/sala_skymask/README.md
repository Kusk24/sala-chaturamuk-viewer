# Sala, sky masked vs sky trained — the measured numbers

Two runs of the same 395 photographs, the same optimiser, the same 50 held-out
views. They differ in one thing: whether the sky is excluded from the loss.

| | sky trained, cropped afterwards | sky masked during training |
|---|---|---|
| Gaussians, final | 593,708 | 597,067 |
| Whole-frame PSNR (`metrics.py`) | **23.45 dB** | **14.45 dB** |
| Pavilion-only PSNR | **22.34 dB** | **22.61 dB** |
| Views improved | — | 42 of 50 (best +2.33, worst −0.64) |
| Gaussians in sky in ≥50% of held-out views | 632 | **34** |
| … in ≥30% of views | 2,285 | **501** |
| Visible share sitting in sky (size × opacity) | 0.95% | **0.49%** |
| Oversized gaussians the size filter removed | 6,435 | 4,756 |

**The whole-frame number is not the comparison.** `metrics.py` scores every pixel.
The masked model was trained to put nothing in the sky and duly renders nothing
there, while the photograph it is scored against is 28% sky on average (1% to 47%).
That column is measuring an absence that was asked for. Note also that the sky is
*easy* — the sky-trained model scores 28.80 dB on those pixels, well above its own
22.34 dB on the pavilion — so including it inflates one run and cannot inflate the
other.

**The pavilion-only number is the comparison**, and it is a modest +0.27 dB. Masking
the sky does not sharpen the building. What it does is stop the optimiser spending
capacity on something it can never resolve, which shows up in the occupancy rows
rather than in PSNR: 95% fewer gaussians committed to the sky.

## Files

| file | what it is |
|---|---|
| `sky_masked_subject.json` | per-view subject and full-frame PSNR, written by cell 13 of the notebook |
| `sky_masked_metrics_fullframe.json` | `metrics.py` output for the masked run (PSNR/SSIM/LPIPS, every pixel) |
| `sky_trained_subject.json` | the earlier run's renders rescored on the same pixels by `tools/sky_audit.py` |
| `sky_occupancy.json` | how much of each model sits in the sky, by projection into the held-out cameras |
| `frame.json` | the true vertical, crop bounds and gaussian counts of the masked run |
| `sky_mask.json` | which segmenter produced the masks, and how many sparse points were dropped as sky |

## Reproducing

Both derived files come from `tools/sky_audit.py`. It needs the masked run's Kaggle
output (`out_sala/masks/`, `cameras_final.json`) and, for the rescoring, the earlier
run's `sala_heldout_renders.zip` unpacked.

```sh
python tools/sky_audit.py subject \
  --renders <unpacked v6 renders>/ours_30000 \
  --masks   <kaggle out_sala>/masks \
  --names   <kaggle out_sala>/results_subject.json \
  -o results/sala_skymask/sky_trained_subject.json

python tools/sky_audit.py occupancy \
  --splat   sala_sky_trained.splat sala_sky_masked.splat \
  --cameras <kaggle out_sala>/cameras_final.json \
  --masks   <kaggle out_sala>/masks \
  --names   <kaggle out_sala>/results_subject.json \
  -o results/sala_skymask/sky_occupancy.json
```

`occupancy` also reads a `viewer/splat_*.js` directly, since those embed the same
32-byte rows as base64.

## What is still not fixed

Haze remains around the roof. Those gaussians are attached to the building's own
silhouette: they are seen against the building in most views and against sky in a
few, so no per-pixel mask suppresses them. Zero gradient in the sky also means zero
penalty, so a gaussian that drifts into open air is never pushed back out — the crop
and the size filter still do that afterwards. The roof itself is unchanged, because
no camera in this capture looks down on it, and the 51 `Sala Inside` frames remain a
separate COLMAP sub-model that neither run includes.
