"""Build a faculty-review draft deck using reviewed evidence and explicit caveats."""
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches,Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN,MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'deliverables/PROJECT_PRESENTATION_DRAFT.pptx'
NAVY=RGBColor(18,39,65);BLUE=RGBColor(38,111,191);TEAL=RGBColor(27,154,145);RED=RGBColor(178,58,72);GRAY=RGBColor(91,105,120);LIGHT=RGBColor(239,244,249);WHITE=RGBColor(255,255,255);DARK=RGBColor(30,43,57)


def textbox(slide,x,y,w,h,text,size=18,color=DARK,bold=False,font='Aptos',align=None):
    shape=slide.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=shape.text_frame;tf.clear();tf.word_wrap=True
    p=tf.paragraphs[0];p.text=text;p.font.name=font;p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=color
    if align is not None:p.alignment=align
    return shape

def base(prs,title,kicker=''):
    s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=WHITE
    bar=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,0,prs.slide_width,Inches(.14));bar.fill.solid();bar.fill.fore_color.rgb=TEAL;bar.line.fill.background()
    textbox(s,.55,.34,12.2,.45,title,25,NAVY,True)
    if kicker:textbox(s,.58,.86,12,.32,kicker,10,GRAY)
    return s

def card(s,x,y,w,h,title,body,color=BLUE):
    sh=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h));sh.fill.solid();sh.fill.fore_color.rgb=LIGHT;sh.line.color.rgb=LIGHT
    textbox(s,x+.18,y+.12,w-.36,.38,title,15,color,True)
    textbox(s,x+.18,y+.56,w-.36,h-.68,body,12,DARK)

def bullets(s,x,y,w,items,size=15,leading=.56,color=DARK):
    for i,item in enumerate(items):
        textbox(s,x,y+i*leading,.28,.34,'•',size+3,TEAL,True)
        textbox(s,x+.28,y+i*leading,w-.28,leading,item,size,color)

def table(s,x,y,w,h,headers,rows,widths=None,font=12):
    t=s.shapes.add_table(len(rows)+1,len(headers),Inches(x),Inches(y),Inches(w),Inches(h)).table
    if widths:
        for c,v in enumerate(widths):t.columns[c].width=Inches(v)
    for r,vals in enumerate([headers]+rows):
        for c,val in enumerate(vals):
            cell=t.cell(r,c);cell.text=str(val);cell.margin_left=Inches(.08);cell.margin_right=Inches(.08);cell.margin_top=Inches(.04);cell.margin_bottom=Inches(.04)
            cell.fill.solid();cell.fill.fore_color.rgb=NAVY if r==0 else (LIGHT if r%2 else WHITE)
            cell.vertical_anchor=MSO_ANCHOR.MIDDLE
            for p in cell.text_frame.paragraphs:
                p.font.name='Aptos';p.font.size=Pt(font if r else font);p.font.bold=(r==0);p.font.color.rgb=WHITE if r==0 else DARK
    return t

def footer(s,n):textbox(s,.55,7.16,12,.18,f'B.Tech CSE major project • Evidence frozen at current review • Slide {n}/11',8,GRAY)

