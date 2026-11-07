"""Audit full-system routed timing, including all paths, not a register-only filter."""
import hashlib
import json
import re
from pathlib import Path
from validate import main as functional_gate, ROOT, HERE, BUILD, read


def main():
    functional_gate()
    protected = json.loads(read(ROOT / 'study/build/a_cg_z020_perf160/protected_source_manifest.json'))
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest for p, digest in protected.items())
    route = BUILD / 'route'
    timing = read(route / 'timing.rpt')
    lines = timing.splitlines()
    for i, line in enumerate(lines):
        if 'WNS(ns)' in line and 'TNS Failing Endpoints' in line:
            for row in lines[i + 1:i + 5]:
                parts = row.split()
                if len(parts) == 12 and re.fullmatch(r'-?\d+\.\d+', parts[0]):
                    values = parts
                    break
            else:
                continue
            break
    else:
        raise AssertionError('Full design timing summary missing')
    wns, tns, ns, ts, whs, ths, nh, th, pw, tpw, npw, total_pw = values
    assert int(ts) > 0 and int(th) > 0 and int(total_pw) > 0
    check = read(route / 'check_timing.rpt')
    assert re.search(r'There are 0 register/latch pins with no clock', check)
    assert re.search(r'There are 0 register/latch pins with constant_clock', check)
    assert 'There are 0 pins that are not constrained for maximum delay.' in check
    for description in ('input ports with no input delay specified', 'ports with no output delay specified',
                        'register/latch pins with multiple clocks', 'generated clocks that are not connected to a clock source',
                        'combinational loops in the design', 'input ports with partial input delay specified',
                        'ports with partial output delay specified'):
        assert f'There are 0 {description}' in check, description
    assert 'All paths are Safely Timed.' in read(route / 'cdc.rpt')
    drc = read(route / 'drc.rpt')
    error_blocks = re.findall(r'^\S+#\d+\s+Error\s*$', drc, re.M)
    metrics = dict(line.split('=', 1) for line in read(route / 'metrics.txt').splitlines())
    assert metrics['BLACKBOX'] == '0' and metrics['PS7'] == '1' and metrics['MMCM'] == '1'
    assert metrics['DSP48'] == '64' and metrics['RAMB18'] == '48'
    resources = {}
    util = read(route / 'util.rpt')
    for key, label in [('lut', 'Slice LUTs'), ('ff', 'Slice Registers'), ('dsp', 'DSPs'), ('ramb18', 'RAMB18')]:
        m = re.search(r'\|\s*' + label + r'\*?\s*\|\s*([\d,]+)', util)
        assert m, label
        resources[key] = int(m[1].replace(',', ''))
    route_status = read(route / 'route_status.rpt')
    def number(label):
        return int(re.search(re.escape(label) + r'\.+\s*:\s*(\d+)', route_status)[1])
    routed = number('# of fully routed nets')
    routable = number('# of routable nets')
    errors = number('# of nets with routing errors')
    passed = (float(wns) >= 0 and float(whs) >= 0 and float(pw) >= 0
              and int(ns) == int(nh) == int(npw) == 0
              and int(metrics['SETUP_FAILING']) == int(metrics['HOLD_FAILING']) == 0
              and not error_blocks and routed == routable and errors == 0
              and resources['lut'] <= 35000)
    result = dict(full_timing_pass=passed, target_mhz=160, setup_wns_ns=float(wns), hold_whs_ns=float(whs),
                  pulse_width_slack_ns=float(pw), setup_failing=int(ns), hold_failing=int(nh),
                  pulse_width_failing=int(npw), resources=resources, routed_nets=routed,
                  routable_nets=routable, routing_errors=errors, drc_error_blocks=len(error_blocks),
                  scope='PS7 + OCM/JTAG + AXI interconnect + AXI-Lite bridge + MMCM/reset + core; DDR/peripherals disabled',
                  hardware_tested=False)
    result['protected_sources_unchanged'] = True
    (BUILD / 'signoff_results.json').write_text(json.dumps(result, indent=2))
    manifest = {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p.name != 'README.md'}
    (BUILD / 'source_manifest.json').write_text(json.dumps(manifest, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
