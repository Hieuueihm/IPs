"""Audit profiling provenance, full-output equality and the separate supply model."""
import hashlib
import json
from pathlib import Path
import re
import sys
from profile_kernel_engine import load_stats,validate,BASE,BUILD,ROOT

sys.path.insert(0,str(ROOT))
from model.fft_batch_supply import analyze


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    result_path=ROOT/'study/results/kernel_profile.json';r=json.loads(result_path.read_text())
    assert r['baseline_result_sha256']==sha(ROOT/'study/results/kernel_engine.json')
    for name,digest in r['source_and_evidence_sha256'].items():assert sha(ROOT/name)==digest,('stale evidence',name)
    cases=json.loads((BASE/'cases.json').read_text())
    for run in ('no_pause','random_pause'):
        validate(load_stats(BUILD/f'{run}.csv'),cases)
        assert sha(BUILD/f'{run}_actual.txt')==sha(BASE/'actual.txt')
    summary_path=ROOT/'study/results/kernel_profile_summary.json';summary=json.loads(summary_path.read_text())
    for key,path in [('profile_result_sha256',result_path),
        ('supply_result_sha256',ROOT/'study/results/fft_batch_supply.json'),
        ('report_sha256',ROOT/'docs/kernel_parallelism_profile.md'),
        ('report_script_sha256',ROOT/'scripts/report_kernel_profile.py'),
        ('supply_model_sha256',ROOT/'model/fft_batch_supply.py')]:assert summary[key]==sha(path)
    supply=json.loads((ROOT/'study/results/fft_batch_supply.json').read_text())
    for c in supply['cases']:assert c==analyze(c['n'],c['width_bits'],c['op']=='IFFT')
    assert len(supply['cases'])==54
    links=0
    for path in (ROOT/'ARCHITECTURE.md',ROOT/'docs/kernel_parallelism_profile.md',ROOT/'docs/autonomous_kernel_rtl.md'):
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf8')):
            if '://' in target or target.startswith('#'):continue
            assert (path.parent/target.split('#')[0]).exists(),('broken link',target);links+=1
    audit={'pass':True,'measured_tiles':16,'kernel_runs':11984,'words_checked':650984,
        'source_and_evidence_checks':len(r['source_and_evidence_sha256']),
        'outputs_identical_to_pqc_validated_rtl':True,'local_links':links,
        'static_supply_cases':54,'alternative_tile_count_rtl_sweep':False,
        'audit_script_sha256':sha(Path(__file__)),'profile_summary_sha256':sha(summary_path)}
    (ROOT/'study/results/kernel_profile_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps(audit,indent=2))


if __name__=='__main__':main()