def build():
    prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
    # 1
    s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=NAVY
    sh=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(.6),Inches(.8),Inches(.12),Inches(4.2));sh.fill.solid();sh.fill.fore_color.rgb=TEAL;sh.line.fill.background()
    textbox(s,1.05,1.05,11.4,1.35,'Integrity and Tamper Localization\nin Dermoscopy',32,WHITE,True)
    textbox(s,1.08,2.75,10.5,.8,'A controlled comparison with diagnostic-model impact analysis',21,RGBColor(205,222,239))
    textbox(s,1.08,4.25,11,.45,'Exact integrity • localization coverage • class-sensitive impact',15,RGBColor(158,220,214),True)
    textbox(s,1.08,4.85,11,.55,'Validation development evidence • historical split overlap remains unresolved',13,RGBColor(250,210,158))
    textbox(s,1.08,6.8,11,.3,'Technical review draft • adapted research cohort • scope defined in the protocol',10,RGBColor(200,211,223))
    # 2 — explicit historical-to-current transition; legacy metrics are not current T1 outcomes.
    s=base(prs,'Transition: from a fragile watermark to evidence-bounded comparisons','Earlier mid-review/poster: separate ISIC 2018 experiment • Current T1: separate adapted-cohort classifier validation')
    card(s,.55,1.4,3.95,2.55,'Earlier stage • reported','Fragile 8×8 QIM watermark. Mid-review reported ISIC 2018 n=2,594: 99.99% copy-move detection and mean IoU .9936. Historical reports—not current T1 results.',BLUE)
    card(s,4.7,1.4,3.95,2.55,'What the limits exposed','Separate JPEG-Q100 probe: 2/300 false claims (0.67%), above the stated 0.50% ceiling. Burned-text mean IoU .272; strict IoU≥.50 detection 0%. Q75/Q50 coverage near zero.',RED)
    card(s,8.85,1.4,3.95,2.55,'Current framing','Separate integrity, localization, and classifier-impact questions. T1 is a different three-model validation study: JPEG70 raised accuracy while MEL sensitivity fell across all models.',TEAL)
    textbox(s,.75,4.35,11.9,.75,'Transition is a research-story synthesis, not proof that a particular past failure caused each later design decision. The old claims are not independently replayed here.',15,NAVY,True)
    textbox(s,.75,5.35,11.9,.72,'The PDFs’ Drive timestamps (Oct 21 and Oct 25) postdate the Oct 19 status snapshot; actual presentation dates are unverified. Details and source links: MIDREVIEW_POSTER_TRANSITION_RECORD.md.',11,GRAY)
    footer(s,2)
    # 3
    s=base(prs,'Research question: what does dermoscopic image protection guarantee?','How do exact-integrity and localization methods trade off storage, coverage and latency, and what classifier changes accompany controlled image operations?')
    card(s,.65,1.55,3.85,2.4,'1  Integrity','Question: are these exact RGB pixels the pixels that were signed?\n\nDetached Ed25519 evidence supports exact-pixel verification. Re-encoding is a content change, not a benign exception.',BLUE)
    card(s,4.75,1.55,3.85,2.4,'2  Localization','Question: where did pixels change, under a sidecar/storage/latency budget?\n\nTile evidence trades compactness for map precision, coverage and verification time.',TEAL)
    card(s,8.85,1.55,3.85,2.4,'3  Diagnostic impact','Question: do operators or embedding change a frozen model’s class-sensitive outputs?\n\nWe report class sensitivity and paired probabilities—not accuracy, PSNR or agreement alone.',RED)
    textbox(s,.85,4.45,11.8,.9,'These endpoints are not interchangeable: integrity failure is not intent, a map is not authentication, and classifier shift is not clinical harm.',18,NAVY,True)
    textbox(s,.85,5.6,11.8,.7,'Prior art includes DICOM digital-signature profiles [1], EdDSA [2], EditGuard [4], WAM [5] and OmniGuard [6]. Our adapted studies are not exact reproductions of these works.',12,GRAY)
    footer(s,3)
    # 4
    s=base(prs,'Cohort and protocol: adapted ISIC2019, not clinical validation','All reported cohort results are development/validation evidence; no confirmatory holdout claim is made.')
    table(s,.65,1.4,7.15,2.1,['Evidence split','Images','MEL','nonMEL'],[['TRAIN pilot pool','1,500','170','1,330'],['Validation','500','56','444']],widths=[2.5,1.5,1.5,1.65],font=14)
    card(s,8.1,1.4,4.55,2.1,'Evaluation boundary','The historical v2 test IDs are unrecoverable from retained evidence. Overlap with the later holdout is unknown; that holdout is excluded from confirmatory claims and further outcome analysis.',RED)
    bullets(s,.8,4.05,11.9,[
      'We selected the adapted DenseNet121 checkpoint using validation balanced accuracy; these outcomes are development evidence.',
      'Preparation records report no exact cross-split RGB-hash duplicates; perceptual similarity was not checked.',
      'Our lesion-disjoint selection does not establish patient independence or authoritative institution balance.'
    ],14,.62)
    textbox(s,.8,6.35,11.8,.45,'Experimental protocol: We checked returned records against declared cohort/settings; we did not rerun the source-image transformations or classifier inference locally.',10,GRAY)
    footer(s,4)
    # 4
    s=base(prs,'Track A: zero-distortion evidence has a coverage/latency tradeoff','Validation, 500 images; exact RGB integrity. Full4/Full8 denote 4×4/8×8 tile grids. Compactness is not a universal optimum.')
    table(s,.45,1.35,12.4,3.15,['Method','Extra bytes / image','Local edit IoU\n(copy / blur)','Global fine maps','Verification time\n(local edits)'],[
      ['Full4','524,378','.837 / .795','Available on tested cases','~0.056 s'],
      ['Full8','131,162','.680 / .644','Available on tested cases','~0.021 s'],
      ['bounded289','18,620\n(−96.45% vs Full4)','Matches Full4 on tested local edits','0 / 3,500 global-operation maps','~1.87 s']
    ],widths=[1.65,2.15,2.6,3.2,2.8],font=12)
    textbox(s,.75,4.85,11.8,.8,'Interpretation: bounded289 is useful when compact evidence and local changes matter and abstention is acceptable. It is not a universal replacement for full manifests.',18,NAVY,True)
    textbox(s,.8,6.0,11.6,.55,'Receipt/map-audited, not full independent pixel/operator replay. Timings are implementation-specific; abstentions remain in denominators.',12,GRAY)
    footer(s,5)
    # 5 — T1: multi-architecture validation, validation-only.
    s=base(prs,'T1: JPEG70 accuracy–sensitivity paradox across architectures','Fixed cohort • 500 validation images • checkpoints selected by validation BA • no TEST access.')
    table(s,.55,1.4,7.2,2.75,['Model','Intact BA','Intact MEL sens.','JPEG70 ΔAccuracy','JPEG70 ΔMEL sens.'],[
      ['DenseNet121-Base','.7440','.5893','+2.80 pp','−19.64 pp'],
      ['DenseNet121-Aug','.7927','.7679','+2.40 pp','−7.14 pp'],
      ['ResNet50-Aug','.7573','.6250','+3.60 pp','−21.43 pp']
    ],widths=[2.05,1.15,1.45,1.3,1.25],font=11)
    card(s,8.05,1.42,4.55,2.72,'Interpretation','Accuracy rose while MEL sensitivity fell for all three models. DenseNet augmentation attenuated the observed drop; ResNet augmentation did not. This is architecture-dependent validation evidence, not a test or clinical result.',RED)
    textbox(s,.8,4.55,11.6,.78,'Paired Δ balanced accuracy: Base −7.01 pp [−13.04, −1.41]; DenseNet-Aug −1.77 [−6.80, +3.04]; ResNet-Aug −7.34 [−13.03, −1.87].',15,NAVY,True)
    textbox(s,.8,5.55,11.6,.85,'Both augmented models exceeded the prespecified validation BA threshold >0.75. The shared validation cohort was used for checkpoint selection, so these comparisons are descriptive and do not estimate external generalization. Results: deliverables/T1_VALIDATION_RESULTS.md.',12,GRAY)
    footer(s,6)
    # 6
    s=base(prs,'Matched validation: EditGuard localization depends on the operation','Separate 500-image validation return • reported pixel recall by operation • receipt-audited, not replayed.')
    table(s,.65,1.4,5.8,3.5,['Operation','Reported pixel recall'],[
      ['copy32','0.714'],['JPEG70','1.000'],['JPEG95','0.010'],['contrast90','<0.001'],['contrast110','0.049']
    ],widths=[3.2,2.6],font=13)
    card(s,6.85,1.4,5.7,1.55,'Intact-image false positives','Positive localization maps were reported on 310 / 500 intact images (62%).',RED)
    textbox(s,6.95,3.25,5.45,1.45,'Signed4 reader: full pixel recall on the tested tampered cases, but expands failed 4×4 tiles and adds 524,378 bytes per image. This is not an equal-storage comparison.',17,NAVY,True)
    textbox(s,.8,5.35,11.7,.9,'Interpretation: high recall on one operation does not imply broad robustness. The clean general-image checkpoint produced operation-dependent maps and frequent intact positives in this adapted dermoscopy validation setting.',13,GRAY)
    footer(s,7)
    # 7
    s=base(prs,'Evidence matrix: compare contracts, not a single leaderboard','Methods differ in pixel changes and external costs. These adapted studies are not matched-cost SOTA comparisons.')
    table(s,.45,1.35,12.4,3.35,['Method / analysis','Pixel change','External cost','Localization / integrity result','Diagnostic result','Evidence boundary'],[
      ['Full4 signed grid','0','524,378 B / image','Dense tile evidence; local maps','Exact RGB unchanged','Validation receipts'],
      ['bounded289','0','18,620 B / image','Compact; global fine-map abstentions','Exact RGB unchanged','Validation receipts'],
      ['EditGuard','In-band; measured distortion','Model/checkpoint cost','Operation-dependent; 62% intact positive maps','Matched classifier contrasts','Returned validation records'],
      ['T1: three classifiers','None (operators only)','Three classifier checkpoints','Not an integrity method','JPEG70 accuracy ↑; MEL sens. ↓ for all 3','Shared validation cohort'],
    ],widths=[1.75,1.35,1.95,2.55,2.45,2.35],font=10)
    textbox(s,.75,5.15,11.8,.8,'No unified cost budget or matched SOTA comparison has been established. The QIM feasibility stop-gate is retained in the appendix; literature methods are context, not reproduced baselines.',13,GRAY)
    footer(s,8)
    # 8
    s=base(prs,'Conclusion and next gates','A defensible project is clear about what is finished—and what is not.')
    card(s,.65,1.4,5.85,2.05,'Supported by current evidence','• Integrity/localization storage–coverage tradeoff\n• Operation-dependent EditGuard validation findings\n• Class-sensitive JPEG70 effects across three T1 classifiers',TEAL)
    card(s,6.8,1.4,5.85,2.05,'Scope & limitations','• T1 uses one shared validation cohort; replay absent\n• Patient independence unverified\n• No clinical outcome/deployment evaluation\n• No matched-cost state-of-the-art claim',RED)
    bullets(s,.85,4.15,11.7,[
      'Historical v2 test membership is unrecoverable; overlap with the later ISIC holdout is unknown.',
      'Earlier PH2 development and heldout use are documented; exact prior membership is not in the current tree.',
      'We need a genuinely new, provenance-audited cohort and a frozen protocol for future confirmation.'
    ],14,.67)
    footer(s,9)
    # 9 — selected references, explicitly literature-only rather than matched results.
    s=base(prs,'Selected sources and attribution','Sources below provide technical and dataset context; these are not matched-score baselines or evidence of reproduction.')
    references=(
      '[1] DICOM PS3.15, Annex C, Digital Signature Profiles. https://dicom.nema.org/medical/dicom/current/output/html/part15.html\n\n'
      '[2] S. Josefsson and I. Liusvaara, RFC 8032: Edwards-Curve Digital Signature Algorithm (EdDSA), 2017. https://www.rfc-editor.org/rfc/rfc8032\n\n'
      '[3] ISIC 2019 Challenge, Data. Dataset terms and source-dataset attribution apply. https://challenge.isic-archive.com/data/\n\n'
      '[4] X. Zhang et al., “EditGuard: Versatile Image Watermarking for Tamper Localization and Copyright Protection,” CVPR 2024, pp. 11964–11974. https://openaccess.thecvf.com/content/CVPR2024/html/Zhang_EditGuard_Versatile_Image_Watermarking_for_Tamper_Localization_and_Copyright_Protection_CVPR_2024_paper.html\n\n'
      '[5] M. Sander et al., “Watermark Anything With Localized Messages,” ICLR 2025. https://proceedings.iclr.cc/paper_files/paper/2025/hash/c5ee1911dffe4886367eee7fca314235-Abstract-Conference.html\n\n'
      '[6] X. Zhang et al., “OmniGuard: Hybrid Manipulation Localization via Augmented Versatile Deep Image Watermarking,” CVPR 2025, pp. 3008–3018. https://openaccess.thecvf.com/content/CVPR2025/html/Zhang_OmniGuard_Hybrid_Manipulation_Localization_via_Augmented_Versatile_Deep_Image_Watermarking_CVPR_2025_paper.html'
    )
    textbox(s,.78,1.45,11.9,5.25,references,12,DARK)
    textbox(s,.8,6.65,11.8,.28,'Check the complete bibliography, source permissions, and dataset licence before public release.',10,RED,True)
    footer(s,10)
    # 10 — backup evidence: retain the bounded negative pilot without letting it distract from the central study.
    s=base(prs,'Appendix: bounded QIM feasibility stop-gate','Small guide-TRAIN pilot; retain as a negative feasibility result, not the primary contribution. QIM = quantization index modulation.')
    textbox(s,.78,1.38,11.6,.62,'‖y − x‖² = ‖b − x‖² + ‖(y − x)outside carriers‖²',24,BLUE,True,align=PP_ALIGN.CENTER)
    table(s,.7,2.35,7.2,2.15,['Variant','Mean RGB-level MSE','Mean guide KL','Predicted class flips'],[
      ['Fixed QIM','.0666','.000544','0 / 12'],['Weaker QIM','.0164','.000047','0 / 12'],
      ['Guided correction','.5451','.000466','0 / 12'],['Query-matched random','2.7683','.000407','0 / 12']
    ],widths=[2.25,1.8,1.6,1.55],font=11)
    card(s,8.2,2.35,4.25,2.15,'Stop-gate outcome','Guided correction matched fixed output on 11/12. One changed MEL image: MSE .0764 → 5.8181 (~76×); all compared variants still predicted MEL. Strict distortion gate returned fixed output on all 12.',RED)
    textbox(s,.8,4.95,11.8,.85,'Payload: clean recovery receipts passed; JPEG70 bit-error rate ≈50%. Clean success is not compression robustness. This closes the unchanged candidate only; it does not refute diagnostic-aware watermarking generally.',15,NAVY,True)
    footer(s,11)
    prs.core_properties.title='Integrity, Tamper Localization, and Diagnostic Impact'
    prs.core_properties.subject='Dermoscopy integrity/localization comparison; validation development evidence; current holdout non-confirmatory'
    prs.core_properties.author='Project review draft'
    prs.save(OUT);return OUT

if __name__=='__main__':print(build())
