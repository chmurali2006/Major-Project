# Design notes

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
- Actual Kaggle/CUDA operation, recovery, runtime and VRAM.
- Authorised complete inputs, patient/lesion identifiers and group independence.
- Clinical preservation, novelty and literature parity; fidelity alone proves none.
