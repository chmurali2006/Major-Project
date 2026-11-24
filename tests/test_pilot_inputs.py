import csv
import hashlib
from pathlib import Path
import pytest
from src import pilot_inputs as P


@pytest.fixture
def attached(tmp_path,monkeypatch):
    images=tmp_path/'dataset'/'images';images.mkdir(parents=True)
    # Preflight checks matching IDs and attachment paths, not image decoding.
    for i in range(2):(images/f'id{i}.jpg').write_bytes(b'input')
    labels=tmp_path/'dataset'/'labels.csv'
    with labels.open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['image',*P.CLASSES]);w.writerows([[f'id{i}',1,0,0,0,0,0,0,0] for i in range(2)])
    checkpoint=tmp_path/'weights'/'clean.pth';checkpoint.parent.mkdir();checkpoint.write_bytes(b'test-weights')
    monkeypatch.setattr(P,'CLEAN_MD5',hashlib.md5(b'test-weights').hexdigest())
    return tmp_path,images,labels,checkpoint


def test_unique_attachments_resolve_without_hardcoded_slug(attached):
    root,images,labels,checkpoint=attached
    r=P.resolve_inputs(root)
    assert (r['data'],r['labels'],r['checkpoint'])==(images,labels,checkpoint)
    assert r['labelled_image_ids']==2


def test_csv_ambiguity_requires_explicit_choice(attached):
    root,images,labels,checkpoint=attached
    extra=root/'other.csv';extra.write_bytes(labels.read_bytes())
    with pytest.raises(ValueError,match='Set LABELS explicitly'):P.resolve_inputs(root)
    assert P.resolve_inputs(root,labels=labels)['data']==images


def test_image_ambiguity_requires_explicit_root(attached):
    root,images,labels,checkpoint=attached
    other=root/'other';other.mkdir();(other/'id0.jpg').write_bytes(b'duplicate')
    with pytest.raises(ValueError,match='Multiple images'):P.resolve_inputs(root)
    assert P.resolve_inputs(root,data=images)['data']==images


def test_missing_checkpoint_has_actionable_official_link(attached):
    root,_,_,checkpoint=attached;checkpoint.unlink()
    with pytest.raises(ValueError,match='Attach official EditGuard clean.pth') as error:P.resolve_inputs(root)
    assert P.CHECKPOINT_URL in str(error.value)


def test_wrong_checkpoint_rejected_without_model_loading(attached):
    root,_,_,checkpoint=attached;checkpoint.write_bytes(b'bad')
    with pytest.raises(ValueError,match='do not substitute'):P.resolve_inputs(root)


def test_missing_images_and_invalid_manual_paths_not_silently_replaced(attached):
    root,images,labels,_=attached
    with pytest.raises(ValueError,match='DATA directory'):P.resolve_inputs(root,data=root/'missing')
    (images/'id1.jpg').unlink()
    with pytest.raises(ValueError,match='labelled images not found'):P.resolve_inputs(root)


def test_notebook_bootstrap_reruns_and_preflight_precedes_network(attached,tmp_path):
    from scripts.build_editguard_pilot_notebook import build
    root,images,labels,checkpoint=attached
    nb=build();namespace={}
    bootstrap=''.join(nb['cells'][1]['source'])
    bootstrap=bootstrap.replace("WORK=Path('/kaggle/working') if Path('/kaggle/working').exists() else Path.cwd()",f'WORK=Path({str(tmp_path)!r})')
    exec(compile(bootstrap,'bootstrap','exec'),namespace)
    first=namespace['CODE']
    exec(compile(bootstrap,'bootstrap-again','exec'),namespace)
    assert namespace['CODE']==first
    preflight=''.join(nb['cells'][3]['source'])
    setup=''.join(nb['cells'][4]['source'])
    assert 'resolve_inputs' in preflight and "'pip','install'" in setup
    namespace.update(INPUT_ROOT=root,DATA=None,LABELS=None,CHECKPOINT=None,METADATA=None,GROUP_FIELD=None,
                     ALLOW_IMAGE_LEVEL_PILOT=False,OUT=tmp_path/'not-created')
    with pytest.raises(ValueError,match='weaker image-level pilot'):exec(compile(preflight,'preflight','exec'),namespace)
    namespace['ALLOW_IMAGE_LEVEL_PILOT']=True
    exec(compile(preflight,'preflight','exec'),namespace)
    assert namespace['DATA']==images and namespace['LABELS']==labels
    # Foreign source edits are never overwritten by rerunning the extraction.
    (first/'src/pilot_inputs.py').write_text('changed')
    with pytest.raises(RuntimeError,match='Nothing was overwritten'):exec(compile(bootstrap,'bootstrap','exec'),namespace)
