# Pre-run verification — audited pipeline

## Decision

**GO for the Kaggle wiring-check stage. Conditional GO for full training only after
that check passes on the actual Kaggle GPU and attached inputs.** This is not a
claim of zero bugs, clinical validity, cryptographic security or paper parity.

Use the newly generated notebook and a **fresh `isic2019-audited-v1` study**.
Pre-audit weights/receipts are not measurements of this corrected recipe and must
not be relabelled. Keep this source version for the entire staged experiment.

## Issues found and corrected

| Finding | Correction / evidence |
|---|---|
| Reconstruction described as authentic-only but jointly updated from edited examples | Dedicated reconstruction pretraining on intact TRAIN cases only; freeze parameters and BatchNorm during localisation; tested frozen state and gradients |
| Three-output auxiliary classifier had no abstention targets | Audited classifier is binary; a separately validation-fitted rule generates CANNOT_SAY; outputs include acceptance masks, verdicts and refusal reason |
| Diagnosis IoU mixed intact empty masks with tampered masks | Diagnosis and headline localisation IoU use tampered images only, with explicit counts; per-family TPR/FPR added |
| Length mismatch could silently truncate scoring via zip | Scoring rejects unaligned lists, incompatible shapes, non-scalar verdicts, nonfinite predictions and inconsistent measured labels |
| Thresholding could conceal nonfinite network logits | Reject nonfinite training loss or raw evaluation logits before boolean thresholding |
| Attention gate failed to feed the next encoder stage | Gate is applied before downsampling; main/attention models start with identical shared tensors to isolate the added attention |
| Any-overlap block IoU was incorrectly called a universal ceiling | Exact block oracle enumerates sorted occupancy prefixes; tested against exhaustive binary masks. Legacy values remain any-overlap measurements, not upper bounds |
| Single-carrier profile still embedded the second mark | Single profile now bypasses the second embedder; equality to the single embedder tested |
| Bootstrap paired IDs/labels but not the actual attack truth | New verdict arrays store attack family and measured-mask hashes; suite uses strict pairing |
| File existence alone could skip damaged outputs | Atomic output writes and checksum seals; resume skips only verified completed artifacts |
| Different sources/settings could enter different seeds of a study | Study-level frozen-settings/source contract plus per-run source/data/split checks; mixed-source aggregation suppressed |
| Dataset canonicalisation dropped supplied group identifiers | Preserve lesion/patient columns; current image-level profile refuses known shared patient/lesion IDs rather than risking group leakage |
| Public display used confusing configuration IDs | Notebook stages are main-model and attention-enhanced; reports use descriptive names. Legacy IDs are internal artifact compatibility keys only |

## Executed evidence

- CPU unit/regression/property tests: **133 passed** at the final audit run (rerun
  with `python -m pytest -q`). Includes exact shared initialisation, authentic-only
  freezing, CPU epoch resume equivalence, strict pairing, corruption detection,
  metric alignment guards and exact block-oracle exhaustive checks.
- Generated notebook code cells compile. The extracted Git-free source package
  executes synthetic disk-image preparation, staged main/attention training,
  key probes, strict paired bootstrap, resume/cache reuse and artifact export.
- Changed source/input resume attempts are rejected. Source ZIP is verified
  against its embedded file manifest.
- A separate tiny **actual ISIC 2019 mirror wiring run** completed controls, both
  learned models, rekey/wrong-key probes and held-out-splicing training on CPU:
  7 train / 7 validation / 7 test, width 4, two reconstruction epochs and one localisation
  epoch. All receipts are explicitly **sanity / unusable as scientific results**.
  The mirror has 25,331 JPEGs but only 20,455 distinct resolving labels; the strict
  notebook audit rejects it as the complete official corpus unless subset use is
  explicitly enabled. This check is not full-corpus training or a performance claim.
- The final `deliverables/VALIDATION.json` binds these checks to a source SHA-256;
  `SHA256SUMS.json` fingerprints the downloadable notebook and source packages.

Reproduce portable checks:

```sh
python -m pytest -q
python scripts/build_release.py
python scripts/validate_notebook.py --execute-wiring
```

## Not verified / remaining scientific limitations

1. **Kaggle/CUDA has not been executed in this CPU sandbox.** Run STAGE='check'
   first. It exercises actual GPU training/evaluation before a long measured job.
   GPU determinism is best-effort; exact cross-hardware identity is not promised.
2. Full three-seed training and paper-competitive performance are unmeasured for
   this corrected recipe. Three epochs on 2,000 training cases are a fixed pilot
   recipe, not evidence of full convergence or a full-corpus paper reproduction.
3. Ground truth/ID/count audits do not prove mirror authenticity. Only a small
   fixed image sample is decoded during attachment audit; experiment images are
   decoded/fingerprinted during preparation. Follow dataset use/licence terms.
4. If patient/lesion metadata is absent, the profile splits by image. Near-duplicate
   or same-patient leakage cannot be ruled out. Exact repeated selected image bytes
   are rejected. Supplied known shared group IDs stop this image-level runner;
   grouped clinical validation is not implemented here.
5. Keys in this study are public benchmark constants. Wrong-key/rekey probes do
   not prove resistance to adaptive attackers, unforgeability or clinical safety.
6. Synthetic edits and measured-difference masks are not expert-annotated clinical
   forgeries. JPEG changes count as integrity tampering, not proof of malicious intent.
7. Confidence margins are not probabilities. Risk/coverage constraints are fitted
   empirically on validation and must be remeasured on test; infeasible constraints
   fail closed and remain visible. No population-risk guarantee is claimed.
8. Historical diagrams and documents under `docs/` and `project-context/` describe
   older recipes and contain superseded geometric/architecture claims. They are
   **not submission evidence for this audited recipe** and are not bundled as
   current results. Regenerate submission figures from the completed audited run.
9. The standalone legacy matrix is not the audited entrypoint. It requires explicit
   legacy opt-in for non-smoke runs and marks those outputs unusable. Use run_suite.py.

## Before authorising the long run

- Use the current notebook, not an earlier downloaded version.
- Attach official training images and complete eight-class ground truth; verify
  dataset_audit.json reports the intended corpus and label counts.
- Complete the GPU wiring check; inspect saved outputs, logs and checkpoints.
- Start the main model with a fresh full-study directory. Freeze settings before
  seeing test results. Continue with attention-enhanced and remaining seeds by
  restoring the preceding saved output, then perform the held-out-family study.
- Keep the result ZIP plus this exact source bundle locally. One completed epoch
  is the resume granularity; a platform shutdown can lose an unfinished epoch and
  any files that were never saved as notebook output.
