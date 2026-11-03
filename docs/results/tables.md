## The configuration matrix

| cfg | configuration | detection | IoU | false claims | params (M) | status |
|---|---|---|---|---|---|---|
| C0 | classical only | 0.8750 (21 / 24) | 0.5384 | 3 / 3 | — | ok |
| C1 | + one-class AE | 0.9167 (22 / 24) | 0.7273 | 0 / 3 | 0.632 | ok |
| C2 | + RefineNet | 0.9167 (22 / 24) | 0.6929 | 0 / 3 | 0.389 | ok |
| C3 | + AE + RefineNet | 0.9583 (23 / 24) | 0.7441 | 0 / 3 | 0.632 | ok |
| C4 | + attention (full PFF-WM) | 0.9167 (22 / 24) | 0.7489 | 0 / 3 | 0.639 | ok |
| C5 | + degradation conditioning | 0.9167 (22 / 24) | 0.6345 | 0 / 3 | 0.639 | ok |
| C6 | + segmentation formulation | 0.9583 (23 / 24) | 0.7862 | 0 / 3 | 0.639 | ok |
| C7 | + three-way head | 0.9167 (22 / 24) | 0.6821 | 2 / 3 | 0.639 | ok |
| C8 | full synthesis | 1.0000 (24 / 24) | 0.8587 | 0 / 3 | 0.639 | ok |
| C9 | C8 minus the key | 0.9583 (23 / 24) | 0.7840 | 0 / 3 | 0.639 | ok |
| C10 | C8 trained K1, tested K2 | 1.0000 (24 / 24) | 0.7853 | 0 / 3 | 0.396 | ok |
| C11 | C8 on held-out tamper family | 0.9167 (22 / 24) | 0.7912 | 1 / 3 | 0.396 | ok |

### C0 — classical only

| tampered area bucket | n | median radius (px) | IoU | ceiling | headroom |
|---|---|---|---|---|---|
| area_0.000-0.005 *(small n)* | 2 | 17.3 | 0.336 | 0.618 | 0.282 |
| area_0.005-0.020 | 12 | 32.3 | 0.570 | 0.805 | 0.235 |
| area_0.020-0.050 *(small n)* | 3 | 42.2 | 0.548 | 0.784 | 0.236 |
| area_0.050-0.200 *(small n)* | 1 | 66.0 | 0.781 | 0.855 | 0.075 |
| area_0.200-1.010 *(small n)* | 3 | 288.3 | 0.996 | 0.987 | -0.009 |

| diagnosis | n | IoU |
|---|---|---|
| ATYPICAL NEVUS *(small n)* | 8 | 0.531 |
| COMMON NEVUS | 15 | 0.542 |
| MELANOMA *(small n)* | 1 | 0.541 |


### C1 — + one-class AE

| tampered area bucket | n | median radius (px) | IoU | ceiling | headroom |
|---|---|---|---|---|---|
| area_0.000-0.005 *(small n)* | 3 | 9.0 | 0.242 | 0.395 | 0.153 |
| area_0.005-0.020 *(small n)* | 8 | 27.3 | 0.761 | 0.702 | -0.059 |
| area_0.020-0.050 *(small n)* | 6 | 48.7 | 0.649 | 0.843 | 0.194 |
| area_0.050-0.200 *(small n)* | 1 | 64.9 | 0.760 | 0.882 | 0.122 |
| area_0.200-1.010 *(small n)* | 3 | 288.3 | 0.994 | 0.987 | -0.007 |

| diagnosis | n | IoU |
|---|---|---|
| ATYPICAL NEVUS *(small n)* | 8 | 0.602 |
| COMMON NEVUS | 15 | 0.776 |
| MELANOMA *(small n)* | 1 | 0.996 |


### C2 — + RefineNet

| tampered area bucket | n | median radius (px) | IoU | ceiling | headroom |
|---|---|---|---|---|---|
| area_0.000-0.005 *(small n)* | 3 | 9.0 | 0.210 | 0.395 | 0.186 |
| area_0.005-0.020 *(small n)* | 8 | 27.3 | 0.705 | 0.702 | -0.003 |
| area_0.020-0.050 *(small n)* | 6 | 48.7 | 0.611 | 0.843 | 0.231 |
| area_0.050-0.200 *(small n)* | 1 | 64.9 | 0.720 | 0.882 | 0.162 |
| area_0.200-1.010 *(small n)* | 3 | 288.3 | 0.991 | 0.987 | -0.004 |

| diagnosis | n | IoU |
|---|---|---|
| ATYPICAL NEVUS *(small n)* | 8 | 0.596 |
| COMMON NEVUS | 15 | 0.724 |
| MELANOMA *(small n)* | 1 | 0.996 |


