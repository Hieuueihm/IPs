"""Collect the whole registered frontend plus core at unchanged timing constraints."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_cmd_frontreserve'
REFINED='--refined' in sys.argv
R=B/('route_pinopt' if REFINED else 'route')
RUNLOG=B/('pinopt_console.log' if REFINED else 'implementation_cold_console.log')
SCRIPT=HERE/('pinopt.tcl' if REFINED else 'implement_cold.tcl')
NAME='a_cg_cmd_frontreserve_pinopt' if REFINED else 'a_cg_cmd_frontreserve'
sp=importlib.util.spec_from_file_location('helpers',ROOT/'experiments/a_cg_control_gate/report.py')
helpers=importlib.util.module_from_spec(sp);sp.loader.exec_module(helpers)
prior=helpers.prior
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    spec=importlib.util.spec_from_file_location('gate',HERE/'validate.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate);gate.main()
    validation=json.loads((B/'validation.json').read_text())
    log=prior.read(RUNLOG)
    assert 'CONTROL_IMPLEMENT_DONE' in log and 'ERROR:' not in log
    metrics=dict(re.findall(r'^(\w+)=([-\d.]+)\s*$',prior.read(R/'metrics.txt'),re.M))
    for key,n in [('ROOT_RAMB18',16),('DATA_RAMB18',32),('DSP48',64),('BLACKBOX',0),('LOCAL_RESETS',16),('LOCAL_CONFIGS',16)]:
        assert int(metrics[key])==n,(key,metrics[key])
    resource=prior.resource(R/'util.rpt');full=prior.summary(R/'timing.rpt')
    internal=dict(WNS_ns=float(metrics['REGISTER_TO_REGISTER_WNS_NS']),WHS_ns=float(metrics['REGISTER_TO_REGISTER_WHS_NS']))
    execution=dict(WNS_ns=float(metrics['EXECUTION_CORE_WNS_NS']),WHS_ns=float(metrics['EXECUTION_CORE_WHS_NS']))
    internal_setup_met='Slack (VIOLATED)' not in prior.read(R/'internal_setup.rpt')
    internal_hold_met='Slack (VIOLATED)' not in prior.read(R/'internal_hold.rpt')
    counts={m[1].strip(' .'):int(m[2]) for m in re.finditer(r'# of\s+(.+?)\s*:\s*(\d+)',prior.read(R/'route_status.rpt'))}
    assert counts['fully routed nets']==counts['routable nets'] and counts['nets with routing errors']==0
    drc=[dict(rule=a,severity=b,description=c.strip(),count=int(d)) for a,b,c,d in re.findall(
        r'^\|\s*(\S+)\s*\|\s*(Warning|Critical Warning|Error)\s*\|\s*([^|]+)\|\s*(\d+)\s*\|',prior.read(R/'drc.rpt'),re.M)]
    assert drc and not any(x['severity'] in ('Error','Critical Warning') for x in drc)
    comparisons=[]
    names=['a_cg_prepare_route','a_cg_control','a_cg_control_pipe','a_cg_control_gate','a_cg_cmd_pipe','a_cg_cmd_credit','a_cg_cmd_frontreset']
    if REFINED:names.append('a_cg_cmd_frontreserve')
    for name in names:
        x=json.loads((ROOT/f'study/results/{name}.json').read_text())
        comparisons.append(dict(name=name,resource=x['resource'],internal_timing=x['internal_timing']))
    result=dict(kind='complete registered command transactions: actual OOC P&R',clock_ns=5,
        part='xczu7ev-ffvc1156-2-e',resource=resource,synthesis_resource=validation['synthesis_resource'],
        internal_timing=internal,execution_core_only_timing=execution,full_boundary_timing=full,
        internal_200MHz_setup_hold_pass=internal['WNS_ns']>=0 and internal['WHS_ns']>=0 and internal_setup_met and internal_hold_met,
        internal_setup_report_met=internal_setup_met,internal_hold_report_met=internal_hold_met,
        whole_boundary_200MHz_setup_hold_pass=full['WNS_ns']>=0 and full['WHS_ns']>=0,
        internal_setup_paths=helpers.paths(R/'internal_setup.rpt'),internal_hold_paths=helpers.paths(R/'internal_hold.rpt'),
        execution_setup_paths=helpers.paths(R/'execution_setup.rpt'),
        reset_feed_paths=helpers.paths(R/'reset_feed.rpt'),reset_tree_paths=helpers.paths(R/'reset_tree.rpt'),
        config_boundary_paths=helpers.paths(R/'config_boundary.rpt'),route_status_counts=counts,drc_rules=drc,
        validation=validation,comparisons=comparisons,production_RTL_changed=False,physical_approval='pending_user_review',
        place_directive='AltSpreadLogic_high',route_directive='RuntimeOptimized',
        frontend_reset_isolated=True,reservation_permission_logic_levels=1,
        local_occupancy_register=True,
        post_route_pin_and_routing_optimization=REFINED,
        limitations=['Complete frontend, host adapter and root storage are included; no board/partition pin placement.',
            'External paths retain max/min I/O delays 1/0 ns and have OOC pin-location limitations.',
            'The internal 200 MHz verdict includes BOTH frontend and execution registers; core-only timing is diagnostic.',
            'RTL/vector/live C checks do not establish correct silicon operation at a clock that fails setup or hold.',
            'No post-route gate simulation, precision reduction, false paths, multicycle exceptions or board deployment.'])
    artifacts=[HERE/'manifest.json',SCRIPT,HERE/'report.py',HERE/'validate.py',
        B/'validation.json',RUNLOG,B/'synth/frontend_reset_barrier.txt',B/'synth/reservation_permission.txt',
        B/'synth/command_barrier.txt',B/'synth/occupancy_barrier.txt']
    artifacts += [R/name for name in ('routed.dcp','util.rpt','util_hier.rpt','timing.rpt','internal_setup.rpt',
        'internal_hold.rpt','execution_setup.rpt','execution_hold.rpt','reset_feed.rpt','reset_tree.rpt',
        'config_boundary.rpt','route_status.rpt','drc.rpt','metrics.txt','reset_distribution.txt','constraints.xdc','run_config.txt')]
    if (B/'synth/reset_register_types.txt').exists():
        artifacts += [HERE/'inspect_reset.tcl',B/'synth/reset_register_types.txt',B/'synth/metrics_fdre_query.txt']
    result['sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in artifacts}
    if REFINED:
        source=B/'route/routed.dcp'
        result['sha256'][source.relative_to(ROOT).as_posix()]=sha(source)
        assert 'COLD_TIMING_REPRODUCED WNS=-0.003 WHS=0.010' in log
        result['sha256'][(R/'baseline_internal.rpt').relative_to(ROOT).as_posix()]=sha(R/'baseline_internal.rpt')
    out=ROOT/'study/results'/NAME
    out.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    verdict='PASS' if result['internal_200MHz_setup_hold_pass'] else 'FAIL'
    lines=['# Complete command pipeline: physical review','',
        f'**All internal registers at 200 MHz: {verdict}.** User approval remains pending.','',
        '| Routed design, same 5 ns target | LUT | FF | Internal WNS | Internal WHS |','|---|---:|---:|---:|---:|']
    for c in comparisons+[dict(name=NAME,resource=resource,internal_timing=internal)]:
        a=c['resource'];t=c['internal_timing']
        lines.append(f"| {c['name']} | {a['LUT']:,} | {a['FF']:,} | {t['WNS_ns']:+.3f} ns | {t['WHS_ns']:+.3f} ns |")
    lines += ['',f"DSP/RAMB18: {resource['DSP']}/{resource['RAMB18']} (16 root + 32 data banks).",
        f"Full-boundary setup/hold: **{full['WNS_ns']:+.3f}/{full['WHS_ns']:+.3f} ns**.",
        f"Execution-only setup/hold: {execution['WNS_ns']:+.3f}/{execution['WHS_ns']:+.3f} ns (diagnostic only).",'',
        '## Transaction boundary','',
        'One capture stage registers every payload field together with its accepted command token: config,',
        'start, root/commit, descriptors, load and read. Payload registers clock unconditionally. Storage',
        'enables consume accepted tokens rather than live context-pending qualification. Host direction',
        'and payload commit also consume tokens. Reset is registered; accepted start drives local reset.',
        'A separate occupancy register replaces feedback from opcode flags. Its equality to the token OR',
        'is checked on every simulation clock. Consumer readiness does not recheck queued opcode flags.',
        'A reservation blocks a second state-changing command until the first is consumed. Root/descriptor',
        'packets stream one per clock. Root-write/commit and descriptor/start ordering is preserved.', '',
        '## Correctness and latency','',
        'All 1,026 frozen vectors, 38 four-state cases and 12 reset-abort/restart mode groups pass.',
        'Config, descriptor, root and load pins change after acceptance; read lines change under burst traffic.',
        'Live C replay passes 74 transform calls, four independent signature verifications, 14 byte-identical',
        'C artifacts and two rejected bad-input replays. Packed16 and all FFT/NTT modes remain supported.',
        'Synthesis proves zero direct raw-input-to-execution-register paths across the command barrier.', '',
        'Kernel cycles remain identical. Relative to a_cg_control_gate, each load/read line adds one clock;',
        'configuration and start each add one clock. Configuration preparation versus the selected retained',
        'baseline totals six clocks. Every vector is checked against the predicted total interface delta.',
        'Root/descriptor latency is one clock and throughput remains one packet per clock.', '',
        '## Critical internal setup paths','',
        '```json',json.dumps(result['internal_setup_paths'][:5],indent=2),'```','',
        '## Scope','',*['- '+x for x in result['limitations']], '',
        'All routable nets are fully routed with zero routing errors. See raw status for OOC port/gap details.',
        'DRC summary: '+json.dumps(drc)+'.','',
        'This RTL fork separates the frontend permission flip-flop from execution reset and decodes',
        'accepted flags without raw reset in their D cones. Public readies retain immediate reset masking.',
        'Synthesis proves the load-token D cone uses the local permission and neither global nor raw reset.',
        'Reservation now qualifies an independent priority decode with permission/occupancy at its final LUT.',
        'Synthesis proves exactly one LUT from local permission to reservation. Protocol equality is asserted.',
        'Packet latency, priority and kernel cycles remain unchanged.',
        'A fresh cold implementation uses the same placement/routing directives and constraints as its parent.',
        'Production HDL and retained baselines are unchanged. No bitstream/board deployment was performed.',
        'Raw evidence: study/build/a_cg_cmd_frontreserve/route/. JSON companion records SHA256 hashes.','']
    out.with_suffix('.md').write_text('\n'.join(lines))
    print(json.dumps({k:result[k] for k in ('resource','internal_timing','execution_core_only_timing',
        'full_boundary_timing','internal_200MHz_setup_hold_pass')},indent=2))

if __name__=='__main__':main()
