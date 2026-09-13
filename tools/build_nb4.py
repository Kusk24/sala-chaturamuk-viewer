"""Builds KAGGLE/COLAB x lamp/sala notebooks from one cell list. Every host/subject
difference lives in cell 2's settings block; nothing else branches."""
import json, os

OUTDIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'notebooks')

SUBJ_MATCHER = {'sala':'sequential', 'lamp':'sequential', 'far':'sequential',
                'salamodel':'exhaustive'}

INFO = {
 'lamp': dict(t='~1 h 45 m', other='sala',
   tbl="""| Stage | Time |
|---|---|
| COLMAP extraction | ~7 min |
| COLMAP matching | ~10 min |
| COLMAP mapper | ~15 min |
| Undistort | ~4 min |
| Build CUDA extensions | ~6 min |
| **Training, 30 000 iters** | **~1 h** |
| Render + score | ~3 min |
| **Total** | **~1 h 45 m** |
| Sky segmentation (SegFormer, 100 frames) | ~2 min |
| **With the v6 version attached** (COLMAP reused) | **~1 h 15 m** |""",
   base='v6 (no mask), 13 held-out views:  PSNR 20.87  SSIM 0.784  LPIPS 0.306   (v5, HSV mask: 15.93)',
   note="100 photographs, three orbit rings (Higher / Middle / Lower) shot 17:51-17:55, portrait "
        "1200x1600. The fold check reports each ring separately - the step *between* rings is a "
        "real move, not a fold.\n\n**Run this one first.** It exercises the whole pipeline in under "
        "two hours, so if anything is wrong you find out cheaply."),
 'sala': dict(t='~6-7 h', other='lamp',
   tbl="""| Stage | Time |
|---|---|
| COLMAP extraction | ~30 min |
| COLMAP matching | ~45 min |
| COLMAP mapper | ~80 min |
| Undistort | ~15 min |
| Build CUDA extensions | ~6 min |
| **Training, 30 000 iters** | **~3-3.5 h** |
| Render + score | ~10 min |
| **Total** | **~6-7 h** |
| Sky segmentation (SegFormer, 446 frames) | ~4 min |
| **With the v6 version attached** (COLMAP reused) | **~2 h 20 m** |""",
   base='v6 (no mask), 50 held-out views:  PSNR 23.45  SSIM 0.769  LPIPS 0.333   (v5, HSV mask: 20.10)',
   note="446 photographs — Sala 360 (264) + Sala Inside (93) + Sala 360 Near (89), shot 17:13-17:41, "
        "landscape 1600x1200. **Three times the 146 images that scored 22.09 dB.**\n\n"
        "Training keeps the images on the CPU (`--data_device cpu`): 446 frames at 1600x1200 would "
        "otherwise occupy ~10 GB of the T4's 15 GB before a single Gaussian is allocated. That is "
        "the 3DGS README's own recommendation for large datasets and costs ~10% speed.\n\n"
        "`Sala 360` has three internal breaks (6.0, 1.0, 6.2 min). If the walk resumed in place, "
        "sequential matching bridges them; if not, that capture may show a couple of large steps "
        "on the fold check. Those are reported and the run continues - see cell 8 for why."),
 'salamodel': dict(t='~4.5-5.5 h', other='sala', cap='12 September', suffix='sep12',
   tbl="""| Stage | Time |
|---|---|
| COLMAP extraction | ~20 min |
| COLMAP matching (**exhaustive**, 45k pairs) | ~60-90 min |
| COLMAP mapper | ~40 min |
| Undistort | ~10 min |
| Build CUDA extensions | ~6 min |
| **Training, 30 000 iters** | **~2-2.5 h** |
| Render + score | ~7 min |
| **Total** | **~4.5-5.5 h** |""",
   base='no prior run - this is the first model of the tabletop Sala model. Nothing to beat yet.',
   note="301 photographs of the **miniature Sala model on a wooden board**, six orbit rings "
        "(view1 61, view2 65, view3 44, view4 45, view5 45, view6 41) shot 08:14-08:42 on 12 Sep "
        "2026, iPhone 17 Pro, 24 mm-equivalent on every frame, portrait 1200x1600.\n\n"
        "The phone wrote EXIF orientation 6 (landscape pixels + a rotate flag); preparation baked "
        "the rotation into the pixels and cleared the flag, so COLMAP, PIL and 3DGS all read the "
        "same 1200x1600 and the model does not come out on its side.\n\n"
        "**Matching is exhaustive, not sequential.** Measured on the prepared frames: the strong "
        "cross-orbit links sit ~60 frames apart in filename order (frame 30 <-> 91 = 91 RANSAC "
        "inliers), far outside any sequential window, while the orbit seams that sequential *would* "
        "use carry only 12-25 inliers. Sequential would join six rings by their weakest seams and "
        "risk a split model. The four-fold-symmetry danger that forced `loop_detection 0` on the "
        "real pavilion does not appear here: a 90-degree-apart pair scores 9 inliers, because the "
        "wood grain and cloth folds make every azimuth's background distinct.\n\n"
        "**No sky mask** (`sky=False`): this is an indoor tabletop scene. SegFormer's sky class "
        "would find no sky and risks labelling the bright white cloth as sky.\n\n"
        "`keep_r`/`keep_h` start permissive at 0.80 so nothing is cut before you have seen the "
        "model. Cell 14 prints the surface percentiles - tighten from those and re-run cell 14 "
        "alone against `salamodel_full.ply`; no retraining needed."),
}

