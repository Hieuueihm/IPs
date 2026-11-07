"""Read measured implementation and functional evidence; never extrapolate Fmax."""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = Path(__file__).resolve().parent
BUILD = ROOT / 'study/build/a_cg_z020_perf160'


def text(path):
    return path.read_text(encoding='utf-8-sig', errors='replace')


def utilization(path):
    report = text(path)
    result = {}
    for label, key in [('Slice LUTs', 'lut'), ('Slice Registers', 'ff'),
                       ('DSPs', 'dsp'), ('RAMB18', 'ramb18')]:
        m = re.search(r'\|\s*' + re.escape(label) + r'\*?\s*\|\s*([\d,]+)', report)
        if m:
            result[key] = int(m[1].replace(',', ''))
    assert 'lut' in result, path
    return result


def cases(path):
    return [dict(re.findall(r'(\w+)=(\S+)', line)) for line in text(path).splitlines()
            if line.startswith('CASE ')]


def main():
    from compare import main as functional_gate
    functional_gate()
    route = BUILD / 'route'
    metrics = dict(line.split('=', 1) for line in text(route / 'metrics.txt').splitlines())
    setup = float(metrics['REGISTER_TO_REGISTER_WNS_NS'])
    hold = float(metrics['REGISTER_TO_REGISTER_WHS_NS'])
    resources = utilization(route / 'util.rpt')
    protected = json.loads(text(BUILD / 'protected_source_manifest.json'))
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in protected.items())
    internal_pass = (setup >= 0 and hold >= 0
                     and not text(route / 'failing_endpoints.txt').strip()
                     and 'Slack (VIOLATED)' not in text(route / 'internal_setup.rpt')
                     and 'Slack (VIOLATED)' not in text(route / 'internal_hold.rpt'))
    assert int(metrics['DSP48']) == 64 and int(metrics['RAMB18']) == 48
    current = cases(BUILD / 'sim.log')
    old = cases(ROOT / 'study/build/a_cg_z020_100mhz/sim.log')
    assert len(current) == len(old) == 1026
    fixtures = json.loads(text(BUILD / 'fixtures.json'))
    rows = []
    for a, b, fixture in zip(current, old, fixtures):
        assert a['errors'] == '0'
        for key in ('packed', 'jobs', 'native', 'fft', 'fmt', 'logn', 'hmin', 'inverse', 'words', 'q'):
            assert a[key] == b[key], (key, a, b)
        rows.append(dict(name=fixture['name'], old_cycles=int(b['cycles']), new_cycles=int(a['cycles']),
                         old_us=int(b['cycles']) / 100, new_us=int(a['cycles']) / 160,
                         old_driver_cycles=int(b['all_host_cycles']), new_driver_cycles=int(a['all_host_cycles'])))
    summary = dict(clock_mhz=160, period_ns=6.25, internal_setup_ns=setup, internal_hold_ns=hold,
                   internal_timing_pass=internal_pass, lut_budget_pass=resources['lut'] <= 35000,
                   resources=resources, kernel_cycles=sum(r['new_cycles'] for r in rows),
                   old_kernel_cycles=sum(r['old_cycles'] for r in rows),
                   aggregate_kernel_speedup=sum(r['old_us'] for r in rows) / sum(r['new_us'] for r in rows),
                   aggregate_test_driver_speedup=1.6 * sum(r['old_driver_cycles'] for r in rows) / sum(r['new_driver_cycles'] for r in rows),
                   protected_sources_unchanged=True, io_scope='OOC: board I/O hold not signed off',
                   application_scope='C application replay with RTL transform substitution, not complete RTL signer')
    (BUILD / 'performance.json').write_text(json.dumps(dict(summary=summary, cases=rows), indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
