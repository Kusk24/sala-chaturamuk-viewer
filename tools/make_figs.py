import sys, json, os, glob, numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import splat_render as sr

K   = '/Users/kusk/Desktop/Computer Vision/Term-Project/kaggle_out'
OUT = '/Users/kusk/Desktop/Computer Vision/Term-Project/sala-chaturamuk-viewer/paper/figs_v5b'

def vm_from_cam(c):
    R = np.array(c['rotation']).reshape(9); t = c['position']
    return [R[0],R[1],R[2],0, R[3],R[4],R[5],0, R[6],R[7],R[8],0,
            -t[0]*R[0]-t[1]*R[3]-t[2]*R[6],
            -t[0]*R[1]-t[1]*R[4]-t[2]*R[7],
            -t[0]*R[2]-t[1]*R[5]-t[2]*R[8], 1]

def cams(sub):  return json.load(open(f'{K}/{sub}/out_{sub}/cameras.json'))
def splat(sub): return f'{K}/{sub}/out_{sub}/{sub}_cropped.splat'

def world_up(cs):
    R = np.array([c['rotation'] for c in cs]); u = -R[:,:,1].mean(0)
    return u/np.linalg.norm(u)

def centre(sub):
    raw = np.fromfile(splat(sub), dtype=np.uint8).reshape(-1,32)
    return np.median(raw[:,0:12].copy().view(np.float32).reshape(-1,3), axis=0)

def label(img, text, h=34):
    bar = np.full((h, img.shape[1], 3), 26, np.uint8)
    cv2.putText(bar, text, (12, h-11), cv2.FONT_HERSHEY_DUPLEX, 0.62, (240,240,240), 1, cv2.LINE_AA)
    return np.vstack([bar, img])

# ---- F1/F2: a photographed viewpoint beside one no camera ever occupied ----
for sub, obs_name, W, H in (('sala','0012.jpg',1100,820), ('lamp','0002.jpg',1000,900)):
    cs = cams(sub); up = world_up(cs); C = centre(sub)
    obs = next(c for c in cs if c['img_name'] == obs_name)
    a = sr.render(splat(sub), vm_from_cam(obs), W=W, H=H)
    d = np.linalg.norm(np.array(obs['position']) - C)
    side = np.cross(up, [1.0,0,0]); side /= np.linalg.norm(side)
    eye = C + up*(d*0.95) + side*(d*0.45)              # above, looking down
    b = sr.render(splat(sub), sr.look_at(eye, C, up=up), W=W, H=H)
    sheet = np.vstack([label(a[:,:,::-1], f'A  from photograph {obs_name} - a viewpoint the capture occupied'),
                       label(b[:,:,::-1], 'B  from above - no camera ever occupied this direction')])
    cv2.imwrite(f'{OUT}/fig_{sub}_observed_vs_not.png', sheet)
    print('wrote', f'fig_{sub}_observed_vs_not.png', sheet.shape)

# ---- F3/F4: held-out ground truth beside the model's own render ----
def heldout(sub, picks, tag):
    base = (f'{K}/{sub}/out_{sub}/model/test/ours_30000' if sub == 'sala' else '/tmp/hr/ours_30000')
    rows = []
    for n, ps in picks:
        g = cv2.imread(f'{base}/gt/{n}.png'); r = cv2.imread(f'{base}/renders/{n}.png')
        if g is None or r is None: continue
        h = 420; s = h/g.shape[0]
        g = cv2.resize(g,(int(g.shape[1]*s),h)); r = cv2.resize(r,(int(r.shape[1]*s),h))
        pair = np.hstack([g, np.full((h,5,3),26,np.uint8), r])
        rows.append(label(pair, f'{n}   PSNR {ps} dB      left: photograph      right: model', 30))
    w = max(x.shape[1] for x in rows)
    rows = [np.hstack([x, np.full((x.shape[0], w-x.shape[1], 3), 26, np.uint8)]) for x in rows]
    sheet = np.vstack(rows)
    cv2.imwrite(f'{OUT}/{tag}', sheet); print('wrote', tag, sheet.shape)

heldout('sala', [('00028','10.45'),('00008','25.24'),('00016','21.40')], 'fig_heldout_sala.png')
heldout('lamp', [('00007','10.07'),('00002','22.34'),('00000','18.93')], 'fig_heldout_lamp.png')

# ---- F8: the sky mask is not consistent between views ----
rows = []
for n, note in (('00009','sky left unmasked'), ('00007','sky left unmasked'), ('00012','same sky, masked black')):
    g = cv2.imread(f'/tmp/hr/ours_30000/gt/{n}.png')
    if g is None: continue
    h = 400; s = h/g.shape[0]; g = cv2.resize(g,(int(g.shape[1]*s),h))
    rows.append(label(g, f'{n}  -  {note}', 30))
w = max(x.shape[1] for x in rows)
rows = [np.hstack([x, np.full((x.shape[0], w-x.shape[1],3),26,np.uint8)]) for x in rows]
cv2.imwrite(f'{OUT}/fig_skymask.png', np.hstack(rows)); print('wrote fig_skymask.png')
