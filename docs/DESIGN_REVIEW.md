# Design notes

> **Current status overlay — 2026-10-19 UTC:** this file is a long, partially append-only protocol-v2 design/experiment log, not the project-wide status source. T1 is a separate classifier study completed on TRAIN/validation only; see `deliverables/T1_VALIDATION_RESULTS.md`. The historical `isic-study-v2` test membership is unrecoverable, the later holdout is non-confirmatory and closed, and old `heldout` commands are revoked by `FREEZE_PROTOCOL.md`. Follow `PROJECT_CONTEXT_MASTER.md` for cross-strand state. Any later-dated receipt timestamps remain unauthenticated.

## 1. Current method

[Protocol v2](../PROTOCOL_V2.md) defines the RGB HMAC carrier, evidence channels,
labels, decision fitting and matched constituent removals. Code and runtime
contracts determine the executed settings.

## 2. Retired design

Legacy Haar profiles have demonstrated brightness-period and luma-preserving
colour collisions. They remain available only for labelled historical probes.
The default profile replaces that fragile carrier; old results are not v2 results.
Original check outputs remain in `deliverables/verification-evidence/` as JSON.

## 3. Checks

Run the tests and source-first probes in [RUNNING.md](../RUNNING.md). Authentication,
synthetic training and CPU recovery checks are not clinical or full-study evidence.
Read the source fingerprint on saved outputs; do not relabel old checks.

## 4. Reporting

Keep negative outcomes. Distinguish strict block authentication, statistical pixel
localisation and experimental learned/count/abstention predictions. No matched
paper comparison, adaptive-attack resistance or clinical approval is established.

## 5. Open questions

- Independent security/composition review of the RGB carrier and its key handling.
- Deployment trust and freshness: secret keys, expected image/version identifiers,
  and prevention of valid old-block replay require an external trusted workflow.
- Full ISIC three-seed, constituent and held-out results, including negative
  effects, key-change behaviour and empirical selective-risk gates.
- Whether physical carrier-removal experiments are required beyond feature
  removals; changed protected pixels need a separately declared evaluation.
- T4 sanity execution is now observed. Strict CUDA attention backward, GPU
  recovery, full-profile runtime and VRAM remain unverified.
- Why localisation and block-count operating points diverge: the 20-epoch
  synthetic TRAIN-only diagnostic still has zero pixel IoU at the shared fitted
  boundary. Whether the models can memorise actual ISIC training images is open;
  do not change the frozen decision rule or tune on the seven test images.
- Authorised complete inputs, patient/lesion identifiers and group independence.
- Clinical preservation, novelty and literature parity; fidelity alone proves none.

- Whether embedded authentication has an application advantage over signed tile
  manifests after accounting for zero-distortion alternatives, external-evidence
  storage and asymmetric versus shared-secret trust; no preferred winner assumed.
- Whether learning improves sub-block localisation over block expansion and an
  image-only control. Digital signatures, tile hashing and segmentation are prior
  art; a new research contribution has not yet been demonstrated.

- Distinguish learned authentication guidance from trivial post-masking: a future
  revised study needs an image-only network with the same final authentication
  mask, not only an ungated image-only control. This amendment is not yet run.

## Published-baseline execution, 2026-10-19

- New active base 3f34ed3 contains signed8 but not earlier session's uncommitted
  refiner/utility modules or variable-grid API. Current results/tests certify this
  checkout only; no prior 405-test or signed4 certification is carried forward.
- Retrieved official EditGuard clean checkpoint through its README Drive link;
  37760088 bytes, MD5 matches Drive metadata. No weights or third-party model code
  added to Git. Strict state load successful after matching upstream parser's
  top-level scale override; the earlier mismatch was preserved in execution ledger,
  not bypassed with strict=False. Device-only inverse-wavelet allocation and unused
  BasicSR-import removal are recorded, along with original model-source hashes.
- Executed full paired inference on 2 synthetic phantoms and 1 separately reported
  upstream example. Example was explicitly converted RGBA->RGB (alpha182..255
  discarded without compositing), no resize. Not ISIC/medical evidence. Fixed
  published clean threshold .2, no test tuning. 3 methods ×6 scenarios ×3 sources
  =54 case maps; independently recomputed confusion/IoU/hash checks passed.
- Evidence is mixed, not a new superiority claim: phantom0 replacement64 IoU
  EditGuard .8111 vs classical .7901, copy64 .8937 vs .7901; EditGuard misses64/1
  pixels respectively vs classical0/0. EditGuard misses the one-bit and brightness
  edits (IoU0), classical .015625/.64. EditGuard intact FP1/0 on the two phantoms;
  original example FP8. Clean checkpoint JPEG masks cover all pixels; cannot infer
  degradation-checkpoint performance. Phantom0 PSNR30.329dB vs HMAC51.139dB; signed8
  MSE0 but requires external evidence. Different contracts/trust models preclude
  declaring one universal winner. All per-case failures retained in receipts.
- Outputs: deliverables/editguard-execution-audit.html and verification-evidence/
  editguard-{adapter-audit-v1.json,synthetic-smoke-v1/,upstream-example-v1/}.
  Numeric maps (~3MiB) retained, no input image pixels committed. Latest full suite
  315 passed, 1 CUDA-only skipped (29.27s); targeted10 passed after report assertion
  tightening. CPU only; no Kaggle GPU spent. Real ISIC paired study and official
  AGE-Set/AIGC reproduction remain unrun. OmniGuard source/checkpoint links found,
  not executed; EditGuard chosen as the first successfully runnable baseline.

## Real-image mirror feasibility pilot, 2026-10-19

- Executed a deterministic 8-image pilot, one per mirrored diagnosis, with fixed
  EditGuard clean threshold0.2 and identical operators/seeds across three methods.
  Selected before model access by SHA256(seed29/image_id) ordering; no replacement
  of difficult examples. All input/output hashes and preprocessing retained.
- Image mirror pinned b9a0b64 (Sushma7890creator/ISIC-2019-dataset), label mirror
  pinned58db7e4 (UdaykiranReddy-1/FedExBC). Five CSVs:25328 rows,20455 unique IDs,
  4873 duplicate rows, no conflicting labels detected. This is NOT the full official
  ground truth. Selected images are already224px; converted RGB and nearest512
  explicitly. No official pixel identity or patient/lesion grouping verified.
  Source/native diagnostic fidelity and redistribution rights remain unverified.
- 144 case maps (8 images ×3 methods ×6 cases) independently recomputed from
  durable numeric NPZ files; all counts, IoU, truth/map hashes matched receipts.
  Original/prepared image pixels remain outside repo. Exact prepared input set/
  file-hash mismatch aborts before checkpoint loading. Summary reports no CI or
  population inference; rare-class n1 is not per-diagnosis performance evidence.
- EditGuard vs classical meanIoU: replacement64 .835100 vs .802469; copy64
  .763521 vs .802011 (includes one EditGuard zero-IoU copy failure, retained).
  EditGuard missed528/4136 pixels respectively, classical0/0. One-bit and brightness
  EditGuard IoU0 vs classical .015625/.66. Intact EditGuard145 highlighted pixels
  total across8 images, classical0; any-pixel positivity8/8 is explicitly NOT a
  calibrated paper image-detection rule. Mean PSNR31.572 vs51.141dB. Signed8MSE0
  but external trust/storage. JPEG separate, no degradation-checkpoint claim.
- Durable receipts/maps: verification-evidence/editguard-isic-mirror-pilot-v1/.
  Viewer: deliverables/editguard-isic-mirror-pilot.html. Full suite322 passed,
  1 CUDA-only skip,29.54s. No GPU used. Renderer footer was clarified after the
  numerical run; original run source hash remains unchanged and honest. Actual
  native-original, grouped held-out ISIC study and SOTA superiority remain unproven.

## Local attached-data execution path, 2026-10-19

- Implemented local input preparation recording pre-resize dimensions and file/
  decoded-RGB hashes; requires explicit supplied patient_id or lesion_id metadata,
  or acknowledged image-only fallback. No invented patient IDs. Prior evaluation
  IDs exclude entire supplied groups; at most one selected image per group across
  the pilot. Fixed hash-order selection precedes decoding/model access. Fail closed
  on missing labels/images/groups, ambiguous stems and selected decoded duplicates.
- One-command wrapper preserves preparation selection order (not shell glob order),
  and binds exact prepared hashes through the paired runner. Original pixels stay
  untouched and outside repo. Optional prepare-only tested via real subprocess
  using generated, variable-dimension RGB fixtures. No fixture result is diagnostic
  evidence. Group IDs remain user-supplied/unverified, not automatic independence.
- Built separate `deliverables/editguard_local_isic_pilot.ipynb`: SHA-bound own
  source ZIP, pinned external upstream clone, attached checkpoint path, explicit
  data/preprocessing/grouping configuration, default CPU inference, export of numeric
  receipts/maps only. No upstream code/weights or dataset pixels embedded. Known
  8 mirror-pilot IDs prepopulated as exclusions; not a complete historical exclusion
  ledger, and user must add other development IDs. Frozen notebook untouched.
- Full regression329 passed,1 CUDA-only skip,34.63s. All notebook Python cells AST
  parsed; embedded archive hashes/file bytes independently matched source. Local
  prepare-only wrapper passed. Actual Kaggle execution, native-original provenance,
  grouped held-out results and SOTA superiority remain UNVERIFIED; notebook is not
  claimed environment-equivalent to local tests. No new GPU or inference run.