### C3 — + AE + RefineNet

| tampered area bucket | n | median radius (px) | IoU | ceiling | headroom |
|---|---|---|---|---|---|
| area_0.000-0.005 *(small n)* | 3 | 9.0 | 0.423 | 0.395 | -0.027 |
| area_0.005-0.020 *(small n)* | 8 | 27.3 | 0.768 | 0.702 | -0.066 |
| area_0.020-0.050 *(small n)* | 6 | 48.7 | 0.627 | 0.843 | 0.215 |
| area_0.050-0.200 *(small n)* | 1 | 64.9 | 0.710 | 0.882 | 0.172 |
| area_0.200-1.010 *(small n)* | 3 | 288.3 | 0.990 | 0.987 | -0.003 |

| diagnosis | n | IoU |
|---|---|---|
| ATYPICAL NEVUS *(small n)* | 8 | 0.670 |
| COMMON NEVUS | 15 | 0.767 |
| MELANOMA *(small n)* | 1 | 0.995 |


### C4 — + attention (full PFF-WM)

| tampered area bucket | n | median radius (px) | IoU | ceiling | headroom |
|---|---|---|---|---|---|
| area_0.000-0.005 *(small n)* | 3 | 9.0 | 0.267 | 0.395 | 0.129 |
| area_0.005-0.020 *(small n)* | 8 | 27.3 | 0.798 | 0.702 | -0.095 |
| area_0.020-0.050 *(small n)* | 6 | 48.7 | 0.668 | 0.843 | 0.174 |
| area_0.050-0.200 *(small n)* | 1 | 64.9 | 0.827 | 0.882 | 0.055 |
| area_0.200-1.010 *(small n)* | 3 | 288.3 | 0.984 | 0.987 | 0.003 |

| diagnosis | n | IoU |
|---|---|---|
| ATYPICAL NEVUS *(small n)* | 8 | 0.616 |
| COMMON NEVUS | 15 | 0.803 |
| MELANOMA *(small n)* | 1 | 0.994 |


### C5 — + degradation conditioning

| tampered area bucket | n | median radius (px) | IoU | ceiling | headroom |
|---|---|---|---|---|---|
| area_0.000-0.005 *(small n)* | 3 | 9.0 | 0.177 | 0.395 | 0.218 |
| area_0.005-0.020 *(small n)* | 8 | 27.3 | 0.615 | 0.702 | 0.087 |
| area_0.020-0.050 *(small n)* | 6 | 48.7 | 0.514 | 0.843 | 0.328 |
| area_0.050-0.200 *(small n)* | 1 | 64.9 | 0.706 | 0.882 | 0.176 |
| area_0.200-1.010 *(small n)* | 3 | 288.3 | 0.994 | 0.987 | -0.007 |

| diagnosis | n | IoU |
|---|---|---|
| ATYPICAL NEVUS *(small n)* | 8 | 0.580 |
| COMMON NEVUS | 15 | 0.639 |
| MELANOMA *(small n)* | 1 | 0.995 |


### C6 — + segmentation formulation

| tampered area bucket | n | median radius (px) | IoU | ceiling | headroom |
|---|---|---|---|---|---|
| area_0.000-0.005 *(small n)* | 3 | 9.0 | 0.308 | 0.395 | 0.088 |
| area_0.005-0.020 *(small n)* | 8 | 27.3 | 0.872 | 0.702 | -0.170 |
| area_0.020-0.050 *(small n)* | 6 | 48.7 | 0.703 | 0.843 | 0.140 |
| area_0.050-0.200 *(small n)* | 1 | 64.9 | 0.831 | 0.882 | 0.050 |
| area_0.200-1.010 *(small n)* | 3 | 288.3 | 0.973 | 0.987 | 0.014 |

| diagnosis | n | IoU |
|---|---|---|
| ATYPICAL NEVUS *(small n)* | 8 | 0.654 |
| COMMON NEVUS | 15 | 0.844 |
| MELANOMA *(small n)* | 1 | 0.978 |


### C7 — + three-way head

| tampered area bucket | n | median radius (px) | IoU | ceiling | headroom |
|---|---|---|---|---|---|
| area_0.000-0.005 *(small n)* | 3 | 9.0 | 0.532 | 0.395 | -0.137 |
| area_0.005-0.020 *(small n)* | 8 | 27.3 | 0.867 | 0.702 | -0.165 |
| area_0.020-0.050 *(small n)* | 6 | 48.7 | 0.715 | 0.843 | 0.128 |
| area_0.050-0.200 *(small n)* | 1 | 64.9 | 0.820 | 0.882 | 0.061 |
| area_0.200-1.010 *(small n)* | 3 | 288.3 | 0.243 | 0.987 | 0.744 |

