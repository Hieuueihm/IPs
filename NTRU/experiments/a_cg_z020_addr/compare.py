"""Check this experiment's functional run (tile latency + 1, NTT CT + 2).

The schedule is new, so kernel cycles are compared with this directory's planner (fixtures.json, model_cycles), which
the previous prototypes matched exactly; they are also reported against a_cg_cmd_dispatch2. Outputs must be exact,
reset-abort, four-state and pipeline-reset checks must pass, and the live C replay must give byte-identical artifacts.
Run after run_sim.ps1: python experiments/a_cg_z020_addr/compare.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEW = ROOT / 'study/build/a_cg_z020_addr'
REF = ROOT / 'study/build/a_cg_cmd_dispatch2'


def cases(p):
    return [dict(re.findall(r'(\w+)=(\S+)', l)) for l in p.read_text(encoding='utf-8', errors='replace').splitlines()
            if l.lstrip('﻿').startswith('CASE ')]


def main():
    new, ref = cases(NEW / 'sim.log'), cases(REF / 'sim.log')
    model = json.loads((NEW / 'fixtures.json').read_text())
    assert len(new) == len(ref) == len(model) == 1026
    more = []
    for i, (a, b, m) in enumerate(zip(new, ref, model)):
        assert a['errors'] == '0', ('output error', i, a)
        assert int(a['cycles']) == m['model_cycles'], ('cycles differ from the planner', i, a['cycles'], m['model_cycles'])
        more.append(int(a['cycles']) - int(b['cycles']))
    log = (NEW / 'sim.log').read_text(encoding='utf-8', errors='replace')
    assert 'TOTAL cases=1026 errors=0 PASS' in log and 'RESET_ABORT modes=12 PASS' in log
    assert 'FOUR_STATE TOTAL cases=38 PASS' in (NEW / 'four_state.log').read_text(errors='replace')
    assert 'PIPELINE_RESET command_stages=2 response_flush=1 PASS' in (NEW / 'pipeline_reset.log').read_text(errors='replace')
    app = json.loads((NEW / 'application/application_results.json').read_text())
    refapp = json.loads((REF / 'application/application_results.json').read_text())
    assert json.loads((NEW / 'application/rtl_records.json').read_text())['calls'] == 74
    assert app['artifacts_sha256'] == refapp['artifacts_sha256'] and len(app['artifacts_sha256']) == 14
    assert len(app['independent_verification']) == 4
    assert all(x['valid'] == 0 and x['wrong_message'] != 0 for x in app['independent_verification'])
    tot_new = sum(int(a['cycles']) for a in new)
    tot_ref = sum(int(b['cycles']) for b in ref)
    print(f'COMPARE_PASS: 1026 cases exact, cycles equal to the planner; 38 four-state; pipeline reset; 74 C calls, '
          f'14 identical artifacts, 4 signatures. Cycles vs dispatch2: total {tot_new} / {tot_ref} '
          f'({100 * (tot_new - tot_ref) / tot_ref:+.2f}%), per case min {min(more)} max {max(more)}')


if __name__ == '__main__':
    main()
