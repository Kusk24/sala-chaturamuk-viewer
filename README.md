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
| Frame extraction | Not started |
| Correspondence + interpolation | Not started |
| Viewer | Not started |
| Evaluation (PSNR/SSIM) | Not started |
| Paper | Draft — Results section pending experiments |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Pipeline

```bash
python src/extract_frames.py   --input data/raw/walk.mov --out data/frames/
python src/match_features.py   --frames data/selected/  --out output/matches.json
python src/interpolate.py      --frames data/selected/  --out output/sequence/ --n-between 2
python src/build_sequence.py   --frames output/sequence/ --out viewer/manifest.json
python src/evaluate.py         --synth output/sequence/ --truth data/frames/ --out output/metrics/
```

Then open `viewer/index.html`.

## Notes

- The lake bounds the capture path — this is a **partial arc**, not a full 360° orbit.
- The pavilion is four-fold symmetric; feature matching is restricted to adjacent frames to avoid
  false correspondences between faces.
- Results in `output/metrics/` are the only source for numbers in the paper. Nothing gets written
  into the paper that wasn't measured here.
