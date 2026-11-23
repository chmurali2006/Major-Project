# Reference starting points

These are research references, not evidence that this implementation reproduces
or matches them. Verify author lists, publication details and dataset licences
before a formal submission. No cross-paper score table is maintained here.

- Yeung and Mintzer, *An invisible watermarking technique for image verification*, ICIP, 1997.
- Wong, *A public key watermark for image verification and authentication*, ICIP, 1998.
- Fridrich, *Security of fragile authentication watermarks with localization*, SPIE, 2002.
- Celik et al., *Hierarchical watermarking for secure image authentication with localization*, IEEE Transactions on Image Processing, 2002.
- PFF-WM, Khaldi et al., 2026 — reference architecture; full bibliographic details require verification.
- WAM — https://arxiv.org/abs/2411.07231
- Zhang et al., *OmniGuard: Hybrid Manipulation Localization via Augmented Versatile Deep Image Watermarking*, CVPR 2025, pp. 3008–3018.
  https://openaccess.thecvf.com/content/CVPR2025/html/Zhang_OmniGuard_Hybrid_Manipulation_Localization_via_Augmented_Versatile_Deep_Image_Watermarking_CVPR_2025_paper.html
- ISIC 2019 — cite the authorised dataset source and applicable licence when reporting results.

The current RGB HMAC fragile carrier is an explicit method amendment. It must not
be described as an exact PFF-WM reproduction. Compare only matched protocols,
mask definitions, sampling, model-selection rules and metric granularity.

## Scope check for the simplified demonstration

- Zhang et al., *EditGuard: Versatile Image Watermarking for Tamper Localization
  and Copyright Protection*, CVPR 2024, pp. 11964–11974.
  [Proceedings and abstract](https://openaccess.thecvf.com/content/CVPR2024/html/Zhang_EditGuard_Versatile_Image_Watermarking_for_Tamper_Localization_and_Copyright_Protection_CVPR_2024_paper.html).
  Proactive watermark-based tamper localisation is already prior art.
- Sander et al., *Watermark Anything With Localized Messages*, ICLR 2025.
  [Proceedings and abstract](https://proceedings.iclr.cc/paper_files/paper/2025/hash/c5ee1911dffe4886367eee7fca314235-Abstract-Conference.html).
  Learned localisation of watermarked regions is also prior art, not a novelty
  established by adding a segmentation network here.

These papers are related work, not matched medical-image benchmark baselines.
The simplified CPU showcase contributes an inspectable implementation and evidence
presentation, not a new cryptographic construction or proven research novelty.
A possible research question remains whether verified-block evidence improves
small-edit pixel localisation over block expansion on matched ISIC splits. It is
unanswered; the current failed learned results cannot support a superiority claim.

## Standards and strongest non-embedding controls

- DICOM PS3.15, Annex C, Digital Signature Profiles:
  https://dicom.nema.org/medical/dicom/current/output/html/part15.html
  The standard already describes signatures for pixel-data integrity. Our RGB
  Ed25519 sidecars do **not** implement those DICOM profiles.
- Josefsson and Liusvaara, RFC 8032 (2017), EdDSA:
  https://www.rfc-editor.org/info/rfc8032/
  Use the cryptography library rather than implementing curve arithmetic; the
  regression suite includes RFC test vector 1. This is not a novel primitive.
- *A Non-Embedding Watermarking Framework Using MSB-Driven Reference Mapping for
  Distortion-Free Medical Image Authentication*, Electronics, DOI:
  https://doi.org/10.3390/electronics15010007
  Related non-embedding medical-image authentication exists. This reference is not
  evidence for that paper's clinical/compliance claims or a matched score baseline.

The defensible research gap must be established by matched experiments, not the
assertion that signatures cannot localise or that combining existing modules is
novel. Digital signatures protect integrity; watermarking is an alternative
packaging/trust trade-off. An external ledger does not itself supply pixel-level
localisation. Image-only versus authentication-guided learning remains unevaluated.

## Verified task distinctions for the next experiment

| Work | Verified scope | Consequence for our claim |
| --- | --- | --- |
| WAM, ICLR 2025 | Watermarked-region segmentation and localised message decoding | Segmentation plus watermarking is not itself new; watermark presence is not our changed-RGB-pixel target. |
| OmniGuard, CVPR 2025 | Proactive/passive localisation with degradation-aware extraction | Adding degradation inputs or a hybrid network is not a sufficient novelty claim. |
| DICOM PS3.15 | Signature profiles for pixel-data integrity | Do not claim signatures cannot authenticate medical images. Our RGB sidecars are not a DICOM implementation. |

The next decision is empirical: first establish trainability, then compare identical
image-only and authentication-guided networks against block expansion. Keep strict
lossless integrity separate from robustness-to-compression tasks. No evidence yet
shows our candidate guidance is novel, generalises, or adds a useful benefit.
