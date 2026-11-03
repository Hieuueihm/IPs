"""Compare this experiment's functional run with the PQC-verified a_cg_cmd_dispatch2 run.

Every change of this experiment is meant to keep latency: each of the 1,026 cases must give the same kernel cycles and the
same host cycles, with no output error. Also required: reset-abort, four-state and pipeline-reset checks pass, and the
live C replay (74 transform calls, 4 signatures) produces byte-identical artifacts.
Run after run_sim.ps1: python experiments/a_cg_z020_timing/compare.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NEW = ROOT / 'study/build/a_cg_z020_timing'
REF = ROOT / 'study/build/a_cg_cmd_dispatch2'


def cases(p):
    rows = []
    for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
        if line.lstrip('﻿').startswith('CASE '):
            rows.append(dict(re.findall(r'(\w+)=(\S+)', line)))
    return rows


def main():
    new, ref = cases(NEW / 'sim.log'), cases(REF / 'sim.log')
    assert len(new) == len(ref) == 1026, (len(new), len(ref))
    for i, (a, b) in enumerate(zip(new, ref)):
        assert a['errors'] == '0', ('output error', i, a)
        for k in ('cycles', 'all_host_cycles', 'words', 'root_writes'):
            assert a[k] == b[k], ('changed', k, i, a[k], b[k])
    log = (NEW / 'sim.log').read_text(encoding='utf-8', errors='replace')
    assert 'TOTAL cases=1026 errors=0 PASS' in log and 'RESET_ABORT modes=12 PASS' in log
    assert 'FOUR_STATE TOTAL cases=38 PASS' in (NEW / 'four_state.log').read_text(errors='replace')
    assert 'PIPELINE_RESET command_stages=2 response_flush=1 PASS' in (NEW / 'pipeline_reset.log').read_text(errors='replace')
    app = json.loads((NEW / 'application/application_results.json').read_text())
    refapp = json.loads((REF / 'application/application_results.json').read_text())
    calls = json.loads((NEW / 'application/rtl_records.json').read_text())
    assert calls['calls'] == 74
    assert app['artifacts_sha256'] == refapp['artifacts_sha256'] and len(app['artifacts_sha256']) == 14
    assert len(app['independent_verification']) == 4
    assert all(x['valid'] == 0 and x['wrong_message'] != 0 for x in app['independent_verification'])
    print('COMPARE_PASS: 1026 cases, cycles and host cycles identical to a_cg_cmd_dispatch2; 38 four-state; '
          'pipeline reset; 74 C calls, 14 identical artifacts, 4 signatures')


if __name__ == '__main__':
    main()
