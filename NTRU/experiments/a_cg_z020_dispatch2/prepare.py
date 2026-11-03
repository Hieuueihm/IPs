"""Re-target the byte-identical verified pipeline RTL to XC7Z020-CLG400-2."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PREV=ROOT/'experiments/a_cg_cmd_dispatch2'
B=ROOT/'study/build/a_cg_z020_dispatch2'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    old=json.loads((PREV/'manifest.json').read_text())
    validation=ROOT/'study/build/a_cg_cmd_dispatch2/validation.json'
    assert json.loads(validation.read_text())['numeric_cases']==1026
    for p,h in old['source_sha256'].items(): assert sha(ROOT/p)==h
    (HERE/'rtl').mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
    for n in ('mul_ss.v','tile_a.sv','a_cg_fast.sv'): shutil.copy2(PREV/'rtl'/n,HERE/'rtl'/n)
    t=(PREV/'synth.tcl').read_text().replace('a_cg_cmd_dispatch2','a_cg_z020_dispatch2')
    t=t.replace('xczu7ev-ffvc1156-2-e','xc7z020clg400-2')
    t=t.replace('RAMB18E2','RAMB18E1').replace('DSP48E2','DSP48E1')
    t=t.replace('set_param general.maxThreads 4', '''set_param general.maxThreads 4
set device [get_parts -quiet xc7z020clg400-2]
if {[llength $device] != 1} {error "XC7Z020 CLG400 -2 device support not installed"}
puts "TARGET_PART=$device"''')
    (HERE/'synth.tcl').write_text(t)
    manifest=dict(part='xc7z020clg400-2',clock_ns=5,kind='synthesis only, no board configuration',
        source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in (HERE/'rtl').glob('*')},
        byte_identical_source=old['source_sha256'],
        functional_evidence=dict(path=validation.relative_to(ROOT).as_posix(),sha256=sha(validation)),
        parent_manifest=dict(path=(PREV/'manifest.json').relative_to(ROOT).as_posix(),sha256=sha(PREV/'manifest.json')),
        production_RTL_changed=False,retained_baseline_changed=False)
    (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (HERE/'README.md').write_text('''# XC7Z020-CLG400-2 synthesis check

Exact RTL copy of the PQC-verified a_cg_cmd_dispatch2 prototype. Re-infers
7-series DSP48E1, RAMB18E1 and carry primitives, at the same 5 ns constraint.
Reports full core including host adapter and root cache. No P&R, board pin
constraints, PS/AXI integration, bitstream or hardware run is implied.
Existing PQC evidence applies to the identical RTL; this is not post-map testing.
The selected baseline, production RTL, precision, modulus and packed16 modes
remain unchanged. This experiment does not implement the separate 30k LUT goal.
''')
    print('Prepared byte-identical RTL for XC7Z020-CLG400-2; synthesis only.')

if __name__=='__main__': main()
