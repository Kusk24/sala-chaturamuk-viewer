# Build paper Version 6 as the FULL paper with this round's progress added in place:
# open Version 5 and APPEND, never strip. (A version is a submission round, not a
# results-only companion - see version5_results.md and the versioning convention.)
# Numbers come from version6_results.md, which in turn cites its sources per claim.
import re, os
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

P    = '/Users/kusk/Desktop/Computer Vision/Term-Project/sala-chaturamuk-viewer/paper'
FIGS = f'{P}/figs_v6'
SRC  = f'{P}/CSX4213_Sala_Thai_Version5.docx'
DST  = f'{P}/CSX4213_Sala_Thai_Version6.docx'

doc = Document(SRC)
have = {s.name for s in doc.styles}
def st(name, fallback='Normal'):
    return name if name in have else fallback
S_BODY = st('Body Text'); S_BULLET = st('bullet list', S_BODY)
S_TABHEAD = st('table head', S_BODY); S_FIGCAP = st('figure caption', S_BODY)

FIGN = [0]; TABN = [0]

def _runs(par, text):
    for i, chunk in enumerate(re.split(r'\*\*(.+?)\*\*', text)):
        if not chunk: continue
        r = par.add_run(chunk)
        if i % 2: r.bold = True

def para(text, style=None, size=None, italic=False):
    p = doc.add_paragraph(style=style or S_BODY)
    _runs(p, text)
    if size or italic:
        for r in p.runs:
            if size: r.font.size = Pt(size)
            if italic: r.italic = True
    return p

def head(text, level=1):
    return doc.add_paragraph(text, style=st(f'Heading {level}', S_BODY))

def bullets(items):
    for it in items:
        _runs(doc.add_paragraph(style=S_BULLET), it)

def _shade(cell, hexcolor):
    el = OxmlElement('w:shd'); el.set(qn('w:val'), 'clear'); el.set(qn('w:fill'), hexcolor)
    cell._tc.get_or_add_tcPr().append(el)

def table(rows, caption=None, widths=None, size=8.5):
    TABN[0] += 1
    if caption:
        c = doc.add_paragraph(style=S_TABHEAD)
        _runs(c, f'TABLE V6-{TABN[0]}.  {caption}')
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = 'Normal Table'; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    borders = OxmlElement('w:tblBorders')
    for edge in ('top','left','bottom','right','insideH','insideV'):
        e = OxmlElement(f'w:{edge}')
        e.set(qn('w:val'),'single'); e.set(qn('w:sz'),'4'); e.set(qn('w:color'),'A6A6A6')
        borders.append(e)
    t._tbl.tblPr.append(borders)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = t.cell(ri, ci); cell.text = ''
            p = cell.paragraphs[0]; p.style = doc.styles[S_BODY]
            p.paragraph_format.space_after = Pt(1); p.paragraph_format.space_before = Pt(1)
            _runs(p, str(val))
            for r in p.runs:
                r.font.size = Pt(size)
                if ri == 0: r.bold = True
            if ri == 0: _shade(cell, 'EFEFEC')
    if widths:
        for ci, w in enumerate(widths):
            for ri in range(len(rows)): t.cell(ri, ci).width = Inches(w)
    doc.add_paragraph('', style=S_BODY)
    return t

def figure(fname, caption, width=6.4):
    FIGN[0] += 1
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(f'{FIGS}/{fname}', width=Inches(width))
    c = doc.add_paragraph(style=S_FIGCAP)
    _runs(c, f'Fig. V6-{FIGN[0]}.  {caption}')
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER

# =================================================================== V6
doc.add_page_break()
head('Version 6 Update — The Tabletop Model')
para('Compiled 13 September 2026. This section is added in place: everything above is Version 5 '
     'unchanged. It records the capture of 12 September, the Kaggle run of 12–13 September, and '
     'what the result does and does not demonstrate. Every number below is reproduced in '
     '`version6_results.md`, which cites a source for each claim.', italic=True)

head('A. Summary', 2)
para('A carved **miniature** of the pavilion was photographed indoors on a wooden board and '
     'reconstructed end to end. **Every photograph registered** — the first complete registration '
     'in this project.')
figure('fig_v6_subject.jpg',
       'The subject. A carved miniature of Sala Chaturamuk Phaichit, roughly 15 cm tall, standing '
       'on a wooden board against a cloth backdrop. Four of the 301 photographs: front at eye '
       'level, three-quarter showing the inlaid roof, side, and looking down onto the roof — the '
       'viewpoint the building itself has never been photographed from.', width=4.6)
