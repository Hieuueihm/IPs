"""Compare actual physical results to the retained prepare_split checkpoint."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_control_gate'
R=B/'route'
spec=importlib.util.spec_from_file_location('previous_reports',ROOT/'experiments/a_cg_timing/report.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def paths(file):
    result=[]
    for block in re.split(r'(?=^Slack \()',prior.read(file),flags=re.M):
        slack=re.match(r'Slack \([^)]*\)\s*:\s*([-\d.]+)ns',block)
        if not slack:continue
        row={'slack_ns':float(slack[1])}
        for name,label in [('source','Source'),('destination','Destination'),('delay','Data Path Delay'),('levels','Logic Levels')]:
            m=re.search(r'^\s*'+label+r':\s*([^\r\n]+)',block,re.M)
            row[name]=m[1].strip() if m else None
        result.append(row)
    return result

def main():
    gate_spec=importlib.util.spec_from_file_location('gate',HERE/'validate.py')
    gate=importlib.util.module_from_spec(gate_spec);gate_spec.loader.exec_module(gate);gate.main()
    validation=json.loads((B/'validation.json').read_text())
    assert 'CONTROL_IMPLEMENT_DONE' in prior.read(B/'implementation_console.log')
    assert 'ERROR:' not in prior.read(B/'implementation_console.log')
    assert (R/'routed.dcp').is_file()
    metrics=dict(re.findall(r'^(\w+)=([-\d.]+)\s*$',prior.read(R/'metrics.txt'),re.M))
    for name,value in [('ROOT_RAMB18',16),('DATA_RAMB18',32),('DSP48',64),('BLACKBOX',0),('LOCAL_RESETS',16),('LOCAL_CONFIGS',16)]:
        assert int(metrics[name])==value,(name,metrics[name])
    resource=prior.resource(R/'util.rpt')
    assert resource['DSP']==64 and resource['RAMB18']==48 and resource['RAMB36']==0
    internal=dict(WNS_ns=float(metrics['REGISTER_TO_REGISTER_WNS_NS']),WHS_ns=float(metrics['REGISTER_TO_REGISTER_WHS_NS']))
    route_counts={m[1].strip(' .'):int(m[2]) for m in re.finditer(r'# of\s+(.+?)\s*:\s*(\d+)',prior.read(R/'route_status.rpt'))}
    assert route_counts['fully routed nets']==route_counts['routable nets']
    assert route_counts['nets with routing errors']==0
    drc=[dict(rule=a,severity=b,description=c.strip(),count=int(d)) for a,b,c,d in re.findall(
        r'^\|\s*(\S+)\s*\|\s*(Warning|Critical Warning|Error)\s*\|\s*([^|]+)\|\s*(\d+)\s*\|',prior.read(R/'drc.rpt'),re.M)]
    assert drc and not any(x['severity'] in ('Error','Critical Warning') for x in drc)
    parent=json.loads((ROOT/'study/results/a_cg_prepare_route.json').read_text())
    combined=json.loads((ROOT/'study/results/a_cg_control.json').read_text())
    pending_gate=json.loads((ROOT/'study/results/a_cg_control_pipe.json').read_text())
    full=prior.summary(R/'timing.rpt')
    result=dict(kind='local reset and staged configuration: actual OOC place and route',clock_ns=5,
        part='xczu7ev-ffvc1156-2-e',resource=resource,synthesis_resource=validation['synthesis_resource'],
        internal_timing=internal,full_boundary_timing=full,
        internal_200MHz_setup_hold_pass=internal['WNS_ns']>=0 and internal['WHS_ns']>=0,
        whole_boundary_200MHz_setup_hold_pass=full['WNS_ns']>=0 and full['WHS_ns']>=0,
        internal_setup_paths=paths(R/'internal_setup.rpt'),internal_hold_paths=paths(R/'internal_hold.rpt'),
        reset_feed_paths=paths(R/'reset_feed.rpt'),reset_tree_paths=paths(R/'reset_tree.rpt'),
        config_boundary_paths=paths(R/'config_boundary.rpt'),
        route_status_counts=route_counts,drc_rules=drc,validation=validation,
        parent_resource=parent['resource'],parent_internal_timing=parent['internal_timing'],
        configuration_sequencer_separate_from_compute_FSM=True,
        redundant_host_pending_gate_removed=True,
        combined_FSM_attempt=dict(resource=combined['resource'],internal_timing=combined['internal_timing']),
        pending_gate_attempt=dict(resource=pending_gate['resource'],internal_timing=pending_gate['internal_timing']),
        delta_LUT=resource['LUT']-parent['resource']['LUT'],
        delta_internal_setup_ns=round(internal['WNS_ns']-parent['internal_timing']['WNS_ns'],3),
        place_directive='AltSpreadLogic_high',route_directive='RuntimeOptimized',
        production_RTL_changed=False,physical_approval='pending_user_review',
        limitations=['OOC core includes host and roots, with no physical board/partition pin placement.',
            'Global boundary timing uses unchanged max/min I/O delay 1/0 ns; inspect both setup and hold.',
            'Positive internal timing alone is not a board or complete interface timing signoff.',
            'RTL correctness checked with frozen vectors and live C kernel replay; no post-route gate simulation.',
            'Configuration acceptance requires five additional setup clocks before cfg_ready returns.'])
    artifacts=[HERE/'manifest.json',HERE/'implement.tcl',B/'validation.json',B/'implementation_console.log',B/'synth/host_ce_fanin.txt']
    artifacts += [R/x for x in ('routed.dcp','timing.rpt','internal_setup.rpt','internal_hold.rpt','reset_feed.rpt',
        'reset_tree.rpt','config_boundary.rpt','util.rpt','util_hier.rpt','metrics.txt','route_status.rpt',
        'drc.rpt','reset_distribution.txt','constraints.xdc','run_config.txt')]
    result['sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in artifacts}
    target=ROOT/'study/results/a_cg_control_gate'
    target.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    verdict='PASS' if result['internal_200MHz_setup_hold_pass'] else 'FAIL'
    lines=['# Local reset and staged config: physical review','',
        f'Internal register timing at 5 ns: **{verdict}**. User approval pending.','',
        '| Metric | Retained baseline after route | Control prototype after route |','|---|---:|---:|',
        *[f"| {k} | {parent['resource'][k]:,} | {v:,} |" for k,v in resource.items()],
        f"| Internal setup WNS | {parent['internal_timing']['WNS_ns']:+.3f} ns | {internal['WNS_ns']:+.3f} ns |",
        f"| Internal hold WHS | {parent['internal_timing']['WHS_ns']:+.3f} ns | {internal['WHS_ns']:+.3f} ns |",'',
        f"Full-boundary setup/hold: **{full['WNS_ns']:+.3f}/{full['WHS_ns']:+.3f} ns**.",
        'Boundary paths are included in that number. OOC partition pin positions are undefined;',
        'do not interpret internal closure as a complete interface or board signoff.','',
        '## Changes and correctness','',
        'Sixteen local reset registers and sixteen local configuration strobes retain the original compute phases.',
        'The captured configuration is decoded in five setup clocks. No butterfly, precision, modular reduction,',
        'rounding or kernel schedule changes. Per-tile sign-control registers are preserved against merging.','',
        'Configuration setup uses a private five-bit valid pipeline, so it adds no states to the compute/host FSM.',
        'The prior combined-FSM prototype is retained separately in `experiments/a_cg_control/`.','',
        'The redundant pending gate on host acceptance has been removed. Configured stays zero during all five',
        'setup clocks; simulation checks this invariant while conflicting commands are asserted.',
        'Synthesis requires zero cfg_pipe registers in the combinational fan-in of every host_line clock enable.','',
        'All 1,026 frozen vectors match; 38 four-state cases pass; 12 reset-abort/restart mode groups pass.',
        'Configuration pins are changed immediately after acceptance to check capture semantics.',
        'All kernel cycle counts are identical; host setup adds exactly five clocks per configuration.',
        'Live C replay: 74 transform calls, four independently verified signatures and 14 byte-identical artifacts.',
        'Packed16, runtime moduli, FFT32/64/128 and native64 are retained. Production RTL is unchanged.','',
        '## Critical internal setup paths','',
        '```json',json.dumps(result['internal_setup_paths'][:5],indent=2),'```','',
        '## Reset distribution and configuration','',
        '```json',json.dumps({k:result[k][:2] for k in ('reset_feed_paths','reset_tree_paths','config_boundary_paths')},indent=2),'```','',
        '## Physical scope','',
        'The same placement and fast timing-driven routing directives are used as the retained baseline.',
        'All routable nets are fully routed with zero routing errors. See raw route status for OOC gaps/ports.',
        'DRC summary: '+json.dumps(drc)+'.','',
        *['- '+x for x in result['limitations']],'',
        'Raw reports and checkpoints: `study/build/a_cg_control_gate/route/`. JSON companion includes evidence hashes.','']
    target.with_suffix('.md').write_text('\n'.join(lines))
    print(json.dumps({k:result[k] for k in ('resource','internal_timing','full_boundary_timing','internal_200MHz_setup_hold_pass')},indent=2))

if __name__=='__main__':main()
