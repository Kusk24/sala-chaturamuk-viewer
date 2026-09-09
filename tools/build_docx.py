# Build the Version 5 results report as a .docx, reusing Version4's template so the
# title block, fonts and named styles carry over. Body is single column: this is a
# supplementary report with wide tables and figures, not the two-column paper.
import re, os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

P    = '/Users/kusk/Desktop/Computer Vision/Term-Project/sala-chaturamuk-viewer/paper'
FIGS = f'{P}/figs_v5b'
DST  = f'{P}/CSX4213_Sala_Thai_Version5_Results.docx'

doc = Document(f'{P}/CSX4213_Sala_Thai_Version4.docx')
body = doc.element.body
kids = list(body)
for k in kids[7:len(kids)-1]:          # keep title, both section breaks, authors, final sectPr
    body.remove(k)

doc.paragraphs[0].runs[0].text = ('Two Gaussian-Splatting Reconstructions from the September '
                                  'Re-Capture of Sala Chaturamuk Phaichit, and What Still Limits Them')

FIGN = [0]; TABN = [0]

def _runs(par, text):
    for i, chunk in enumerate(re.split(r'\*\*(.+?)\*\*', text)):
        if not chunk: continue
        r = par.add_run(chunk)
        if i % 2: r.bold = True

def para(text, style='Body Text', size=None, italic=False, space_after=None):
    p = doc.add_paragraph(style=style)
    _runs(p, text)
    if size or italic:
        for r in p.runs:
            if size: r.font.size = Pt(size)
            if italic: r.italic = True
    if space_after is not None: p.paragraph_format.space_after = Pt(space_after)
    return p

def head(text, level=1):
    return doc.add_paragraph(text, style=f'Heading {level}')

def bullets(items):
    for it in items:
        p = doc.add_paragraph(style='bullet list'); _runs(p, it)

def _shade(cell, hexcolor):
    el = OxmlElement('w:shd'); el.set(qn('w:val'), 'clear'); el.set(qn('w:fill'), hexcolor)
    cell._tc.get_or_add_tcPr().append(el)

def table(rows, caption=None, widths=None, size=8.5):
    TABN[0] += 1
    if caption:
        c = doc.add_paragraph(style='table head')
        _runs(c, f'TABLE {TABN[0]}.  {caption}')
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = 'Normal Table'; t.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = t._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        e = OxmlElement(f'w:{edge}')
        e.set(qn('w:val'), 'single'); e.set(qn('w:sz'), '4'); e.set(qn('w:color'), 'A6A6A6')
        borders.append(e)
    tblPr.append(borders)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = t.cell(ri, ci)
            cell.text = ''
            p = cell.paragraphs[0]; p.style = doc.styles['Body Text']
            p.paragraph_format.space_after = Pt(1); p.paragraph_format.space_before = Pt(1)
            _runs(p, str(val))
            for r in p.runs:
                r.font.size = Pt(size)
                if ri == 0: r.bold = True
            if ri == 0: _shade(cell, 'EFEFEC')
    if widths:
        for ci, w in enumerate(widths):
            for ri in range(len(rows)): t.cell(ri, ci).width = Inches(w)
    doc.add_paragraph('', style='Body Text').paragraph_format.space_after = Pt(4)
    return t

def figure(fname, caption, width=6.4):
    FIGN[0] += 1
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(f'{FIGS}/{fname}', width=Inches(width))
    c = doc.add_paragraph(style='figure caption')
    _runs(c, f'Fig. {FIGN[0]}.  {caption}')
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER

