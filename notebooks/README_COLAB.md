> **Revision v7 (9 Sep 2026, `*_sep05.ipynb`).** The sky is masked properly: SegFormer-B2 (ADE20K) labels it in every frame, the mask goes into the training images as an alpha channel (zero gradient in the sky, nothing painted black), and every COLMAP sparse point seen in the sky is dropped before 3DGS starts. Held-out views are scored twice: full frame (`results.json`, comparable with v5/v6) and subject only (`results_subject.json`). Attach the v6 version as input and COLMAP is reused; training restarts because `RUN` changed. `sky='hsv'` / `sky=False` in cell 2 reproduce v5 / v6.
>
> **Revision v6 (8 Sep 2026).** Sky mask off (it cost 2.2–2.4 dB), crop about the true vertical, floaters removed, model exported upright with rotated spherical harmonics, `splat_<subject>.js` written for the viewer. Attach the September version as input and COLMAP is reused; training restarts because `RUN` changed. Options `exposure` and `SUBMODEL` in cell 2.

# Running the 352-image Gaussian splatting on Google Colab

## Step 1 — build the upload archive (on this Mac)

```bash
cd "/Users/kusk/Desktop/Computer Vision/Term-Project/sala-chaturamuk-viewer"
zip -r -0 ~/Desktop/sala_352.zip \
    data/raw_versions/salathai_version1 \
    data/raw_versions/salathai_version2
```

`-0` skips compression — JPEGs do not compress further and it finishes far faster.
Expect roughly **1.3 GB** (862 MB + 425 MB).

## Step 2 — upload

Put `sala_352.zip` in the **top level** of your Google Drive (`MyDrive/sala_352.zip`).
Upload it from drive.google.com and let it finish before starting the notebook.

## Step 3 — run

1. Open <https://colab.research.google.com> → **File → Upload notebook** →
   `COLAB_sala_splat_352.ipynb`
2. **Runtime → Change runtime type → T4 GPU.** Not the P100 — it compiles the CUDA
   extensions and then fails about an hour into training.
3. Run the cells in order.

## What to watch

**Step 6, the fold check.** This is the one that decides whether the run is worth continuing.
The pavilion is four-faced, so views 90° apart look alike and the mapper can fold the geometry
into something that looks healthy in the numbers and is wrong. Reference values from the
previous failure: 7.0 for a healthy single capture, 36.0 and 102.2 inside the folded combined
model. If you see large ratios, stop — retraining on folded poses wastes the whole session.

**Step 8, the sky masks.** Look at the contact sheet. A leftover sliver of sky is fine; a chewed
roofline is not. Raise `V_MIN` if edges are being eaten.

**Step 12, the crop.** Adjust `KEEP_R` from the printed percentiles. Too tight clips the terrace,
too loose keeps the lawn.

## Time and outputs

Roughly 3–5 hours total; the 146-image run took 1 h 36 min for training alone.
Everything lands in `MyDrive/sala_splat_out/`, written as it goes, so a disconnect costs time
rather than results. Checkpoints are saved at 7k, 15k and 30k iterations.

Bring back `sala_352_masked_final.ply` and it goes into the local viewer and the paper.

## Or run it on Kaggle instead

Kaggle runs the notebook **detached** on its own servers, so closing the laptop cannot kill it.
That is the better host for this pipeline. See `README_KAGGLE.md` and `KAGGLE_sala_splat_352.ipynb`.
The two notebooks are not interchangeable — this one mounts Google Drive and uses `/content`
paths, neither of which exists on Kaggle.
