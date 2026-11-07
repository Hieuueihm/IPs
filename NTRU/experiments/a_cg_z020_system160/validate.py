"""Functional gate for the integrated AXI bridge, against frozen core evidence."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BUILD = ROOT / 'study/build/a_cg_z020_system160'
BASE = ROOT / 'study/build/a_cg_z020_perf160'


def read(p):
    return p.read_text(encoding='utf-8-sig', errors='replace')


def cases(p):
    return [dict(re.findall(r'(\w+)=(\S+)', line)) for line in read(p).splitlines() if line.startswith('CASE ')]


def main():
    for name, digest in json.loads(read(BUILD / 'core_manifest.json')).items():
        assert hashlib.sha256((HERE / 'rtl' / name).read_bytes()).hexdigest() == digest
        assert (HERE / 'rtl' / name).read_bytes() == (ROOT / 'experiments/a_cg_z020_perf160/rtl' / name).read_bytes()
    for p in (HERE / 'rtl').iterdir():
        assert p.read_bytes() == (BUILD / 'rtl_run' / p.name).read_bytes()
    new, old = cases(BUILD / 'sim.log'), cases(BASE / 'sim.log')
    assert len(new) == len(old) == 1026
    for a, b in zip(new, old):
        for key in ('fft', 'fmt', 'logn', 'hmin', 'inverse', 'packed', 'jobs', 'native', 'words', 'q', 'cycles'):
            assert a[key] == b[key], (key, a, b)
        assert a['errors'] == '0'
    assert 'TOTAL cases=1026 errors=0 PASS' in read(BUILD / 'sim.log')
    assert 'AXI_PROTOCOL decoupled_aw_w=1 b_stall=1 r_stall=1 wstrb=1 invalid_access=1 PASS' in read(BUILD / 'sim.log')
    assert 'AXI_RESET aw_split=1 w_split=1 b_pending=1 r_pending=1 PASS' in read(BUILD / 'axil_reset.log')
    assert 'GENERATED_RESET startup=1 lock_gate=1 ps_reset=1 lock_loss=1 aux_polarity=1 PASS' in read(BUILD / 'reset_sim/run.log')
    app = json.loads(read(BUILD / 'application/application_results.json'))
    oldapp = json.loads(read(BASE / 'application/application_results.json'))
    assert app['artifacts_sha256'] == oldapp['artifacts_sha256'] and len(app['artifacts_sha256']) == 14
    assert len(app['independent_verification']) == 4
    assert all(x['valid'] == 0 and x['wrong_message'] != 0 for x in app['independent_verification'])
    assert json.loads(read(BUILD / 'application/rtl_records.json'))['calls'] == 74
    result = dict(cases=1026, cycle_equivalence=True, axi_protocol=True, axi_reset=True,
                  c_calls=74, identical_artifacts=14, signatures=4, core_unchanged=True)
    (BUILD / 'functional_verified.json').write_text(json.dumps(result, indent=2))
    print('SYSTEM_FUNCTIONAL_PASS', json.dumps(result))


if __name__ == '__main__':
    main()