table([['','Photographs','Registered','Gaussians (trained)','PSNR','SSIM','LPIPS'],
       ['**Sala model** (12 Sep)','301','**301**','222,199','**25.08 dB**','**0.851**','0.371'],
       ['Sala, sky trained (7 Sep)','446','395','593,708','23.45 dB','0.769','0.333'],
       ['Lamp (7 Sep)','100','100','154,729','20.87 dB','0.784','0.306']],
      caption='This round against the September pavilion runs. Same scoring protocol; different subjects.',
      widths=[1.5,0.8,0.8,1.1,0.8,0.6,0.6])
para('**The headline must not be read as progress in method.** This is a 15-centimetre object on a '
     'table in even indoor light, captured in six complete orbits at a fixed focal length. The '
     'pavilion is a building beside a lake, with sky behind it and no viewpoint above −10°. A '
     'tabletop object is an easier reconstruction problem than a building, and the correct '
     'conclusion from 25.08 dB is that the capture was good, not that the pipeline improved. '
     'LPIPS — perceptual rather than per-pixel — is **worse** here, 0.371 against the pavilion’s '
     '0.333: the plain cloth backdrop flatters PSNR and SSIM while adding nothing a perceptual '
     'metric rewards.')
para('Per-view PSNR ranges from **16.58 dB to 30.58 dB**, median **25.93**, over 38 held-out views.')

head('B. The Capture', 2)
para('301 photographs, 08:14–08:42, a single 28-minute session. Every clause of the capture rule '
     'that earlier rounds violated is satisfied.')
table([['Property','Value'],
       ['Camera','iPhone 17 Pro, all 301 frames'],
       ['Focal length','24 mm equivalent (6.765 mm), **spread 1.00×** — zero variation'],
       ['Dimensions','5712 × 4284, identical on all 301'],
       ['EXIF','Present on all 301'],
       ['Orbits','view1 61, view2 65, view3 44, view4 45, view5 45, view6 41'],
       ['Filenames','IMG_2069 – IMG_2373, unbroken']],
      caption='The 12 September capture. For comparison, the August set was three camera configurations across two phones six days apart.',
      widths=[1.6,4.8])
para('**The camera moves and the object does not** — a turntable capture cannot be solved by '
     'structure-from-motion without masking the background. Mean absolute difference between '
     'consecutive frames is **13.88 on the frame corners** (background) against 20.58 at the '
     'centre; a fixed camera would put the corners near zero.')
figure('fig_v6_capture_orbits.jpg',
       'One prepared frame from each of the six orbit rings, in capture order. Elevation rises '
       'across the set: the later rings look down onto the roof, which is the coverage the '
       'pavilion has never had. All 301 frames are 1200 × 1600 after the orientation fix of '
       'section D.', width=6.2)

head('C. Why the Matching Had to Change', 2)
para('Every previous run used sequential matching with loop detection off, because the pavilion is '
     'four-faced and vocabulary-tree retrieval pairs views 90° apart. That reasoning does not '
     'transfer here, and the measurements said so **before** any GPU time was spent.')
table([['Pair type','Frames apart','RANSAC inliers'],
       ['Adjacent, within an orbit','1','**241**'],
       ['Orbit seam (last of ring *n* → first of ring *n+1*)','1','**12–25**'],
       ['Same azimuth, different orbit','**~60**','**78–91**'],
       ['90° apart, same orbit (the symmetry trap)','15','**9**']],
      caption='Measured on the prepared frames with SIFT, Lowe ratio 0.75 and a RANSAC fundamental matrix.',
      widths=[3.2,1.4,1.6])
bullets([
 '**Sequential matching would have joined six rings by their weakest joints.** The strong '
 'cross-orbit links sit ~60 frames apart; no sequential window of 10 or 14 reaches them.',
 '**The four-fold symmetry trap does not spring here.** A 90°-apart pair scores 9 inliers. Wood '
 'grain and cloth folds differ at every azimuth, so the background breaks a symmetry that sky and '
 'lake could not.'])
para('Exhaustive matching was therefore both safe and affordable — 301 frames is ~45,000 pairs, each '
     'geometrically verified — and produced 301 of 301 in a single model. Under sequential matching '
     'the plausible failure was a split reconstruction, which is exactly what the pavilion run '
     'produced when 51 interior photographs were filed into a `sparse/1` that was never trained.')

head('D. A Defect That Nearly Shipped: EXIF Orientation', 2)
para('Preparation wrote **landscape pixels carrying EXIF orientation tag 6**. COLMAP and PIL read '
     'stored pixels and see landscape; anything honouring the tag sees portrait. It was uniform '
     'across all 301 frames, so nothing crashed — the failure mode was a model lying on its side, '
     'not an error message. The fix bakes the rotation into the pixels and clears the tag. This is '
     'the same class of defect as every entry in Version 5’s process-failure section: a value '
     'trusted without being checked against what it actually measured.')

