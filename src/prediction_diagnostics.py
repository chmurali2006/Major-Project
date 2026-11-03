"""Compact per-image evidence; probabilities are not calibrated confidence."""
import numpy as np

QUANTILES = (0., .01, .1, .5, .9, .99, 1.)


def map_diagnostics(samples, block_maps, pixel_maps, tau):
    if not len(samples) or not (len(samples) == len(block_maps) == len(pixel_maps)):
        raise ValueError('aligned nonempty samples/maps required')
    packet = {'quantile_levels': np.array(QUANTILES),
              'confusion_order': np.array(['tp', 'fp', 'fn', 'tn'])}
    for name, maps, truth_field in [('block', block_maps, 'gt_block'),
                                    ('pixel', pixel_maps, 'gt_pixel')]:
        quantiles, confusion = [], []
        for s, scores in zip(samples, maps):
            scores = np.asarray(scores)
            truth = np.asarray(getattr(s, truth_field), dtype=bool)
            if scores.shape != truth.shape or not np.isfinite(scores).all():
                raise ValueError('invalid diagnostic map shape/values')
            if (scores < 0).any() or (scores > 1).any():
                raise ValueError('diagnostics require probabilities in [0,1]')
            pred = scores > tau
            quantiles.append(np.quantile(scores, QUANTILES))
            confusion.append([np.count_nonzero(pred & truth), np.count_nonzero(pred & ~truth),
                              np.count_nonzero(~pred & truth), np.count_nonzero(~pred & ~truth)])
        cm = np.asarray(confusion, dtype=np.int64)
        packet[name + '_quantiles'] = np.asarray(quantiles)
        packet[name + '_confusion'] = cm
        packet[name + '_positive_count'] = cm[:, 0] + cm[:, 1]
        packet[name + '_truth_count'] = cm[:, 0] + cm[:, 2]
    return packet


def collapse_summary(packet):
    result = {}
    for name in ('block', 'pixel'):
        cm = packet[name + '_confusion']
        positive = packet[name + '_positive_count']
        result[name] = {'n_images': len(cm),
                        'all_foreground_images': int(np.count_nonzero(positive == cm.sum(1))),
                        'all_background_images': int(np.count_nonzero(positive == 0))}
    return result
