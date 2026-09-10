"""Two measurements that make the sky-masked run comparable with the run before it.

`metrics.py` in 3DGS scores every pixel, so a model trained not to render the sky
must lose on it: the sky is ~28% of these photographs and the model puts nothing
there. Neither number below is that one.

  subject   scores held-out renders on the subject pixels only, using the same
            SegFormer masks the training used. Run it on each model's renders and
            the two are directly comparable, pixel for pixel.

  occupancy answers the question the score cannot: how much of the model actually
            sits in the sky. Every gaussian is projected into the held-out cameras
            and checked against those cameras' sky masks. A gaussian counts as sky
            geometry when it lands on sky in at least `--thresh` of the views that
            see it at all.

Both take the masks and cameras from the sky-masked run's Kaggle output, so a model
trained without masks is judged by exactly the same regions.

  python tools/sky_audit.py subject   --renders DIR --masks DIR --names results_subject.json
  python tools/sky_audit.py occupancy --splat  A.splat B.splat --cameras cameras_final.json \
                                      --masks DIR --names results_subject.json
"""
import argparse, glob, json, os, sys
import numpy as np
import cv2

ROW = 32


def load_splat(path):
    raw = np.fromfile(path, dtype=np.uint8).reshape(-1, ROW)
    xyz = raw[:, 0:12].copy().view(np.float32).reshape(-1, 3).astype(np.float64)
    scale = raw[:, 12:24].copy().view(np.float32).reshape(-1, 3).astype(np.float64)
    opacity = raw[:, 27].astype(np.float64) / 255.0
    return xyz, scale, opacity


def splat_from_js(path):
    """the viewer files embed the same 32-byte rows as base64"""
    import base64, re
    s = open(path).read()
    b64 = re.search(r'window\.SPLAT_DATA_B64 = "([^"]+)"', s).group(1)
    return np.frombuffer(base64.b64decode(b64), dtype=np.uint8).reshape(-1, ROW)


def test_names(names_arg, masks_dir):
    """the held-out names, in 3DGS's own order: sorted, every 8th"""
    if names_arg and names_arg.endswith('.json'):
        return [r['name'] for r in json.load(open(names_arg))['per_view']]
    return sorted(os.path.basename(p).replace('.png', '.jpg') for p in glob.glob(f'{masks_dir}/*.png'))


def read_mask(masks_dir, name, shape):
    m = cv2.imread(f'{masks_dir}/{os.path.splitext(name)[0]}.png', 0)
    if m is None:
        raise SystemExit(f'no mask for {name} in {masks_dir}')
    keep = m > 127                                    # 255 = subject, 0 = sky
    if shape is not None and keep.shape != shape:
        keep = cv2.resize(keep.astype(np.uint8), (shape[1], shape[0]),
                          interpolation=cv2.INTER_NEAREST) > 0
    return keep


def cmd_subject(a):
    names = test_names(a.names, a.masks)
    rend = sorted(glob.glob(f'{a.renders}/renders/*.png')) or sorted(glob.glob(f'{a.renders}/*.png'))
    gt_dir = f'{a.renders}/gt' if os.path.isdir(f'{a.renders}/gt') else a.gt
    if len(rend) != len(names):
        raise SystemExit(f'{len(rend)} renders but {len(names)} held-out names')
    rows = []
    for i, nm in enumerate(names):
        r = cv2.imread(rend[i]).astype(np.float64)
        g = cv2.imread(f'{gt_dir}/{os.path.basename(rend[i])}').astype(np.float64)
        keep = read_mask(a.masks, nm, r.shape[:2])
        se = (r - g) ** 2
        rows.append(dict(name=nm,
                         psnr_full=10 * np.log10(255 ** 2 / se.mean()),
                         psnr_subject=10 * np.log10(255 ** 2 / se[keep].mean()),
                         psnr_sky=(10 * np.log10(255 ** 2 / se[~keep].mean())) if (~keep).any() else None,
                         sky_frac=float(1 - keep.mean())))
    subj = np.array([r['psnr_subject'] for r in rows])
    full = np.array([r['psnr_full'] for r in rows])
    sky = np.array([r['psnr_sky'] for r in rows if r['psnr_sky'] is not None])
    out = dict(n_test=len(rows),
               psnr_subject=float(subj.mean()), psnr_subject_min=float(subj.min()),
               psnr_subject_median=float(np.median(subj)),
               psnr_full=float(full.mean()),
               psnr_sky=float(sky.mean()) if len(sky) else None,
               mean_sky_frac=float(np.mean([r['sky_frac'] for r in rows])),
               per_view=[{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()} for r in rows])
    print(f'subject {out["psnr_subject"]:.2f} dB   full frame {out["psnr_full"]:.2f} dB   '
          f'sky pixels {out["psnr_sky"]:.2f} dB   sky is {out["mean_sky_frac"]*100:.0f}% of a frame')
    return out