# ----------------------------------------------------------------- abstract
a = doc.add_paragraph(style='Abstract')
_runs(a, 'Abstract—The 5 September 2026 re-capture removed every cause identified in the Version 5 '
         'failure analysis, and for the first time in this project a reconstruction ran end to end. '
         'Two 3D Gaussian Splatting models were trained: the pavilion, from 395 registered '
         'photographs, scoring 20.10 dB PSNR on 50 held-out views, and an adjacent stone lamp, from '
         '100 photographs, scoring 15.93 dB on 13. This report documents both the failure that '
         'preceded them and the result, and argues that the headline PSNR is the wrong number to '
         'read. Decomposed by image region, the same renders score 22.33 dB and 18.14 dB once '
         'sky-mask artefacts are excluded, and 20.89 dB and 20.25 dB over the region the subject '
         'occupies. Three limits remain, none of them a training limit: a sky mask that is not '
         'consistent between views, worth 2.2–2.4 dB; an interior that never bound to the exterior, '
         'leaving 51 of 93 interior photographs untrained; and a capture in which not one camera '
         'looks down at the pavilion, so the roof is unobserved. A fitted extrapolation of the '
         'training loss bounds all remaining benefit from further optimisation at 7–12 per cent, '
         'against 2.4 dB available from a software fix.')
k = doc.add_paragraph(style='Keywords')
_runs(k, 'Keywords—3D Gaussian splatting, structure from motion, novel view synthesis, capture '
         'planning, held-out evaluation, Thai pavilion')

# ------------------------------------------------------------------ I
head('Summary')
para('The re-capture worked. For the first time in this project a reconstruction ran end to end — '
     'structure-from-motion, undistortion, 30,000 iterations of Gaussian splatting, held-out '
     'scoring and export — without a single geometric failure. Two models came out of it.')
table([['','Photographs','Registered','Gaussians (cropped)','PSNR','SSIM','LPIPS'],
       ['**Sala**','446','395','291,764','**20.10 dB**','0.739','0.342'],
       ['**Lamp**','100','100','163,756','**15.93 dB**','0.707','0.314']],
      caption='The two models produced by the September re-capture.')
para('Both are scored on held-out photographs the model never saw — every eighth frame, 50 for the '
     'sala and 13 for the lamp — using the same protocol as the 146-image version2 model reported '
     'in Version 4 (22.09 dB, 0.785, 0.346 at 15,000 iterations), so the three are comparable.')
para('**The single most transferable finding of this round:** the reported PSNR is dominated by '
     'parts of the photograph that are not the subject. Sky that the mask blackened inconsistently, '
     'and distant scenery no orbit could constrain, account for most of the loss. A single headline '
     'number conceals a reconstruction that is good where it was photographed and absent where it '
     'was not.')
para('Three limits remain, and **none of them is a training limit**:')
table([['#','Limit','Status'],
       ['1','The sky mask fires on some frames and not others, so the same tree is black in one '
            'view and textured in the next','Measured, costs 2.2–2.4 dB, fixable in software'],
       ['2','The interior never bound to the exterior; COLMAP filed it as a second reconstruction '
            'and it was never trained','Measured, 51 of 93 interior photographs unused'],
       ['3','Not one photograph looks down at the pavilion — the highest viewpoint is −10° '
            'elevation','**Requires new photographs.** Named in the Version 5 failure analysis and '
            'not acted on']],
      caption='What still limits the result.', widths=[0.35, 3.2, 2.6])

# ------------------------------------------------------------------ II
head('What the Failure Analysis Asked For, and What Happened')
para('Section 9 of version5_failure_analysis.md listed three actions in order of cost. Recording '
     'the outcome honestly matters more than recording the plan.')
table([['#','Recommended','Outcome'],
       ['1','Re-run COLMAP on the 352-photograph set with single_camera_per_folder',
            '**Not done, and correctly so.** Superseded by action 3, which removed the cause rather '
            'than working around it'],
       ['2','Train and report whatever that produced','**Not applicable** — the combined set was abandoned'],
       ['3','Re-shoot: one camera, one session, one focal length, unbroken chain, **elevated '
            'positions from floor 6 or higher**',
            '**Done, except the elevated positions.** Every other clause was satisfied exactly. The '
            'elevation clause was not, and it had been named "the only route to an observed roof"']],
      caption='Continuity with the previous round.', widths=[0.35, 2.8, 3.15])
para('The re-capture solved every cause the failure analysis identified — and reproduced, untouched, '
     'the one cause it had flagged as needing height.')

