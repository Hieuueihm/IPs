"""Check autonomous-kernel evidence is current and all application artifacts match."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    engine=json.loads((ROOT/'study/results/kernel_engine.json').read_text())
    axi=json.loads((ROOT/'study/results/kernel_axil.json').read_text())
    app=json.loads((ROOT/'study/results/kernel_application.json').read_text())
    checked=0
    for evidence in (engine,axi):
        for name,digest in evidence['sha256'].items():
            assert sha(ROOT/name)==digest,('stale evidence',name);checked+=1
    assert app['kernel_result_sha256']==sha(ROOT/'study/results/kernel_engine.json')
    assert app['script_sha256']==sha(ROOT/'scripts/replay_kernel_application.py')
    for key,path in [('c_build_manifest_sha256','manifest.json'),('c_bridge_sha256','pqc_bridge'),('independent_verifier_sha256','independent_verify')]:
        assert app[key]==sha(ROOT/'study/build/pqc_application/c'/path)
    signatures=0
    for artifact in app['artifacts']:
        n=artifact['n'];name=artifact['file'];actual=ROOT/f'study/build/kernel_engine/N{n}/replay'/name
        baseline=ROOT/f'study/build/pqc_application/N{n}/capture'/name
        assert sha(actual)==artifact['sha256']==sha(baseline)
        signatures+=name.startswith('sig')
    assert signatures==4 and len(app['applications'])==4
    assert all(a['valid']==0 and a['wrong_message']!=0 for a in app['applications'])
    assert len(app['output_mutation_guards'])==1 and app['output_mutation_guards'][0]['returncode']==7
    cases=json.loads((ROOT/'study/build/kernel_engine/cases.json').read_text())
    counts=dict(Counter(c['origin'] for c in cases))
    assert len(cases)==engine['kernels']==5992 and engine['words']==325492
    assert counts=={'r8_synthetic':364,'custom_narrow_contract':100,'modular_oracle':56,'application_N512':1840,'application_N1024':3632},counts
    links=0
    for path in (ROOT/'ARCHITECTURE.md',ROOT/'docs/autonomous_kernel_rtl.md'):
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf8')):
            if '://' in target or target.startswith('#'):continue
            assert (path.parent/target.split('#')[0]).exists(),('broken link',path,target);links+=1
    result={'pass':True,'sha256_checks':checked,'local_links':links,'kernels':engine['kernels'],
        'words':engine['words'],'origins':counts,'byte_identical_signatures':signatures,
        'actual_output_mutation_detected':True,'fpga_confirmed':False,
        'audit_script_sha256':sha(Path(__file__))}
    (ROOT/'study/results/kernel_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