def cmd_occupancy(a):
    names = test_names(a.names, a.masks)
    cams = {c['img_name']: c for c in json.load(open(a.cameras))}
    use = []
    for n in names:
        c = cams.get(n) or cams.get(os.path.splitext(n)[0])
        if c is None:
            continue
        use.append((c, read_mask(a.masks, n, (c['height'], c['width']))))
    if not use:
        raise SystemExit('no camera matched a mask - check --cameras and --masks')
    out = {}
    for path in a.splat:
        raw = splat_from_js(path) if path.endswith('.js') else None
        if raw is None:
            xyz, scale, opacity = load_splat(path)
        else:
            xyz = raw[:, 0:12].copy().view(np.float32).reshape(-1, 3).astype(np.float64)
            scale = raw[:, 12:24].copy().view(np.float32).reshape(-1, 3).astype(np.float64)
            opacity = raw[:, 27].astype(np.float64) / 255.0
        weight = (4 / 3) * np.pi * np.prod(scale, axis=1) * opacity   # how visible a floater is
        seen = np.zeros(len(xyz))
        in_sky = np.zeros(len(xyz))
        per_cam = []
        for c, keep in use:
            R = np.array(c['rotation'])                    # camera -> world
            q = (xyz - np.array(c['position'])) @ R        # world -> camera, looking along +z
            z = q[:, 2]
            ok = z > 0.05
            u = c['fx'] * q[:, 0] / np.where(ok, z, 1) + c['width'] / 2
            v = c['fy'] * q[:, 1] / np.where(ok, z, 1) + c['height'] / 2
            ok &= (u >= 0) & (u < c['width']) & (v >= 0) & (v < c['height'])
            s = np.zeros(len(xyz), bool)
            s[ok] = ~keep[v[ok].astype(int), u[ok].astype(int)]
            seen += ok
            in_sky += s
            per_cam.append((s.sum() / ok.sum(), weight[s].sum() / weight[ok].sum()))
        pc = np.array(per_cam)
        good = seen >= a.min_views
        frac = np.where(good, in_sky / np.maximum(seen, 1), 0)
        rec = dict(gaussians=int(len(xyz)),
                   judged=int(good.sum()),
                   sky_at_50=int((good & (frac >= 0.5)).sum()),
                   sky_at_30=int((good & (frac >= 0.3)).sum()),
                   share_per_camera=float(pc[:, 0].mean()),
                   share_per_camera_weighted=float(pc[:, 1].mean()),
                   cameras=len(use))
        out[os.path.basename(path)] = rec
        print(f'{os.path.basename(path):24s} in sky in >=50% of views: {rec["sky_at_50"]:6,}   '
              f'>=30%: {rec["sky_at_30"]:6,}   visible share in sky {rec["share_per_camera_weighted"]*100:.2f}%')
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('subject', help='PSNR on the subject pixels of held-out renders')
    s.add_argument('--renders', required=True, help='a 3DGS test/ours_N directory, or a directory of renders')
    s.add_argument('--gt', help='ground-truth directory, if not <renders>/gt')
    s.add_argument('--masks', required=True)
    s.add_argument('--names', help='results_subject.json, to fix the held-out order')
    s.add_argument('-o', '--out')

    o = sub.add_parser('occupancy', help='how much of a model sits in the sky')
    o.add_argument('--splat', nargs='+', required=True, help='.splat files, or the viewer .js that embeds one')
    o.add_argument('--cameras', required=True, help='cameras_final.json, same frame as the splat')
    o.add_argument('--masks', required=True)
    o.add_argument('--names')
    o.add_argument('--thresh', type=float, default=0.5)
    o.add_argument('--min-views', type=int, default=3)
    o.add_argument('-o', '--out')

    a = p.parse_args(argv)
    res = cmd_subject(a) if a.cmd == 'subject' else cmd_occupancy(a)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        json.dump(res, open(a.out, 'w'), indent=1)
        print('wrote', a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