## Returned-results audit stage, 2026-10-19

- Added bounded, non-executing ZIP/directory ingestion. Recomputes counts/IoU/F1/
  missed fractions/highlight positivity from saved arrays; validates declared file
  hashes, original prepared-selection binding, shared decoded source per method,
  paired operator seeds, intact truth and score-mask consistency at fixed .2.
  All methods/cases required; missing/worse results cannot be silently omitted
  relative to the declared preparation selection. No source truth/authorship proof.
- ZIP path traversal/unexpected files, duplicate JSON keys, nonfinite numbers,
  object arrays and oversized NPY shapes fail. Members are never extracted and
  included HTML is never executed. Per-family paired source IoU differences report
  defined-pair counts, not a global winner or unsupported population confidence.
- Executed on durable8-image mirror pilot: all144 cases recomputed. Copy64 shows
  EditGuard higher IoU on7/8 images yet mean paired difference -.03849 due one
  severe failure; replacement64 higher on6/8, mean paired difference+.03263.
  This is why wins alone cannot support superiority. Small-change results and
  intact highlights retained, JPEG separate. No threshold fitting or model rerun.
- Full suite350 passed,1 CUDA-only skip,28.67s; actual notebook-layout ZIP and CLI
  exercised against executed fixture receipts, including tamper rejection tests.
  Existing notebook/Drive file unchanged while user runs it. New audited receipt:
  verification-evidence/editguard-mirror-independent-audit-v1.json. Main viewer:
  deliverables/editguard-independent-map-audit.html. Kaggle ZIP still awaited.

## Kaggle DATA=None configuration failure correction, 2026-10-19

- User log showed a configuration ValueError, not model inference failure: DATA
  remained None. Earlier notebook allowed dependency setup/upstream clone before
  reporting this. Added stdlib-only unique attachment resolver with explicit-path
  override, ID coverage/duplicate checks, actionable clean.pth link/checksum check,
  and preflight before package installation/network/model execution. No guessed
  slug, patient grouping or silent fallback. Missing grouping needs explicit weaker
  image-level acknowledgement or supplied documented metadata.
- Rebuilt separate pilot notebook only; frozen study unchanged. Bootstrap now
  uses archive-hash-specific CODE directory and can rerun identical extraction;
  edited existing source fails rather than being overwritten. Prior results remain
  protected by new-OUT requirement. Local notebook bootstrap and preflight cells
  actually executed with temporary attachment fixtures; false/true grouping gate
  and ambiguity/missing/changed checkpoint paths tested. No installs/clones/models
  executed in those fixture tests; actual Kaggle replay remains unverified.
- Full regression357 passed,1 CUDA-only skip,40.06s. Fix addresses the supplied
  traceback and likely next attachment errors without claiming training completed.

## Returned actual Kaggle pilot, 2026-10-19

- Downloaded Drive editguard-local-pilot-results.zip, file1epY0i3Y7lBMuzpneNuWb5C1UCVUfupt5,
  6793697 bytes, SHA256 b34616f872aa4565dc56374cef51f41e9b985e5228fb5b38bda012d4ad24be6f.
  CRC passed,27 members. Report complete; top-level and embedded preparation match.
  All144 case metrics independently recomputed; declared map hashes/threshold/source
  matching passed. This verifies internal consistency, not original-pixel authenticity.
- Actual environment reports Py3.13.18,Torch2.11.0+cpu,two threads.25331 labels,
  EIGHT evaluated images, one per class.5 sources1024² and3 sources600×450, explicit
  nearest512 prep. Image-only grouping acknowledged; no patient independence or
  held-out statistical claim. Mirror8 prior IDs excluded; no complete lifetime
  development-exclusion claim. Original identity remains unverified.
- EditGuard/classical meanIoU: one-bit0/.015625;brightness0/.66;
  replacement .8488137008/.8024691358;copy .7707484972/.8024691358.
  EditGuard missed962 replacement pixels and4145 copy pixels; classical0/0.
  EditGuard intact38 false-highlight pixels over6/8 images, classical0. Any-highlight
  rule is not paper-calibrated image detection. Mean per-image PSNR29.0423 vs51.1381dB;
  signed8MSE0 with external evidence/trust cost. EditGuard mean recorded localisation
  6.405s vs classical.0415s; descriptive single-run CPU measurements only.
- Copy failure ISIC_0058884: all4096 target pixels missed; max target score.0392157
  below fixed.2. This observed failure is not only near-threshold boundary pixels.
  No threshold retuning performed. JPEG remains separate: high changed-RGB IoU
  under recompression is NOT evidence of benign-processing tolerance/robustness.
- Preserved raw numerical ZIP, report/preparation/audit/provenance and failure-score
  diagnostic. Viewer deliverables/kaggle-editguard-results-audit.html. Full regression
  358 passed,1 CUDA-only skip,45.99s,including returned-ZIP regression. No assistant
  model/GPU rerun. Results support a measured trade-off, not SOTA superiority,
  clinical safety, learned-model advantage or a new research contribution.

## Executed security showcase extension, 2026-10-19

Implemented linked signed-evidence control beside existing classical watermark
showcase.14 actual signed-control scenarios pass on a512-square procedural
fixture, including missing/altered/swapped evidence, missing/wrong trusted key,
same-ID content swap, new-version replay rejection and old-version replay
acceptance. Invalid evidence never supplies a localisation map. Original RGB
is not passed to verification. No learned estimates are displayed.

Synthetic run signed-grid sidecar274697bytes; measured, not hidden. This detached
hash evidence has different storage/trust assumptions than the embedded watermark.
No private key exported. No new cryptographic construction/security proof claimed.
Numerical receipts: deliverables/verification-evidence/security-showcase-v1/.
Pixel-bearing HTML/PNGs remain outside Git at /tmp/integrity-security-showcase-v2.
Full regression360 passed,1CUDA-only skip47.75s; after final synthetic-scope HTML
label change,59 focused showcase/signature tests passed1.00s and CLI regenerated
successfully. No real-data benchmark, GPU training, or frozen-study changes.

## Gated metadata audit / bounded follow-up, 2026-10-19

Implemented dependency-free CSV coverage/group-size/exclusion audit. No metadata
provided in sandbox: actual Kaggle grouping remains UNKNOWN, not audited as complete.
Duplicate metadata IDs rejected; blank patient IDs never become invented patients.
Separate source-bound followup32 notebook defaults RUN_EVALUATION=False and writes
then stops at metadata audit before package installs/inference. User supplies
metadata path and documented field explicitly. Known16 prior image IDs from both
pilot receipts excluded; supplied groups also excluded by existing preparation.
No claim that this ledger includes every historical development image.

Four/class (32 images) remains the existing bounded pilot preparation maximum;
not a powered/full-study or population superiority evaluation. Existing threshold.2,
nearest512 and six cases unchanged. Exact configuration hash persisted before
execution with labels/metadata/source hashes, exclusions and scope. No independently
timestamped preregistration claim. Config/audit download separately from strict
results ZIP. No changes to existing pilot notebook or frozen study.

Actual preflight code executed with fixture/mocked attachment resolution: writes
metadata_missing and stops before installs/models. Notebook source archive hashes
and all code ASTs tested.364passed,1CUDA-onlyskip30.89s. No actual Kaggle metadata
or32-image execution occurred here. Drive notebook1ltF2QZ0M49Nu1c1CDkGtlyDx3EFP1SQm.

## Follow-up protocol gate implemented while Kaggle runs, 2026-10-19

Added separate companion-config checker plus CLI invoking existing independent
map audit only after declaration checks. Rejects label/metadata hash mismatch,
seed/threshold/case drift, changed exclusion set, known prior ID omission,
wrong sample/class counts, repeated selected groups, and unacknowledged image-only
scope. Lesion grouping never relabelled patient grouping. No original source
provenance or independently timestamped registration claim. Source archive hash
has a different domain from runtime repository source digest; equality between
those is deliberately NOT asserted as an execution attestation.

12 tests cover valid image-level/supplied-lesion scope and ten drift scenarios.
Full376passed1CUDA-onlyskip54.28s. CLI actually exercised against earlier8-image
ZIP plus fixture companion config: correctly rejected preparation count mismatch,
no output created. No actual32-image result received yet; no performance numbers
invented. Existing Kaggle notebook and running configuration left unchanged.

## Failure/cost ledger completed while follow-up runs, 2026-10-19

Implemented descriptive ledger derived only from independently recomputed rows:
changed-source denominator, any missed pixels, complete target misses, total
missed/extra pixels and worst three sources by missed fraction per method/case.
Empty truth never counts as a complete miss. Complete means zero true-positive
pixels, not zero total highlights. JPEG retains its benign-lossy family, never
pooled into edit successes. No population rates or confidence intervals.

Follow-up audit now appends the ledger plus submitted-run setup/localisation
costs, per-image PSNR/MSE and sidecar bytes. Missing records stay unavailable;
sidecar does not include key/model/transport costs. Timings are NOT independently
reproduced measurements. No inference execution or submitted timing authenticity
is certified. Standalone report generated on already audited actual8-image pilot:
deliverables/kaggle-editguard-failure-cost-review.html; numeric ledger kept beside
its old receipts. Report preserves catastrophic copy miss ISIC_0058884 and all4145
missed copy pixels. It is not the pending32-image result.