# ------------------------------------------------------------------ III
head('The 5 September Capture')
para('724 photographs, one continuous 55-minute session, iPhone 16 Pro, ultra-wide 2.22 mm lens.')
table([['Property','Combined Aug set (failed)','5 Sep set'],
       ['Cameras','2 phones (iPhone 17 Pro, 16 Pro)','**1**'],
       ['Lens configurations','3','**1**'],
       ['35 mm-equivalent focal spread','**7×** (24–100 mm)','**1.00×** (14 mm on every frame)'],
       ['Sessions','2, six days apart','**1**'],
       ['Frames with no EXIF','131','**0**'],
       ['Frames slower than 1/60 s','not measurable','**1 of 724**'],
       ['ISO range','not measurable','50–250']],
      caption='The capture that failed, against the capture that worked.', widths=[2.1, 2.3, 2.0])
para('This is the fix. Every mechanism identified in the failure analysis — one intrinsic forced '
     'across incompatible sensors, invisible because downscaling to 1600 px gives different fields '
     'of view identical pixel dimensions — is structurally impossible on a single-lens capture.')
table([['Subject','Frames','Size','Segments'],
       ['sala','446','1600×1200','Sala 360 (264), Sala 360 Near (89), Sala Inside (93)'],
       ['lamp','100','1200×1600','Higher (30), Middle (33), Lower (37)'],
       ['far','171','1600×1200','not yet trained']],
      caption='Prepared subsets. Seven 16:9 frames were dropped.', widths=[0.8, 0.7, 1.0, 3.9])

# ------------------------------------------------------------------ IV
head('Attempt Log')
table([['#','Date','Subject','Outcome'],
       ['1','7 Sep','lamp','**Failed at training.** FileNotFoundError: sparse/0/images.bin'],
       ['2','7 Sep','lamp','**Succeeded.** 1 h 35 m 35 s wall clock, 1.97 GB output'],
       ['3','7 Sep','sala','**Succeeded.** 1 h 43 m 16 s of training alone']],
      caption='Runs in this round.', widths=[0.35, 0.7, 0.8, 4.4])
para('No run in this round produced a folded or geometrically wrong reconstruction. That is the '
     'difference between this week and the five attempts documented in the failure analysis. The '
     'fold diagnostic — maximum consecutive-camera step divided by the median step, scale-'
     'invariant, with a healthy reference of 7.0 from the clean 146-image capture — reports:')
table([['Capture','Segment','Frames','max/median','Jumps > 5×'],
       ['Sala','Sala 360','264','10.0','2 (0.8%)'],
       ['Sala','Sala 360 Near','89','14.3','17 (19.3%)'],
       ['Sala','Sala Inside','42','2.4','0'],
       ['Lamp','Higher','30','3.7','0'],
       ['Lamp','Middle','33','2.9','0'],
       ['Lamp','Lower','37','2.4','0']],
      caption='Fold ratios. The failed combined runs reported 102.2 and 36.0.',
      widths=[0.9, 1.6, 0.8, 1.3, 1.3])
para('**Sala 360 Near is the one number to keep an eye on:** at 14.3, with 19.3% of its steps '
     'beyond five times the median, it sits just under the 15.0 gate, and it passed on a threshold '
     'the failure analysis itself called arbitrary. It is a near-orbit of a large building where '
     'the photographer’s distance changes sharply, so a genuine walk break is the likelier '
     'explanation than a fold — but it was not independently verified, and it should not be quoted '
     'as if it had been.')

# ------------------------------------------------------------------ V
head('The Defect That Stopped the First Run')
para('colmap image_undistorter --output_type COLMAP writes its output as '
     'sparse/{cameras,images,points3D}.bin, flat. The 3DGS function readColmapSceneInfo reads '
     'sparse/0/, a path it hardcodes. The undistorted scene was therefore invisible to the trainer '
     'and the run died three hours in, after all the expensive work had completed.')
para('The reason this was not caught earlier is worth stating plainly: **the undistort-to-train path '
     'had never once executed in this project.** Every earlier attempt died at the fold check before '
     'reaching it, and the one model that did train used a pre-made pinhole dataset that bypassed '
     'undistortion entirely. The defect was not a regression. It was a section of the pipeline that '
     'had never run.')
