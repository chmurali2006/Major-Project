# Faculty framing and completed classifier return

> **Status note — 2026-10-19 UTC:** This file reviews the original adapted DenseNet classifier and prior-art framing; it is not the complete current classifier status. T1 later added DenseNet121-Aug and ResNet50-Aug validation-only results on the fixed cohort; see `deliverables/T1_VALIDATION_RESULTS.md`. T1 did not access TEST and does not establish external or clinical generalization. Historical test membership and timestamp provenance remain unresolved as described in `PROJECT_CONTEXT_MASTER.md`.

## Faculty: relevant public evidence, not guessed preferences

The supplied Scholar profile identifies Dr. Choudhary Shyam Prakash, NIT Andhra Pradesh, and lists image forensics, medical image watermarking and medical image authentication. His institutional page independently lists those interests and relevant publications.

Sources:
- https://scholar.google.co.in/citations?user=u8lyCQQAAAAJ&hl=en
- https://nitandhra.ac.in/dept/cse/23034 (institutional listing returned by search)
- https://www.nature.com/articles/s41598-025-11023-9 (primary abstract/introduction reviewed)

The 2025 Scientific Reports paper coauthored by him, *Ensuring integrity and security of medical image transmission in IoMT using highly imperceptible and robust watermarking approach*, describes ROI/RONI separation, no ROI embedding, localized tamper detection/recovery bits and DWT-SVD RONI embedding. Its abstract reports high PSNR/SSIM and low BER; these are published claims on its protocol, not our reproduced results. Full algorithm/results review and a matched implementation remain pending. Do not claim that protecting diagnostic regions is our new idea. The faculty also has passive medical authentication and copy-move/splicing publications; active and passive methods must not be conflated.

### Questions to prepare (our inference, not stated faculty demands)

1. What is the precise threat model, and is the method active watermarking, passive forensics or signed sidecar authentication?
2. What, specifically, differs from ROI/RONI protection, PFF-WM and MedSign?
3. Does decoded message recovery actually authenticate all image content? Our counterexample says no.
4. What is counted in payload, packet size, keys, verification latency and map coverage?
5. Are JPEG/resize accepted operations or integrity violations? Exact RGB signatures reject them; compact map abstention is not correct localisation.
6. Are localisation maps assessed against exact changed pixels? How are abstentions counted?
7. Were models and thresholds frozen before evaluation? Are validation and final test separated?
8. Why should classifier agreement mean clinical preservation? It does not; show class-wise baseline quality and transfer failures.

## Returned classifier: verified results

Drive return `adapted-isic2500-classifier-v1-results.zip` (26,951,310 bytes), SHA256 `ee481eaad49387678cc74662af9debb0b0fc8146f54be80cbff0214f6a6f2f70`.

Checkpoint `best.pt` is inside the return: SHA256 `38d52ca825472cb525c4c2745f9f7e2e047ddcbc34a6fe6cdcbfbdc0786ba57e`.

The review checked archive CRC/membership, exact code against the sent notebook, cohort/preparation identity, train/validation membership and lesion separation, all 20 epochs, first-best balanced-accuracy selection, stored prediction arithmetic and safe tensor checkpoint loading. Selected epoch: **3**. A reviewer bug comparing torch tuples against JSON lists was corrected by canonical JSON comparison; no training artefacts or notebook were changed. The fixture now exercises that serialization difference. Targeted reviewer tests: **3 passed**.

| Validation metric | Result |
|---|---:|
| Images: nonMEL / MEL | 444 / 56 |
| Accuracy | 86.40% |
| Balanced accuracy | 74.40% |
| Macro F1 | 0.7070 |
| ROC AUC | 0.8454 |
| Melanoma sensitivity | 58.93% (33/56) |
| Specificity | 89.86% (399/444) |
| False negatives / false positives | 23 / 45 |

The always-nonMEL reference has **88.80% accuracy**, higher than the model, but only **50% balanced accuracy** and zero melanoma sensitivity. Therefore do not headline raw accuracy. The class-stratified image-bootstrap interval for model balanced accuracy is approximately 67.48–81.00%; melanoma sensitivity 44.64–71.43%. These are descriptive intervals on checkpoint-selection validation data, not independent final performance.

The separately downloaded `densenet121-imagenet-compatible.zip` is a torch serialized weights archive despite its suffix, not an additional result package to extract. Its SHA256 matches the compatible-initialization receipt (`2bf68431a4b7e515afe55cb4ee8fb1bc263b55267041a6f9b28bd090285dc2b6`). Original publisher weights bytes were not supplied/rehashed; do not claim full independent source verification.

Evidence lives in `deliverables/verification-evidence/adapted-classifier-return-v1/`. Stored validation probabilities were checked arithmetically, not independently rerun against image files in this environment. The classifier is a limited research probe, not clinically ready. Test evaluation is false in the reviewed receipts and sent code; the final test was not run here.

## Next executable step

`deliverables/adapted_classifier_impact.ipynb` is generated with the reviewed checkpoint SHA256 pinned. It runs the frozen classifier on **validation only**, with ten existing operators and adapted FGSM/PGD, and records paired diagnostic impacts. Attach the saved classifier output directory containing `best.pt` and `summary.json` plus the original ISIC2019 dataset. This is an unexecuted handoff, not new results. It neither retrains nor evaluates test images and does not alter the original training notebook.

Embedding efficacy needs the separate training-only candidate pilot and later independent-model controls. The impact notebook does not execute that pilot. Do not present the classifier baseline as evidence that watermarking harmed diagnosis, or the candidate as already superior.