Full379passed1CUDA-onlyskip38.36s before adding MSE/storage display columns;
15focused ledger/protocol tests passed after columns, existing receipt rendering
executed successfully. Running notebook/config left unchanged. Real grouping
metadata,32-image outcomes, independent diagnostic classifier validation and any
novel learned-model advantage remain unresolved; none fabricated here.

## Returned32-image follow-up

Drive12n4dF5TeeOPWY_mJQ9KHzb_ED_EgXqyo downloaded28516982bytes; ZIP SHA256
95993122195258ab4c99b5d599d44921c99edff1e4558f363600b2f28551f9fb.
Companion JSON reconstructed from user-pasted contents, not claimed byte-identical
to downloaded originals. Protocol checker and independent saved-map audit passed
576cases.32images/four per class, image-level only, known16prior IDs excluded.
Receipts deliverables/verification-evidence/followup32-v1/. No new inference.

EditGuard/classical meanIoU: one-bit0/.015625;brightness.000030281/.6975;
replace.854854648/.824845679;copy.633339734/.824827595. EditGuard missed4497
replacement and37063copy pixels; seven complete copy target misses. Classical
missed0 for these edits. EditGuard intact301extra pixels across24/32images;
classical0. Mean per-image PSNR31.6115/51.1405dB. Submitted CPU localisation
8.4973/.06977s per call; not independently timed. Signed8zero embeddingMSE,
274697byte sidecar per image. JPEG separate, not benign-tolerance certification.

Evidence supports strict small-change authentication versus learned spatial
precision trade-off, not universal superiority/SOTA or clinical safety. These
outcomes do not validate failed learned refiners or justify blind training.

## Fixed-strength finer-grid control executed

Implemented separate experimental4x4/8x8 domain-separated HMAC grid control.
Both carry192tag bits/block:4LSBs/channel at4x4 versus1at8x8. Existing classical
scheme untouched. All eight input bitplanes tested, wrong key/version, relocation,
geometry and input immutability. Full384passed1skip31.58s before adding optional
hash-validated preparation loader. No formal security proof/novelty claimed.

Executed four synthetic512-square fixtures, six cases/grid,48case measurements:
8/4grid meanPSNR51.14395/31.84984dB; onebitIoU.015625/.0625;
brightness.68/.842593;replacement.814815/.914360;copy.814381/.914306.
Zero missed pixels for these edit cases in both controls. These are synthetic
engineering observations, NOT medical benchmark evidence or SOTA superiority.
JSON deliverables/verification-evidence/fixed-tag-grid-synthetic-v1.json.
Runner supports existing hash-bound preparation.json/PNG outputs for next real-data
comparison without rerunning EditGuard. Real-data execution not yet performed.

This control demonstrates why simply shrinking blocks is not sufficient novelty:
it improves spatial precision with a large embedding distortion cost. Any proposed
method must be compared against this explicit strength/distortion trade-off.

## Same32-source grid notebook ready

Built source-bound grid_control32.ipynb; Drive1hWgLJJTi-DAJ7TJsFremMkAWDTCF7yVA.
Selection/order embedded from actual returned followup32 preparation; no resampling.
Source file/decoded RGB and prepared RGB must match; duplicate hash-matching source
paths rejected rather than guessed. PNG encoder differences recorded, never used
to excuse changed RGB. New OUT, numeric-only ZIP, no EditGuard/checkpoint/training.

Actual notebook preparation cell executed against fixture source; actual non-synthetic
loader branch and both grid evaluations executed; tampered-file and overwrite
rejection tested. This is fixture testing, not real32-image execution. Full suite
386passed1CUDA-onlyskip30.14s. Existing pilot/followup notebook untouched.

## Direct2026 literature check: PFF-WM (read publisher method/results)

Primary: Khaldi et al., “Explainable and proactive fragile watermarking for medical
Deepfake detection”, Intelligent Systems with Applications31(2026)200684,
DOI10.1016/j.iswa.2026.200684.
https://www.sciencedirect.com/science/article/pii/S2667305326000591
Read publisher sections3.1–3.6,4.1–4.8,Tables2–13 and data availability. Not just
abstract or inherited summary. Publisher data availability: “Data will be made
available on request.” Targeted title/PFF-WM/GitHub search did not locate verified
author code/weights. This is not proof none exists. No author implementation run.

Important novelty restriction: DWT fragile + attention-guided DCT reference,
authentic-only stacked AE, lightweight refinement and classifier-gradient clinical
explanation are already claimed here. We cannot call that combination our novelty.
Paper3.4 explicitly uses RefineNet on E,A,Downsample(I); whether receiver I is original
or received needs clarification. AE authentic-only claim must be distinguished
from full pipeline3.6 detection BCE and synthetic attack/mask supervised training.

Metric attribution: Table2 accuracy97.6%,AUC.989 is CHEXPERT. Table4 IoU.832±.015 is
LiTS500manipulated images, NOT our ISIC test or an ISIC localisation target.
Section4.8.7 reports ISIC detection97.1%; exact split IDs/grouping not established
from inspected text. Section4.1.1 uses2500ISIC images,60/20/20split; not our32image
subset. Table13 full44ms is512grayscale A100 and includes explainability; no
comparison against our CPU timings. Table8 benign JPEGQ85 FPR.2%,Q70.4%,chain.7%
is a semantic-tamper decision, not exact-RGB integrity. Our JPEG fragile failure
cannot be called a robustness win against this operating contract. No cross-table
numerical superiority claim. No CheXpert/LiTS runs proposed or authorised.

Reproduction ambiguities, not allegations:
- Eq4 spatial softmax sums1; Eq16 uses A>.1. At most9locations can pass strictly,
  uniform512attention leaves empty ROI. Actual gate/normalisation needs code.
-3.2.4 gives258048available3level grayscale detail coefficients;3.3 describes
  64*65536=4194304fragile bits as subset. Feature reuse versus independent payload
  is unresolved; Table5 units64kbits differ from per-location64channels.
- Eq10 lower/upper=.15/.35*512 yields76.8..179.2; local8x8DCT u+v<=14, empty
  literal band. Need actual index scaling before implementing a reproduction.
Arithmetic checked locally; durable numeric evidence pff-wm-literature-arithmetic.json.
No claim that ambiguities disprove published experiments. Do not silently fix them
and label our implementation “official PFF-WM”.

Other relevant primary works located, not reproduced:
Arham et al., “Reversible watermarking for medical images using ROI-based tamper
localization and recovery”, Franklin Open15(2026)100545,
DOI10.1016/j.fraope.2026.100545,
https://www.sciencedirect.com/science/article/pii/S2773186326000617 .
Publisher title/abstract/outline inspected: ROI/RONI recovery/reversibility contract,
not equivalent to our irreversible RGB HMAC. Full method still to review.
“Secure and reversible fragile watermarking for accurate authentication and tamper
localization in medical images” (2025),
https://www.sciencedirect.com/science/article/abs/pii/S0045790625000151 .
Publisher search abstract reports4x4DWT/DFT control; full implementation, rounding,
bitdepth, recovery and PSNR reference not verified. Reported>88dB cannot be compared
against our integerRGB before checking conventions. This further rules out claiming
small blocks alone as novelty. DeepMark DOI10.1016/j.ipm.2025.104600 located in
PFF-WM bibliography; must independently read/verify before treating as runnable SOTA.

Decision: retain paper-reported literature results separate from reproduced
EditGuard and our controls. Current differentiator is explicit exact authentication
versus semantic localisation with distortion/security trade-offs, still not proven
novel. A new method must demonstrate added value against both learned and simple
grid controls under a matched protocol; no next blind refiner training justified.

## Returned real32-image fixed-strength grid control

Downloaded Drive1rX7kentJGogb7t9kEdCWwZOu45GknuXX,46078bytes,
ZIP SHA256 c098d5b20273672aafd5f94e35f64d6735ab156f9e27c553354756ad4ee50143.
64method/source rows,384cases. Original followup32 selection/order and RGB/source
hashes matched; only prepared PNG encoding hash allowed to differ. Receipt
confusion/IoU/F1 arithmetic, seeds,192bit declaration and PSNR/MSE consistency
checked. ZIP has numeric receipts ONLY: no independent prediction-map recomputation
or actual execution attestation claimed. Raw receipts/review preserved under
verification-evidence/grid-control32-v1/. Still image-level, not patient independent.

8/4 meanPSNR51.141929/31.730767dB,meanMSE.499905/43.747449,max channelchange1/15.
OnebitIoU.015625/.0625;brightness.6975/.847222;replace.824846/.917388;
copy.824808/.917388. Zero missed edit pixels and zero intact false highlights in
both returned control receipts. Mean copy verification.08569/.35172s, submitted
CPU measurements only. JPEG separate: no benign-tolerance success claim.
Existing classical versus grid8 uses different domains/tags, not byte-identical
protected images; do not silently substitute receipts. Fine grid now established
as real-image control, not a proposed novel method or clinical safety result.

Stopped both assistant-owned preview processes (static8080 and interactive8081)
at user request. Follow-up ps check found no matching preview server processes.

## Compact binary signed-grid implemented/executed

Separate versioned Ed25519/SHA256 baseline supports4/8grids, fixed26byte header,
raw32byte digests,64byte signature. Invalid evidence/key/version/grid/geometry,
truncation/extension and tampered payload/signature return CANNOT_AUTHENTICATE
with no map. Exact changed signed pixels return FAILED_INTEGRITY and block map.
No source RGB needed by verifier; trusted public key/version external. Old valid
pair still verifies at accepted old ID. Standard primitive composition, not new
cryptography/security proof. Existing JSON8grid and classical watermark untouched.