para('The fix is to move the files into sparse/0/ after undistortion, which is what the 3DGS '
     'repository’s own convert.py does. It was verified locally before re-running — COLMAP '
     '4.1.1 over all 100 real lamp photographs, then loaded back through 3DGS’s own '
     'colmap_loader.py: 100 images, one PINHOLE camera at 1191×1588, 45,393 points at 0.434 px mean '
     'reprojection error. An assertion now fails at undistortion rather than three hours later.')

# ------------------------------------------------------------------ VI
head('Results')
para('395 of 446 photographs, 30,000 iterations, NVIDIA T4 ×2, 1 h 43 m 16 s.')
table([['Metric','Sala','Lamp'],
       ['PSNR','20.096 dB','15.932 dB'],
       ['SSIM','0.7392','0.7068'],
       ['LPIPS','0.3418','0.3140'],
       ['Held-out views','50','13'],
       ['Per-view PSNR range','10.45 – 25.61 dB','10.07 – 22.34 dB'],
       ['Gaussians, full field','653,917','1,053,976'],
       ['Gaussians after object crop','291,764','163,756']],
      caption='Measured results for both models.', widths=[2.4, 2.0, 2.0])
para('The lamp registered every photograph and produced the cleanest fold ratios in the project, '
     'yet scores nearly 4.2 dB below the sala. The next section explains why, and the explanation '
     'is not that the lamp reconstructed worse.')
figure('fig_heldout_sala.png',
       'Held-out photographs of the pavilion beside the model’s own render of the same pose. '
       'Top: the worst-scoring view. Below: two typical ones. The structure is reproduced; the sky '
       'behind it is not.', width=4.6)

# ------------------------------------------------------------------ VII
head('Where the Score Is Actually Lost')
para('Recomputing PSNR over sub-regions of the same renders, with no retraining:')
figure('fig_psnr_regions.png',
       'The same renders, scored over three regions. Excluding pixels the sky mask blackened lifts '
       'both models by more than 2 dB; over the region the subject occupies the two are within '
       '0.6 dB of each other.', width=4.4)
table([['Region','Sala','Lamp'],
       ['Whole frame','20.10 dB','15.93 dB'],
       ['Excluding pixels the sky mask blackened','**22.33 dB** (+2.40)','**18.14 dB** (+2.21)'],
       ['Central region — the subject','20.89 dB','**20.25 dB**'],
       ['Best single held-out view, central region','25.56 dB','**30.01 dB**'],
       ['Blackened pixels, share of average frame','11.8%','17.4%']],
      caption='Region-decomposed scores.', widths=[3.0, 1.7, 1.7])
para('**The lamp’s low headline number is a framing artefact.** Over the region the lamp '
     'occupies it scores 20.25 dB and reaches 30.01 dB on its best view — comparable to the sala, '
     'and on its best view better than anything else in the project. Its whole-frame number is low '
     'because a small object photographed from 3.6 m leaves most of the frame filled with a lake, a '
     'treeline and buildings a hundred metres away, which a 3.6 m orbit gives no parallax on and '
     'therefore cannot constrain. The model renders them as smear, and PSNR counts every one of '
     'those pixels.')
para('**The sky mask costs more than any hyperparameter.** The HSV-and-gradient mask fires on some '
     'frames and not on others: in held-out views 00007 and 00009 the ground truth shows open sky, '
     'while in 00012 the same sky is black. The model cannot satisfy both, so it learns a '
     'compromise and is penalised in both. This is worth 2.2–2.4 dB — roughly forty times what '
     'doubling the training budget would buy — and it is fixable in software, without new '
     'photographs.')
figure('fig_skymask.png',
       'The sky mask is not consistent between views. The same overcast sky is left textured in two '
       'held-out frames and painted black in a third. Every blackened pixel is scored against a '
       'render that cannot match both cases.', width=6.4)
