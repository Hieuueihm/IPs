"""Freeze the validated four-leaf candidate into an isolated full-system P&R project."""
import hashlib
import json
import shutil
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=ROOT/'experiments/a_cg_z020_system160'
CANDIDATE=ROOT/'experiments/a_cg_packed4'
BUILD=ROOT/'study/build/a_cg_packed4_system160'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    assert not (BUILD/'project').exists(), 'Preserve the existing private project.'
    manifest=json.loads((CANDIDATE/'manifest.json').read_text())
    assert all(sha(ROOT/p)==h for p,h in manifest['source_sha256'].items())
    results=json.loads((ROOT/'study/build/a_cg_packed4/results.json').read_text())
    assert results['cases']==1026 and results['independently_verified_signatures']==4
    assert results['synthesis']['candidate_shared_t']['lut']==34185
    if (HERE/'rtl').exists():
        assert all((HERE/'rtl'/p.name).read_bytes()==p.read_bytes() for p in (CANDIDATE/'rtl').iterdir())
    else:
        shutil.copytree(CANDIDATE/'rtl',HERE/'rtl')
    for name in ['create_project.tcl','implement.tcl','signoff.tcl']:
        if name=='signoff.tcl':
            shutil.copy2(BASE/name,HERE/name)
            continue
        text=(BASE/name).read_text()
        if name!='signoff.tcl':
            text=text.replace('a_cg_z020_system160','a_cg_packed4_system160')
        if name=='create_project.tcl':
            text=text.replace('create_project acg_qiming',
                'if {[file exists [file join $out project]]} {error "Preserve existing private project"}\ncreate_project acg_packed4_qiming')
        if name=='implement.tcl':
            text=text.replace('file mkdir $out','if {[file exists [file join $out signoff.dcp]]} {error "Preserve previous private sign-off"}\nfile mkdir $out')
            text=text.replace('puts "SYSTEM_IMPLEMENT_DONE"',
                'write_checkpoint -force [file join $out signoff.dcp]\nputs "PACKED4_SYSTEM_IMPLEMENT_DONE"')
        (HERE/name).write_text(text)
    BUILD.mkdir(parents=True,exist_ok=True)
    snapshot=dict(baseline='a_cg_z020_system160',candidate='a_cg_packed4 shared T-high',
        accepted_baseline_changed=False,part='xc7z020clg400-2',clock_mhz=160,
        candidate_manifest_sha256=sha(CANDIDATE/'manifest.json'),
        validated_results_sha256=sha(ROOT/'study/build/a_cg_packed4/results.json'),
        source_sha256={p.name:sha(p) for p in (HERE/'rtl').iterdir()},
        workflow_sha256={n:sha(HERE/n) for n in ['create_project.tcl','implement.tcl','signoff.tcl']})
    assert (HERE/'signoff.tcl').read_bytes()==(BASE/'signoff.tcl').read_bytes(), 'Clock contract changed'
    (HERE/'manifest.json').write_text(json.dumps(snapshot,indent=2)+'\n')
    (BUILD/'input_manifest.json').write_text(json.dumps(snapshot,indent=2)+'\n')
    print('PACKED4_SYSTEM_SNAPSHOT_READY',HERE)

if __name__=='__main__':main()