Executed4synthetic512fixtures x2grids x6cases =48cases. Zero embeddingMSE,
zero missed edit pixels; storage8grid131162bytes,4grid524378bytes, not JSON savings
mislabelled as research novelty. Numeric receipts binary-grid-synthetic-v1.json.
These are fixtures, not real32-image outcomes. Full399passed1skip32.87s, then
14focused binary tests passed after adding actual benchmark/notebook AST test.
No background servers started. Exact32source notebook binary_grid32.ipynb uploaded
Drive1UlfvINtPaEsaXsGtU5_h0T6cIfAT5rmg; real run pending. No original pixels in repo.

## Returned binary signed-grid real32-image run

Drive1UoD2Zp2hrvX91oSEfNaIN9WO0oXyAUJC34339bytes;
SHA256122ec50926cc800b8ebfa1095cb0ec619886c9ca3f11522417e0441017053fd9.
Same32sources/order and original/prepared RGB hashes matched earlier followup;
384case receipts checked for pairing, confusion/IoU/F1 consistency, zeroMSE and
format-predicted manifest length. No prediction maps, source pixels or actual
binary manifests in ZIP: not independent map/signature execution verification.
Raw receipts/review deliverables/verification-evidence/binary-grid32-v1/.

8/4grid sidecar131162/524378bytes; no embedding changes; zero missed edit pixels
and zero intact highlights in reported cases. MeanIoUs onebit.015625/.0625,
brightness.6975/.847222,replace.824846/.917388,copy.824754/.917284.
Submitted mean copy verification.02000/.05046s; not cross-run hardware benchmark.
JPEG remains exact-pixel change test, NOT benign semantic tolerance. Same source
inputs but embedded-grid reference pixels differ; copy truth/IoU differs slightly.
This is a standard signed-grid baseline, not novelty or a SOTA superiority claim.
No patient/lesion independence, clinical safety or recovery result inferred.

## Sparse authenticated reconciliation feasibility executed

Implemented src/sparse_refinement.py: signed fixed-size IBLT-style sketch of
(index,SHA256tilehash) entries, plus signed commitment to entire ordered leaf
vector. Receiver subtracts own sketch, peels differences and reconstructs original
leaf vector. A fine map is exposed ONLY after reconstructed commitment matches;
nonempty residual/mismatched pairs/root/over-capacity return FAILED_INTEGRITY,
fine map unavailable. Untrusted/missing/context-mismatched evidence returns
CANNOT_AUTHENTICATE. No original pixels used by verifier, no embedding distortion,
no freshness guarantee or formal security proof. Missing fine map is NOT a pass.
This prototype is a detached alternative, not an invented reason to add a watermark.

Known prior art: Eppstein/Goodrich/Uyeda/Varghese2011 Difference Digest,
https://dl.acm.org/doi/abs/10.1145/2043164.2018462 ; Goodrich/Mitzenmacher2011 IBLT,
DOI10.1109/ALLERTON.2011.6120248. Set reconciliation, XOR peeling and sparse-difference
communication are established. Signed-root composition is not asserted novel.
Focused image-specific prior-art comparison still needed before contribution claim.

Executed3synthetic512fixtures x3budgets x7cases=63decodes, raw numeric receipts
sparse-sketch-feasibility-v1.json. Buckets128/512/2048 =>7294/28798/114814bytes,
INCLUDING header+root+signature. All intact and one-bit maps correct3/3 per budget.
25changedtiles:2/3,3/3,3/3.64distributedtiles:0/3,3/3,3/3.
289changedtiles(unaligned64square):0/3,0/3,3/3.
1024distributedtiles and whole-image changes:0/3fine maps at ALL budgets;
all return failed integrity, not false acceptance. No exposed map disagreed with
truth in this finite probe. These are development fixtures, not medical results,
not a guaranteed decoding capacity, attack robustness proof or SOTA claim.
2048bucket budget is78.1% smaller than524378byte4grid, but with incomplete decoding
coverage. This trade-off must not be advertised as unconditional dominance.

Nine tests include wrong key/version/evidence, overcapacity, root-mismatch even
with peelable table, and12random edit patterns with no incomplete exposed map.
Full409passed1CUDA-onlyskip29.84s. No Kaggle/GPU request or background process.

## Sparse capacity sweep and same-source development runner

Executed180decode trials:5randomRGB512inputs x3budgets x6counts x2patterns.
Fixed single-channel-bit changes at16/32/64/128/256/512distinct4tiles; clustered
and distributed locations.128buckets decoded16/32tiles5/5 for each pattern,
64+0/5.512buckets decoded through128tiles5/5,256+0/5.
2048buckets decoded through512tiles5/5. All exposed maps exact; zero false accepts
in finite trials. Not a guaranteed capacity, worst-case/adaptive-adversary proof,
or population failure probability. Initial feasibility already showed a25tile
failure at128buckets: do NOT advertise the sweep's32tile5/5 as a universal bound.
Each changedtile creates TWO reconciliation entries, old/new hashes.
Raw evidence sparse-capacity-development-v1.json contains all failures/denominators.

Implemented separate same32source development runner at3fixed budgets,6operators,
576cases, unavailable localisation metrics remain null (not0misses); all-case
coverage explicitly printed. Prototype has no embedding and needs no secret
watermark layer. Real32execution pending; fixture runner executed18cases locally.
Notebook sparse32_development.ipynb uploaded Drive1P9CC_abXqM-GYvpYBVuoUW_puG-NWXss.
Full412passed1CUDA-onlyskip33.37s. No GPU request/background process or frozen
study change. IBLT/signed-root composition remains standard-control research probe,
not an established novel contribution; image-specific prior-art gate unresolved.

## Returned real32 sparse-sketch development experiment

Drive131dZsN1QyecmINxLTT-n5i3u9mSKqklz22731bytes;
ZIP SHA256bf61496affad2a3be5e9f779d04a758f64c68f3b152c6d9871cacc135896ba7d.
576rows verified for exact32selection/source hashes,case/seed completeness,
byte formula and available-map metrics against previous signed4grid receipts.
No sketch/map/source artifacts in ZIP: consistency only, not re-decoding attestation.
Raw receipts/review verification-evidence/sparse32-development-v1/.

7294byte budget:32/32onebit maps;0/32brightness/replacement/copy/JPEG.
28798bytes:32/32onebit/brightness;0/32replacement/copy/JPEG.
114814bytes:32/32each onebit/brightness/replacement/copy;0/32JPEG.
All32intact verified at all budgets; all changed cases failed integrity even
when fine map unavailable. Exposed map matches truth declared true; available
IoUs match binary4grid:onebit.0625,brightness.847222,replace.917388,copy.917284.
114814bytes saves78.1% vs524378bytefull4manifest on tested edit coverage only;
JPEG changed14806..16384tiles and all fine decoding failed. No all-case dominance.
Submitted replacement verify.09864s at2048budget vs prior fullgrid.05056s;
descriptive cross-run numbers, NOT controlled speed comparison. No distortion.
This establishes useful sparse operating range, not novel mechanism or final
heldout/patient-independent proof. Need prior-art/stronger compressed-reference
controls before any new-method claim. No further dataset run launched here.

## Stronger shortened-reference/compression controls executed

Implemented signed per-tile truncated fingerprint control with separate fullSHA256
ordered-leaf commitment, zero embedding. Integrity verdict does not depend on
short fingerprints; maps explicitly estimated/not certified complete. Counts:
4x4at512square,8/32/64/128/256bitfingerprints =>16507/65659/131195/262267/524411bytes
including header/root/signature. No claim different lengths have equal localisation
security.256bitfull-length variant conservatively retains same API flag; it is not
an argument that fullSHA256digest lists intrinsically lack completeness.

Executed3syntheticimages x5lengths x6operators=90cases.8bit183missedtiles,
32/64/128/256zeroobserved misses on ordinary fixture edits. This is NOT adaptive
attack resistance. Constructed8bitcollision in241attempts: onechangedtile,
zeroestimatedhighlights, FAILED_INTEGRITY via fullroot. Never a falseverified image.
6tests cover context/signature, bit lengths and collision distinction. Full418pass,
1CUDA-onlyskip32.77s. Numeric evidence fingerprint-control-v1.json.

Compressed fullsigned4grid via zlib9:524378 ->524544bytes for all3fixtures, not
compressible in this probe; doesn't prove all evidence encodings incompressible.
At64bitfingerprints131195bytes is only modestly larger than114814sparse sketch
and has no sparse-decoding cliff, but lower per-tile attack work factor than full
hash/root-checked complete reconciliation. Thus earlier78%reduction versus256bit
manifest does NOT establish best available tradeoff.32bit65659bytes may look
better on ordinary edits but must not be passed off as equally secure.

Prior-art targeted search found generic robustLSH+IBLT reconciliation (Mitzenmacher/
Morgan arXiv1807.09694), ratelessIBLT implementations referencing arXiv2402.02668,
and2015IBLTsync file-synchronisation thesis. These are further reasons NOT to
claim sparse difference reconciliation, adaptive retries or arbitrary file/image
application alone as novelty. No exhaustive image-specific novelty clearance.
No new Kaggle request/background process. Next contribution gate remains a
specific algorithmic or evaluation advance over these standard controls, not
another benchmark repetition of established IBLT machinery.

## Authenticated coarse fallback control implemented/executed

