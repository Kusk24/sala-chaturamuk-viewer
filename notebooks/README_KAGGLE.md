# Running the 352-image Gaussian splatting on Kaggle

Notebook: `KAGGLE_sala_splat_352.ipynb`

This is the recommended host. `COLAB_sala_splat_352.ipynb` will **not** run here unchanged —
it mounts Google Drive and uses `/content` paths, neither of which exists on Kaggle.

Build the upload archive exactly as in Step 1 of `README_COLAB.md`.

## Why Kaggle is the better host for this

**Save & Run All commits the notebook and runs it on Kaggle's servers, detached.** Closing the
laptop, sleeping it, losing wifi — none of it touches the run. That is the exact failure that
killed the two Colab attempts. Kaggle's session limit is 12 h and the whole pipeline is ~4–5 h,
so in the normal case nothing needs to resume at all.

Kaggle also gives 4 CPU cores against Colab free's 2, which roughly halves the COLMAP stages.

## Setup

1. **Dataset, once:** left sidebar → *Datasets* → *New Dataset* → upload `sala_352.zip`
   (built as in Step 1 of `README_COLAB.md`). Name it `sala-352`. It persists forever.
2. Right sidebar → *Input* → *Add Input* → `sala-352`.
3. Right sidebar → *Accelerator* → **GPU T4 ×2**.
4. Right sidebar → *Internet* → **On**. Without it `apt-get`, `git clone` and `pip install` all
   fail — the most common way this run dies early.
5. **Save Version → Save & Run All (Commit).**

`T4 ×2` is what the earlier 146-image run used and it worked, but be clear that **the second GPU
does nothing here**: 3DGS trains on one device and COLMAP runs on CPU. Pick it because it is the
healthy Turing option, not for speed. The P100 is compute 6.0 and training aborts on it.

## Estimated wall time

| Stage | Kaggle | Basis |
|---|---|---|
| Unpack + downscale | 4 min | CPU-bound |
| Feature extraction | 12–15 min | 25 min measured on Colab's 2 cores |
| Sequential matching | 25–35 min | 45–60 min on Colab |
| Mapper | 10–20 min | largely single-threaded, scales least |
| Undistort + sky masking | 8–10 min | |
| Compile CUDA extensions | 5–8 min | measured, previous Kaggle run |
| **Training, 30 000 iters** | **2.5–3 h** | extrapolated from 1 h 36 min at 146 images |
| Render + score | 5 min | |
| **Total** | **≈ 4–5 h** | |

Only the training row is extrapolated rather than measured. 1 h 36 min is real, from the
`sala-v2-pinhole` run at 146 images; cost scales with Gaussian count more than image count, so
treat 2.5–3 h as an estimate.

## Differences from the Colab version

- Scratch goes to `/kaggle/temp` (wiped, uncounted); deliverables to `/kaggle/working/out`,
  which becomes the version's **Output** and is capped at 20 GB.
- `cached()` searches the current output *and* every attached input, so resuming means
  *Add Input → Notebook Output → this notebook's last version*. Anything restored that way is
  re-emitted into the new version's output too, so you only ever attach the **one latest**
  version instead of a growing chain. Keep it attached and the COLMAP hour never runs again.
- COLMAP is installed with `apt-get` here. That half has **never run on Kaggle before** — the
  earlier Kaggle notebook consumed poses computed locally — so it is the one genuinely untested
  step. The cell asserts on failure and carries an `add-apt-repository` fallback in a comment.
- A `.splat` is exported alongside the `.ply`. The 137 MB ply failed to download four times last
  run (`IncompleteRead`, 3.7 MB of 137 MB); the `.splat` is ~8× smaller and is what
  `viewer/splat.html` loads anyway.
- The sky contact sheet is written to a PNG as well as displayed, because a committed run has no
  live output to look at.
- The fold check raises. That matters more here: nobody is watching a detached run.
