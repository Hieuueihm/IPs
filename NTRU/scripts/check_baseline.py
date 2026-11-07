"""Read-only verification of the user-accepted source and measured evidence."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'experiments/BASELINE.json'


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=MANIFEST)
    parser.add_argument('--workflow-snapshot',type=Path,help='Archived original workflow bytes for a historical manifest')
    args=parser.parse_args()
    baseline = json.loads(args.manifest.read_text(encoding='utf-8'))
    assert baseline['status'] == 'accepted'
    problems = []
    for group in ('source_sha256', 'workflow_sha256', 'evidence_sha256'):
        for name, expected in baseline[group].items():
            path = (args.workflow_snapshot / name) if group=='workflow_sha256' and args.workflow_snapshot else ROOT / name
            if not path.is_file():
                problems.append(f'MISSING {name}')
            elif digest(path) != expected:
                problems.append(f'CHANGED {name}')
    if problems:
        print('\n'.join(problems))
        raise SystemExit('BASELINE_CHECK_FAILED: restore pinned assets or review a new revision; do not replace hashes to bypass this check.')
    measured = json.loads((ROOT / baseline['results']).read_text())
    for key, value in baseline['measured'].items():
        assert measured[key] == value, (key, measured[key], value)
    assert measured['full_timing_pass'] and not measured['hardware_tested']
    if baseline.get('schema_version',1)>=2:
        assert measured['signoff_pass'] and measured['implementation_clean'] and measured['cdc_safe']
        assert measured['unconstrained_endpoints']==measured['drc_errors']==measured['routing_errors']==0
        assert measured['resources']['lut']<=baseline['lut_budget']
        assert measured['routed_nets']==measured['routable_nets']
        assert measured['resources']['dsp']==64 and measured['resources']['ramb18']==48
        for canonical,provider in baseline['equivalent_source_directories']:
            for p in (ROOT/canonical).iterdir():
                if p.is_file():assert p.read_bytes()==(ROOT/provider/p.name).read_bytes(),p.name
    functional = json.loads((ROOT / baseline['functional_results']).read_text())
    for key, value in baseline['functional'].items():
        assert functional[key] == value, (key, functional[key], value)
    timing = (ROOT / baseline['timing_report']).read_text(encoding='utf-8-sig')
    assert 'All user specified timing constraints are met.' in timing
    rows = re.findall(r'^\s*([\d.-]+)\s+([\d.-]+)\s+(\d+)\s+(\d+)\s+([\d.-]+)\s+([\d.-]+)\s+(\d+)\s+(\d+)\s+([\d.-]+)\s+([\d.-]+)\s+(\d+)\s+(\d+)\s*$', timing, re.M)
    row = rows[0]
    assert (float(row[0]), float(row[4]), float(row[8])) == (measured['setup_wns_ns'], measured['hold_whs_ns'], measured['pulse_width_slack_ns'])
    assert int(row[2]) == int(row[6]) == int(row[10]) == 0
    assert int(row[3]) == int(row[7]) == baseline['timed_endpoints']
    print(f"BASELINE_CHECK_PASS {baseline['id']} accepted={baseline['accepted_on']} spec={baseline['contract_version']}")
    print(f"Full-system STA: {measured['target_mhz']} MHz; LUT={measured['resources']['lut']}; "
          f"setup={measured['setup_wns_ns']:+.3f} ns hold={measured['hold_whs_ns']:+.3f} ns; "
          f"functional cases={functional['cases']}; hardware_tested=False")
    print('Pinned source, workflow and evidence match. No RTL or reports were changed.')


if __name__ == '__main__':
    main()