Extended binary signed-grid accepted block set4/8/16/32; existing4/8 wire output
unchanged. Composite control stores signed coarse16/32 grid plus existing signed
4tile sparse sketch; OUTER signature binds both complete packets, preventing
same-ID component mixing. All3signatures/envelope counted. Verify all evidence
before map, invalid/missing fine evidence is CANNOT_AUTHENTICATE, not decoder
exhaustion. Valid exhausted sketch falls back to authenticated coarse map; verified
fine root yields4tile map. Inconsistent component verdicts rejected. No original
pixels or online evidence at receiver. No embedding, freshness or novelty claim.

Executed3synthetic512images x2coarsegrids x2budgets x6cases=72composite cases,
compared with plain signed coarse grid. Numeric coarse-fallback-control-v1.json.
coarse16+512sketch=61736bytes vs plain32858;coarse32+512=37160vs8282.
Both decoded onebit/brightness3/3; replacement/copy fine0/3 but coarse map present.
coarse16+2048=147752;coarse32+2048=123176. Both decoded all4nonJPEGedits3/3,
fell back on allJPEG. Zero missed pixels in exposed maps in these finite trials;
JPEG high changedRGBIoU still NOT semantic benign tolerance. No real-data claim.

Composite improves small-edit precision over coarse grid but costs more; fine
precision degrades explicitly on saturation. Straightforward multiresolution
composition is established design, not yet a research advance. Cannot count
fallback as successful4tile decoding or conceal coarse-map excess highlighted area.
Full420passed1CUDA-onlyskip35.01s. No GPU/Kaggle request, no background process.

## Index-aware syndrome decoder: equal-byte experiment executed

Implemented src/index_syndrome.py as a development coding control. Fixed public
tile index determines3bucket locations; each bucket holds XOR full256bit leaf
hash and GF(2^16) index-weighted hash,64bytes. Single-error candidate derived from
syndrome ratio and checked across16field words. Reconstructed complete original
leaf vector MUST match signedSHA256commitment before exposing fine map. Invalid
signature/context =>CANNOT_AUTHENTICATE; residual/invalid reconstruction =>
FAILED_INTEGRITY with no map. No original pixels/online service/embedding.
GF16supports<=65535tiles, explicit rejection above limit. Primitive polynomial
0x1100b verified full65535nonzerocycle. Counts/headers/root/signature all included.
Known algebraic sparse-recovery/peeling ingredients, NOT claimed novel/optimal.

Compared same5randomRGB512images x2editpatterns x6editcounts x3matchedbudgets,
180trials PER decoder,360total.7168/28672/114688tablebytes correspond old
128/512/2048buckets vs new112/448/1792; complete packets EXACTLY7294/28798/114814.
At7294bytes64changedtiles: old0/10,new10/10. At28798bytes256tiles:old0/10,
new10/10. Both fail128tiles at7294 and512tiles at28798; both decode512tiles
10/10at114814. All returned fine maps exact, all modified images failed integrity.
This is finite development evidence, NOT a guaranteed capacity or2xuniversal gain.
Old/new hash placement differs; no assertion gain isolates ONLY removed old/new
entries. Needs controls for placement/decoder construction and coding prior art.
Raw numeric evidence equal-byte-decoder-development-v1.json. No real-image result.

Tests: field cycle/linearity, random tile changes, root mismatch despite valid
signature, overcapacity, allbitplanes, truncated/extra/missing evidence, equal-byte
format formulas. Full424passed1CUDA-onlyskip32.59s. No Kaggle request/background
process or frozenstudy change. Next defensible question: whether fixed-index
structure gives useful equal-budget coverage beyond existing sparse codes, not
whether signatures/finite fields/peeling are new inventions.

## Targeted stopping-set probe reverses index-decoder robustness impression

Executed public-layout search WITHOUT keys/original hashes. At112buckets tile
indices309/315 share neighbours17/31/91 (316positions examined); at448buckets
indices19/4302 share248/259/284 (4303examined). First search.00060s,second.00635s
in this run. No duplicate triple found over16384indices at1792buckets; not proof
of no larger stopping sets. Two tiles in the same3neighbours leave no singleton
and disable fine peeling. This is availability attack, NOT signature forgery.

Across3newrandomRGB512inputs x2budgets, two one-bit changes disabled index decoder
fine localisation6/6; all6stillFAILED_INTEGRITY. Equal-byte oldsetdecoder returned
exact fine maps6/6, fullsigned4grid6/6. Total18verification cases. Evidence
index-stopping-set-probe-v1.json. Earlier ordinary360trial gain remains real but
is NOT universal superiority. No security threshold weakened/relabelled.

Added regression test deliberately preserving discovered limitation and warning
in prototype. Full425passed1skip34.34s. No Kaggle or larger-data run justified for
this fixed-public-layout candidate until addressed. Coarse authenticated fallback
preserves coarse localisation but does not repair fine-resolution availability.
Public random salt or simply rejecting duplicate triples cannot by itself prove
absence of higher-order stopping sets; do not advertise those as a complete fix.

Decision: do NOT promote current index-aware sketch as adversarially reliable
research method. Next algorithmic comparator should be an established bounded-
error syndrome construction with explicit correction radius, rather than another
layout tweak measured only on ordinary random edits. Such a code is also prior art;
novelty remains a separate gate. No SOTA/conference readiness claim established.

## Classical bounded-error syndrome baseline implemented/executed

src/bounded_syndrome.py implements standard2tGF16power moments per16hash lanes,
Berlekamp–Massey error-location recurrence, Chien-style root search and Vandermonde
value recovery. Reconstructs original full leaf vector and checks signedSHA256root
before fine map. Uses unchanged receivedRGB, trusted publickey/version, no original
pixels at verifier. Prototype limits65535tiles,t<=64. All header/root/signature
included:124+64tbytes. Standard algebraic coding, NOT a novel error-correcting code.
<=terror correction is the established distinct-position power-syndrome model;
finite tests are not a proof, code audit or cryptographic availability guarantee.
No full pixel recovery is performed: recovers leaf digests and changedtile positions.

Executed78synthetic512trials:3inputs, t2/8/32/64, ordinary clustered/distributed
1/t/t+1changedtiles plus both earlier targeted2tilepatterns att2. All54withinradius
fine maps exact, all24above-radius unavailable; allmodified imagesFAILED_INTEGRITY.
Targeted2tile attacks that disabled fixed-indexpeeling now decode6/6at252bytes.
Budgets t2=252,t8=636,t32=2172,t64=4220bytes. Meanverification bybudget
.03494/.06866/.22158/.43606s in this localrun. These are descriptive, not a controlled
cross-environment speedbenchmark. Much lower evidence than earlier sketches for
withinradius cases, but greater algebraic compute cost. Evidence
bounded-syndrome-development-v1.json. No real-image/finalheldout or SOTAclaim.

Eighttests cover widths1/2/4/8radii, zero hash lanes, boundary positions, all136
single/pair error supports of16positions, malformed/context/key/root cases and
above-radius rejection. Full433passed1CUDA-onlyskip32.38s. NoGPU/Kaggle/background.

Literature search confirms error-correcting image verification/recovery is old:
“A Robust and Recoverable Tamper Proofing Technique for Image Authentication”,
https://link.springer.com/chapter/10.1007/3-540-45036-X_5 (2003), abstract describes
verificationinformation compressed using errorcorrection. “Fragile Watermarking
for Tamper Localization and Self-Recovery Based on AMBTC and VQ”,
https://doi.org/10.3390/electronics12020415 (2023), relatedwork citesRSrecovery.
These are leads, not reproduced equivalent constructions. Need direct syndromic
hash authentication/secure-sketch references before any novelty statement.

Decision: prior compact-sketch storage wins against fullmanifest are insufficient
research motivation; this standard bounded-code comparator is substantially
stronger in its advertised sparse radius. Do not keep enlarging medical benchmarks
for known sketch constructions to manufacture novelty. First evaluate against this
baseline and identify a real remaining capability/compute trade-off.

## Matched local4220byte ceiling comparison executed