def cells(host, subj):
    I = INFO[subj]; C = []
    CFG_MATCHER = SUBJ_MATCHER.get(subj, 'sequential')
    def md(t): C.append(('markdown', t.strip('\n')))
    def co(t): C.append(('code', t.strip('\n')))
    K = host == 'kaggle'

    setup = ("""1. **Dataset, once:** upload `cv_photos_prepared.zip` as a Kaggle Dataset named `sala-cv-sep05`.
2. Right sidebar → *Input* → *Add Input* → that dataset. **Attach nothing else** unless resuming.
3. **Accelerator → GPU T4 x2.** Not the P100.
4. **Internet → On.** Without it `apt-get`, `git clone`, `pip install` and the VGG download for LPIPS all fail.
5. **Save Version → Save & Run All (Commit).** Detached; closing the laptop cannot kill it.

**To run this revision on the cached COLMAP result:** *Add Input → Notebook Output → the
v6 (or September) version of this notebook*, then Save & Run All. Extraction, matching and the mapper — the
expensive 2.5 h — are restored and skipped. **Training starts fresh on purpose:** the run tag `RUN`
in cell 2 changed, so the old checkpoint is ignored and the new preprocessing actually takes effect.

**To resume this revision after a failure:** attach *its* last version the same way; its checkpoint
is picked up and training continues.""" if K else
"""1. Put `cv_photos_prepared.zip` anywhere in your Google Drive.
2. **Runtime → Change runtime type → T4 GPU.** Not the P100.
3. Run all cells.

**Colab free has no background execution** — if the laptop sleeps or the tab closes, the runtime
dies. Every stage banks to Drive and is restored on the next run, so you lose time rather than
work, but the Kaggle version runs detached and is the better host if you have quota.""")

    md(f"""
# {subj.upper()} — Gaussian Splatting from the {I.get('cap','5 September')} capture ({'Kaggle' if K else 'Colab'})

**This file builds the `{subj}` model only.** Its twin, `{host.upper()}_{I['other']}_sep05.ipynb`,
builds the other one. Nothing to edit — attach the dataset and run.

{I['note']}

## Why this capture should work where the last five did not

| | Old set (352) | This set |
|---|---|---|
| Cameras | 2 phones | **1** — iPhone 16 Pro |
| Lenses | 3 (ultra-wide, main, tele) | **1** — 2.22 mm ultra-wide |
| Focal length spread | 14 → 100 mm (**7x**) | **14 mm on every frame (1.00x)** |
| Sessions | 2, six days apart | **1**, 55 minutes |
| Frames with no EXIF | 131 | **0** |

The failure was never the code or the model — it was that COLMAP was told 352 photographs shared
one lens when they had many. Here they genuinely do share one lens, so `single_camera 1` is now
the *correct* setting rather than the bug it was before.

## What this revision fixes, so it runs in one go

- **`sparse/0`** — `image_undistorter` writes `sparse/` flat; 3DGS reads `sparse/0/`. This is what
  killed the first lamp run at the training step. Verified locally against 3DGS's own loader.
- **Out-of-memory auto-retry** — if `train.py` dies with a CUDA OOM, the cell resumes from the
  latest checkpoint with images on CPU and gentler densification. Two retries, then it stops.
- **Checkpoints pruned during training** — only the newest is kept, so output stays far under
  Kaggle's 20 GB cap.
- **`--test_iterations -1`** — no in-training evaluation, which the 3DGS README names as a memory
  spike. Scoring happens once, after training, in cell 13.
- **The fold check warns and continues** instead of stopping the run. On this capture the lens
  cause is structurally impossible, so a large step can only be a real break in the walk, which is
  not a reason to throw away six hours. The numbers are still printed and saved.
- **COLMAP 3.x / 4.x flag names** are detected, so an image upgrade does not break extraction.
- **Scoring never crashes the run** — if `metrics.py` fails, PSNR/SSIM are computed directly.

## What changed in this revision (`RUN = 'v7'`) — the sky is masked properly

v6 removed the sky *after* training, in space. Its held-out views still showed mid-sized sky
Gaussians as wisps around the roof: the size filter only catches the huge ones. v7 stops them
being created:

- **Semantic sky masks.** A pre-trained segmentation network (SegFormer-B2, ADE20K) labels the
  sky in every frame — consistently, which the v5 colour heuristic was not. The mask goes into the
  training image as an **alpha channel**, the route 3DGS's own loader supports: masked pixels give
  **zero gradient**, so nothing is ever pushed to exist there. Nothing is painted black; the ground
  truth is untouched. A pixel masked in one view and not in another is one fewer observation, not a
  contradiction — that is why this tolerates an imperfect mask where v5 could not.
- **No sky points in the initialisation.** Every COLMAP sparse point observed in the sky is
  dropped before 3DGS reads the scene — the effect of COLMAP's own mask option, without repeating
  the 2.5 h of COLMAP.
- **Two scores.** `metrics.py` scores every pixel, sky included; a model that renders no sky
  *must* lose on that number even as it visibly improves. So the held-out views are also scored on
  the subject only, and both are reported (`results.json`, `results_subject.json`).
- The crop, size filter and upright export from v6 stay: a Gaussian that drifts *into* the sky is
  not penalised either, so a few can still survive and are removed in space as before.

Not done: modelling the sky (a learned background / "haze"). Vanilla 3DGS has no such term; that
is a different codebase (WildGaussians and the like), not a setting.

## What v6 changed — no new photographs

Measured on the September models, not guessed:

- **The v5 sky mask was turned off.** It fired on some frames and not others, so the same
  overcast sky was textured in one photograph and black in the next. The model could not satisfy
  both and lost **2.2–2.4 dB** on every held-out score. Sala went 20.10 → 23.45 dB, lamp
  15.93 → 20.87 dB, with the worst views improving most.
- **The crop is about the true vertical.** COLMAP's y-axis was 15.5° (sala) / 29.3° (lamp) off
  vertical, so the old crop cylinder sliced diagonally through the subject and took the lamp's base
  with it. The vertical is now derived from the cameras' own up axes.
- **Floaters are removed by size.** 1% of the Gaussians — huge and nearly transparent — held
  80% of the model's volume. They are sky and far background; they go.
- **The final model is exported upright**, positions, orientations *and* spherical harmonics
  rotated, so SuperSplat and the viewer open it straight without a manual rotation.
- **A viewer script is written for you** (`splat_<subject>.js`) with the cameras in the new frame
  and an opening view chosen automatically.
- **`exposure` and `SUBMODEL` options** in cell 2: per-image exposure compensation, and training
  the second COLMAP sub-model (for sala, the interior — 71 photographs no model has used yet).

## Setup

{setup}

## Expected wall time

{I['tbl']}
""")

    md("## 1 · GPU check")
    co(r"""
!nvidia-smi
import torch
print('torch', torch.__version__, '| CUDA available:', torch.cuda.is_available())
assert torch.cuda.is_available(), 'No GPU. Select a T4 GPU accelerator.'
major, _ = torch.cuda.get_device_capability(0)
name = torch.cuda.get_device_name(0)
print('device:', name, f'(compute {major}.x)')
assert major >= 7, f'{name} is compute {major}.x, unsupported by this PyTorch build. Use the T4.'
""")

    md(r"""
## 2 · Settings, paths, and where we left off

Everything downstream keys off `SUBJECT`, so the two models never overwrite each other.
""")
    host_block = (r"""
HOST = 'kaggle'
WORK  = f'/kaggle/temp/work_{SUBJECT}'          # scratch: wiped, uncounted
OUT   = f'/kaggle/working/out_{SUBJECT}'        # becomes the version's Output
GS    = '/kaggle/working/gaussian-splatting'
INPUT_ROOTS = ['/kaggle/input']
REPORT_ROOT = '/kaggle/working'
""" if K else r"""
HOST = 'colab'
from google.colab import drive
drive.mount('/content/drive')
_z = glob.glob('/content/drive/MyDrive/**/cv_photos_prepared.zip', recursive=True)
DRIVE = os.path.dirname(_z[0]) if _z else '/content/drive/MyDrive'
print('drive folder:', DRIVE)
WORK  = f'/content/work_{SUBJECT}'               # wiped on disconnect
OUT   = f'{DRIVE}/out_{SUBJECT}'                 # survives on Drive
GS    = '/content/gaussian-splatting'
INPUT_ROOTS = [DRIVE]
REPORT_ROOT = DRIVE
""")
    co(f"""
import os, glob, zipfile, shutil, time, csv, subprocess, collections

# ============================ RUN SETTINGS ============================
SUBJECT  = '{subj}'   # fixed: this file is {subj} only
CAPTURE_DATE = '{I.get('cap','5 September')} 2026'
RUN      = 'v7'       # training/output tag - bump it to retrain from scratch while COLMAP stays cached
SUBMODEL = None       # None = largest COLMAP sub-model; '1' = the second one (sala: the interior)
FORCE    = set()      # e.g. {{'matching','mapper'}} to recompute a COLMAP stage
# ======================================================================

CFG = {{
  # overlap     : sequential matching window; the lamp orbits tightly so neighbours
  #               stay relevant for longer.
  # keep_r/h    : crop radius / half-height as a fraction of the camera-ring radius,
  #               measured about the TRUE vertical (cell 14). The sala's solid surface -
  #               pavilion, terrace, balustrade, steps - extends to ~1.05x ring because the
  #               near ring walked ON the terrace; 0.55 kept only 39% of it and cut the
  #               wings off. Its roof tops out ~0.65x ring above the cameras, so keep_h=1.0
  #               clears it. The lamp's own surface plateaus at ~0.5x ring (0.4 chewed its front
  #               corner); it sits BELOW its ring, so a tight keep_h=0.6 trims terrace and sky.
  # floater     : drop gaussians whose largest axis exceeds this x ring. At 0.04 that is
  #               ~1% of them, holding ~80% of the volume - sky and far background.
  # sky         : 'seg' = semantic sky mask (SegFormer) as an alpha channel, zero gradient in
  #               the sky and no sky points in the initialisation. 'hsv' = the v5 heuristic that
  #               painted the sky black (cost 2.2-2.4 dB). False = train the sky and crop it
  #               away afterwards (v6).
  # exposure    : --train_test_exp, per-image exposure fitting. Changes the scoring
  #               protocol (right halves of held-out frames only), so off by default.
  # data_device : where 3DGS keeps the training images. 446 frames at 1600x1200 are
  #               ~10 GB on the GPU; the README recommends cpu for large sets.
  'sala': dict(matcher='sequential', overlap=10, keep_r=1.10, keep_h=1.00, floater=0.04, sky='seg', exposure=False, data_device='cpu'),
  'lamp': dict(matcher='sequential', overlap=14, keep_r=0.50, keep_h=0.60, floater=0.04, sky='seg', exposure=False, data_device='cuda'),
  'far':  dict(matcher='sequential', overlap=10, keep_r=1.20, keep_h=1.00, floater=0.04, sky='seg', exposure=False, data_device='cpu'),
  # salamodel: tabletop miniature. exhaustive matching links the six orbits (see cell 6);
  #            no sky indoors; crop starts permissive and is tuned from cell 14's percentiles.
  'salamodel': dict(matcher='exhaustive', overlap=10, keep_r=0.80, keep_h=0.80, floater=0.04, sky=False, exposure=False, data_device='cpu'),
}}
assert SUBJECT in CFG, SUBJECT
CF = CFG[SUBJECT]
SKY = {{True: 'hsv', False: 'off', None: 'off'}}.get(CF['sky'], CF['sky'])
assert SKY in ('seg', 'hsv', 'off'), SKY
{host_block.strip()}
SCENE = f'{{WORK}}/scene'; SRC = f'{{SCENE}}/input'; DB = f'{{SCENE}}/database.db'
TAG = SUBJECT + (f'_sub{{SUBMODEL}}' if SUBMODEL else '')        # output filename stem
MODEL_DIR = f'{{OUT}}/model_{{RUN}}' + (f'_sub{{SUBMODEL}}' if SUBMODEL else '')
for d in (WORK, OUT, SCENE): os.makedirs(d, exist_ok=True)

STAGE_OF = {{'db_extracted.db':'extraction', 'db_matched.db':'matching', 'sparse':'mapper'}}
def cached(name):
    if STAGE_OF.get(name) in FORCE:
        print(f'  [FORCE] ignoring cached {{name}}'); return None
    p = f'{{OUT}}/{{name}}'
    if os.path.exists(p): return p
    hits = []
    for root in INPUT_ROOTS:
        hits += glob.glob(f'{{root}}/**/out_{{SUBJECT}}/{{name}}', recursive=True)
    hits = sorted(h for h in hits if os.path.abspath(h) != os.path.abspath(p))
    return hits[0] if hits else None

def adopt(hit, name):
    # re-emit whatever we restored, so only the LATEST version ever needs attaching
    dst = f'{{OUT}}/{{name}}'
    if os.path.abspath(hit) != os.path.abspath(dst):
        if os.path.isdir(hit):
            if os.path.exists(dst): shutil.rmtree(dst)
            shutil.copytree(hit, dst)
        else: shutil.copy(hit, dst)
    return dst

z = []
for root in INPUT_ROOTS: z += glob.glob(f'{{root}}/**/cv_photos_prepared.zip', recursive=True)
if z:
    print('unpacking', z[0])
    with zipfile.ZipFile(z[0]) as f: f.extractall(f'{{WORK}}/raw')
    RAW = [f'{{WORK}}/raw']
else:
    RAW = INPUT_ROOTS
    print('no zip found - assuming the dataset is already unpacked')

hits = []
for root in RAW: hits += glob.glob(f'{{root}}/**/{{SUBJECT}}/*.jpg', recursive=True)
assert hits, f'no {{SUBJECT}}/*.jpg found - is the dataset attached / uploaded?'
IMGDIR = os.path.dirname(sorted(hits)[0])
imgs = sorted(glob.glob(f'{{IMGDIR}}/*.jpg'))

MAN = {{}}
mf = []
for root in RAW: mf += glob.glob(f'{{root}}/**/{{SUBJECT}}_manifest.csv', recursive=True)
if mf:
    for r in csv.DictReader(open(mf[0])): MAN[r['new']] = r['folder']
    print('captures:', dict(collections.Counter(MAN.values())))

print(f'\\nsubject : {{SUBJECT}}   {{len(imgs)}} images from {{IMGDIR}}')
print(f'run     : {{RUN}}   model dir {{MODEL_DIR}}   sub-model {{SUBMODEL or "largest"}}')
print(f'outputs : {{OUT}}')
print('\\n--- resume report ---')
for label, nm in (('extraction','db_extracted.db'), ('matching  ','db_matched.db'), ('mapper    ','sparse')):
    h = cached(nm); print(f'  {{label}} cached : {{bool(h)}}' + (f'   <- {{h}}' if h else ''))
def latest_ckpt():
    ck = glob.glob(f'{{MODEL_DIR}}/chkpnt*.pth')
    # only a checkpoint from the SAME run tag can resume; an attached older run's model/
    # is ignored, which is what makes changed preprocessing actually take effect
    for root in INPUT_ROOTS: ck += glob.glob(f'{{root}}/**/out_{{SUBJECT}}/{{os.path.basename(MODEL_DIR)}}/chkpnt*.pth', recursive=True)
    # highest iteration wins; on a tie the copy already inside MODEL_DIR wins, so a
    # checkpoint adopted from an attached version is never mistaken for a foreign one
    ck = sorted(set(ck), key=lambda p: (int(''.join(c for c in os.path.basename(p) if c.isdigit())),
                                        p.startswith(MODEL_DIR)))
    return ck[-1] if ck else None
print(f'  training ckpt     : {{os.path.basename(latest_ckpt()) if latest_ckpt() else "none"}}')
""")

    md(r"""
## 3 · Stage the images

Already 1600 px on the long edge, so this only copies and confirms every frame in the subject
shares one pixel size. **A mixed size inside one subject means a mixed field of view, which is
exactly the failure this capture was designed to avoid** — so it stops here rather than reproducing it.
""")
    co(r"""
from PIL import Image
os.makedirs(SRC, exist_ok=True)
if len(glob.glob(f'{SRC}/*.jpg')) != len(imgs):
    for p in imgs: shutil.copy(p, f'{SRC}/{os.path.basename(p)}')
staged = sorted(glob.glob(f'{SRC}/*.jpg'))
sizes = collections.Counter(Image.open(p).size for p in staged)   # header only, fast
print(f'{len(staged)} images   sizes (w,h): {dict(sizes)}')
assert len(sizes) == 1, (f'MIXED IMAGE SIZES {dict(sizes)} - different fields of view in one '
                         'camera group is the exact defect that broke the previous five runs.')
""")

    md(r"""
## 4 · Install COLMAP and detect its flag names

COLMAP 3.x calls the options `SiftExtraction.use_gpu` / `SiftMatching.*`; 4.x renamed them to
`FeatureExtraction.*` / `FeatureMatching.*`. Kaggle's image currently ships 3.x, but detecting it
costs nothing and means an image upgrade cannot break extraction.
""")
    co(r"""
os.environ['QT_QPA_PLATFORM'] = 'offscreen'   # headless: Qt's default plugin wants an X display
if shutil.which('colmap') is None:
    !apt-get -qq update > /dev/null 2>&1
    !apt-get -qq install -y colmap > /dev/null 2>&1
assert shutil.which('colmap'), 'colmap did not install - is Internet On?'

_h = subprocess.run(['colmap','feature_extractor','--help'], capture_output=True, text=True)
_h = _h.stdout + _h.stderr
NEWFLAGS = '--FeatureExtraction.use_gpu' in _h
F_GPU  = '--FeatureExtraction.use_gpu'        if NEWFLAGS else '--SiftExtraction.use_gpu'
F_SIZE = '--FeatureExtraction.max_image_size' if NEWFLAGS else '--SiftExtraction.max_image_size'
M_GPU  = '--FeatureMatching.use_gpu'          if NEWFLAGS else '--SiftMatching.use_gpu'
M_MAX  = '--FeatureMatching.max_num_matches'  if NEWFLAGS else '--SiftMatching.max_num_matches'
_v = subprocess.run(['colmap','-h'], capture_output=True, text=True); _v = (_v.stdout + _v.stderr).split('\n')[0]
print(shutil.which('colmap'), '|', _v.strip(), '| flag family:', 'FeatureExtraction/FeatureMatching (4.x)' if NEWFLAGS else 'SiftExtraction/SiftMatching (3.x)')

def sh(cmd):
    # run a shell command, stream its output, return the exit code
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in p.stdout: print(line, end='')
    return p.wait()
""")

    md(r"""
## 5 · Feature extraction — cached

`single_camera 1` is **correct here**: every frame in a subject came from the same phone, the same
ultra-wide lens and the same 14 mm-equivalent focal length. `OPENCV` fits k1, k2, p1, p2 rather than
`SIMPLE_RADIAL`'s single parameter — an ultra-wide needs it.
""")
    co(r"""
hit_m, hit_e = cached('db_matched.db'), cached('db_extracted.db')
if hit_m:
    shutil.copy(adopt(hit_m,'db_matched.db'), DB); print('matched db restored - extraction and matching skipped')
elif hit_e:
    shutil.copy(adopt(hit_e,'db_extracted.db'), DB); print('extracted db restored - skipping extraction')
else:
    if os.path.exists(DB): os.remove(DB)
    t0 = time.time()
    rc = sh(f'colmap feature_extractor --database_path {DB} --image_path {SRC}'
            f' --ImageReader.single_camera 1 --ImageReader.camera_model OPENCV'
            f' {F_GPU} 0 {F_SIZE} 1600 --SiftExtraction.max_num_features 8192')
    assert rc == 0 and os.path.exists(DB), f'feature_extractor failed (rc={rc})'
    shutil.copy(DB, f'{OUT}/db_extracted.db')
    print(f'extraction done in {(time.time()-t0)/60:.1f} min, banked')
""")

    md(r"""
## 6 · Matching — cached
""" + ("""
**Exhaustive** for this subject. Every pair is proposed and geometrically verified. The six orbit
rings only connect through pairs that sit ~60 frames apart in filename order, which no sequential
window reaches; the seams sequential *would* use carry a fraction of the inliers. Exhaustive is
affordable here because the set is small (301 frames, ~45k pairs).

Loop detection's four-faced failure does not apply: this scene's background (wood grain, cloth
folds) differs at every azimuth, so 90-degree-apart pairs do not falsely match.
""" if CFG_MATCHER == 'exhaustive' else """
**Sequential, loop detection OFF.** The pavilion is four-faced, so views 90 degrees apart look
alike. Vocabulary-tree loop detection retrieves on appearance and cannot tell them apart, which is
what folded every earlier attempt. Sequential matching proposes only temporally adjacent pairs,
which cannot be 90 degrees apart.
"""))
    co(r"""
if cached('db_matched.db'):
    print('matching already cached - skipping')
else:
    t0 = time.time()
    if CF.get('matcher', 'sequential') == 'exhaustive':
        rc = sh(f'colmap exhaustive_matcher --database_path {DB}'
                f' {M_GPU} 0 {M_MAX} 16384')
        assert rc == 0, f'exhaustive_matcher failed (rc={rc})'
    else:
        rc = sh(f'colmap sequential_matcher --database_path {DB}'
                f' {M_GPU} 0 {M_MAX} 16384'
                f' --SequentialMatching.overlap {CF["overlap"]}'
                f' --SequentialMatching.loop_detection 0')
        assert rc == 0, f'sequential_matcher failed (rc={rc})'
    shutil.copy(DB, f'{OUT}/db_matched.db')
    print(f'matching done in {(time.time()-t0)/60:.1f} min, banked')
""")

    md("## 7 · Mapper — cached")
    co(r"""
SPARSE = f'{SCENE}/sparse'
hit_s = cached('sparse')
if hit_s and (glob.glob(f'{hit_s}/*/images.bin') or glob.glob(f'{hit_s}/*/images.txt')):
    if os.path.exists(SPARSE): shutil.rmtree(SPARSE)
    shutil.copytree(adopt(hit_s,'sparse'), SPARSE); print('mapper result restored - skipping')
else:
    if os.path.exists(SPARSE): shutil.rmtree(SPARSE)
    os.makedirs(SPARSE, exist_ok=True)
    t0 = time.time()
    rc = sh(f'colmap mapper --database_path {DB} --image_path {SRC} --output_path {SPARSE}')
    assert rc == 0 and glob.glob(f'{SPARSE}/*'), f'mapper failed (rc={rc}) or produced no model'
    dst = f'{OUT}/sparse'
    if os.path.exists(dst): shutil.rmtree(dst)
    shutil.copytree(SPARSE, dst)
    print(f'mapper done in {(time.time()-t0)/60:.1f} min, banked')
print('sub-models:', sorted(os.listdir(SPARSE)))
""")

    md(r"""
## 8 · Fold check — reported, not fatal

Consecutive frames in a walk should land close together. Two numbers are printed per capture:
the ratio of the largest step to the median, and the *fraction* of steps above 5x the median.

| | ratio | jumps > 5x |
|---|---|---|
| healthy single capture (v2 alone) | 7.0 | 1.4% |
| folded (the old combined set) | 27–102 | 5.5–9.3% |
| one real pause-and-relocate in a walk | high | ~0.5% |

A fold shows up in **both** numbers. A genuine break in the walk spikes the ratio but not the
fraction. This capture is one camera at one focal length with loop detection off, so the two
causes that produced folds before are structurally ruled out — which is why this cell now
**warns and continues** rather than throwing away the run. The verdict is printed, saved to
`FOLD_WARNING.txt` in the output if triggered, and the 7k / 15k / 30k models let you judge afterwards.
""")
    co(r"""
import numpy as np
PICK = SUBMODEL
sub = sorted(glob.glob(f'{SPARSE}/*'))
assert not PICK or os.path.isdir(f'{SPARSE}/{PICK}'), f'SUBMODEL={PICK!r} but sparse/ has {sorted(os.listdir(SPARSE))}'
for m in sub:
    if not os.path.exists(f'{m}/images.txt'):
        sh(f'colmap model_converter --input_path {m} --output_path {m} --output_type TXT > /dev/null')

def read_pos(model):
    pos = {}
    for line in open(f'{model}/images.txt'):
        if line.startswith('#') or not line.strip(): continue
        f = line.split()
        if len(f) < 10 or not f[0].isdigit(): continue
        qw,qx,qy,qz,tx,ty,tz = map(float, f[1:8]); nm = f[9]
        q = np.array([qw,qx,qy,qz]); q /= np.linalg.norm(q); w,x,y,z = q
        R = np.array([[1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)],
                      [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)],
                      [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]])
        pos[nm] = -R.T @ np.array([tx,ty,tz])
    return pos

def ratios(pos):
    g = {}
    for n in pos: g.setdefault(MAN.get(n, 'all'), []).append(n)
    out = {}
    for cap, ns in sorted(g.items()):
        ns = sorted(ns)
        if len(ns) < 5: continue
        P = np.array([pos[n] for n in ns])
        step = np.linalg.norm(np.diff(P, axis=0), axis=1); med = np.median(step)
        jumps = int((step > 5*med).sum())
        out[cap] = (len(ns), step.max()/med, jumps, jumps/len(step))
    return out

report = {m: read_pos(m) for m in sub}
for m in sub: print(f'  sub-model {os.path.basename(m)}: {len(report[m])} images')
MODEL = f'{SPARSE}/{PICK}' if PICK else max(sub, key=lambda m: len(report[m]))
pos = report[MODEL]
print(f'\nusing sub-model {os.path.basename(MODEL)}: {len(pos)} of {len(os.listdir(SRC))} images\n')

lines, folded = [], []
for cap,(n,r,j,fr) in ratios(pos).items():
    fold = r >= 15 and fr >= 0.04          # BOTH conditions: a real fold, not a walk break
    tag = '*** FOLD PATTERN ***' if fold else ('large step, walk break?' if r >= 15 else 'ok')
    line = f'{cap:32s} {n:4d} imgs  max/median = {r:6.1f}  jumps>5x = {j:3d} ({fr*100:4.1f}%)  {tag}'
    print(line); lines.append(line)
    if fold: folded.append(cap)
if folded:
    msg = ('FOLD PATTERN in ' + ', '.join(folded) + ' - both ratio and jump fraction are high.\n'
           'The run continues so the 7k/15k/30k models exist to inspect, but treat them with suspicion.\n\n'
           + '\n'.join(lines))
    open(f'{OUT}/FOLD_WARNING.txt','w').write(msg)
    print('\n' + '!'*78 + '\n' + msg + '\n' + '!'*78)
else:
    print('\nfold check: no fold pattern')
""")

    md("## 9 · Undistort to a pinhole camera, then lay it out the way 3DGS reads it")
    co(r"""
PIN = f'{WORK}/scene_pinhole'
if SKY != 'hsv' and os.path.exists(f'{PIN}/.sky_removed'):
    print('scratch images were painted black by an earlier run in this session - rebuilding them clean')
    shutil.rmtree(PIN)
if os.path.exists(f'{PIN}/images') and len(glob.glob(f'{PIN}/images/*')) >= len(pos) - 2:
    print('already undistorted, skipping')
else:
    if os.path.exists(PIN): shutil.rmtree(PIN)
    rc = sh(f'colmap image_undistorter --image_path {SRC} --input_path {MODEL} --output_path {PIN}'
            f' --output_type COLMAP --max_image_size 1600')
    assert rc == 0, f'image_undistorter failed (rc={rc})'
print(len(glob.glob(f'{PIN}/images/*')), 'undistorted images')

# colmap image_undistorter writes sparse/{cameras,images,points3D}.bin FLAT, but 3DGS's
# readColmapSceneInfo hardcodes sparse/0/. The repo's own convert.py does this move;
# image_undistorter on its own does not. This is what killed the first lamp run.
sp = f'{PIN}/sparse'
if not os.path.isdir(f'{sp}/0'):
    os.makedirs(f'{sp}/0', exist_ok=True)
    for f in os.listdir(sp):
        if f != '0': shutil.move(f'{sp}/{f}', f'{sp}/0/{f}')
print('sparse/0 contains:', sorted(os.listdir(f'{sp}/0')))
assert glob.glob(f'{sp}/0/images.*') and glob.glob(f'{sp}/0/cameras.*'), 'sparse/0 incomplete - training would fail'
""")

    md(r"""
## 10 · Sky — segmented, and handed to 3DGS as an alpha channel

Three sky strategies have now been measured on this capture:

| | how | result |
|---|---|---|
| v5 | HSV + gradient heuristic, sky painted black | fired inconsistently; **−2.2 to −2.4 dB** |
| v6 | no mask; crop and size-filter the sky away in space afterwards | +3.35 / +4.93 dB, but mid-sized sky wisps survive |
| **v7** | **SegFormer-B2 (ADE20K) sky mask as alpha; sparse sky points dropped** | this run |

The mask is written into the alpha channel of a copy of each training image. 3DGS's loader keeps
a fourth channel as `alpha_mask` and multiplies the *render* by it before the loss — the ground
truth is never touched — so a masked pixel contributes no gradient at all. That is the difference
from v5: nothing is told "the sky is black", the sky is simply unobserved. The sky mask is eroded
by a few pixels so a wobbly boundary costs a thin rim of sky rather than the roofline.

The same masks then remove every COLMAP sparse point that was observed in the sky, so 3DGS's
initial Gaussians contain none — the equivalent of running COLMAP with a sky mask, without
repeating 2.5 h of COLMAP. `sky='hsv'` / `sky=False` in cell 2 reproduce v5 / v6.
""")
    co(r"""
import numpy as np, cv2, time, json
from PIL import Image
SEG_MODEL, SEG_LONG, SKY_ID, ERODE = 'nvidia/segformer-b2-finetuned-ade-512-512', 1024, 2, 6
MASKS = f'{PIN}/masks'          # 8-bit PNG per frame: 255 = subject (trained), 0 = sky (ignored)
ALPHA = f'{PIN}/images_alpha'   # training copies of the images with that mask as alpha
CACHE = f'{OUT}/masks'          # the masks again, in the version OUTPUT: {PIN} is scratch and is
                                # wiped between versions, so without this a rerun repeats the GPU
                                # pass. ~30 KB a frame; the RGBA copies are far too big to keep.
files = sorted(glob.glob(f'{PIN}/images/*'))

def stem(p): return os.path.splitext(os.path.basename(p))[0]

def restore_masks():
    # any earlier version of this notebook, attached as input, or this session's own output
    dirs = [CACHE]
    for root in INPUT_ROOTS: dirs += glob.glob(f'{root}/**/out_{SUBJECT}/masks', recursive=True)
    n = 0
    for d in dirs:
        if not os.path.isdir(d) or os.path.abspath(d) == os.path.abspath(MASKS): continue
        for p in files:
            src, dst = f'{d}/{stem(p)}.png', f'{MASKS}/{stem(p)}.png'
            if os.path.exists(src) and not os.path.exists(dst): shutil.copy(src, dst); n += 1
    return n

def build_alpha(paths):
    # RGB from the photograph, alpha from the mask. PNG bytes under the ORIGINAL name: 3DGS looks
    # the file up by the name in COLMAP's images.bin, and PIL reads the format from the header.
    for p in paths:
        im = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)
        keep = cv2.imread(f'{MASKS}/{stem(p)}.png', 0)
        assert keep is not None and keep.shape == im.shape[:2], p
        Image.fromarray(np.dstack([im, keep])).save(f'{ALPHA}/{os.path.basename(p)}', format='PNG')

def segment_sky(paths):
    import torch
    from transformers import SegformerForSemanticSegmentation
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    net = SegformerForSemanticSegmentation.from_pretrained(SEG_MODEL).to(dev).eval()
    mean = torch.tensor([0.485, 0.456, 0.406], device=dev).view(1, 3, 1, 1)
    std  = torch.tensor([0.229, 0.224, 0.225], device=dev).view(1, 3, 1, 1)
    k = np.ones((2 * ERODE + 1, 2 * ERODE + 1), np.uint8); frac = []; t0 = time.time()
    for i, p in enumerate(paths):
        im = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB); H, W = im.shape[:2]
        sc = SEG_LONG / max(H, W); h, w = int(round(H * sc / 32)) * 32, int(round(W * sc / 32)) * 32
        x = torch.from_numpy(cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA)).to(dev)
        x = x.permute(2, 0, 1)[None].float() / 255
        with torch.no_grad():
            lg = net(pixel_values=(x - mean) / std).logits                       # 1 x 150 x h/4 x w/4
            lg = torch.nn.functional.interpolate(lg, size=(H, W), mode='bilinear', align_corners=False)
            sky = (lg.argmax(1)[0] == SKY_ID).to(torch.uint8).cpu().numpy()
        sky = cv2.erode(sky, k)                       # shrink the SKY: silhouettes keep a rim of sky, never lose edge pixels
        cv2.imwrite(f'{MASKS}/{stem(p)}.png', ((1 - sky) * 255).astype(np.uint8))
        frac.append(sky.mean())
        if i % 50 == 0 or i == len(paths) - 1:
            print(f'  {i + 1:4d}/{len(paths)}  sky {sky.mean() * 100:5.1f}%   {time.time() - t0:5.0f} s')
    return np.array(frac)

def filter_sparse_points(sp0):
    # drop every sparse point that COLMAP observed in a sky pixel (majority of its views).
    # 3DGS reads sparse/0/points3D.ply if it exists, so the filtered cloud is written there.
    if not os.path.exists(f'{sp0}/images.txt'):
        assert sh(f'colmap model_converter --input_path {sp0} --output_path {sp0} --output_type TXT > /dev/null') == 0
    masks = {}
    def mask_of(name):
        if name not in masks: masks[name] = cv2.imread(f'{MASKS}/{os.path.splitext(name)[0]}.png', 0) > 127
        return masks[name]
    n_obs, n_sky = collections.Counter(), collections.Counter()
    lines = [l for l in open(f'{sp0}/images.txt') if not l.startswith('#') and l.strip()]
    for hdr, pts in zip(lines[0::2], lines[1::2]):
        name = hdr.split()[9]; m = mask_of(name); H, W = m.shape; v = pts.split()
        xs = np.array(v[0::3], float); ys = np.array(v[1::3], float); ids = np.array(v[2::3], int)
        ok = ids >= 0; xs = np.clip(xs[ok].round().astype(int), 0, W - 1); ys = np.clip(ys[ok].round().astype(int), 0, H - 1)
        insky = ~m[ys, xs]
        for pid, sk in zip(ids[ok], insky): n_obs[pid] += 1; n_sky[pid] += int(sk)
    xyz, rgb, kept, total = [], [], 0, 0
    for l in open(f'{sp0}/points3D.txt'):
        if l.startswith('#') or not l.strip(): continue
        v = l.split(); pid = int(v[0]); total += 1
        if n_sky[pid] * 2 > n_obs[pid]: continue            # seen in the sky in most of its views
        xyz.append([float(v[1]), float(v[2]), float(v[3])]); rgb.append([int(v[4]), int(v[5]), int(v[6])]); kept += 1
    xyz = np.array(xyz, np.float32); rgb = np.array(rgb, np.uint8)
    arr = np.zeros(kept, dtype=[('x','<f4'),('y','<f4'),('z','<f4'),('nx','<f4'),('ny','<f4'),('nz','<f4'),
                                ('red','u1'),('green','u1'),('blue','u1')])
    arr['x'], arr['y'], arr['z'] = xyz.T; arr['red'], arr['green'], arr['blue'] = rgb.T
    with open(f'{sp0}/points3D.ply', 'wb') as f:
        f.write(('ply\nformat binary_little_endian 1.0\nelement vertex %d\n' % kept
                 + ''.join(f'property float {c}\n' for c in ('x','y','z','nx','ny','nz'))
                 + ''.join(f'property uchar {c}\n' for c in ('red','green','blue')) + 'end_header\n').encode())
        f.write(arr.tobytes())
    return kept, total

MARK = f'{PIN}/.sky_removed'
if SKY == 'seg':
    for d in (MASKS, ALPHA, CACHE): os.makedirs(d, exist_ok=True)
    r = restore_masks()
    if r: print(f'restored {r} sky masks from a previous version - no GPU pass needed for those')
    todo = [p for p in files if not os.path.exists(f'{MASKS}/{stem(p)}.png')]
    if todo:
        print(f'segmenting the sky in {len(todo)} frames with {SEG_MODEL}')
        frac = segment_sky(todo)
        print(f'sky: mean {frac.mean() * 100:.1f}% of each frame (min {frac.min() * 100:.1f}%, max {frac.max() * 100:.1f}%)')
    else:
        print('sky masks already built, skipping the segmentation pass')
    for p in files:                                   # bank them where the next version can find them
        if not os.path.exists(f'{CACHE}/{stem(p)}.png'): shutil.copy(f'{MASKS}/{stem(p)}.png', f'{CACHE}/{stem(p)}.png')
    todo_a = [p for p in files if not os.path.exists(f'{ALPHA}/{os.path.basename(p)}')]
    if todo_a: print(f'writing {len(todo_a)} RGBA training copies'); build_alpha(todo_a)
    a = Image.open(f'{ALPHA}/{os.path.basename(files[0])}'); assert a.mode == 'RGBA', a.mode
    kept, total = filter_sparse_points(f'{PIN}/sparse/0')
    print(f'sparse points: {kept:,} of {total:,} kept ({(total - kept) / max(total, 1) * 100:.1f}% were observed in the sky)')
    json.dump(dict(model=SEG_MODEL, long_edge=SEG_LONG, erode=ERODE, sparse_total=total, sparse_kept=kept),
              open(f'{OUT}/sky_mask.json', 'w'), indent=2)
elif SKY == 'hsv':
    V_MIN, S_MAX, HSV_ERODE = 140, 50, 9
    def sky_mask(img):
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV); S, V = hsv[..., 1], hsv[..., 2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        grad = cv2.magnitude(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3), cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3))
        smooth = cv2.blur((grad < 25).astype(np.uint8), (9, 9)) > 0.7
        cand = ((S < S_MAX) & (V > V_MIN) & smooth).astype(np.uint8)
        cand = cv2.morphologyEx(cand, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        _, lab = cv2.connectedComponents(cand)
        top = set(np.unique(lab[: img.shape[0] // 20])) - {0}
        return cv2.erode(np.isin(lab, list(top)).astype(np.uint8), np.ones((HSV_ERODE, HSV_ERODE), np.uint8))
    if os.path.exists(MARK): print('sky already painted black, skipping')
    else:
        frac = []
        for p in files:
            im = cv2.imread(p); m = sky_mask(im); im[m.astype(bool)] = 0
            cv2.imwrite(p, im, [cv2.IMWRITE_JPEG_QUALITY, 95]); frac.append(m.mean())
        open(MARK, 'w').write('done'); frac = np.array(frac)
        print(f'sky painted black: mean {frac.mean() * 100:.1f}% per frame')
else:
    print('sky mask OFF (v6 behaviour) - the sky is trained with the scene and removed in space by cell 14')

import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
sel = files[::max(1, len(files) // 8)][:8]
fig, ax = plt.subplots(2, 4, figsize=(16, 6))
for a, p in zip(ax.ravel(), sel):
    im = cv2.cvtColor(cv2.imread(p), cv2.COLOR_BGR2RGB)
    if SKY == 'seg':
        sky = cv2.imread(f'{MASKS}/{stem(p)}.png', 0) < 128
        im = im.copy(); im[sky] = (0.45 * im[sky] + 0.55 * np.array([255, 40, 40])).astype(np.uint8)
    a.imshow(im); a.axis('off'); a.set_title(os.path.basename(p), fontsize=8)
plt.suptitle('training frames' + (' - red = sky, ignored by the loss' if SKY == 'seg' else ''), fontsize=10)
plt.tight_layout(); plt.savefig(f'{OUT}/training_contact_sheet.png', dpi=90); plt.show()
""")
    md("## 11 · Install 3D Gaussian Splatting")
    co(r"""
os.environ['TORCH_CUDA_ARCH_LIST'] = '7.5'      # T4
if not os.path.exists(f'{GS}/train.py'):
    shutil.rmtree(GS, ignore_errors=True)
    os.chdir(os.path.dirname(GS))
    rc = sh('git clone --recursive -q https://github.com/graphdeco-inria/gaussian-splatting')
    assert rc == 0, 'git clone failed - is Internet On?'
os.chdir(GS)
try:
    import diff_gaussian_rasterization, simple_knn, plyfile
    print('CUDA extensions already built')
except ImportError:
    for cmd in ('pip install -q plyfile',
                'pip install -q submodules/diff-gaussian-rasterization',
                'pip install -q submodules/simple-knn'):
        assert sh(cmd) == 0, f'failed: {cmd}'
    import diff_gaussian_rasterization, simple_knn
print('cwd:', os.getcwd())
""")

    md(r"""
## 12 · Train — resumable, and self-healing on out-of-memory

`--checkpoint_iterations` writes a full optimiser state every 5,000 iterations; only the newest is
kept on disk. If `train.py` dies with a CUDA out-of-memory, the cell resumes from that checkpoint
with the images moved to CPU and densification made gentler, up to two times. Any other failure
stops the run with the last 60 lines of output.

`--eval` holds out every 8th photograph, so the scores in the next cell are against images the
model never saw. With `sky='seg'`, `-i images_alpha` points 3DGS at the RGBA copies from cell 10;
its loader keeps the fourth channel as `alpha_mask` and the render is multiplied by it before the
loss, so sky pixels contribute nothing. `exposure=True` in cell 2 adds `--train_test_exp`: a per-image affine colour
correction is learned during training, absorbing auto-exposure drift between frames. It also
changes the scoring protocol — the held-out photographs' *left* halves are used to fit their
exposure and scores are computed on the *right* halves — so its numbers are not directly comparable
with a run without it. Off by default, so this revision changes one thing at a time. `--test_iterations -1` skips the in-training evaluation the README names as a
memory spike; scoring happens once, properly, in cell 13.
""")
    co(r"""
os.makedirs(MODEL_DIR, exist_ok=True)
# adopt a checkpoint from an attached earlier version, if any
_c = latest_ckpt()
if _c and not _c.startswith(MODEL_DIR):
    shutil.copy(_c, f'{MODEL_DIR}/{os.path.basename(_c)}'); print('adopted', os.path.basename(_c))

def prune_ckpts():
    ck = sorted(glob.glob(f'{MODEL_DIR}/chkpnt*.pth'),
                key=lambda p: int(''.join(c for c in os.path.basename(p) if c.isdigit())))
    for c in ck[:-1]:
        try: os.remove(c); print(f'  [pruned {os.path.basename(c)}]')
        except OSError: pass

def run_train(extra):
    # resume only from what is physically in MODEL_DIR (adoption above already copied
    # any attached checkpoint in), so the resume path is never an input-only file
    ck = sorted(glob.glob(f'{MODEL_DIR}/chkpnt*.pth'),
                key=lambda p: int(''.join(c for c in os.path.basename(p) if c.isdigit())))
    resume = ck[-1] if ck else None
    cmd = (f'python train.py -s {PIN} -m {MODEL_DIR} --iterations 30000 --eval'
           f' --save_iterations 7000 15000 30000'
           f' --checkpoint_iterations 5000 10000 15000 20000 25000 30000'
           f' --test_iterations -1 --disable_viewer {extra}'
           + (' -i images_alpha' if SKY == 'seg' else '')
           + (' --train_test_exp' if CF.get('exposure') else '')
           + (f' --start_checkpoint {resume}' if resume else ''))
    print('\n>>>', cmd, '\n')
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    tail = collections.deque(maxlen=60); buf = ''; n = 0
    for chunk in iter(lambda: p.stdout.read(4096), ''):
        buf += chunk
        while True:
            i = min([k for k in (buf.find('\n'), buf.find('\r')) if k >= 0], default=-1)
            if i < 0: break
            line, buf = buf[:i], buf[i+1:]
            if line.strip():
                print(line); tail.append(line); n += 1
                if n % 300 == 0: prune_ckpts()
    if buf.strip(): print(buf); tail.append(buf)
    rc = p.wait(); prune_ckpts()
    return rc, '\n'.join(tail)

os.chdir(GS)
profiles = [f'--data_device {CF["data_device"]}',
            '--data_device cpu --densify_grad_threshold 0.0004',
            '--data_device cpu --densify_grad_threshold 0.0006 --densify_until_iter 10000']
for attempt, extra in enumerate(profiles):
    t0 = time.time()
    rc, tail = run_train(extra)
    print(f'\ntrain.py exit {rc} after {(time.time()-t0)/60:.1f} min')
    if rc == 0: break
    if 'out of memory' in tail.lower() and attempt < len(profiles) - 1:
        print(f'\n*** CUDA out of memory on attempt {attempt+1}; resuming with relief profile {attempt+2} ***')
        continue
    raise RuntimeError('train.py failed and it was not an out-of-memory:\n' + tail)

plys = glob.glob(f'{MODEL_DIR}/point_cloud/iteration_*/point_cloud.ply')
assert plys, 'training finished but wrote no point_cloud.ply'
print('models written:', sorted(os.path.basename(os.path.dirname(p)) for p in plys))
""")

    md(r"""
## 13 · Render the held-out views and score them — twice

Only the test set is rendered (`--skip_train`); that is all `metrics.py` reads. `metrics.py`
scores **every pixel, sky included**, and a model trained not to render the sky must lose there.
So the same renders are scored a second time on the subject pixels only, using the cell-10 masks,
and both numbers are kept: the full-frame one is comparable with v5/v6, the subject-only one is
the honest measure of this revision. Note `metrics.py` reads the held-out photographs in sorted
name order, so mask *i* is the *i*-th name — checked by count. LPIPS needs a VGG
download the first time, so if `metrics.py` fails for any reason, PSNR and SSIM are computed
directly from the renders instead of letting a scoring hiccup end a six-hour run.
""")
    co(f"""
BASELINE = '{I['base']}'
""" + r"""
import json
os.chdir(GS)
rc = sh(f'python render.py -m {MODEL_DIR} --skip_train')
assert rc == 0, 'render.py failed'
sh(f'python metrics.py -m {MODEL_DIR}')

RES = f'{MODEL_DIR}/results.json'
if os.path.exists(RES):
    print(json.dumps(json.load(open(RES)), indent=2))
else:
    print('metrics.py did not write results.json - computing PSNR/SSIM directly')
    import numpy as np, cv2
    try:
        from skimage.metrics import structural_similarity as ssim_fn
    except ImportError:
        ssim_fn = None
    td = sorted(glob.glob(f'{MODEL_DIR}/test/ours_*'))[-1]
    ps, ss = [], []
    for r in sorted(glob.glob(f'{td}/renders/*.png')):
        a = cv2.imread(r).astype(np.float64); b = cv2.imread(f'{td}/gt/{os.path.basename(r)}').astype(np.float64)
        mse = np.mean((a-b)**2); ps.append(10*np.log10(255**2/mse) if mse > 0 else 99)
        if ssim_fn: ss.append(ssim_fn(a, b, channel_axis=2, data_range=255))
    res = {os.path.basename(td): {'PSNR': float(np.mean(ps)), 'SSIM': float(np.mean(ss)) if ss else None, 'LPIPS': None, 'n_test': len(ps)}}
    json.dump(res, open(RES,'w'), indent=2); print(json.dumps(res, indent=2))
print('\nbaseline to beat - ' + BASELINE)

# ---- subject-only score: same renders, sky pixels excluded ----------------------------------
if SKY == 'seg':
    import numpy as np, cv2
    names = sorted(os.path.basename(p) for p in glob.glob(f'{PIN}/images/*'))[::8]   # 3DGS: sorted names, every 8th
    td = sorted(glob.glob(f'{MODEL_DIR}/test/ours_*'), key=lambda p: int(p.rsplit('_', 1)[1]))[-1]
    rend = sorted(glob.glob(f'{td}/renders/*.png'))
    assert len(rend) == len(names), (len(rend), len(names))
    rows = []
    for i, nm in enumerate(names):
        r = cv2.imread(rend[i]).astype(np.float64); g = cv2.imread(f'{td}/gt/{os.path.basename(rend[i])}').astype(np.float64)
        m = cv2.imread(f'{MASKS}/{os.path.splitext(nm)[0]}.png', 0) > 127
        if CF.get('exposure'): m = m[:, m.shape[1] // 2:]                 # right-halves protocol
        if m.shape != r.shape[:2]: m = cv2.resize(m.astype(np.uint8), (r.shape[1], r.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
        se = (r - g) ** 2
        full = 10 * np.log10(255 ** 2 / se.mean())
        subj = 10 * np.log10(255 ** 2 / se[m].mean()) if m.any() else float('nan')
        rows.append(dict(name=nm, psnr_full=round(full, 3), psnr_subject=round(subj, 3), sky_frac=round(float(1 - m.mean()), 4)))
    P = np.array([r['psnr_subject'] for r in rows]); F = np.array([r['psnr_full'] for r in rows])
    summ = dict(n_test=len(rows), psnr_full=float(F.mean()), psnr_subject=float(np.nanmean(P)),
                psnr_subject_min=float(np.nanmin(P)), psnr_subject_median=float(np.nanmedian(P)),
                mean_sky_frac=float(np.mean([r['sky_frac'] for r in rows])), per_view=rows)
    json.dump(summ, open(f'{MODEL_DIR}/results_subject.json', 'w'), indent=2)
    print(f'\nsubject-only PSNR (sky excluded): {summ["psnr_subject"]:.2f} dB   '
          f'(min {summ["psnr_subject_min"]:.2f}, median {summ["psnr_subject_median"]:.2f})   '
          f'full-frame {summ["psnr_full"]:.2f} dB   sky = {summ["mean_sky_frac"] * 100:.0f}% of a held-out frame')
""")

    md(r"""
## 14 · Crop, remove floaters, stand it upright

Three things the September models needed by hand afterwards, now done here, in this order:

1. **Crop about the true vertical.** COLMAP's world axes come from its first registered frame, not
   from gravity — on this capture the y-axis was 15.5° (sala) / 29.3° (lamp) off vertical, and a
   crop cylinder aligned to it sliced diagonally through the subject and took the lamp's base with
   it. The vertical is now the mean of the cameras' own up axes; on a level hand-held walk they
   agree to ~0.95.
2. **Drop the floaters.** About 1% of the Gaussians are huge and nearly transparent — sky and far
   background the optimiser could not place — and they hold ~80% of the model's volume. Anything
   whose largest axis exceeds `floater` x ring goes.
3. **Rotate upright**, so the true vertical becomes -Y like every level 3DGS capture. Positions,
   orientations *and* the spherical harmonics are rotated; the per-band SH matrices are recovered
   against 3DGS's own basis and self-checked on random directions before the model is touched.
   The cameras are written in the same frame so the viewer opens on a real photograph's pose.

Tune `keep_r`, `keep_h`, `floater` in cell 2 from the printed percentiles.
""")
    co(r"""
import json, numpy as np
from plyfile import PlyData, PlyElement

cands = sorted(glob.glob(f'{MODEL_DIR}/point_cloud/iteration_*/point_cloud.ply'),
               key=lambda p: int(p.split('iteration_')[1].split('/')[0]))
SRC_PLY = cands[-1]; print('using', SRC_PLY)
v = PlyData.read(SRC_PLY)['vertex']; data = v.data.copy()
xyz = np.stack([data['x'], data['y'], data['z']], 1).astype(np.float64)
cams = json.load(open(f'{MODEL_DIR}/cameras.json'))          # same frame as the model
Rc = np.array([c['rotation'] for c in cams]); Pc = np.array([c['position'] for c in cams])

# ---- the true vertical: mean of every camera's own up axis ----------------------
up = -Rc[:, :, 1].mean(0); up /= np.linalg.norm(up)
agree = float(np.abs((-Rc[:, :, 1]) @ up).mean())
centre = np.median(Pc, axis=0); ring = float(np.median(np.linalg.norm(Pc - centre, axis=1)))
tilt = float(np.degrees(np.arccos(abs(up @ np.array([0, 1., 0])))))
cam_h = (Pc - centre) @ up
print(f'{len(xyz):,} gaussians   {len(cams)} cameras   ring radius {ring:.2f}')
print(f'true vertical is {tilt:.1f} deg off the y-axis   (camera up-axis agreement {agree:.3f})')

# ---- 1. crop: a cylinder about the TRUE vertical, centred on the camera ring -----
rel = xyz - centre; h = rel @ up; rad = np.linalg.norm(rel - np.outer(h, up), axis=1)
for q in (50, 70, 80, 90, 95, 99): print(f'  radius p{q:<3d} = {np.percentile(rad, q):6.2f}')
KEEP_R, KEEP_H = CF['keep_r'] * ring, CF['keep_h'] * ring
keep = (rad < KEEP_R) & (np.abs(h) < KEEP_H)
n_crop = int(keep.sum())
print(f'crop    : keeping {n_crop:,} of {len(xyz):,} ({keep.mean()*100:.1f}%)   KEEP_R {KEEP_R:.2f}   KEEP_H {KEEP_H:.2f}')
print(f'          kept height {h[keep].min():.2f} .. {h[keep].max():.2f}   cameras sit at {cam_h.min():.2f} .. {cam_h.max():.2f}')

# ---- 2. floaters: few, huge, nearly transparent, most of the volume ---------------
sc = np.exp(np.stack([data['scale_0'], data['scale_1'], data['scale_2']], 1).astype(np.float64))
FLOAT = CF['floater'] * ring
small = sc.max(1) < FLOAT
vol = 4/3 * np.pi * sc.prod(1)
big = keep & ~small
print(f'floaters: dropping {big.sum():,} gaussians larger than {FLOAT:.2f}, holding '
      f'{vol[big].sum() / max(vol[keep].sum(), 1e-12) * 100:.0f}% of the cropped volume')
keep &= small
data = data[keep]; xyz = xyz[keep]

# ---- 3. upright: true vertical -> -Y, rotating positions, quaternions AND SH -------
C1 = 0.4886025119029199
C2 = [1.0925484305920792, -1.0925484305920792, 0.31539156525252005, -1.0925484305920792, 0.5462742152960396]
C3 = [-0.5900435899266435, 2.890611442640554, -0.4570457994644658, 0.3731763325901154,
      -0.4570457994644658, 1.445305721320277, -0.5900435899266435]
def sh_basis(d):                        # bands 1..3 of 3DGS's real SH basis, in its storage order
    x, y, z = d[:, 0], d[:, 1], d[:, 2]; xx, yy, zz = x*x, y*y, z*z; xy, yz, xz = x*y, y*z, x*z
    return np.stack([-C1*y, C1*z, -C1*x,
        C2[0]*xy, C2[1]*yz, C2[2]*(2*zz-xx-yy), C2[3]*xz, C2[4]*(xx-yy),
        C3[0]*y*(3*xx-yy), C3[1]*xy*z, C3[2]*y*(4*zz-xx-yy), C3[3]*z*(2*zz-3*xx-3*yy),
        C3[4]*x*(4*zz-xx-yy), C3[5]*z*(xx-yy), C3[6]*x*(xx-3*yy)], 1)
BANDS = [(0, 3), (3, 8), (8, 15)]
def sh_rot_mats(R, n=4000):
    # per-band matrices M with colour_new(d) = colour_old(R^-1 d), by least squares on the basis
    rng = np.random.default_rng(0); d = rng.normal(size=(n, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
    A, B = sh_basis(d), sh_basis(d @ R)
    return [np.linalg.lstsq(A[:, lo:hi], B[:, lo:hi], rcond=None)[0] for lo, hi in BANDS]
def align(a, b):
    a = a/np.linalg.norm(a); b = b/np.linalg.norm(b); vv = np.cross(a, b); c = a @ b
    if np.linalg.norm(vv) < 1e-9: return np.eye(3) * (1 if c > 0 else -1)
    Kx = np.array([[0, -vv[2], vv[1]], [vv[2], 0, -vv[0]], [-vv[1], vv[0], 0]])
    return np.eye(3) + Kx + Kx @ Kx * (1 / (1 + c))
def mat_to_quat(R):
    t = np.trace(R)
    if t > 0:
        s = np.sqrt(t + 1) * 2; return np.array([0.25*s, (R[2,1]-R[1,2])/s, (R[0,2]-R[2,0])/s, (R[1,0]-R[0,1])/s])
    i = int(np.argmax(np.diag(R)))
    if i == 0: s = np.sqrt(1+R[0,0]-R[1,1]-R[2,2])*2; return np.array([(R[2,1]-R[1,2])/s, 0.25*s, (R[0,1]+R[1,0])/s, (R[0,2]+R[2,0])/s])
    if i == 1: s = np.sqrt(1+R[1,1]-R[0,0]-R[2,2])*2; return np.array([(R[0,2]-R[2,0])/s, (R[0,1]+R[1,0])/s, 0.25*s, (R[1,2]+R[2,1])/s])
    s = np.sqrt(1+R[2,2]-R[0,0]-R[1,1])*2; return np.array([(R[1,0]-R[0,1])/s, (R[0,2]+R[2,0])/s, (R[1,2]+R[2,1])/s, 0.25*s])
def quat_mul(q1, q2):                   # (w,x,y,z); q1 broadcast over the rows of q2
    w1, x1, y1, z1 = q1; w2, x2, y2, z2 = q2.T
    return np.stack([w1*w2-x1*x2-y1*y2-z1*z2, w1*x2+x1*w2+y1*z2-z1*y2,
                     w1*y2-x1*z2+y1*w2+z1*x2, w1*z2+x1*y2-y1*x2+z1*w2], 1)

R = align(up, np.array([0, -1., 0]))
Ms = sh_rot_mats(R)
rng = np.random.default_rng(1); d = rng.normal(size=(500, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
c = rng.normal(size=15); cn = c.copy()
for (lo, hi), M in zip(BANDS, Ms): cn[lo:hi] = M @ c[lo:hi]
sh_err = float(np.abs(sh_basis(d) @ cn - sh_basis(d @ R) @ c).max())
assert sh_err < 1e-6, f'SH rotation self-check failed ({sh_err:.2e}) - model left untouched'

new = (xyz - centre) @ R.T
data['x'], data['y'], data['z'] = new[:, 0], new[:, 1], new[:, 2]
q = np.stack([data[f'rot_{i}'] for i in range(4)], 1).astype(np.float64); q /= np.linalg.norm(q, axis=1, keepdims=True)
qn = quat_mul(mat_to_quat(R), q)
for i in range(4): data[f'rot_{i}'] = qn[:, i]
rest = np.stack([data[f'f_rest_{i}'] for i in range(45)], 1).astype(np.float64).reshape(-1, 3, 15)
for (lo, hi), M in zip(BANDS, Ms): rest[:, :, lo:hi] = rest[:, :, lo:hi] @ M.T
rest = rest.reshape(-1, 45)
for i in range(45): data[f'f_rest_{i}'] = rest[:, i]

FINAL = f'{OUT}/{TAG}_final.ply'
PlyData([PlyElement.describe(data, 'vertex')]).write(FINAL)
print(f'upright : rotated {np.degrees(np.arccos(np.clip(up @ np.array([0, -1., 0]), -1, 1))):.1f} deg   SH self-check {sh_err:.1e}')
print(f'wrote {FINAL}  ({os.path.getsize(FINAL)/1e6:.1f} MB, {len(data):,} gaussians)')

# the cameras in the same frame, so the viewer can open on a real photograph's pose
cams_final = [{**cc, 'rotation': (R @ np.array(cc['rotation'])).tolist(),
                     'position': (R @ (np.array(cc['position']) - centre)).tolist()} for cc in cams]
json.dump(cams_final, open(f'{OUT}/cameras_final.json', 'w'))
json.dump({'centre': centre.tolist(), 'ring': ring, 'up': up.tolist(), 'R': R.tolist(), 'tilt_deg': tilt,
           'camera_up_agreement': agree, 'keep_r': KEEP_R, 'keep_h': KEEP_H, 'floater': FLOAT,
           'total': int(len(v.data)), 'after_crop': n_crop, 'floaters_dropped': int(big.sum()), 'final': int(len(data))},
          open(f'{OUT}/frame.json', 'w'), indent=1)
print('wrote cameras_final.json, frame.json')
""")

    md(r"""
## 15 · Export, write the viewer file, tidy

`<tag>_final.ply` is the model for SuperSplat — upright, cropped, full spherical harmonics.
`<tag>_final.splat` is the same model in the 32-byte-per-Gaussian layout the web viewer reads,
and `splat_<tag>.js` wraps it, with its cameras and an opening view chosen automatically, into the
one script `viewer/<tag>.html` loads from `file://`. The raw 30k model is kept as `<tag>_full.ply`
for anyone who wants to redo the crop.
""")
    co(r"""
import json, base64, numpy as np
from plyfile import PlyData

def ply_to_splat(src, dst):
    # 32-byte rows: xyz f32[3], scale f32[3], rgba u8[4], quat u8[4] - antimatter15/splat layout
    p = PlyData.read(src)['vertex']
    SH_C0 = 0.28209479177387814
    xyz    = np.stack([p['x'], p['y'], p['z']], 1).astype(np.float32)
    scales = np.exp(np.stack([p['scale_0'], p['scale_1'], p['scale_2']], 1)).astype(np.float32)
    rot    = np.stack([p['rot_0'], p['rot_1'], p['rot_2'], p['rot_3']], 1).astype(np.float32)
    rot   /= np.linalg.norm(rot, axis=1, keepdims=True)
    rgb    = 0.5 + SH_C0 * np.stack([p['f_dc_0'], p['f_dc_1'], p['f_dc_2']], 1)
    alpha  = 1.0 / (1.0 + np.exp(-np.asarray(p['opacity'], dtype=np.float64)))
    order  = np.argsort(-(scales.astype(np.float64).prod(1) * alpha))
    n = len(order); buf = np.zeros((n, 32), dtype=np.uint8)
    buf[:,  0:12] = xyz[order].view(np.uint8).reshape(n, 12)
    buf[:, 12:24] = scales[order].view(np.uint8).reshape(n, 12)
    buf[:, 24:27] = np.clip(rgb[order] * 255, 0, 255).astype(np.uint8)
    buf[:, 27:28] = np.clip(alpha[order, None] * 255, 0, 255).astype(np.uint8)
    buf[:, 28:32] = np.clip(rot[order] * 128 + 128, 0, 255).astype(np.uint8)
    buf.tofile(dst); return n

for src, nm in ((SRC_PLY, f'{TAG}_full'), (FINAL, f'{TAG}_final')):
    d = f'{OUT}/{nm}.splat'; n = ply_to_splat(src, d)
    print(f'{nm}.splat  {n:,} gaussians  {os.path.getsize(d)/1e6:.1f} MB')
shutil.copy(SRC_PLY, f'{OUT}/{TAG}_full.ply')
for f in ('cameras.json', 'results.json', 'results_subject.json', 'cfg_args', 'per_view.json'):
    p = f'{MODEL_DIR}/{f}'
    if os.path.exists(p): shutil.copy(p, f'{OUT}/{f}')
if os.path.isdir(f'{MODEL_DIR}/test'):
    shutil.make_archive(f'{OUT}/{TAG}_heldout_renders', 'zip', f'{MODEL_DIR}/test')

# ---- the viewer file: model + cameras + opening view, one script, loads from file:// ----
cf = json.load(open(f'{OUT}/cameras_final.json'))
raw = np.fromfile(f'{OUT}/{TAG}_final.splat', dtype=np.uint8).reshape(-1, 32)
pts = raw[:, 0:12].copy().view(np.float32).reshape(-1, 3).astype(np.float64)
model_c = np.median(pts, axis=0)
sub = pts[np.random.default_rng(0).choice(len(pts), min(len(pts), 40000), replace=False)]
def visible(cc):
    # fraction of the model inside this camera's frustum. rotation is camera->world,
    # so world->camera is its transpose: q = (X - p) @ R. Camera looks along +z.
    Rm = np.array(cc['rotation']); q = (sub - np.array(cc['position'])) @ Rm
    z = np.maximum(q[:, 2], 1e-9); ok = q[:, 2] > 0.05
    ok &= (np.abs(q[:, 0] / z) < cc['width'] / (2 * cc['fx'])) & (np.abs(q[:, 1] / z) < cc['height'] / (2 * cc['fy']))
    return float(ok.mean())
def facing(cc):
    Rm = np.array(cc['rotation']); t = model_c - np.array(cc['position'])
    return float(Rm[:, 2] @ (t / max(np.linalg.norm(t), 1e-9)))
# the real photograph that has the most of the model in frame, among those looking at it
start = max(cf, key=lambda cc: (facing(cc) > 0.8, visible(cc)))
Rm = np.array(start['rotation']).reshape(9); t = start['position']
vm = [Rm[0], Rm[1], Rm[2], 0, Rm[3], Rm[4], Rm[5], 0, Rm[6], Rm[7], Rm[8], 0,
      -t[0]*Rm[0] - t[1]*Rm[3] - t[2]*Rm[6], -t[0]*Rm[1] - t[1]*Rm[4] - t[2]*Rm[7],
      -t[0]*Rm[2] - t[1]*Rm[5] - t[2]*Rm[8], 1]
JS = f'{OUT}/splat_{TAG}.js'
with open(JS, 'w') as f:
    f.write(f'// Generated - 3D Gaussian Splatting model ({TAG}), Sala Chaturamuk Phaichit, {CAPTURE_DATE} capture, run {RUN}.\n'
            f'// {len(raw):,} gaussians after crop / floater filter / upright, 32 bytes each. Base64 because a file:// page cannot fetch().\n'
            f'window.SPLAT_COUNT = {len(raw)};\n'
            f'window.SPLAT_VIEW_MATRIX = {json.dumps([round(float(x), 9) for x in vm])};\n'
            f'window.SPLAT_CAMERAS = {json.dumps(cf, separators=(",", ":"))};\n'
            f'window.SPLAT_DATA_B64 = "{base64.b64encode(raw.tobytes()).decode()}";\n')
print(f'viewer file: splat_{TAG}.js  {os.path.getsize(JS)/1e6:.1f} MB   opens on {start["img_name"]} ({visible(start)*100:.0f}% of the model in frame, facing {facing(start):.2f})')

os.chdir(os.path.dirname(GS))
shutil.rmtree(GS, ignore_errors=True)
prune_ckpts()
for d in sorted(glob.glob(f'{MODEL_DIR}/point_cloud/iteration_*'), key=lambda p: int(p.rsplit('_', 1)[1]))[:-2]:
    shutil.rmtree(d, ignore_errors=True); print('dropped', os.path.basename(d))

total = 0
print('\n--- output ---')
for root, _, fs in os.walk(OUT):
    for f in sorted(fs):
        p = os.path.join(root, f); sz = os.path.getsize(p); total += sz
        if sz > 1e6: print(f'  {os.path.relpath(p, OUT):50s} {sz/1e6:8.1f} MB')
print(f'\ntotal {total/1e6:.0f} MB')
print(f'\n=== {TAG} finished. Download splat_{TAG}.js, {TAG}_final.ply, results.json, {TAG}_heldout_renders.zip ===')
""")

    md(f"""
## What to download

1. **`out_{subj}/splat_{subj}.js`** — drop into `viewer/`; `{subj}.html` loads it. Cameras and opening view included.
2. **`out_{subj}/{subj}_final.ply`** — open in SuperSplat. Upright, cropped, floaters removed, full SH.
3. **`out_{subj}/results.json`** — held-out PSNR / SSIM / LPIPS, every pixel (comparable with v5/v6).
   **`out_{subj}/results_subject.json`** — the same views scored on the subject only, per view.
   `out_{subj}/sky_mask.json` — segmenter, erosion, and how many sparse points were sky.
4. **`out_{subj}/{subj}_heldout_renders.zip`** — render-versus-photograph pairs, paper figures.
5. **`out_{subj}/frame.json`** — the vertical, its tilt, crop bounds and counts that produced the final model.
6. `out_{subj}/training_contact_sheet.png` — what the model was actually trained on.
7. `out_{subj}/FOLD_WARNING.txt` — only exists if cell 8 saw a fold pattern. Read it if it does.
8. `out_{subj}/{subj}_full.ply` — the raw 30k model, only if you want to redo the crop yourself.

(With `SUBMODEL` set, the stem is `{subj}_sub1` instead of `{subj}`.)
""")
    return C

