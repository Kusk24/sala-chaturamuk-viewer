# Figures for the Version 6 (final) update, all derived from files on disk.
# Renders use the CPU rasteriser in splat_render.py with explicit view matrices, never
# the viewer's orbit rig (which re-centres each model on load, so two models given the
# same matrix are NOT seen from the same camera).
#   python tools/make_figs_v6.py <tmpdir-with-held/ours_30000>
import json, re, base64, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageEnhance
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.lines import Line2D

ROOT = "/Users/kusk/Desktop/Computer Vision/Term-Project"
VW   = f"{ROOT}/sala-chaturamuk-viewer/viewer"
OUT  = f"{ROOT}/sala-chaturamuk-viewer/paper/figs_v6"
KO   = f"{ROOT}/kaggle_out/salamodel/out_salamodel"
TMP  = sys.argv[1]
sys.path.insert(0, f"{ROOT}/sala-chaturamuk-viewer/tools")
import splat_render as sr

FB = lambda s: ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", s)
U  = np.array([0, -1.0, 0])

def js_splat(js, out):
    b = re.search(r'window\.SPLAT_DATA_B64\s*=\s*"([^"]*)"', open(js).read()).group(1)
    open(out, "wb").write(base64.b64decode(b)); return out
def js_view(js):
    return [float(x) for x in re.search(r'window\.SPLAT_VIEW_MATRIX\s*=\s*\[([^\]]*)\]', open(js).read()).group(1).split(",")]