para('**Implication for the paper.** A single whole-frame PSNR is not a measure of how well the '
     'subject reconstructed. Where the subject occupies a minority of the frame, the number is '
     'mostly reporting the background. This parallels the finding of the previous round — that '
     'sub-pixel reprojection error is not evidence of correct geometry — and has the same moral: '
     'the standard summary statistic answers a different question than the one being asked.')

# ------------------------------------------------------------------ VIII
head('The Interior Never Joined the Exterior')
para('COLMAP produced **two disconnected sub-models** for the sala, and 3DGS trained only the larger.')
table([['Sub-model','Images','Trained'],
       ['sparse/0','395','yes'],
       ['sparse/1','71','**no**'],
       ['In both','20','—'],
       ['**Exclusive to sparse/1**','**51**','**no**']],
      caption='The split reconstruction.', widths=[2.4, 1.6, 1.6])
para('Those 51 photographs are not a random scatter. Cross-referenced against the capture manifest, '
     '**every one of them belongs to the Sala Inside folder.** Of 93 interior photographs, 42 bound '
     'to the exterior walk and 51 did not.')
para('The cause is ordinary and worth naming: standing under the roof, the camera sees painted '
     'ceiling and columns and almost nothing it saw from the terrace. Without frames that observe '
     'both at once, sequential matching finds no bridge, and COLMAP correctly reports two '
     'reconstructions rather than inventing a link between them. The model published as "the sala" '
     'is therefore **the exterior**.')
para('The fix is cheap and belongs in the next capture: a handful of deliberate transition frames '
     'taken standing in the doorway, turning slowly from outside to inside, so the two halves share '
     'features. The 71 images in sparse/1 are already reconstructed and could be trained as a '
     'separate interior model at any time for roughly 40 minutes of GPU.')

# ------------------------------------------------------------------ IX
head('The Roof Was Never Photographed')
para('Measuring the elevation of every camera about the centre of the reconstructed object, using a '
     'world up-vector derived from the cameras’ own up axes (mean agreement 0.97, i.e. the '
     'capture was level):')
figure('fig_elevation.png',
       'Camera elevation about the subject. Every sala photograph sits at or below the horizon; '
       'the upper hemisphere is empty. The lamp’s three orbits reach +43° but nothing '
       'overhead.', width=4.4)
para('Azimuth coverage is complete for both — 12 of 12 sectors, thinnest 22 photographs for the '
     'sala and 4 for the lamp. The deficiency is entirely in elevation.')
para('**Not one of the 446 sala photographs looks down at the pavilion.** The upper surfaces of the '
     'roof were never observed, so no Gaussian was ever placed on them and no amount of '
     'optimisation can create one. Viewed from above, the roof opens into a hollow shell — not '
     'because the model is undertrained, but because a radiance field contains only what was seen.')
figure('fig_sala_observed_vs_not.png',
       'The same model, two viewpoints. A: rendered from the pose of a photograph the capture '
       'actually took. B: rendered looking down from above, a direction no camera ever occupied. '
       'Nothing distinguishes these two renders except whether the viewpoint was photographed.',
       width=4.3)
para('This is the same limitation reported in the previous round, whose section 9.3 specified the '
     'remedy: elevated positions from floor 6 or higher of the main building’s east facade. '
     'The re-capture followed every other instruction and omitted this one. The honest conclusion '
     'is that **the roof remains unobserved by choice of viewpoint, not by limitation of method**, '
     'and that the project now has a direct measurement of the gap rather than an impression of it.')

# ------------------------------------------------------------------ X
head('Was 30,000 Iterations Enough?')
para('Yes, and the question can be answered quantitatively rather than by eye. Mean training L1 '
     'loss per 5,000 iterations, read from the TensorBoard event files:')
table([['','0–5k','5–10k','10–15k','15–20k','20–25k','25–30k'],
       ['Lamp','0.0911','0.0538','0.0438','0.0362','0.0335','**0.0319**'],
       ['Sala','0.0919','0.0663','0.0564','0.0477','0.0447','**0.0429**']],
      caption='Training loss, binned.', widths=[0.7,0.9,0.9,0.9,0.9,0.9,0.9])
