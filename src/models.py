"""Evidence-reading neural modules for the watermarking assembly study.

The audited portable trainer pretrains/freeze-checks authentic reconstruction,
then trains binary auxiliary classification and block/pixel localisation.
Abstention is calibrated separately, not learned as an unsupported third class.
Image features remain an input: wrong-key collapse/security must be measured,
not asserted. These custom modules are not a verified paper reproduction.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

N_SLOTS_CH = 2          # E and S from the keyed channel
N_DEGRADE = 4           # jpeginess, noise, sharpness, clipping


# ---------------------------------------------------------------- building blocks

class ConvBlock(nn.Module):
    def __init__(self, cin: int, cout: int):
        super().__init__()
        self.body = nn.Sequential(
            nn.Conv2d(cin, cout, 3, padding=1, bias=False),
            nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
            nn.Conv2d(cout, cout, 3, padding=1, bias=False),
            nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.body(x)


class Up(nn.Module):
    """Upsample, concatenate the skip, then mix."""

    def __init__(self, cin: int, cskip: int, cout: int):
        super().__init__()
        self.conv = ConvBlock(cin + cskip, cout)

    def forward(self, x, skip=None):
        x = F.interpolate(x, scale_factor=2, mode="bilinear", align_corners=False)
        if skip is not None:
            x = torch.cat([x, skip], dim=1)
        return self.conv(x)


# ---------------------------------------------------------------- row 3

class OneClassAE(nn.Module):
    """Evidence autoencoder; one-class behaviour depends on the trainer.

    The audited portable pipeline trains reconstruction on intact TRAIN cases
    only and freezes this module during segmentation training. Elevated error
    on unseen tampering is a hypothesis to measure, not a security guarantee.
    """

    def __init__(self, cin: int = N_SLOTS_CH, width: int = 24):
        super().__init__()
        self.enc = nn.Sequential(
            ConvBlock(cin, width), nn.MaxPool2d(2),
            ConvBlock(width, width * 2), nn.MaxPool2d(2),
            ConvBlock(width * 2, width * 4),
        )
        self.dec = nn.Sequential(
            Up(width * 4, 0, width * 2),
            Up(width * 2, 0, width),
            nn.Conv2d(width, cin, 1),
        )

    def forward(self, x):
        z = self.enc(x)
        rec = self.dec(z)
        return rec, (rec - x).abs().mean(dim=1, keepdim=True)


# ---------------------------------------------------------------- row 4

class RefineNet(nn.Module):
    """Three encoder levels with skip connections.

    Input channels: the evidence maps, the anomaly map from the AE, a saliency
    prior, degradation scalars broadcast to a map, and a downsampled copy of the
    image. Output: one logit per block.
    """

    def __init__(self, cin: int = N_SLOTS_CH + 1 + 1 + N_DEGRADE + 3, width: int = 32):
        super().__init__()
        w = width
        self.e1 = ConvBlock(cin, w)
        self.e2 = ConvBlock(w, w * 2)
        self.e3 = ConvBlock(w * 2, w * 4)
        self.bottleneck = ConvBlock(w * 4, w * 4)
        self.u3 = Up(w * 4, w * 4, w * 2)
        self.u2 = Up(w * 2, w * 2, w)
        self.u1 = Up(w, w, w)
        self.head = nn.Conv2d(w, 1, 1)

    def forward(self, x):
        e1 = self.e1(x)
        e2 = self.e2(F.max_pool2d(e1, 2))
        e3 = self.e3(F.max_pool2d(e2, 2))
        b = self.bottleneck(F.max_pool2d(e3, 2))
        d3 = self.u3(b, e3)
        d2 = self.u2(d3, e2)
        d1 = self.u1(d2, e1)
        return self.head(d1)


# ---------------------------------------------------------------- rows 5-8

class FusionNet(nn.Module):
    """The assembled system.

    Forward returns a dict so a caller cannot silently use the wrong tensor:
        mask_logits  (B,1,64,64)  per-block tamper logits
        presence     (B,1,64,64)  AE reconstruction error
        cls          (B,3)        INTACT / TAMPERED / CANNOT_SAY
    """

    def __init__(self, width: int = 32, degrade_ch: int = N_DEGRADE, n_cls: int = 3):
        super().__init__()
        self.degrade_ch = degrade_ch
        cin = N_SLOTS_CH + 1 + 1 + degrade_ch + 3      # E, S, err, sal, deg, image
        self.cin = cin
        self.ae = OneClassAE(N_SLOTS_CH, width=max(8, width // 2))
        self.refine = RefineNet(cin=cin, width=width)
        # The image-level head reads the same fused input as the localiser, so a
        # single backbone serves both. Pooling the raw concat would let the
        # degrade scalars dominate; pooling after the first refine block keeps
        # the spatial evidence. Cheap either way at this size.
        self.cls_head = nn.Sequential(
            nn.Conv2d(cin, width, 3, padding=1, bias=False),
            nn.BatchNorm2d(width), nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(1), nn.Flatten(),
            nn.Linear(width, 32), nn.ReLU(inplace=True),
            nn.Linear(32, n_cls),
        )

    def forward(self, evidence: torch.Tensor, degrade: torch.Tensor,
                saliency: torch.Tensor, image: torch.Tensor) -> dict:
        rec, err = self.ae(evidence)
        b, _, h, w = evidence.shape
        deg = degrade.view(b, self.degrade_ch, 1, 1).expand(b, self.degrade_ch, h, w)
        img = F.interpolate(image, size=(h, w), mode="bilinear", align_corners=False)
        x = torch.cat([evidence, err, saliency, deg, img], dim=1)
        logits = self.refine(x)
        return {"mask_logits": logits, "presence": err,
                "cls": self.cls_head(x)}


# ---------------------------------------------------------------- losses

def mask_loss(logits: torch.Tensor, target: torch.Tensor,
              pos_weight: float | None = None) -> torch.Tensor:
    """Dice + BCE. Dice handles the class imbalance: tampered blocks are a few
    percent of the grid, and BCE alone would learn to predict 'clean'.

    `pos_weight` up-weights the positive class in the BCE term. It exists
    because the first full smoke run scored IoU 0.013 with block accuracy 0.998:
    the model had learned to say 'nothing is tampered', which is correct 99% of
    the time and useless. Dice alone was not enough at that minority fraction.
    """
    pw = None if pos_weight is None else torch.tensor(
        [float(pos_weight)], device=logits.device, dtype=logits.dtype)
    bce = F.binary_cross_entropy_with_logits(logits, target, pos_weight=pw)
    p = torch.sigmoid(logits)
    num = 2 * (p * target).sum(dim=(1, 2, 3)) + 1.0
    den = p.sum(dim=(1, 2, 3)) + target.sum(dim=(1, 2, 3)) + 1.0
    return bce + (1.0 - (num / den)).mean()


def counting_summary() -> dict[str, int]:
    """Parameter counts per module, so the comparison quotes them."""
    def n(m):
        return sum(p.numel() for p in m.parameters() if p.requires_grad)
    ae, rn, fn = OneClassAE(), RefineNet(), FusionNet()
    return {"one_class_ae": n(ae), "refine_net": n(rn), "fusion_net": n(fn)}


# =====================================================================
# v2 architecture — pixel-resolution localisation (see docs/DESIGN_REVIEW.md)
# =====================================================================
#
# The pixel branch can represent sub-block boundaries. The old claim that an
# any-overlap block mask was a universal IoU ceiling was incorrect; exact block
# oracle IoU is computed by metrics.optimal_block_iou on each actual mask.

N_RICH = 10


class SaliencyNet(nn.Module):
    """Module 1: multi-scale attention, Conv 3x3 / 5x5 / 7x7 in parallel.

    This is a custom multi-scale saliency input inspired by the reference design,
    not a verified reproduction of its diagnostic-saliency map. In v1 it was passed as zeros,
    which means row 1 of the synthesis table was claimed but never built.

    A note on what it does and does not do here: it is trained end-to-end from
    the localisation loss, not against an external pathology annotation. So it
    learns 'where errors are expected to matter', which is what the refiner
    needs, and it is NOT a validated clinical saliency model. Do not describe
    it as one.
    """

    def __init__(self, cin: int = 3, width: int = 16):
        super().__init__()
        self.p3 = ConvBlock(cin, width)
        self.p5 = nn.Sequential(nn.Conv2d(cin, width, 5, padding=2, bias=False),
                                nn.BatchNorm2d(width), nn.ReLU(inplace=True))
        self.p7 = nn.Sequential(nn.Conv2d(cin, width, 7, padding=3, bias=False),
                                nn.BatchNorm2d(width), nn.ReLU(inplace=True))
        self.fuse = nn.Sequential(nn.Conv2d(width * 3, width, 1, bias=False),
                                  nn.BatchNorm2d(width), nn.ReLU(inplace=True),
                                  nn.Conv2d(width, 1, 1))

    def forward(self, image: torch.Tensor) -> torch.Tensor:
        return torch.sigmoid(self.fuse(torch.cat(
            [self.p3(image), self.p5(image), self.p7(image)], dim=1)))


class StageAttention(nn.Module):
    """Sequential channel/spatial attention, not a claimed PFF-WM reproduction.

    Shared average/max channel descriptors precede a spatial gate. Used only
    by the explicit C12 ablation; C8 and its checkpoint keys stay unchanged.
    """

    def __init__(self, channels: int, reduction: int = 8):
        super().__init__()
        hidden = max(1, channels // reduction)
        self.channel = nn.Sequential(nn.Conv2d(channels, hidden, 1), nn.ReLU(),
                                     nn.Conv2d(hidden, channels, 1))
        self.spatial = nn.Conv2d(2, 1, 7, padding=3, bias=False)

    def forward(self, x):
        gate = torch.sigmoid(self.channel(F.adaptive_avg_pool2d(x, 1)) +
                             self.channel(F.adaptive_max_pool2d(x, 1)))
        x = x * gate
        summary = torch.cat([x.mean(1, keepdim=True), x.amax(1, keepdim=True)], 1)
        return x * torch.sigmoid(self.spatial(summary))


class PixelRefineNet(nn.Module):
    """Module 4 at full resolution: 512 -> 256 -> 128 -> 64 -> ... -> 512.

    Inputs at 512: the image (3), saliency (1), degradation broadcast (4).
    The evidence is block-granular, so it enters upsampled (nearest, to keep
    block edges crisp) at 64x64 and is carried down the encoder, where it meets
    the encoder features at matching resolution.
    """

    def __init__(self, n_ev: int = N_RICH, n_deg: int = N_DEGRADE,
                 width: int = 16, n_cls: int = 3, stage_attention: bool = False):
        super().__init__()
        w = width
        self.n_deg = n_deg
        self.ev_proj = nn.Conv2d(n_ev, w, 1)                  # 64x64
        # full-resolution stem
        self.stem = nn.Sequential(
            nn.Conv2d(3 + 1 + n_deg, w, 3, padding=1, bias=False),
            nn.BatchNorm2d(w), nn.ReLU(inplace=True),
            nn.Conv2d(w, w, 3, stride=2, padding=1, bias=False),   # 256
            nn.BatchNorm2d(w), nn.ReLU(inplace=True),
        )
        self.d2 = ConvBlock(w, w * 2)                         # 256 -> pool 128
        self.d3 = ConvBlock(w * 2 + w, w * 4)                 # 128 + ev@64 pooled
        self.d4 = ConvBlock(w * 4 + w, w * 6)                 # 64 + ev@64
        # Decoder resolutions must line up with the encoder skips:
        #   u4: 64  -> 128  skip s3 (128)
        #   u3: 128 -> 256  skip s1 (256)
        #   u2: 256 -> 512  no skip
        self.u4 = Up(w * 6, w * 4, w * 4)
        self.u3 = Up(w * 4, w, w)
        self.u2 = Up(w, 0, w)
        self.stage_gates = nn.ModuleList([
            StageAttention(c) if stage_attention else nn.Identity()
            for c in (w, w * 4, w * 6)
        ])
        self.pixel_head = nn.Conv2d(w, 1, 1)
        self.block_head = nn.Conv2d(w * 6, 1, 1)
        self.cls_head = nn.Sequential(
            nn.AdaptiveAvgPool2d(1), nn.Flatten(),
            nn.Linear(w * 6, 64), nn.ReLU(inplace=True),
            nn.Linear(64, n_cls))

    def forward(self, ev64: torch.Tensor, degrade: torch.Tensor,
                saliency: torch.Tensor, image: torch.Tensor) -> dict:
        b, _, h64, w64 = ev64.shape
        # Project the block evidence once, then resize the projected features.
        # Projecting at 512x512 would be 64x the work for no extra information:
        # the evidence has no sub-block detail to preserve.
        ev_feat = self.ev_proj(ev64)                                   # 64x64, w
        deg = degrade.view(b, self.n_deg, 1, 1).expand(b, self.n_deg, image.shape[2], image.shape[3])

        s1 = self.stem(torch.cat([image, saliency, deg], dim=1))      # 256
        s1 = self.stage_gates[0](s1)
        s2 = self.d2(F.max_pool2d(s1, 2))                             # 128
        ev_at_128 = F.interpolate(ev_feat, size=s2.shape[-2:], mode="nearest")
        s3 = self.d3(torch.cat([s2, ev_at_128], dim=1))                # 128
        s3 = self.stage_gates[1](s3)
        s4 = self.d4(torch.cat([F.max_pool2d(s3, 2), ev_feat], dim=1)) # 64
        s4 = self.stage_gates[2](s4)
        block_logits = self.block_head(s4)
        if getattr(self,'pixel_enabled',True):
            u4 = self.u4(s4, s3)
            u3 = self.u3(u4, s1)
            u2 = self.u2(u3, None)
            pixel_logits = self.pixel_head(u2)
        else:
            pixel_logits = block_logits.repeat_interleave(8,2).repeat_interleave(8,3)
        return {
            "pixel_logits": pixel_logits,                       # 512x512
            "block_logits": block_logits,                       # 64x64
            "cls": self.cls_head(s4),
        }


def consistency_loss(pixel_logits: torch.Tensor, block_logits: torch.Tensor) -> torch.Tensor:
    """Match block-presence probability to max pixel probability in that block.

    Protocol v2 labels a block positive for ANY changed pixel. Average occupancy
    is incompatible with that target for sparse edits. Max is a differentiable
    presence surrogate, not a calibrated probability of the union event.
    """
    p = torch.sigmoid(pixel_logits)
    b = p.shape[0]
    pooled = F.max_pool2d(p, kernel_size=8)
    return F.mse_loss(pooled, torch.sigmoid(block_logits))


def pixel_mask_loss(logits: torch.Tensor, target: torch.Tensor,
                    pos_weight: float | None = None) -> torch.Tensor:
    """BCE + soft Dice. Tampered pixels are a tiny minority; BCE alone learns
    'all clean'. See `mask_loss` for why `pos_weight` is needed on top of Dice:
    at pixel resolution the minority is ~0.1%, and a Dice term alone still lets
    the head collapse on a small batch."""
    pw = None if pos_weight is None else torch.tensor(
        [float(pos_weight)], device=logits.device, dtype=logits.dtype)
    bce = F.binary_cross_entropy_with_logits(logits, target, pos_weight=pw)
    p = torch.sigmoid(logits)
    num = 2 * (p * target).sum(dim=(1, 2, 3)) + 1.0
    den = p.sum(dim=(1, 2, 3)) + target.sum(dim=(1, 2, 3)) + 1.0
    return bce + (1.0 - (num / den)).mean()


def total_loss(out: dict, gt_block: torch.Tensor, gt_pixel: torch.Tensor,
               cls_target: torch.Tensor, w_pixel: float = 1.0,
               w_consistency: float = 0.5, w_cls: float = 0.5,
               pos_weight: float | None = None,
               pos_weight_pixel: float | None = None) -> tuple[torch.Tensor, dict]:
    """One loss function for the whole system, so no head can be silently left
    out of the training step.

    This exists because exactly that happened: v1 trained the pixel branch with
    only `pixel_mask_loss`, so the block head and the classifier received no
    gradient at all. They looked trained and were random. The returned parts are
    logged every epoch and asserted non-zero by the tests.
    """
    # The two resolutions have different minority fractions -- a few percent of
    # the block grid, well under one percent of the pixel grid -- so they get
    # separate weights. Sharing one weight set the pixel head's positives 12x
    # against a 0.1% base rate and drove the model to predict tampering
    # everywhere: validation block accuracy collapsed from 0.84 to 0.26.
    pw_pix = pos_weight if pos_weight_pixel is None else pos_weight_pixel
    l_pix = pixel_mask_loss(out["pixel_logits"], gt_pixel, pos_weight=pw_pix)
    l_blk = mask_loss(out["block_logits"], gt_block, pos_weight=pos_weight)
    l_con = consistency_loss(out["pixel_logits"], out["block_logits"])
    l_cls = F.cross_entropy(out["cls"], cls_target)
    total = l_blk + w_pixel * l_pix + w_consistency * l_con + w_cls * l_cls
    return total, {"block": float(l_blk.detach()), "pixel": float(l_pix.detach()),
                   "consistency": float(l_con.detach()), "cls": float(l_cls.detach())}
