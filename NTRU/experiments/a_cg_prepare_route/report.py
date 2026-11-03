"""Collect the single selected implementation; never label estimates as routed results."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
B = ROOT / 'study/build/a_cg_prepare_route'
OUT = B / 'fast'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    spec = importlib.util.spec_from_file_location('reports', ROOT / 'experiments/a_cg_timing/report.py')
    r = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(r)
    selected = json.loads((HERE / 'selected_manifest.json').read_text())
    for group in ('source_sha256', 'evidence_sha256', 'production_sha256'):
        for name, digest in selected[group].items():
            assert sha(ROOT / name) == digest, ('Frozen file changed', name)
    for name in selected['source_sha256']:
        assert (ROOT / name).read_bytes() == (ROOT / selected['source'] / Path(name).name).read_bytes()
    log = r.read(B / 'implementation_console.log')
    assert 'SELECTED_IMPLEMENT_DONE' in log, 'Implementation/reporting incomplete'
    assert (OUT / 'routed.dcp').is_file()
    assert 'ERROR:' not in log, 'Inspect implementation errors before publishing'
    metrics = dict(re.findall(r'^(\w+)=([-\d.]+)\s*$', r.read(OUT / 'metrics.txt'), re.M))
    internal = dict(WNS_ns=float(metrics['REGISTER_TO_REGISTER_WNS_NS']),
                    WHS_ns=float(metrics['REGISTER_TO_REGISTER_WHS_NS']))
    resource = r.resource(OUT / 'util.rpt')
    assert resource['DSP'] == 64 and resource['RAMB18'] == 48 and resource['RAMB36'] == 0
    for key, value in [('ROOT_RAMB18', 16), ('DATA_RAMB18', 32), ('DSP48', 64), ('BLACKBOX', 0)]:
        assert int(metrics[key]) == value, (key, metrics[key])
    route = r.read(OUT / 'route_status.rpt')
    route_counts = {}
    for line in route.splitlines():
        m = re.search(r'# of\s+(.+?)\s*:\s*(\d+)', line, re.I)
        if m:
            route_counts[m[1].strip(' .')] = int(m[2])
    bad = {k: v for k, v in route_counts.items()
           if re.search(r'unrouted|routing errors|partially routed|conflicts', k, re.I) and v}
    full = r.summary(OUT / 'timing.rpt')
    drc = r.read(OUT / 'drc.rpt')
    drc_rules = [dict(rule=rule, severity=severity.strip(), description=description.strip(), count=int(count))
        for rule, severity, description, count in re.findall(
            r'^\|\s*(\S+)\s*\|\s*(Warning|Critical Warning|Error)\s*\|\s*([^|]+)\|\s*(\d+)\s*\|', drc, re.M)]
    assert drc_rules, 'Missing DRC summary'
    assert not any(x['severity'] in ('Error', 'Critical Warning') for x in drc_rules), drc_rules
    assert route_counts['fully routed nets'] == route_counts['routable nets']
    assert route_counts['nets with routing errors'] == 0
    result = dict(kind='single fast timing-driven OOC place and route',
        selected_synthesis_LUT=37917, part='xczu7ev-ffvc1156-2-e', clock_ns=5.0,
        place_directive='AltSpreadLogic_high', route_directive='RuntimeOptimized',
        resource=resource, full_boundary_timing=full, internal_timing=internal,
        critical_internal_setup=r.path(OUT / 'internal_setup.rpt'),
        critical_internal_hold=r.path(OUT / 'internal_hold.rpt'),
        critical_boundary_setup=r.path(OUT / 'timing.rpt'), drc_rules=drc_rules,
        route_status_counts=route_counts, route_issues=bad,
        internal_200MHz_setup_hold_pass=internal['WNS_ns'] >= 0 and internal['WHS_ns'] >= 0 and not bad,
        source_unchanged=True, production_RTL_changed=False, packed16_retained=True,
        numeric_cases=selected['numeric_cases'], four_state_cases=selected['four_state_cases'],
        C_transform_calls=selected['C_transform_calls'], verified_signatures=selected['verified_signatures'],
        physical_approval='pending_user_review',
        limitations=[
            'OOC core including host and root; no board/partition pin placement or bitstream.',
            'Boundary timing uses 1/0 ns max/min I/O delays, not a board interface model.',
            'Register-to-register setup/hold is reported separately from boundary paths.',
            'Route status reports one explicit gap and 476 implicitly routed ports in this OOC design.',
            'One fast routing attempt; not an exhaustive physical optimization.',
            'Correctness evidence belongs to the unchanged RTL; no post-route gate-level simulation.',
        ])
    artifacts = [HERE/'implement.tcl', HERE/'selected_manifest.json', B/'implementation_console.log']
    artifacts += [OUT/name for name in ('routed.dcp','run_config.txt','constraints.xdc','util.rpt',
                   'util_hier.rpt','route_status.rpt','timing.rpt','drc.rpt',
                   'internal_setup.rpt','internal_hold.rpt','metrics.txt')]
    result['sha256'] = {p.relative_to(ROOT).as_posix(): sha(p) for p in artifacts}
    target = ROOT / 'study/results/a_cg_prepare_route'
    target.with_suffix('.json').write_text(json.dumps(result, indent=2)+'\n')
    verdict = 'PASS' if result['internal_200MHz_setup_hold_pass'] else 'FAIL'
    lines = ['# Selected prepare_split: physical review', '',
        'The exact 37,917-LUT synthesis candidate was frozen and implemented once.', '',
        '| Metric | After routing |', '|---|---:|',
        *[f'| {key} | {value:,} |' for key,value in resource.items()],
        f"| Internal setup WNS at 5 ns | {internal['WNS_ns']:+.3f} ns |",
        f"| Internal hold WHS | {internal['WHS_ns']:+.3f} ns |",
        f"| Full-boundary setup WNS | {full['WNS_ns']:+.3f} ns |",
        f"| Full-boundary hold WHS | {full['WHS_ns']:+.3f} ns |", '',
        f'Internal 200 MHz setup and hold: **{verdict}**. User approval remains pending.', '',
        'Routing: 59,304/59,304 routable nets fully routed, zero nets with routing errors.',
        'OOC status also reports one explicit gap and 476 implicitly routed ports; no board interface is implemented.',
        'DRC: zero errors; 64 DSP input-pipeline warnings and one no-routable-loads warning for boundary outputs.', '',
        'Includes host, 16 root RAMB18, 32 data RAMB18 and packed16. RTL and numerical contracts are unchanged.',
        'Prior checks: 1,026 numeric cases; 38 four-state cases; 74 live C transform calls; 4 verified signatures.', '',
        'Placement: AltSpreadLogic_high. Routing: RuntimeOptimized. Constraints: 5 ns clock,',
        '0.100/0.050 ns setup/hold uncertainty, 1/0 ns max/min I/O delay.', '',
        '## Critical internal setup path', '',
        '```json', json.dumps(result['critical_internal_setup'], indent=2), '```', '',
        'The internal worst path is the core state decoder to a tile synchronous reset:',
        '`state_reg[2] -> engine[12].u_tile/wbi_reg[0]/R`.',
        'Its 5.257 ns data delay contains 5.030 ns routing (95.682%) and 0.227 ns logic.',
        'There are also failing paths beyond reset: an engine[0] to engine[6] path at -0.207 ns',
        'and a tile arithmetic-input path at -0.173 ns. Fixing reset alone does not establish closure.', '',
        'The full-design worst setup path is `cfg_logn[0] -> planes_reg[1]/D` (-3.831 ns).',
        'It is an actual configuration path as well as an OOC-boundary path; it cannot simply be ignored.',
        'The configuration interface needs a defined physical/register boundary before system signoff.', '',
        '## Scope', '', *['- '+x for x in result['limitations']], '',
        'See `study/build/a_cg_prepare_route/fast/` for the routed checkpoint, routing status, DRC,',
        'utilization and separate internal/boundary timing reports. See the JSON companion for hashes.', '']
    target.with_suffix('.md').write_text('\n'.join(lines))
    print(json.dumps({k:result[k] for k in ('resource','internal_timing','full_boundary_timing',
          'internal_200MHz_setup_hold_pass','route_issues')}, indent=2))

if __name__ == '__main__':
    main()