para('The final 5,000 iterations improved the loss by 4.8% (lamp) and 4.0% (sala). Fitting '
     'L(t) = c + A·t^−b over the post-densification regime (16k–30k, after densification stops at '
     '15,000) and extrapolating:')
figure('fig_loss.png',
       'Measured loss (solid) with the fitted extrapolation (dashed) and its asymptote (dotted). '
       'The asymptote bounds what any amount of further training could achieve.', width=4.4)
table([['Iterations','Lamp','Sala'],
       ['30,000 (measured)','0.0319','0.0429'],
       ['40,000','0.0302 (−4.3%)','0.0413 (−3.0%)'],
       ['60,000','0.0291 (−7.8%)','0.0404 (−5.1%)'],
       ['∞ (fitted asymptote)','**0.0278 (−11.7%)**','**0.0396 (−6.9%)**']],
      caption='Extrapolated training loss.', widths=[2.2, 2.1, 2.1])
para('The asymptote is the important row: it bounds what any amount of further training could ever '
     'achieve. For the sala that ceiling is 6.9%, worth on the order of +0.3 dB, and roughly half '
     'of it would be reached by 40,000 iterations at a cost of about 2 h 20 m of additional GPU. '
     'For comparison, fixing the sky mask is worth 2.40 dB and costs no GPU at all.')
para('One implementation detail bears on any attempt to extend a run: 3DGS decays the position '
     'learning rate over position_lr_max_steps, which defaults to 30,000. Resuming a finished '
     '30,000-iteration checkpoint therefore continues at the floor of that schedule, where '
     'Gaussians barely move, and yields materially less than the extrapolation above. Reaching the '
     'predicted values requires a fresh run with --iterations 40000 so that the schedule stretches.')
para('**Conclusion: 30,000 iterations was the correct stopping point.** Training is not the binding '
     'constraint on any result in this report.')

# ------------------------------------------------------------------ XI
head('The Viewer')
para('Both models are published as interactive pages alongside the existing image-based renderer '
     'and photogrammetry mesh, and linked from index.html. Consistent with the project’s '
     'standing constraint, these are the clearly-labelled reconstruction comparison arm and are '
     'never mixed into the image-based rendering pipeline.')
table([['Page','Model'],
       ['sala.html','September capture, 291,764 Gaussians, 395 poses'],
       ['lamp.html','163,756 Gaussians, 100 poses'],
       ['splat.html','August version2 capture, retained for comparison']],
      caption='Published viewer pages.', widths=[1.6, 4.8])
para('Each embeds its model as base64 in a JavaScript global and reads the renderer from '
     'vendor/splat.js (antimatter15/splat, MIT), so the pages open from file:// with no server and '
     'no build step — the same constraint the rest of the viewer observes. The vendored renderer '
     'was extended by six lines to accept per-page camera poses and an opening view matrix; pages '
     'that supply neither are unaffected, so the existing splat.html renders exactly as before.')
para('The published models are the **cropped** fields, not the full ones. This is deliberate: the '
     'discarded Gaussians are the background that scores around 10 dB, and including them would '
     'make the pages both heavier and worse. The sala page shows 291,764 of 653,917 Gaussians; the '
     'lamp page 163,756 of 1,053,976. Both pages state their own limitations, with the measured '
     'numbers, rather than presenting a headline score without context.')
figure('fig_lamp_observed_vs_not.png',
       'The lamp model. A: from a photographed pose, where the mouldings resolve cleanly. B: from '
       'above, outside the envelope its three orbits covered.', width=3.6)

