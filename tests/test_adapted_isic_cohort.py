import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_adapted_isic_cohort import allocate,select


def test_apportionment():
    assert allocate({'A':3,'B':2},4)=={'A':2,'B':2}
    assert sum(allocate({'A':7,'B':8,'C':2},10).values())==10
    with pytest.raises(ValueError):allocate({'A':1},2)


def test_selection_deterministic_lesion_disjoint_and_exact_sizes():
    rows=[{'image_id':f'{i}-{j}','lesion_id':str(i),'diagnosis':'MEL' if i%3==0 else 'NV'} for i in range(100) for j in range(2)]
    report={'candidates':rows,'previously_used_ids':['old'],'previously_used_images':1,'inputs':{}}
    a=select(report,size=50);b=select({**report,'candidates':list(reversed(rows))},size=50)
    assert a==b and a['split_counts']=={'test':10,'train':30,'validation':10}
    assert len({r['lesion_id'] for r in a['selected']})==50
    assert all(r['melanoma_label']==int(r['diagnosis']=='MEL') for r in a['selected'])
    assert a['exact_paper_reproduction'] is False
    with pytest.raises(ValueError):select(report,size=105)