scripts/compare_bounded_budget.py compares all3implementations with same3new512RGB
inputs, samechangedpixels/truth, sameprocess/threadsettings, rotated method order,
intact warmup beforetiming. Parameters bounded t64=4220bytes, index63buckets=4158,
set73buckets=4214. Same ceiling NOT identical sizes nor same decoding guarantees.
36ordinary trials/method (counts2/16/32/64/65/128 x2patterns x3inputs), plus9targeted
trials/method (historical112/448layouts and comparator'sactual63bucketlayout).
135total modified verificationcalls. Numeric matched-budget-development-v1.json.

Ordinary fine maps: bounded24/36, index18/36, set11/36. Bounded24/24within64radius,
0/12above. Targeted fine maps:bounded9/9,index6/9,set9/9. Actual63layout pair defeats
index3/3. All135modifiedverdictsFAILED_INTEGRITY, zero incorrectexposedmaps. Missing
maps stay in denominators. No zero-filledmissmetrics that conceal abstentions.

Ordinary mean local verificationseconds bounded.42269,index.06254,set.05623.
Targeted.34562/.04969/.05379. Mean signseconds.97139/.23644/.05377. Single run/no
repetitions; not stable latency estimate or crossmachine ranking. Shows a real
coverage-versus-compute tradeoff in THESEimplementations, not universal Pareto
optimality or new contribution. No GPU, no realimage/training/heldoutclaim.

Added all16lanes64denseerrors reconstruction, maxGF16position65534, ceiling/trial
accounting tests. Full436passed1CUDA-onlyskip33.32s. Existingbounded t64prototype
still limited to64radius: do not extrapolate measured timings/coverage to bigger
patches, nor call failed radius65 a crypto failure. Signed integrity remains valid.

Research decision: current evidence favours standard bounded syndrome for strict
sparse-radius localisation and peeling only as cheaper empirical decoder; neither
is a new medical-image authentication algorithm. Next useful implementation would
be a measured acceleration of SAME bounded construction or a carefully defined
higher-capacity control, not another cosmetic architecture combination. Novelty
and diagnostic utility remain unresolved, so no new Kaggle run warranted yet.

## Byte-identical bounded-code acceleration measured

Added opt-in backend='accelerated' to bounded sign/verify; default remains reference.
No wire/header/signature/root/radius change. src/bounded_acceleration.py reuses
per-leaf logarithms during moments, searches identical lane locator polynomials
once percall, vectorises Gaussian rowelimination. No persistent image cache,
probabilistic lane sampling, shortened fingerprints or skipped root checks.
Reference funcs retained unchanged for differential tests. OrdinaryNumPy engineering,
not newcode or researchcontribution. Transientmemory bounded per moment (no n*t*16
allocation); no measured peak-memory claim.

Executed paired benchmark2new512RGBinputs x2radii x4counts x3repeats x2backends=
96timedverificationcalls,24timedsigncalls; warmups excluded, orderalternated.
Packets identical byteforbyte, verdict/reason/maps identical for allpairs. All
within-radius exact; above-radius unavailable. Numeric
bounded-acceleration-benchmark-v1.json. Medianverificationseconds(reference/fast):
t8,count8 .09263/.04333 (2.14x);t64,count64 .67701/.24153 (2.80x).
t64,count2 .38329/.16796;t64,count65 .40067/.17527. Intact~.020/.0195, essentially
unchanged as rootmatches before syndrome. Median signing t8 .06552/.03964;
t64 .37791/.15949. SinglelocalCPU, not machineindependent speedup; medians from6
measurements/group, not tail latency guarantee. Earlier sign timing differed,
reinforcing need to use paired same-run comparison, not old cross-run figures.

Sevennew differentialtests: radii1/2/8/32/64, allzero vectors, densehashchanges,
heterogeneous per-lane supports, above-radius, packet equality/verdicts. Full
443passed1CUDA-onlyskip37.95s. NoGPU/dataupload/Kaggle/frozenstudy change.

Conclusion: much of reference runtime is implementation overhead, not an inherent
penalty of the standard coding model. Still no medical-specific novelty established.
Do not use slowreference vs peeling as an inherent algorithm ranking. Larger-radius
implementation/evaluation remains undone; typical64x64patch changes256..289tiles,
so currentradius64 is not yet sufficient for those historical imageoperators.

## Extended bounded syndrome to historical patch capacity

Raised prototype MAX_T64->320, unchanged version/wirelayout/field; newradius289
packet18620bytes includingheader/fullroot/signature. Existing oldpackets remain
accepted. Bothbackends support newrange; measured accelerated only here. Reference
still default. No frozenstudy/protocol redefinition, no noveltystatement.
Executed2synthetic512phantoms x6unchangedoperators=12cases. Intact2/2verified,
8/8nonJPEG editsFAILED_INTEGRITY with exact4tilemaps and zero missedpixels.
Replacement/copy changed272/289tiles, all4decoded. JPEG changed16384tiles2/2,
FAILED_INTEGRITY with no finemap (explicitnullpixelmetrics). IoU dependsgridboundary:
replacement.941176/.885813, copy.935202/.885813, onebit.0625. Not exactpixelmask.
Setup.659/.652s; patchverification2.02..2.20s; intact~.0195s, onebit.640..731s,
brightness.960..1.000s. SingleCPUrun not speedranking. Numeric evidence
bounded-patch-development-v1.json. No realmedicalimage/heldout/rankingclaim.

Dense all16lanes289errors tested on320positions, full recoveredhash equality;
newheaderlimits289/320andinvalidradius tested. Full445passed1CUDA-onlyskip35.45s.
Storage18620vs earlier sparse114814/full524378 is descriptive; different trialsets,
explicitboundedradius vs empiricalpeelingcoverage, no pairedspeedclaim. Stronger
standardbaseline now covers historicalpatchsize; this weakens any proposal based
only on compactdetachedevidence/localisation capability. No additionalKaggle run.

Progress against originalresearchgoal: functionalstrict-integrity/localisation and
reusablebaseline implementation substantial; defensibleoriginalcontribution still
not demonstrated. Current32realset developmentonly; independentlyfrozenfinalsplit,
patient/lesionindependence, matched strongestSOTA contract, diagnosticutility remain
unresolved. Do not attach an invented percentage/conference-readiness score. Next
substantivegate is choose a real unsolvedtradeoff after direct relevantpriorart,
not endlessly add knowncodingvariants. If no gap survives, frame honestbenchmark
study with limitedclaims or pivotquestion explicitly, rather than promise novelty.

## Direct relevant prior art and matched real-development runner

Read author PDF intro and codingmethodsection2.2 of Lefevre/Carre/Fontaine/Gaborit/
Huang, SignalProcessing190(2022)108342, doi10.1016/j.sigpro.2021.108342,
https://hal.science/hal-03359426v1/file/manuscript_revised_v1.pdf . Already compares
syndrome detection, localisation and correction usingBCH/RS/ELcodes; ELlocates
subblocks without correction. Described repetition subword ambiguity1111 and
additionalparity that misses evennumbers of suchsubwords. DWTsemifragile embedded
setting differs from our strictRGBdetached hashes; do not claim publishedELmethod
reproduced or equivalentguarantees. Reducing correction to location alone for
speed is also not an untouchednovelty. PDFmatrix text extraction malformed, cannot
implement from thoseextracted matrices faithfully without inspecting sourcefigure.

Read Lin/Varodayan/Girod MMSP2007 authorPDF systemmodel and conclusion:
https://web.stanford.edu/~bgirod/pdfs/LinMMSP2007.pdf . SlepianWolfLDPC syndrome
ofquantised randomprojections+digitalsignature, decoder sideinformation is received
image, incremental localization. PermitsJPEG/JPEG2000>=30dB,16x16blocks. Its232byte
bitstream claim is NOT totalall-insignaturepacket and NOT strictonebitRGB guarantee;
text reports~20%missedblocks/~2%missedpixels underchosenexperiment. Do not rank our
18620byte strictRGBcontrol against232 without contract/signatureaccounting. Confirms
signedcompressedsideinformationforauthentication/localization already established.
No exhaustive novelty clearance; no numeric SOTA claim from differentcontracts.

Implemented scripts/experiment_coding_real.py and notebookgenerator. Reuseexact32
sources/order/preprocessing/operators. Fourcontrols: bounded28918620bytes,
index28818558,set33018606,full4grid524378. Rotated methodorder, sameinputsandtruth,
allunavailable retainednullmetrics. Exports signedpackets, rawpublickey, boolean
truth/predictedtilemaps inNPZ (no pixels/privatekey). Exportedpublickey corroborates
run but is NOT externaltrustedproductionprovenance. Fullsignature/rootdecoding can
be rerun if matchingreceivedimages available; not claimable fromnumericalreceiptalone.

Executed24fixturecases, evidencecoding-matched-fixture-v1.json; two newtests check
fixtures/exports/formulas/notebookcompile. Full447passed1CUDA-onlyskip43.56s.
Notebook62020bytes, Drive1GHHxWMRIPCKiipAAVXm3JXG4xvNqN-iP. Runtimeestimate15–30CPUmin,
not measuredKaggle32run; noGPU. Attach samefollowup32dataset; output
coding32-development-results.zip. Actual32run NOT executed here; network/dataaccess
still unavailable. This is strongerbaseline developmentcomparison not newmethod
or independentfinaltest. No promisednovelty/SOTA/diagnosticutility established.

Remaining actual blockers: officialprovenanceandlesion/patientmetadata for untouched
finalsplit, independentlyfrozenclassifier/checkpointandtrainingprovenance for
utility, and a demonstrated originalquestion beyond priorcoding/localisation.
No silentrelabel existing32development asfinal. No syntheticnumbers passed off as
realmedicalevaluation. No architecture/training study changed merely to passgate.

## Returned matched coding32 development run checked

Drive1k0LPa7oypOo1HuCqVfQCSQphAakCzRZ5, coding32-development-results.zip18636900bytes,
SHA25617c2c9518d9426d0d889a6d040717858589c83a7c8251f06c57fc6ced4bb506f.
CheckedCRC/exact163archiveentries,768rows/128setuprecords, same32orderedsource
selection/sourcehashes/preparedRGB vs followup32, notebookpackagedcodedigest,
128Ed25519signatures against returnedrunkey, headercontext/budgets, shared
bounded/index/setcommitments,544available maps vs savedtiletruth, pixelmetric
arithmetic/nullmetrics forunavailable. Fullgrid192changedpixel/IoUvalues match
previousbinary32receipts. review_coding_return.py repeats these primarychecks;
receipts saved coding32-development-v1. RawZIP remains external/ignoredartifact.
No pixels available to independently derive savedtruth or rerundecoders: signatures
andmapconsistency independentlychecked, full imageverification NOT replayed.
Returnedrunkey is NOT independent productiontrust/provenance.

At~18.6Kbytes,bounded289 fine maps32/32onebit/brightness/replace/copy,0/32JPEG;
index288/set330 both32/32onebit/brightness,0/32replace/copy/JPEG. Full4grid524378bytes
all32maps eachcase inclJPEG. Intact32/32verified allmethods. All640modifiedcases
FAILED_INTEGRITY inclunavailablemaps; noincorrectsavedmap among544availablecases.
Bounded18620bytes=96.4491%less thanfull524378, explicitlyfinite289tilebudget.
AvailableonebitIoU.0625,brightness.8472222222,replace.917387543253,copy.917284058040,
matchingfull4grid. NoembeddingMSE. DoesNOTmeanexactpixelmaps orclinicalutility.

SAME-run meanreplaceverification bounded3.98012s,index.13157s,set.14374s,full.05246s.
Boundedcopy3.97416s vsfull.05143s. Intact~.0477sbounded/~.0516sfull. Peeling's faster
replacecalls produceNOmap; neverrankthattiming as comparable successfullocalisation.
One measurement/source/case; no tail-latency/independentheldoutSOTAclaim.

Consequence: standardboundedcode's compactdetached tradeoff now supported on actual
32developmentimages; earlierIBLTwinsagainstfullmanifest doNOTestablishresearchnovelty.
Boundedcode is far smaller but substantiallyslower inthisimplementation. JPEGdense
finecoverage unavailable atcompactbudget. Patientindependence/finalsplit/diagnostic
classifier remainunresolved. No moreblindtraining/benchmarkrepetition proposed.

## Paired development uncertainty analysis executed

src/paired_coding_analysis.py resamples complete sourceimage units preserving
methodpairs,10000resamplesseed1201. ExplicitimageNOTpatient resampling. Includes
allunavailable maps in coverage denominator, allcalls in runtime; classwisecoverage
reported. Wilsonintervals supplied alongside pairedbootstrap because unanimous
success/failure yields degenerate empiricalbootstrap and isNOTperfectpopulation
coverage. Developmentselection/patientdependence remain unresolved, so intervals
are descriptive and no multiplicity-correctedconfirmatoryclaim made.
Actualcoding32paired-analysis.json: bounded32/32coverage descriptiveWilson95%
[.8928208,1];NOT100%guaranteedcoverage. Replacement boundedminusfullruntime mean
3.92766s,pairedpercentile95[3.87814,3.97377];copy3.92273[3.87385,3.96888].
Replacementcoverage boundedminusindex/set+1(all32pairs),minusfull0;degenerate
bootstrap notproof. Each8diagnosis4/4boundedreplacementmaps;4/classinadequate
classwisegeneralisation. Timings onecall/source/method, not technicalrepeats.
No significance-basedSOTAclaim. Threeunit tests pairing/denominators/extremes/
missingduplicateunsafe records. No newdataset/GPUrun; no frozenstudy change.

## Uploaded ISIC2019 CSVs received and joined

DriveGroundTruth1bvQiIpcabEcEyIvAOFG0xmQxy36JLVuy1291479bytes;
Metadata1w7AiOnxFOK2yixWSpLFRCDAGZxQbpJn71214351bytes. DownloadedrawCSVs,
profile_isic_metadata.py strictuniqueID/fulljoin/onehotlabels, actual25331images,
23247knownlesionIDs/2084missing,11847uniqueknownlesions,0conflictinglesionlabels.
48previouslyusedIDs fromallpreparationreceipts,1withoutlesionID. Excluded48images,
140additionalknownsame-lesionimages,2083othermissinglesionimages;23060candidate
images/11800knownlesions remain. Candidatepool NOT frozenfinalsplit, notauthors
selection, no patientindependence. Fullnumericprofileisic2019-metadata-profile-v1.json
inclCSVhashes/eligibilityIDs(no pixels). Missinglesionusedimage cannot haveunknown
relatedimages fullyexcluded. Twofocusedtests pass. No newtraining/evaluationrun.

Re-readpublisherPFF-WM4.1.1: explicitlyISIC2019,2500dermoscopyimages,512square,
melanomadetection. Confirmsrelease but NOT selectionidentity/splitIDs or faithful
implementation. Previous32nearestRGB8classcontrol stilldifferentprotocol. Do not
claimreproduction merelybecauseCSVrelease matches. DrivecontainsCSVsonly inISICname
search, no ISICimagearchive located. ExistingKaggleimageattachment canbe reused for
execution, but no sourcepixelsdownloadedhere. Authorcode/split clarification still
needed beforeexactreproduction, no hiddenassumptions substituted.

## Explicit adapted paper-size cohort selected, not author reproduction

Re-readPFF-WM4.1.2–4.1.4:60/20/20,copy-move32square,FGSM/PGDeps4andPGD3steps,
GANStyleGAN2/DDPMinpainting,benignJPEG70/85/95/resize90%/contrast10%/blur.5;
classifierDenseNet121finetune20epochs,threephase10/30/20watermarktrainingA100batch8.
NoauthorIDs/split/attackcheckpointobtained. DoNOTsubstituteoldonebit/64patchbench
andcallthatsameprotocol, nor launch60epochreimplementationwithunresolvedequations.

Executed build_adapted_isic_cohort.py onuploadedCSVs; selected2500actualIDs,
knownlesiononeimageeach,1,500train/500validation/500test. SHA256deterministicranking
seed1301,proportionalclassallocationbyeligiblelesions (OURchoice, notpaperclaim).
Prior48usedimages/knownlesiongroups andmissinglesionIDsexcluded upstream.
Manifestadapted-isic2019-cohort-v1.json fixedbeforeanynewtraining/evaluation.
Melanomalabelvsrest supplied,original8classesretained. MELtrain170,val56,test57.
NVtrain901,val300,test301. Minorityclasssamplecounts small; nostrongclassclaim.
No pixelsdownloaded/verified, no preprocessingchosenasauthoridentical, no testing.
Missingfilesmustnottrigger substitutions. No patientindependenceclaim; unknown
relatedlesionsofpriorusedmissingIDimagecannotfullyexcluded. Candidatepool23060
notitselftestdata. Two newsplit tests plus2metadatatests pass. Newcohortdoesnot
changeexistingfrozen2000/150/1000studysettings; separateadaptedcomparisononly.

## Supported adapted operators and fixed-cohort image preparation implemented

src/paper_aligned_operators.py actual10outputs:intact,copy32,localblur32surrogate,
JPEG70/85/95,resize90%restore,contrast.9/1.1,Gaussian.5. ExactRGBchangetruth separate
fromrequestedregion; constanttexture may yieldnoactualchange. Copydestination
1024pixels/source disjoint. Gaussianseparablekernels4sigmatruncate/reflect;
Pillowcontrast/4:4:4JPEG/bicubicround461restore explicitlyOURimplementationchoices,
notpaperexact. Localblur sigma2 isOURsurrogate, notverifiedsemanticlesionremoval.
NoFGSM/PGD/GAN/DDPM subbedin. No64patchoperators relabelledaspapertests.

prepare_adapted_isic_cohort.py strictfixedIDs/noambiguoussources/no substitutions,
RGBconversion/directbicubic512 (explicitadaptation), fullsource/preparedfile/RGB
hashes. Records crosssplitidenticaldecodedRGB andblockstraining iffound. No
patientindependence or officialchecksummanifestclaim. Localfixture preparation,
missingIDs, crosssplitduplicateblocking tested. build_adapted_preparation_notebook
embedsactual2500manifest+scriptwithhashes, no training/evaluation; attachesoriginal
Kaggleimages andexportscohort+preparationJSONonly. Notebook
adapted_isic2500_preparation.ipynb generatedandcompilationtested. Actual2500image
preparation NOT runhere (noimagefiles). RuntimeestimatedseveralCPUminutesplusI/O,
notmeasuredfullrun. Five newtests;full459passed1CUDA-onlyskip47.12s.

No newfrozenstudysettings/60epochtraining/unresolvedPFF-WMequations silentlyfixed.
Nextneedsreturnedpreparationreceipts/sourcefilecoverage,thenvalidationoperator
comparison;testoutcomesremainuntouched. No claimthatpreparationalonecompletes
novelty/SOTA/clinicalutility orfaithfulauthorreproduction.

## Actual adapted2500 preparation returned and checked

Drive1g5eqZzcHuilDFrKxdcWLqxeJB1Q4mBFR,467386byteZIP,
SHA256e73d3884995f263873bffeafca506695d4bc63eba6de49a3b9ec17a01b1d2a6d.
review_adapted_preparation.py checkedCRC/exacttwoentries,byteidenticalfixedcohort,
cohorthash,all2500orderedrecords/labels/lesions/splits,hashformats/dimensions,
1500train/500validation/500test. RGB2500,uniquepreparedRGBhashes2500;
zero crosssplitknownlesion/decodedRGB/preparedRGB groups. ReturnedPillow13.0.0.
Receipts persisted adapted-isic2500-preparation-v2. Flagtrue means preparation
consistent, not modeltrainingapproval/researchproof. Rawpixelsabsenthere, cannot
recomputehashes; nodetectionofnearduplicates/patientindependence/authorselection.
No train/validation/testmodelperformance computed. Next execution should operate
onvalidationonly while models/protocol remainunsettled; preserve500testoutcomes.

## Adapted adversarial operators and paired diagnostic impact (implementation only)

Implemented `adversarial_operators.py`, `adversarial_evaluation.py` and
`diagnostic_impact.py` while the classical validation notebook runs externally.
The running notebook/cohort/operators have not changed. FGSM and PGD are separate
opt-in components; no real ISIC adversarial results or classifier selected yet.

Explicit adaptation: epsilon 4 in uint8 RGB units (4/255), PGD 3 steps of 1/255,
clean start, cross-entropy ascent for untargeted labels or descent for explicitly
supplied targets. Mean/std are mandatory; no implicit resize or augmentation.
All classifier modules must be eval and parameters frozen. Uses input-only
autograd, checks finite logits/gradients and re-evaluates quantized uint8 outputs.
Records exact changed-pixel truth and measured per-image Linf. Paper author
checkpoint, objective/target policy, epsilon units, normalization and start rule
are not established; these choices do not resolve faithful-reproduction gaps.

Connected evaluation returns paired clean/received probabilities, RGB hashes,
all-image and clean-correct-only attack-success numerators/denominators. Impact
includes confusion matrices, balanced accuracy, macroF1, per-class sensitivity,
correct-to-wrong/wrong-to-correct counts and probability shifts. Paired
class-stratified image bootstrap is descriptive and conditional on class counts,
not patient-independent inference. Missing declared classes yield null balanced
accuracy/macroF1 rather than dropping those classes. No classifier training or
provenance is established by accepting probabilities/model objects.

Eleven focused tests passed: analytic gradient direction, FGSM4/PGD3 bounds,
clipping, source/parameter preservation, frozen-eval enforcement, malformed
inputs, quantized-output evaluation, hand-computed confusion matrices, complete
failure retention, missing classes and bootstrap repeatability. Full suite passed
with one pre-existing skip. No clinical safety, novel-method or SOTA result.

## Adapted classifier trainer implemented; not yet trained on ISIC

Added `src/isic_classifier_training.py` and
`scripts/train_adapted_isic_classifier.py`: DenseNet121 binary MEL/rest head,
local torchvision-compatible ImageNet1000 initialization with mandatory SHA256
and source, no download/random-initialization fallback. This is explicitly NOT
the paper's CheXpert-initialized checkpoint. Missing author checkpoint remains
unresolved. Raw official legacy-key state dicts may require documented conversion
to torchvision-compatible keys; no silently relaxed state loading.

Explicit adapted settings: prepared512 RGB, ImageNet mean/std, no augmentation,
Adam1e-5 for20epochs, batch8, train-derived inverse-frequency class weights,
argmax decision. Highest validation balanced accuracy selects checkpoint with
earliest-epoch ties; no claim of an independent validation result after selection.
Train/validation image and lesion overlap rejected, test split forbidden by data
loader, input RGB hashes rechecked on load. Exports protocol, loss/validation
history, selected validation probabilities and hashed selected checkpoint.
No real classifier weights acquired or ISIC training launched. Class weighting,
normalization, objective and initialization are adaptations, not author settings.

Four focused tests passed: actual two-epoch fixture training/checkpoint selection
with deliberately absent test pixels, mismatch/provenance rejection, initialization
hash rejection, DenseNet121 state round-trip and binary forward pass. Fixture
training initially revealed torch.__version__ TorchVersion was incompatible with
weights_only loading; serialize plain string instead, safe reload then passed.
Full suite passed before the final additional architecture test; focused four
passed afterwards. No real-data diagnostic utility or learned advantage measured.

## Actual adapted validation500 results received and analysed

All five Drive ZIP parts downloaded (397,513,266 bytes combined); hashes in
`adapted-validation500-v1/analysis.json`. Raw archives are local cache, not Git.
Reviewed all 15,000 rows, 1,500 Ed25519 packet signatures, 11,500 available maps,
full image/case/method matrix, returned code byte identity, fixed cohort identity,
summary counts, tile/pixel truth arithmetic and map coverage. Recomputed all
saved-map metrics. All2500 source-file/decodedRGB/preparedRGB hashes also match
the earlier preparation receipts. Source/received pixels absent locally: this is
NOT independent pixel/operator replay or trusted-issuer provenance verification.

Intact: all three methods500/500 VERIFIED, no exposed-map false positives.
All13,500 manipulated rows FAILED_INTEGRITY. Copy32/localblur32: all methods
500/500 maps, zero missed changed pixels. Bounded289 and full4 identical maps:
copy IoU .8373135072503558; localblur IoU .7946093822614777. Full8 IoUs
.6796539322916667/.64357434286079. These are exact RGB truth, not semantic edits.
Bounded289: ZERO maps on all seven global paper-benign operators (3,500 cases);
full4/full8 expose all3,500. Do not report null maps as zero localisation errors.
No benign tolerance or clinical utility established.

Per-image evidence: bounded18,620B, full4 524,378B, full8 131,162B (96.4491% and
85.8038% reduction respectively). Mean copy verification seconds bounded1.869478,
full4 .0567432, full8 .0213499. Bounded-minus-full4 paired mean1.8127347s,
image-bootstrap95%[1.8028399,1.8225432], 10,000 draws seed5101. Localblur respective
1.873014/.0563991/.0214323s, difference1.8166149[1.8026289,1.8295448]. Mean signing
seconds1.095880/.0505666/.0196976 for bounded/full4/full8. One timing/input;
intervals descriptive image-not-patient, not final or machine-independent claims.

Conclusion: larger development sample supports a storage/latency/coverage
tradeoff, NOT an overall improvement or novel coding claim. Do not spend another
run tuning classical variants. Next executable step is the diagnostic classifier.

Built `adapted_isic2500_classifier.ipynb`: same fixed cohort and automatic
preparation recovery; official torchvision ImageNet initialization with hash-prefix
check and recorded full source/converted-file hashes, no random fallback. Training
adds CUDA AMP and a six-hour elapsed guard; partial training never writes completed
summary. Classifier checkpoint can be loaded frozen with explicit checksum/cohort/
class-order/preprocessing checks. Fixture training, safe reload/freeze, architecture
initialization, timeout, notebook bundle/export, and full repository tests passed
(one existing skip). Notebook GPU20epoch execution and external weight download
have NOT been run here. This adapted initialization is NOT paper CheXpert and all
validation classifier outcomes remain development-selected.

Also implemented and fixture-executed `evaluate_adapted_classifier.py`: requires
reviewed complete training/checkpoint checksum and exact training-membership
match; freezes DenseNet121 before evaluating only validation. Runs the same ten
classical operators plus explicit adapted untargeted FGSM/PGD, recomputes uint8
predictions, saves per-image probabilities/hashes/perturbation size, and aggregates
paired diagnostic impact with clean-correct attack-success denominators. Actual
fixture execution produced24rows for2validationimages with intentionally missing
test pixels. No real classifier or adversarial performance inferred from fixtures.
This evaluation is deliberately not auto-run after training: the checkpoint and
its clean-class performance need review before interpreting attack success.

Drive deliverables: classifier notebook1ypHrkl3Roq86NP6FhuF7j7ws3PYeLygt;
derived numeric validation bundle1btCj6H3fuZqwhlMv7TUHaXbXGHLHOFyg.

## Parallel implementation while diagnostic classifier trains

Did NOT regenerate or modify the already-sent classifier notebook, nor access
held-out test outcomes. Added classifier-return review against the exact embedded
source bytes in that sent notebook (not subsequently edited working sources),
checkpoint safe loading/hash/architecture and earliest-best epoch checks, exact
training membership, recomputed validation metrics, majority-nonMEL comparison,
ROC AUC with half-credit ties, and class-stratified descriptive image intervals.
Returned prediction receipts are not independent model inference/provenance proof.

Added checkpoint-pinned classifier-impact notebook BUILDER. It rejects absent or
placeholder hashes; the runnable deliverable is intentionally not issued until the
actual checkpoint is reviewed. Saved-output discovery and missing-preparation
recovery are implemented; tests execute decode/discovery/export cells with explicit
fixtures. No automatic approval of an unreviewed checkpoint or hidden test run.

Executed the existing seven-image synthetic TRAIN-only20epoch memorisation probe
with full epoch traces for both refiner models, plus a new shared-image-stem
objective-gradient probe. This does NOT amend the frozen study or establish
real-data performance. Compact evidence: `refiner-failure-diagnostic-v3`.
Selected epochs6(main)/7(attention): existing shared threshold suppresses all7
pixel maps in each. A lower TRAIN-only pixel diagnostic threshold gives mean IoU
.2541217/.3892706 but112/1157intact false-positive pixels and zero T1 overlap;
main also zero T2 overlap. Thus separate thresholds alone are NOT an acceptable
fix; these remain failing models. At initial refiner state, block-vs-pixel gradient
cosines are negative on4/7fixtures for each shared stem. This is a local conflict
observation, NOT proof of the cause or justification to change loss weights.

Implemented `experiment_matched_editguard_validation.py` for a future published-
checkpoint reader comparison on the fixed validation cohort and supported paper
operators. Both readers get IDENTICAL EditGuard-marked reference/received RGB;
additional signed4 evidence is explicitly524378B/image, so NOT an equal-storage or
end-to-end method ranking. Measures embedding distortion, complete target misses,
intact false highlights, numeric masks and CUDA-synchronized times. Actual pinned
EditGuard CLI adapter required; no author code/checkpoint redistributed. Executed
only with an intentionally failing synthetic reader fixture to test pairings,
protected-reference truth, retained failures and signature-control arithmetic.
No new real EditGuard or clinical comparison result claimed; no concurrent GPU job
requested. This prepares a defensible comparison rather than a new blind trainer.