# ------------------------------------------------------------------ XII
head('Process Failures, and What They Cost')
table([['Failure','Cost','Correction'],
       ['A pipeline path — undistort to train — that had never been executed was assumed to work',
        'One full Kaggle run, ~3 h',
        'Verified locally end to end against 3DGS’s own loader before re-running'],
       ['The fold check was applied to captures whose frame ordering could not be verified',
        'Two runs rejected on a test that did not apply',
        'Gated to captures with verified ordering; now warns rather than aborting'],
       ['The sky mask was never checked for consistency between views, only for whether it ate the subject',
        '2.2–2.4 dB in every reported score','Measured this round; not yet fixed'],
       ['The elevated-viewpoint instruction was not carried through to the capture plan',
        'The roof is unobserved for a second consecutive round',
        'Must appear in the capture one-pager as a required segment, not a recommendation'],
       ['Full-frame PSNR was quoted for four rounds without asking what share of the frame is subject',
        'Understated every object-scale result',
        'Region-decomposed scores reported alongside the headline from this round on']],
      caption='Process failures.', widths=[2.6, 1.7, 2.2])
para('The pattern across this round and the last is consistent: **the failures were in '
     'verification, not in the method.** Every one was a case of a number or a stage being trusted '
     'without being checked against what it actually measured.')

# ------------------------------------------------------------------ XIII
head('What Version 6 Should Do')
para('In order of cost.')
bullets([
 '**Fix the sky mask, retrain nothing.** Enforce view-consistency — either mask nothing and let '
 'the crop remove distant floaters, or segment the sky per-frame with a model that does not flip '
 'between adjacent views. Worth 2.2–2.4 dB, zero GPU.',
 '**Constrain the viewer’s camera** to the photographed envelope (−30° to 0° for the sala, '
 '−43° to +43° for the lamp) so unobserved directions cannot be flown into. No retraining; removes '
 'the most visible artefact in the published pages.',
 '**Train the interior sub-model** from sparse/1. 71 photographs already reconstructed, ~40 min '
 'GPU, and it adds content that currently exists in no model.',
 '**Train the far set** — 171 photographs, prepared and untouched, at a second capture radius.',
 '**Re-shoot for elevation.** 40–60 frames between +30° and +60°, plus doorway transition frames '
 'so the interior binds. This is the only route to an observed roof and to a single connected '
 'model, and it is now the third round in which it has been the outstanding item.'])
para('**Do not** spend GPU on more iterations. The extrapolation above bounds the entire remaining '
     'benefit at 7–12% of training loss, against a 2.4 dB gain available from a software fix.')

# ------------------------------------------------------------------ XIV
head('Reproducing the Numbers')
table([['Claim','Source'],
       ['Capture EXIF, focal-length spread, ISO, shutter','PIL.Image.getexif() over the 5 Sep HEIC originals; pillow-heif for decoding'],
       ['Segment counts','CV_Photos_prepared/{sala,lamp}_manifest.csv'],
       ['Registration counts, fold ratios','Kaggle run logs; notebook cells 8 and 9'],
       ['Two sub-models, and which images are in each','COLMAP sparse/{0,1}/images.bin, decoded from the binary record format'],
       ['Held-out scores','results.json, 3DGS metrics.py, every 8th frame held out via --eval'],
       ['Per-view scores','model/per_view.json'],
       ['Region-decomposed PSNR','Recomputed from model/test/ours_30000/{gt,renders}/*.png; background = pixels below value 18 in either image'],
       ['Loss curves and extrapolation','model/events.out.tfevents.*, parsed from the TFRecord/protobuf stream'],
       ['Camera elevation coverage','cameras.json positions against the median of the cropped model’s Gaussian centres; world up from the mean of the cameras’ own up axes'],
       ['Gaussian counts','.splat file size ÷ 32 bytes per row; PLY element vertex header'],
       ['Renders in Figs. 1, 4 and 5','CPU EWA splat rasteriser written for this report: 3D covariance from quaternion and scale, projected through the perspective Jacobian, alpha-composited back to front']],
      caption='Where every number in this report comes from.', widths=[2.3, 4.2])
para('Raw outputs are in Term-Project/kaggle_out/{sala,lamp}/. The notebooks are resumable: every '
     'expensive stage banks to /kaggle/working and is restored before any work is redone, so '
     're-running the same file after a failure skips whatever already completed.')

doc.save(DST)
print('saved', DST, os.path.getsize(DST)/1e6, 'MB')
