"""Train adapted DenseNet121 binary classifier from explicit local initialization.

Not included in the active classical-validation run. Does not evaluate test.
Requires a torchvision-compatible ImageNet DenseNet121 state dict, expected SHA256
and source description. No automatic network download or random-init fallback.
"""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import torch
from src.isic_classifier_training import PreparedSplit,initialise_densenet,fit


def main():
    parser=argparse.ArgumentParser(__doc__)
    for name in ('preparation','cohort','weights','out'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--weights-sha256',required=True)
    parser.add_argument('--weights-source',required=True)
    parser.add_argument('--device',default='cuda')
    a=parser.parse_args()
    train=PreparedSplit(a.preparation,a.cohort,'train');val=PreparedSplit(a.preparation,a.cohort,'validation')
    # Seed before replacing the head; fit seeds the subsequent training sequence.
    torch.manual_seed(4101)
    model=initialise_densenet(a.weights,a.weights_sha256)
    fit(model,train,val,a.out,{'initial_weights_sha256':a.weights_sha256,'initial_weights_source':a.weights_source,
        'architecture':'torchvision DenseNet121, ImageNet1000 initialization, replacement binary head'},device=a.device)

if __name__=='__main__':main()