def write(host, subj):
    nb = {"nbformat":4, "nbformat_minor":4,
          "metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},
                      "language_info":{"name":"python","version":"3.10"},"accelerator":"GPU"},
          "cells":[]}
    for kind, text in cells(host, subj):
        lines = text.split('\n')
        cell = {"cell_type":kind, "metadata":{}, "source":[l+'\n' for l in lines[:-1]]+[lines[-1]]}
        if kind == 'code': cell["execution_count"] = None; cell["outputs"] = []
        nb["cells"].append(cell)
    out = f'{OUTDIR}/{host.upper()}_{subj}_{INFO[subj].get("suffix","sep05")}.ipynb'
    json.dump(nb, open(out,'w'), indent=1); open(out,'a').write('\n')
    return out, len(nb['cells'])

if __name__ == '__main__':
    import ast, re
    for host in ('kaggle','colab'):
        for subj in ('lamp','sala','salamodel'):
            out, n = write(host, subj)
            nb = json.load(open(out)); bad = 0
            for i,c in enumerate(nb['cells']):
                if c['cell_type'] != 'code': continue
                o, skip = [], False
                for l in ''.join(c['source']).split('\n'):
                    if skip: o.append(''); skip = l.rstrip().endswith('\\'); continue
                    m = re.match(r'^(\s*)[!%]', l)
                    if m: o.append(m.group(1)+'pass'); skip = l.rstrip().endswith('\\')
                    else: o.append(l)
                try: ast.parse('\n'.join(o))
                except SyntaxError as e: print(f'!! {out} cell {i}: {e}'); bad += 1
            print(f'{os.path.basename(out):26s} {n} cells  syntax problems: {bad}')
