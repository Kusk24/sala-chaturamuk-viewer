# Sala Viewer

Image-based rendering viewer for **Sala Chaturamuk Phaichit**, the four-porched Thai pavilion at
Assumption University's Suvarnabhumi campus.

Novel viewpoints are synthesized directly from photographs through optical-flow view interpolation —
no 3D reconstruction, no mesh, no radiance field. Follows Szeliski Ch. 14 (Image-Based Rendering).

**CSX4213 / ITX4283 Computer Vision — term project**
Win Yu Maung · Myat Bhone Thet · Min Pyae Hein

## Status

| Stage | State |
|---|---|
| Capture | Not started |
| Frame extraction | Implemented — awaiting capture |
| Correspondence + interpolation | Implemented — awaiting capture |
| Viewer | Implemented — awaiting frames |
| Evaluation (PSNR/SSIM) | Implemented — no measurements taken yet |
| Paper | Draft — Results section pending experiments |

The pipeline has been run end to end on synthetic test frames only. No number in this repository,
in `output/metrics/`, or in the paper comes from the real pavilion yet.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Pipeline

```bash
# 1. every frame of the walk -> ground truth pool
python src/extract_frames.py   --input data/raw/walk.mov  --out data/frames/

# 2. subsample to the capture set (every 15th frame here)
python src/extract_frames.py   --input data/frames/       --out data/selected/ --every 15

# 3. check adjacent frames are close enough to interpolate
python src/match_features.py   --frames data/selected/    --out output/matches.json

# 4. synthesize 2 in-between views per pair
python src/interpolate.py      --frames data/selected/    --out output/sequence/ --n-between 2

# 5. order + tag frames for the viewer
python src/build_sequence.py   --frames output/sequence/  --out viewer/manifest.json --angular-step 12

# 6. score synthesized frames against the real held-out ones
python src/evaluate.py         --synth output/sequence/ --truth data/frames/ --out output/metrics/
```

Then open `viewer/index.html` — drag to rotate, `B` toggles the captured-only baseline.

If you shot stills rather than video, drop them into `data/selected/` and start at step 3. Hold-out
evaluation needs the dense video capture, since it scores against frames that were deliberately
withheld.

## How the stages fit together

Each stage writes a small JSON next to its output so the next one doesn't have to guess:

- `data/*/index.json` — maps every extracted frame back to its index in the original capture.
- `output/sequence/interpolation.json` — records, per synthesized frame, which pair it came from
  and at what `t`.
- `viewer/manifest.json` — ordered frame list with `real` / angle tags. A `manifest.js` twin is
  written beside it because browsers block `fetch()` of local JSON, and the viewer must open from
  `file://`.

`evaluate.py` follows that chain to work out which real frame each synthesized frame should be
compared against, so the mapping stays right even if the capture is uneven.

## Evaluation

`evaluate.py` scores every synthesized frame twice against the same withheld photograph:

- **interp** — the flow-interpolated frame
- **baseline** — the nearest captured frame, i.e. what plain frame-switching would have shown

That pair of columns is what fills Table I of the paper. Results go to `output/metrics/metrics.csv`
(per frame) and `summary.csv` (aggregate). To get error against angular spacing, re-run steps 2–6
with different `--every` values and pass `--append-summary`.

## Notes

- The lake bounds the capture path — this is a **partial arc**, not a full 360° orbit. Nothing in
  the pipeline or viewer wraps around.
- The pavilion is four-fold symmetric; feature matching is restricted to adjacent frames to avoid
  false correspondences between faces. `match_features.py --symmetry-stride K` deliberately matches
  across that gap to measure the effect.
- Results in `output/metrics/` are the only source for numbers in the paper. Nothing gets written
  into the paper that wasn't measured here.
