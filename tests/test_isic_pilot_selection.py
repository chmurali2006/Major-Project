import pytest
from src.dataset_audit import CLASSES
from src.isic_pilot_selection import select


def labels():
    return {f'{name}_{j}':tuple(float(i==k) for i in range(8)) for k,name in enumerate(CLASSES) for j in range(4)}


def test_selection_balanced_deterministic_without_image_or_model_access():
    rows=labels();chosen=select(rows,set(rows),1,29)
    assert len(chosen)==8 and [r['diagnosis'] for r in chosen]==list(CLASSES)
    assert chosen==select(dict(reversed(list(rows.items()))),set(rows),1,29)
    assert chosen!=select(rows,set(rows),1,31)
    assert len({r['image_id'] for r in chosen})==8


def test_missing_class_rejected_not_silently_dropped():
    rows=labels()
    available={k for k in rows if not k.startswith('SCC_')}
    with pytest.raises(ValueError,match='SCC'):select(rows,available)


@pytest.mark.parametrize('n',[0,5,True])
def test_size_limits(n):
    rows=labels()
    with pytest.raises(ValueError):select(rows,set(rows),n)


def test_acquisition_rejects_repo_pixel_destination_before_network(tmp_path):
    import subprocess,sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    result=subprocess.run([sys.executable,str(root/'scripts/prepare_isic_mirror_pilot.py'),
                           '--destination',str(root/'data/forbidden-pilot')],capture_output=True,text=True)
    assert result.returncode!=0 and 'OUTSIDE' in result.stderr
    assert not (root/'data/forbidden-pilot').exists()


def test_comparison_refuses_mismatched_prepared_file_before_checkpoint_load(tmp_path):
    import subprocess,sys,json
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    image=tmp_path/'image.png';image.write_bytes(b'changed')
    prep=tmp_path/'preparation.json'
    prep.write_text(json.dumps({'complete':True,'selected':[{'image_id':'image','prepared_file_sha256':'0'*64}]}))
    out=tmp_path/'results'
    result=subprocess.run([sys.executable,str(root/'scripts/compare_editguard.py'),
         '--checkout',str(tmp_path/'missing-checkout'),'--checkpoint',str(tmp_path/'missing.pth'),
         '--images',str(image),'--preparation',str(prep),'--out',str(out)],capture_output=True,text=True)
    assert result.returncode!=0 and 'exact preparation selection/hashes' in result.stderr
    assert not out.exists()
