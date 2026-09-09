import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT='/Users/kusk/Desktop/Computer Vision/Term-Project/sala-chaturamuk-viewer/paper/figs_v5b/fig_pipeline.png'
INK,MUTED='#0b0b0b','#52514e'
SHARED,IBR,REC='#e8e8e4','#dbe8f8','#d8f0e6'
EDGE_S,EDGE_I,EDGE_R='#9a9a94','#2a78d6','#1baf7a'
plt.rcParams.update({'font.family':'DejaVu Sans'})

fig,ax=plt.subplots(figsize=(7.0,9.2)); ax.set_xlim(0,100); ax.set_ylim(-16,120); ax.axis('off')

def box(x,y,w,h,text,fc,ec,fs=7.2,bold=False,align='center'):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.6,rounding_size=1.2',
                 fc=fc,ec=ec,lw=0.9))
    ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=fs,color=INK,
            fontweight='bold' if bold else 'normal',linespacing=1.35)

def arrow(x1,y1,x2,y2,color=EDGE_S,style='-|>'):
    ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle=style,mutation_scale=9,
                 color=color,lw=0.9,shrinkA=1,shrinkB=1))

# ---- shared input -------------------------------------------------------
box(20,112,60,6,'Photographs of Sala Chaturamuk Phaichit',SHARED,EDGE_S,bold=True)
arrow(50,112,50,108.5)
box(14,101,72,7,'the two arms are fed by DIFFERENT captures and hold out at\nDIFFERENT densities — their scores are not directly comparable',
    SHARED,EDGE_S,fs=6.6)
arrow(50,101,26,93); arrow(50,101,74,93)

box(3,86,44,7,'Aug closed-loop capture, 146 frames\nevery 2nd withheld -> 73 kept, 144 scored',IBR,EDGE_I,fs=6.6)
box(53,86,44,7,'5 Sep capture, sala 446 / lamp 100\nevery 8th withheld -> 50 and 13 scored',REC,EDGE_R,fs=6.6)
arrow(25,86,25,81.5,EDGE_I); arrow(75,86,75,81.5,EDGE_R)

# ---- headers ------------------------------------------------------------
box(3,74.5,44,6,'ARM A — Image-based rendering\nthe project’s contribution',IBR,EDGE_I,bold=True,fs=7.4)
box(53,74.5,44,6,'ARM B — Reconstruction\nthe comparison, kept separate',REC,EDGE_R,bold=True,fs=7.4)

ibr=['extract_frames.py — decode the walk','subsample → capture set + held-out',
     'match_features.py — SIFT, adjacent\npairs only, RANSAC filtered',
     'interpolate.py — Farneback flow,\nbackward warp + cross-dissolve',
     'build_sequence.py — order by angle','evaluate.py — PSNR / SSIM']
rec=['stage images, install COLMAP','feature extraction  (cached)',
     'sequential matching, loop detection OFF','mapper → sparse/   (cached)',
     'fold check — reported, not fatal','undistort → PINHOLE, laid out as sparse/0/',
     'sky mask','3DGS train, 30k iters — resumable,\nOOM self-healing',
     'render held-out views','metrics.py — PSNR / SSIM / LPIPS',
     'crop to the subject','export .splat']

y=71
for i,t in enumerate(ibr):
    h=5.2 if '\n' in t else 4.2
    y-=h+1.4; box(3,y,44,h,t,IBR,EDGE_I)
    if i<len(ibr)-1: arrow(25,y,25,y-1.4,EDGE_I)
y_ibr=y

y=71
for i,t in enumerate(rec):
    h=5.2 if '\n' in t else 4.2
    y-=h+1.0; box(53,y,44,h,t,REC,EDGE_R)
    if i<len(rec)-1: arrow(75,y,75,y-1.0,EDGE_R)
y_rec=y

arrow(25,y_ibr,25,y_ibr-2.2,EDGE_I); arrow(75,y_rec,75,y_rec-2.2,EDGE_R)
box(3,y_ibr-8.4,44,6,'viewer/index.html\ndrag-to-rotate, no 3D model',IBR,EDGE_I,bold=True)
box(53,y_rec-8.4,44,6,'viewer/sala.html · lamp.html\n291,764 and 163,756 Gaussians',REC,EDGE_R,bold=True)

ax.text(50,-13,'Arm B never feeds Arm A. The contribution stays geometry-free; the reconstruction is reported\n'
               'alongside it — same subject, same kind of hold-out evaluation, but not the same protocol.',
        ha='center',va='center',fontsize=6.6,color=MUTED,style='italic',linespacing=1.5)

fig.savefig(OUT,dpi=300,bbox_inches='tight',facecolor='white')
print('wrote',OUT)
