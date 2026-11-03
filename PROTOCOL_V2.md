# Protocol amendment: ISIC RGB authentication v2

**New protocol identifier:** `isic-rgb-auth-v2`  
**New study directory:** `isic2019-rgb-auth-v2`  
**Scheme:** `rgb-lsb-hmac-sha256-192-v1`

This is a method change, not a repaired measurement of the old Haar-only fragile
carrier. All earlier weights/caches/results are incompatible. Source/data/settings
fingerprints reject incompatible resumes. Keep earlier negative results as history.
No published-paper reproduction/parity claim is made.

## Full-RGB fragile authentication

For each 8×8 RGB uint8 block:

1. Clear all 192 sample low bits to obtain canonical content. This is what can
   be recovered exactly after embedding; no approximate wavelet/DC code is used.
2. HMAC-SHA256 authenticates a versioned domain, trusted unsigned-64-bit image/
   version identifier, full image dimensions, block row/column and every canonical
   RGB sample. Truncate to 24 bytes (192 bits).
3. Embed all 192 tag bits in the RGB sample low bits, one bit per sample.
4. Verification reconstructs the canonical content, recomputes the HMAC and
   checks every received tag bit. `authentication.failures` is block-local;
   `authentication.verify` rejects if **any** block fails. It is independent of
   neural scores/count boundaries and cannot be overridden by a neural prediction.

The default `authenticated` profile writes the semi-robust DCT carrier first,
then this RGB fragile tag. `authenticated-single` omits the DCT carrier.
`single` and `dual` are explicitly **legacy Haar profiles**, retained only for
historical regressions; they still have the documented brightness/colour failures.
The low-level historical `evidence.embed/read` APIs are legacy too.

The new fragile carrier replaces—not supplements authentication with—the old
periodic Haar tag. In the existing 13-channel evidence tensor, `E` is now binary
RGB authentication failure. The remaining nine wavelet channels are diagnostic
features; the last three are DCT features. Their legacy PCG/selector construction
is not the security basis. Full-tensor channel count is unchanged but meaning is
versioned: old checkpoints MUST NOT be reused.

### Explicit limits

- Lossless storage/transport is required: save protected images as PNG or another
  exact RGB representation. JPEG, resizing and recompression break integrity and
  are labelled changed-pixel tamper events in this research protocol, not evidence
  of malicious intent. The semi-robust carrier cannot override a failed RGB MAC.
- Low-bit replacement is irreversible and changes original samples. Fidelity is
  measured, not assumed; no diagnostic safety claim follows from PSNR.
- HMAC forgery/collision resistance is a cryptographic assumption, not a proof
  that finite tests detect every possible attack. This is not a formal security
  audit, encryption, robust authentication through codecs, or clinical approval.
- A secret, high-entropy key is required for adversarial use. Benchmark keys in
  source are public and **not production secrets**; a key holder can re-tag edits.
- The receiver must obtain the expected image/version identifier and geometry
  context from a trusted workflow. A previously valid block at the same address
  with the same identifier/key can be replayed. Freshness requires an externally
  trusted unique version identifier/registry, not something guessed from pixels.
- The supported input is 8-bit RGB with dimensions divisible by 8. No DICOM,
  16-bit or clinical deployment capability is claimed.

## Labels and degradation

Pixel truth remains exact before/after byte differences. Block truth now marks
**any changed pixel**, including a one-bit edit; the previous >5% occupancy rule
is retired. Both image and block labels therefore include sparse edits. Cross-head consistency
uses max pixel probability as a block-presence surrogate, not mean pixel occupancy;
the old average was incompatible with an any-pixel block target.

Default sharpness is mean Sobel gradient magnitude divided by
`4*255*sqrt(2)`, a fixed analytic upper bound for uint8 luma with 3×3 Sobel kernels.
It varies with input and uses no VAL/TEST or corpus-fitted statistic. An explicitly
supplied finite positive reference still supports deliberate alternative studies;
it is not used by this frozen default recipe.

## Matched classical/learned operating-point selection

Both use the same validation objective: balanced image accuracy, then tampered
**pixel** IoU, then lower threshold/count for deterministic ties. The common grid
is thresholds .05…2.00 in .05 steps and counts 0,1,2,4,8,16,32,64,128,256. Classical
fusion also prefers smaller semi-carrier weight on ties. Model epoch selection
uses validation tampered-pixel IoU. No test label is used for selection. Learned pixel masks estimate sub-block
boundaries; they are not cryptographic pixel-level certificates.

The trained model's count prediction and empirical abstention remain experimental
outputs; they are NOT permission to assert that an image with a failed MAC is
verified. Receipts separately report strict authentication counts and whether they
match measured edit labels. Learned models may still be worse than the classical
baseline. No improvement or probability calibration is presumed.

## Runnable constituent removals

All variants start from identical shared weights and consume the **same cached
protected images and measured masks**:

| Variant argument | Actual removed computation/input |
|---|---|
| `without-ae` | AE pretraining and residual feature; zero placeholder |
| `without-saliency` | Learned multi-scale saliency path; neutral constant input |
| `without-degradation` | All four degradation conditioning inputs |
| `without-pixel` | Pixel decoder/head; block output upsampling, block/class losses only |
| `without-fragile` | First ten fragile/diagnostic feature channels before AE and localiser |
| `without-semi` | Three semi-robust feature channels before AE and localiser |
| `rgb-only` | All watermark features and AE residual; image-derived paths remain |

Removed modules can remain frozen in the checkpoint for exact shared initialization
and storage compatibility; they are not run. Both stored and trainable parameter
counts are reported. Feature removals do not pretend to remove embedding: physically
removing a carrier would change protected pixels and attack truth and requires a
separately declared protocol, not a falsely strict paired comparison.

Enable/freeze the full model list from the first job:

```sh
python scripts/run_suite.py --data <images> --metadata <labels.csv> \
  --out <new-study> --cache <outside-repo-cache> --device cuda \
  --seeds 0 --ablations --execute-configs C8 --probes
```

Later jobs use the **same command/settings/source**, `--resume`, and
`--execute-configs without-ae` (or another registered removal). Internal `C8`
means the Main watermark-verification model; `C12` means Attention-enhanced model.
Use seeds 0,1,2 and the planned main-model heldout run. These are planned experiments,
not completed results. The summary expects ablations when `--ablations` was frozen
in `study.json` and verifies their strict paired comparisons against the main model.

In the notebook choose `STAGE='ablation'` and `ABLATION='<variant>'`, one saved job
at a time. Main/attention/check/heldout stages freeze the same full model list.
The initial check executes only the two principal models; the CPU integration
validator can additionally exercise all seven removals.

## Reproduce engineering checks

```sh
python -m pytest -q
python scripts/review_from_source.py --exercise-crash --out /tmp/review-v2.json
python scripts/validate_rgb_auth.py --images 16 --out /tmp/auth-synthetic.json
python scripts/validate_rgb_auth.py --data <local-jpegs> --images 32 --out /tmp/auth-images.json
python scripts/validate_notebook.py --execute-wiring --exercise-ablations
```

Temporary paths may be changed for Windows. These checks do not replace the full
ISIC three-seed/ablation/heldout study, GPU preflight, or independent security review.