head('E. Where the Score Is Lost, and the Clean That Followed', 2)
para('The same pattern as every previous round, with cloth in the role of sky. The white backdrop '
     'is nearly textureless, so nothing pins down the volume between camera and subject, and a '
     'large semi-transparent Gaussian there costs the loss very little. The result is a milky haze '
     'in front of the model, worst in the views that scored worst.')
para('**The notebook’s floater filter did not touch it.** Its threshold, 0.04 × ring = 0.147, was '
     'inherited from the outdoor scenes. On this model the largest-axis distribution peaks at '
     '0.143 at the 99.9th percentile — the threshold sits above almost the entire distribution and '
     'removed 3,557 Gaussians, about 1.5%. A constant tuned on one scene was carried to another '
     'without being re-checked.')
table([['Cut','Rule','Removes'],
       ['Radius','horizontal distance from the model’s own axis < 0.90','the haze'],
       ['Height','above the top of the board (h > −2.06 along up = [0, −1, 0])','the board and cloth'],
       ['Size','largest Gaussian axis < 0.05, alpha > 0.15','remaining floaters']],
      caption='Three cuts applied to the trained model directly — no retraining, no second GPU run — plus a gamma 1.9 midtone lift.',
      widths=[1.0,3.6,1.6])
table([['','Frame lit','Classified as haze','Mean luminance'],
       ['As trained (222,199)','95.9%','**41.0%**','98.6'],
       ['After the clean (77,626)','11.4%','**0.5%**','63.6']],
      caption='Both models rendered from the identical view matrix. 34.9% of the Gaussians survive.',
      widths=[2.0,1.2,1.6,1.4])
figure('fig_v6_fog_before_after.png',
       'The trained model (a) and the same model after the geometric clean (b), rendered from the '
       'identical camera. Haze falls from 41.0% of the frame to 0.5%; the board is removed.', width=6.6)
figure('fig_v6_turntable.png',
       'The cleaned model at 0°, 90°, 180° and 270°. Haze stays between 0.4% and 1.6% of the frame '
       'through a full revolution.', width=6.6)
para('**The scores in section A were not re-measured after this, and must not be quoted as scores '
     'of what the viewer shows.** They belong to the model the optimiser produced, haze included. '
     'Cropping changes what is displayed, not what was learned, and re-scoring a cropped model '
     'against photographs that still contain a board and a backdrop would measure the crop rather '
     'than the reconstruction.')
figure('fig_v6_heldout_gt_vs_render.jpg',
       'Held-out photographs (top) against renders (bottom), with per-view PSNR. The 16.58 dB view '
       'is the haze failure; the 27.98 dB view reproduces carving and inlay closely.', width=6.4)

head('F. What This Capture Cannot Show', 2)
bullets([
 '**The underside.** The model stands on a board; its base was never photographed, and nothing in '
 'the reconstruction can invent it.',
 '**The backdrop.** Plain cloth carries little texture, so what survived the crop there is thin.',
 '**The building.** This is a model *of* the pavilion. It belongs beside the outdoor runs as a '
 'controlled comparison, not as a replacement. The roof problem is answered here and still open there.'])

head('G. What Version 7 Should Do', 2)
para('In order of cost.')
bullets([
 '**Re-tune the floater threshold per subject, in the notebook.** A constant carried between scenes '
 'is worthless; derive it from the scene’s own percentile distribution. Zero GPU.',
 '**Apply the same geometric clean to the pavilion runs.** The lever is now measured — haze 41.0% → '
 '0.5% — and the pavilion pages still show haze around the roofline. Zero GPU.',
 '**Constrain the viewer’s camera** to the photographed envelope. Outstanding from Version 5.',
 '**Train the interior sub-model** from `sparse/1` — 71 photographs already reconstructed, ~40 min GPU.',
 '**Re-shoot the pavilion for elevation.** Outstanding since Version 5. This round demonstrates what '
 'complete orbit coverage buys — 301 of 301 registered, roof observed — and is the argument for '
 'doing it on the building.'])
para('**Do not** spend GPU on more iterations; the Version 5 extrapolation bounding the remaining '
     'benefit at 7–12% of training loss has not been superseded.')

doc.save(DST)
print('saved', DST, round(os.path.getsize(DST)/1e6, 1), 'MB')
print('figures', FIGN[0], 'tables', TABN[0])