def band(im, text, size, h=None):
    h = h or int(size * 1.5)
    out = Image.new("RGB", (im.width, im.height + h), (255, 255, 255))
    ImageDraw.Draw(out).text((6, (h - size) // 2 - 1), text, font=FB(size), fill=(0, 0, 0))
    out.paste(im, (0, h)); return out
def vstack(ims, gap=12):
    W = max(i.width for i in ims); s = Image.new("RGB", (W, sum(i.height for i in ims) + gap * (len(ims) - 1)), "white"); y = 0
    for i in ims: s.paste(i, ((W - i.width) // 2, y)); y += i.height + gap
    return s
def hstack(ims, gap=12):
    H = max(i.height for i in ims); s = Image.new("RGB", (sum(i.width for i in ims) + gap * (len(ims) - 1), H), "white"); x = 0
    for i in ims: s.paste(i, (x, (H - i.height) // 2)); x += i.width + gap
    return s
def content_box(arrs, thr=30, pad=0.06):
    m = np.zeros(arrs[0].shape[:2], bool)
    for a in arrs: m |= a.sum(2) > thr
    ys, xs = np.where(m); H, W = m.shape
    py, px = int((ys.max() - ys.min()) * pad), int((xs.max() - xs.min()) * pad)
    return max(xs.min() - px, 0), max(ys.min() - py, 0), min(xs.max() + px, W), min(ys.max() + py, H)
def splat_geom(path):
    raw = np.fromfile(path, dtype=np.uint8).reshape(-1, 32)
    xyz = raw[:, 0:12].copy().view(np.float32).reshape(-1, 3).astype(float)
    scl = raw[:, 12:24].copy().view(np.float32).reshape(-1, 3).astype(float); a = raw[:, 27] / 255.0
    solid = (a > 0.6) & (scl.max(1) < np.percentile(scl.max(1), 60))
    return xyz, solid
LABEL = 40     # bold px; every figure below is sized so this prints at >= 7 pt

pav_v6 = js_splat(f"{VW}/splat_sala.js", f"{TMP}/pavilion_v6.splat")
mod_cl = js_splat(f"{VW}/splat_salamodel.js", f"{TMP}/salamodel_clean.splat")

# ---- (1) photographs ---------------------------------------------------------------
pav = Image.open(f"{ROOT}/CV_Photos_prepared/sala/0176.jpg").convert("RGB")   # uncropped: the whole
# pavilion with every roof finial is in this frame, which a crop risks losing
m1 = Image.open(f"{ROOT}/CV_Photos_prepared/salamodel/0000.jpg").convert("RGB")
m2 = Image.open(f"{ROOT}/CV_Photos_prepared/salamodel/0290.jpg").convert("RGB")
gain = np.asarray(m1).mean() / np.asarray(m2).mean()
m2 = ImageEnhance.Brightness(m2).enhance(min(gain, 1.6))                             # match the pair
pav.thumbnail((1000, 1000)); half = (pav.width - 12) // 2
m1.thumbnail((half, 2000)); m2.thumbnail((half, 2000))
fig = vstack([band(pav, "(a) Full-size pavilion", LABEL), band(hstack([m1, m2]), "(b) Sala model", LABEL)])
fig.save(f"{OUT}/fig_v6_photos.jpg", quality=92)
print("photos", fig.size, "model pair brightness gain %.2f" % gain)

# ---- (2) coverage -------------------------------------------------------------------
def elev_v5(splat, cams):
    xyz, _ = splat_geom(splat); c = json.load(open(cams))
    C = np.array([k["position"] for k in c]); R = np.array([k["rotation"] for k in c])
    up = -R[:, :, 1].mean(0); up /= np.linalg.norm(up)
    d = C - np.median(xyz, axis=0); h = d @ up
    return np.degrees(np.arctan2(h, np.linalg.norm(d - np.outer(h, up), axis=1)))
def slice_top(splat, cams):
    xyz, solid = splat_geom(splat); ctr = np.median(xyz[solid], axis=0)
    S = xyz[solid] - ctr; sh = S @ U; shz = np.linalg.norm(S - np.outer(sh, U), axis=1)
    top, bot, r90 = np.percentile(sh, 99), np.percentile(sh, 1), np.percentile(shz, 90)
    C = np.array([k["position"] for k in json.load(open(cams))]) - ctr
    h = C @ U; hz = np.linalg.norm(C - np.outer(h, U), axis=1); ring = np.median(hz)
    return hz / ring, (h - top) / ring, r90 / ring, (bot - top) / ring, int((h > top).sum())
el_p = elev_v5(f"{ROOT}/kaggle_out/sala/out_sala/sala_cropped.splat", f"{ROOT}/kaggle_out/sala/out_sala/cameras.json")
el_m = elev_v5(mod_cl, f"{KO}/cameras_final.json")
sp = slice_top(pav_v6, f"{ROOT}/kaggle_out/v6/sala/cameras_final.json")
sm = slice_top(mod_cl, f"{KO}/cameras_final.json")
print("elev max: pavilion %.1f (above 0: %d), model %.1f (above 0: %d); above top: %d vs %d"
      % (el_p.max(), (el_p > 0).sum(), el_m.max(), (el_m > 0).sum(), sp[4], sm[4]))

BR, BL = "#8a5a1f", "#2468a8"
plt.rcParams.update({"font.family": "Arial", "font.size": 8})
f, (ax1, ax2) = plt.subplots(2, 1, figsize=(3.4, 5.0), dpi=300, gridspec_kw={"height_ratios": [1, 1.15]})
bins = np.arange(-40, 80, 10)
ax1.hist(el_p, bins=bins, color=BR, alpha=.9, label=f"Full-size pavilion ({len(el_p)})")
ax1.hist(el_m, bins=bins, color=BL, alpha=.6, label=f"Sala model ({len(el_m)})")
ax1.axvline(0, color="k", lw=.7, ls="--")
ax1.set_xlabel("Camera elevation about the model centre (°)"); ax1.set_ylabel("Photographs")
ax1.set_title("(a)", loc="left", fontweight="bold")
ax1.legend(frameon=True, framealpha=1, edgecolor="#bbb", fontsize=7, loc="upper right")
ax2.axhline(0, color="k", lw=.8)
ax2.add_patch(Rectangle((0, sp[3]), sp[2], -sp[3], fc=BR, alpha=.18, ec=BR, lw=1))
ax2.add_patch(Rectangle((0, sm[3]), sm[2], -sm[3], fc=BL, alpha=.18, ec=BL, lw=1, ls="--"))
ax2.scatter(sp[0], sp[1], s=5, color=BR, alpha=.8, lw=0)
ax2.scatter(sm[0], sm[1], s=5, color=BL, alpha=.8, lw=0)
ax2.set_xlim(0, 1.45); ax2.set_ylim(-0.95, 0.85)
ax2.set_xlabel("Horizontal distance from centre (camera-ring radii)")
ax2.set_ylabel("Height above top of subject (ring radii)")
ax2.set_title("(b)", loc="left", fontweight="bold")
ax2.text(1.43, 0.03, "top of subject", ha="right", va="bottom", fontsize=7)
handles = [Line2D([], [], marker="o", ls="", color=BR, ms=4, label="Pavilion cameras"),
           Line2D([], [], marker="o", ls="", color=BL, ms=4, label="Model cameras"),
           Rectangle((0, 0), 1, 1, fc=BR, alpha=.18, ec=BR, label="Pavilion surface"),
           Rectangle((0, 0), 1, 1, fc=BL, alpha=.18, ec=BL, ls="--", label="Model surface")]
ax2.legend(handles=handles, frameon=True, framealpha=1, edgecolor="#bbb", fontsize=6.5, ncol=2,
           loc="upper center", bbox_to_anchor=(0.5, -0.2))
f.tight_layout(); f.savefig(f"{OUT}/fig_v6_coverage.png", dpi=300, bbox_inches="tight"); plt.close(f)

# ---- (3) both subjects from directly above ------------------------------------------
def top_down(splat, lift):
    xyz, solid = splat_geom(splat); ctr = np.median(xyz[solid], axis=0)
    return sr.render(splat, sr.look_at(ctr + U * lift, ctr, up=(0, 0, 1)), W=1000, H=1000)
ta, tb = top_down(pav_v6, 9.0), top_down(mod_cl, 2.4)
crops = []
for arr in (ta, tb):
    x0, y0, x1, y1 = content_box([arr], thr=60, pad=0.04)
    im = Image.fromarray(arr).crop((x0, y0, x1, y1)); im.thumbnail((700, 700)); crops.append(im)
fig = hstack([band(crops[0], "(a) Full-size pavilion", 60), band(crops[1], "(b) Sala model", 60)], 16)
fig.save(f"{OUT}/fig_v6_from_above.jpg", quality=92); print("from above", fig.size)

# ---- (4) true 0/90/180/270 azimuth views of the cleaned model ------------------------
xyz, solid = splat_geom(mod_cl); ctr = np.median(xyz[solid], axis=0)
e1 = np.cross(U, [0, 0, 1.0]); e1 /= np.linalg.norm(e1); e2 = np.cross(U, e1)
el = np.radians(20)
arrs = []
for az in (0, 90, 180, 270):
    a = np.radians(az)
    eye = ctr + 2.6 * (np.cos(el) * (np.cos(a) * e1 + np.sin(a) * e2) + np.sin(el) * U)
    arrs.append(sr.render(mod_cl, sr.look_at(eye, ctr, up=tuple(U)), W=800, H=800))
x0, y0, x1, y1 = content_box(arrs, thr=40, pad=0.05)
tiles = [band(Image.fromarray(a).crop((x0, y0, x1, y1)).resize((480, int(480 * (y1 - y0) / (x1 - x0)))), f"{az}°", LABEL)
         for a, az in zip(arrs, (0, 90, 180, 270))]
grid = vstack([hstack(tiles[:2], 8), hstack(tiles[2:], 8)], 8)
grid.save(f"{OUT}/fig_v6_turntable_2x2.jpg", quality=92); print("turntable", grid.size)

# ---- (5) trained vs cleaned from ONE explicit camera --------------------------------
view = js_view(f"{KO}/splat_salamodel.js")            # the notebook's own opening view
ra = sr.render(f"{KO}/salamodel_final.splat", view, W=900, H=900)
rb = sr.render(mod_cl, view, W=900, H=900)
lit = lambda a: float((a.sum(2) > 30).mean() * 100)
print("same camera: lit %.1f%% trained vs %.1f%% cleaned" % (lit(ra), lit(rb)))
json.dump({"lit_trained_pct": round(lit(ra), 1), "lit_cleaned_pct": round(lit(rb), 1),
           "threshold": "sum of RGB > 30", "view": "notebook opening view of splat_salamodel.js",
           "renderer": "tools/splat_render.py, 900x900"}, open(f"{OUT}/fig_v6_model_clean.json", "w"), indent=1)
x0, y0, x1, y1 = content_box([ra], thr=30, pad=0.02)
pa = Image.fromarray(ra).crop((x0, y0, x1, y1)); pb = Image.fromarray(rb).crop((x0, y0, x1, y1))
pa.thumbnail((620, 620)); pb.thumbnail((620, 620))
fig = hstack([band(pa, "(a) As trained", LABEL), band(pb, "(b) Cleaned", LABEL)], 12)
fig.save(f"{OUT}/fig_v6_model_clean.jpg", quality=92); print("clean", fig.size)

# ---- (6) held-out photographs against renders --------------------------------------
H = f"{TMP}/held/ours_30000"
pv = json.load(open(f"{KO}/per_view.json"))["ours_30000"]["PSNR"]
cols = []
for n in ("00007.png", "00034.png", "00026.png"):
    g = Image.open(f"{H}/gt/{n}").convert("RGB"); r = Image.open(f"{H}/renders/{n}").convert("RGB")
    g.thumbnail((380, 520)); r.thumbnail((380, 520))
    cols.append(vstack([band(g, "Photo", 40), band(r, f"{pv[n]:.2f} dB", 40)], 6))
fig = hstack(cols, 10); fig.save(f"{OUT}/fig_v6_model_heldout.jpg", quality=92); print("heldout", fig.size)
