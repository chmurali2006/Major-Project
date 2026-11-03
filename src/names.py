"""Descriptive public model names; legacy artifact identifiers remain internal."""
MODEL_NAMES = {
    'C0_count': 'Classical watermark baseline',
    'C0_B': 'Dual-carrier classical baseline',
    'C8': 'Main watermark-verification model',
    'C12': 'Attention-enhanced model',
}
MODEL_NAMES.update({
    'without-ae': 'Without authentic-evidence autoencoder',
    'without-saliency': 'Without multi-scale saliency',
    'without-degradation': 'Without degradation conditioning',
    'without-pixel': 'Without pixel-resolution refinement',
    'without-fragile': 'Without fragile verification features',
    'without-semi': 'Without semi-robust verification features',
    'rgb-only': 'RGB-only evidence control',
})
STAGE_MODELS = {'main-model': 'C8', 'attention-enhanced': 'C12'}


def model_name(identifier):
    return MODEL_NAMES.get(identifier, identifier)