| diagnosis | n | IoU |
|---|---|---|
| ATYPICAL NEVUS *(small n)* | 8 | 0.530 |
| COMMON NEVUS | 15 | 0.800 |
| MELANOMA *(small n)* | 1 | 0.129 |


### C8 — full synthesis

| tampered area bucket | n | median radius (px) | IoU | ceiling | headroom |
|---|---|---|---|---|---|
| area_0.000-0.005 *(small n)* | 2 | 17.3 | 0.849 | 0.618 | -0.231 |
| area_0.005-0.020 | 12 | 32.3 | 0.840 | 0.805 | -0.035 |
| area_0.020-0.050 *(small n)* | 3 | 42.2 | 0.675 | 0.784 | 0.109 |
| area_0.050-0.200 *(small n)* | 1 | 66.0 | 0.951 | 0.855 | -0.096 |
| area_0.200-1.010 *(small n)* | 3 | 288.3 | 0.954 | 0.987 | 0.033 |

| diagnosis | n | IoU |
|---|---|---|
| ATYPICAL NEVUS *(small n)* | 8 | 0.919 |
| COMMON NEVUS | 15 | 0.826 |
| MELANOMA *(small n)* | 1 | 0.864 |


### C9 — C8 minus the key

| tampered area bucket | n | median radius (px) | IoU | ceiling | headroom |
|---|---|---|---|---|---|
| area_0.000-0.005 *(small n)* | 3 | 9.0 | 0.298 | 0.395 | 0.097 |
| area_0.005-0.020 *(small n)* | 8 | 27.3 | 0.886 | 0.702 | -0.184 |
| area_0.020-0.050 *(small n)* | 6 | 48.7 | 0.712 | 0.843 | 0.131 |
| area_0.050-0.200 *(small n)* | 1 | 64.9 | 0.846 | 0.882 | 0.036 |
| area_0.200-1.010 *(small n)* | 3 | 288.3 | 0.905 | 0.987 | 0.082 |

| diagnosis | n | IoU |
|---|---|---|
| ATYPICAL NEVUS *(small n)* | 8 | 0.648 |
| COMMON NEVUS | 15 | 0.850 |
| MELANOMA *(small n)* | 1 | 0.879 |


### C10 — C8 trained K1, tested K2

| tampered area bucket | n | median radius (px) | IoU | ceiling | headroom |
|---|---|---|---|---|---|
| area_0.000-0.005 *(small n)* | 2 | 17.3 | 0.818 | 0.618 | -0.200 |
| area_0.005-0.020 | 12 | 32.3 | 0.799 | 0.805 | 0.006 |
| area_0.020-0.050 *(small n)* | 3 | 42.2 | 0.608 | 0.784 | 0.177 |
| area_0.050-0.200 *(small n)* | 1 | 66.0 | 0.890 | 0.855 | -0.035 |
| area_0.200-1.010 *(small n)* | 3 | 288.3 | 0.636 | 0.987 | 0.351 |

| diagnosis | n | IoU |
|---|---|---|
| ATYPICAL NEVUS *(small n)* | 8 | 0.889 |
| COMMON NEVUS | 15 | 0.721 |
| MELANOMA *(small n)* | 1 | 0.923 |


### C11 — C8 on held-out tamper family

| tampered area bucket | n | median radius (px) | IoU | ceiling | headroom |
|---|---|---|---|---|---|
| area_0.000-0.005 *(small n)* | 3 | 9.0 | 0.310 | 0.395 | 0.086 |
| area_0.005-0.020 *(small n)* | 8 | 27.3 | 0.873 | 0.702 | -0.170 |
| area_0.020-0.050 *(small n)* | 6 | 48.7 | 0.717 | 0.843 | 0.125 |
| area_0.050-0.200 *(small n)* | 1 | 64.9 | 0.830 | 0.882 | 0.052 |
| area_0.200-1.010 *(small n)* | 3 | 288.3 | 0.982 | 0.987 | 0.005 |

| diagnosis | n | IoU |
|---|---|---|
| ATYPICAL NEVUS *(small n)* | 8 | 0.660 |
| COMMON NEVUS | 15 | 0.848 |
| MELANOMA *(small n)* | 1 | 0.985 |


## Provenance

| field | value |
|---|---|
| config | C0 — classical only |
| isolates | the control — our existing system |
| n | 24 (tampered 21, intact 3) |
| commit | `21bf525` |
| code_dirty | False |
| usable | True |
| threshold | 0.40 (chosen on validation) |
| wall clock | 5.4 s |
| smoke | False |
