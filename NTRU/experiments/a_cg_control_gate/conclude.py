"""Summarize measured control-path attempts without promoting failed timing."""
from pathlib import Path
import hashlib
import json

ROOT=Path(__file__).resolve().parents[2]

def main():
    names=[('Retained baseline','a_cg_prepare_route'),
           ('Local reset + combined config FSM','a_cg_control'),
           ('Private config pipeline','a_cg_control_pipe'),
           ('Private pipeline + redundant host gate removed','a_cg_control_gate')]
    records=[]
    for label,name in names:
        p=ROOT/f'study/results/{name}.json'
        r=json.loads(p.read_text())
        for path,digest in r['sha256'].items():
            assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,('Evidence changed',path)
        assert r['resource']['DSP']==64 and r['resource']['RAMB18']==48
        records.append((label,r))
    final=records[-1][1]
    assert not final['internal_200MHz_setup_hold_pass']
    assert max(records,key=lambda x:x[1]['internal_timing']['WNS_ns'])[0]=='Retained baseline'
    v=final['validation']
    for key,value in [('numeric_cases',1026),('four_state_cases',38),('reset_abort_modes',12),
                      ('live_C_calls',74),('verified_signatures',4),('identical_C_artifacts',14)]:
        assert v[key]==value,(key,v[key])
    assert v['kernel_cycles_identical'] and not v['production_RTL_changed']
    pinned=json.loads((ROOT/'experiments/a_cg_control_gate/manifest.json').read_text())
    for p,h in pinned['source_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    for p,h in pinned['baseline']['production_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    fanin=(ROOT/'study/build/a_cg_control_gate/synth/host_ce_fanin.txt').read_text()
    assert 'CHECKED_REGISTERS=10' in fanin and 'CFG_PIPE_DEPENDENCIES=0' in fanin
    rows=['# Control-path optimization: measured conclusion','',
        '**No tested control prototype closes internal timing at 200 MHz. Do not promote these experiments.**',
        'The retained baseline is also not closed at 200 MHz; it remains the best measured internal setup point.',
        'Production RTL and the selected immutable source are unchanged.','',
        '| Routed design, same 5 ns target | LUT | FF | Internal setup WNS | Internal hold WHS |',
        '|---|---:|---:|---:|---:|']
    for label,r in records:
        a=r['resource'];t=r['internal_timing']
        rows.append(f"| {label} | {a['LUT']:,} | {a['FF']:,} | {t['WNS_ns']:+.3f} ns | {t['WHS_ns']:+.3f} ns |")
    rows += ['', 'All include the host and roots, packed16, all FFT precision modes, 64 DSP and 48 RAMB18.', '',
        '## What was established','',
        '- Local tile reset distribution has positive leaf setup slack in the last prototype (+1.016 ns).',
        '  Its upstream state-to-reset-register feed still fails (-0.637 ns), so the complete reset path is not closed.',
        '- The redundant cfg_pipe-to-host_line clock-enable dependency is absent from all ten host_line registers',
        '  in the synthesized netlist. This fixes that dependency, not the entire command frontend.',
        '- The new worst internal path is cfg_pipe_reg[0] to engine[8].root_mem_reg/WEBWE[2]:',
        '  -2.940 ns slack, 7.248 ns data delay, of which 6.976 ns (96.247%) is routing.',
        '- Other near-worst paths remain: state to host_direction (-2.913 ns) and cfg_pipe to descriptor CE (-2.911 ns).',
        '  Fixing only root WE would therefore not establish 200 MHz.', '',
        'These are register-to-register failures. Missing OOC partition-pin locations do not remove those failures.',
        'Full-boundary setup/hold is -2.940/-2.415 ns; external-interface timing also remains incomplete.', '',
        '## Correctness and contracts','',
        'The last source passes 1,026 frozen numeric vectors, 38 four-state cases, 12 reset-abort/restart mode groups,',
        '74 live C transform replacements, four independent signature verifications and 14 byte-identical C artifacts.',
        'Conflicting commands are driven during configuration preparation and the no-exposure invariant is checked.',
        'Tile arithmetic is unchanged apart from a preservation attribute on a control register. No precision or',
        'modular arithmetic has been approximated. Kernel cycle counts match the retained source in every vector.',
        'Configuration preparation adds five clocks per accepted configuration. These are RTL correctness checks,',
        'not evidence of correct silicon operation at a clock that fails timing.', '',
        '## Design implication','',
        'The next architectural candidate should register complete accepted command transactions (valid/type,',
        'destination, address and data together) before fan-out to root/descriptor storage and host state.',
        'Distributed registered write strobes and a bounded reset broadcast tree are needed; adding a shared',
        'pending condition to distant memory/host enables creates long timing paths.',
        'Root commit/drain ordering and any new interface latency must be specified and checked before another',
        'implementation attempt. This frontend revision has not been implemented or measured here.', '',
        'Evidence: study/results/a_cg_control_gate.{md,json} and study/build/a_cg_control_gate/route/.',
        'The final routed checkpoint is retained for inspection; no bitstream or board deployment was performed.', '']
    out=ROOT/'study/results/a_cg_control_conclusion.md'
    out.write_text('\n'.join(rows))
    print('Control timing conclusion verified; no baseline promotion; production hashes unchanged.')
    print(out)

if __name__=='__main__':main()
