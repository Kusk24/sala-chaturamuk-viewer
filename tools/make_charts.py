import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, numpy as np

OUT='/Users/kusk/Desktop/Computer Vision/Term-Project/sala-chaturamuk-viewer/paper/figs_v5b'
SALA, LAMP = '#2a78d6', '#eb6834'          # categorical slots 1 and 2, fixed order
INK, MUTED, GRID = '#0b0b0b', '#52514e', '#d8d7d2'
plt.rcParams.update({'font.size':7,'font.family':'DejaVu Sans','axes.edgecolor':MUTED,
                     'axes.labelcolor':INK,'text.color':INK,'xtick.color':MUTED,'ytick.color':MUTED,
                     'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':300})

def finish(ax, xlabel=None):
    ax.grid(axis='x', color=GRID, lw=.6); ax.set_axisbelow(True)
    if xlabel: ax.set_xlabel(xlabel, color=MUTED)

# --- 1. where the score is lost -------------------------------------------
regions=['Whole frame','Excluding\nmasked sky','Central region\n(the subject)']
sala=[20.10,22.33,20.89]; lamp=[15.93,18.14,20.25]
fig,ax=plt.subplots(figsize=(3.3,2.15))
y=np.arange(len(regions)); h=0.36
ax.barh(y+h/2+0.01, sala, h, color=SALA, label='Sala')
ax.barh(y-h/2-0.01, lamp, h, color=LAMP, label='Lamp')
for yy,v in zip(y+h/2+0.01,sala): ax.text(v+0.25,yy,f'{v:.2f}',va='center',fontsize=6.5,color=INK)
for yy,v in zip(y-h/2-0.01,lamp): ax.text(v+0.25,yy,f'{v:.2f}',va='center',fontsize=6.5,color=INK)
ax.set_yticks(y); ax.set_yticklabels(regions); ax.set_xlim(0,30)
finish(ax,'PSNR (dB), same renders')
ax.legend(frameon=False, loc='lower right', fontsize=6.5)
fig.tight_layout(pad=0.4); fig.savefig(f'{OUT}/fig_psnr_regions.png'); plt.close(fig)

# --- 2. loss curves + fitted extrapolation --------------------------------
t=np.array([2500,7500,12500,17500,22500,27500])
sl=np.array([0.0911,0.0538,0.0438,0.0362,0.0335,0.0319])   # lamp
ss=np.array([0.0919,0.0663,0.0564,0.0477,0.0447,0.0429])   # sala
fit={'sala':(0.0396,1821936.316,-1.965),'lamp':(0.0278,45707.526,-1.585)}
x=np.linspace(30000,60000,60)
fig,ax=plt.subplots(figsize=(3.3,2.15))
ax.plot(t,ss,color=SALA,lw=1.6,marker='o',ms=3,label='Sala')
ax.plot(t,sl,color=LAMP,lw=1.6,marker='o',ms=3,label='Lamp')
for k,col in (('sala',SALA),('lamp',LAMP)):
    c,A,b=fit[k]; ax.plot(x,c+A*x**b,color=col,lw=1.1,ls=(0,(3,2)))
    ax.axhline(c,color=col,lw=.7,ls=':',alpha=.65)
ax.annotate('fitted ceiling',xy=(52000,fit['sala'][0]),xytext=(37000,0.055),fontsize=6,color=MUTED,
            arrowprops=dict(arrowstyle='-',color=MUTED,lw=.6))
ax.text(45000,0.0345,'extrapolated',fontsize=6,color=MUTED,style='italic')
ax.set_xlim(0,60000); ax.set_ylim(0.025,0.098)
ax.set_xticks([0,15000,30000,45000,60000]); ax.set_xticklabels(['0','15k','30k','45k','60k'])
ax.grid(color=GRID,lw=.6); ax.set_axisbelow(True)
ax.set_xlabel('training iterations',color=MUTED); ax.set_ylabel('L1 loss (mean per 5k)',color=MUTED)
ax.axvline(30000,color=MUTED,lw=.7,ls='-',alpha=.5)
ax.text(30400,0.093,'run ended',fontsize=6,color=MUTED)
ax.legend(frameon=False,loc='upper right',fontsize=6.5)
fig.tight_layout(pad=0.4); fig.savefig(f'{OUT}/fig_loss.png'); plt.close(fig)

# --- 3. camera elevation coverage -----------------------------------------
bins=['-90 to -30','-30 to 0','0 to +30','+30 to +60','+60 to +90']
s=[21,374,0,0,0]; l=[15,27,37,21,0]
fig,ax=plt.subplots(figsize=(3.3,2.15))
y=np.arange(len(bins)); h=0.36
ax.barh(y+h/2+0.01,s,h,color=SALA,label='Sala (446 photos)')
ax.barh(y-h/2-0.01,l,h,color=LAMP,label='Lamp (100 photos)')
for yy,v in zip(y+h/2+0.01,s): ax.text(v+6 if v else 6,yy,str(v),va='center',fontsize=6.5,color=INK if v else MUTED)
for yy,v in zip(y-h/2-0.01,l): ax.text(v+6 if v else 6,yy,str(v),va='center',fontsize=6.5,color=INK if v else MUTED)
ax.set_yticks(y); ax.set_yticklabels(bins); ax.set_xlim(0,430)
finish(ax,'photographs')
ax.set_ylabel('camera elevation (deg)',color=MUTED,fontsize=6.5)
ax.legend(frameon=False,loc='lower right',fontsize=6.5)
fig.tight_layout(pad=0.4); fig.savefig(f'{OUT}/fig_elevation.png'); plt.close(fig)
print('charts written')
