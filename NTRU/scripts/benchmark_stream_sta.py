"""Nangate45 reference mapping/STA of the entire 16-tile arithmetic island.

WSL native Yosys/OpenSTA; local dependencies from bootstrap_stream_sta.py.
Does not include SRAM, placement, clock tree, or extracted interconnect.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from arith_experiment_common import ROOT, hashes, check_hashes

BUILD=ROOT/'study/build/stream_sta'
TOOLS=ROOT/'study/tools/stream_sta'
LIB=TOOLS/'NangateOpenCellLibrary_typical.lib'
SOURCES=['hdl/mul_ss.v','hdl/proto/flex_stream_tile.sv','hdl/proto/flex_stream_array.sv','hdl/proto/flex_stream_tops.sv']
TOPS=['stream_plain','stream_stall','stream_buffered']
RESULT=ROOT/'study/results/stream_sta.json'


def checked(cmd,log):
    p=subprocess.run([str(x) for x in cmd],capture_output=True,text=True)
    log.write_text(p.stdout+p.stderr)
    if p.returncode or re.search(r'^Error:',p.stdout+p.stderr,re.M):
        raise RuntimeError(f'{cmd[0]} failed; see {log}')
    return p.stdout+p.stderr


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--yosys',default=str(ROOT/'study/tools/yosys_native/root/usr/bin/yosys'))
    ap.add_argument('--sta',default=str(TOOLS/'root/usr/bin/sta'))
    ap.add_argument('--top',choices=TOPS)
    ap.add_argument('--sta-only',action='store_true',help='Reuse existing mapped netlists after checking RTL timestamps')
    ap.add_argument('--collect',action='store_true',help='Collect validated per-top results without remapping or rerunning STA')
    args=ap.parse_args();BUILD.mkdir(parents=True,exist_ok=True)
    validation=json.loads((ROOT/'study/results/flex_stream_validation.json').read_text())
    check_hashes(validation['source_sha256'])
    manifest=json.loads((TOOLS/'manifest.json').read_text())
    assert hashlib.sha256(LIB.read_bytes()).hexdigest()==manifest['files'][0]['sha256']
    def one(top):
        start=time.monotonic();print('Mapping '+top,flush=True)
        net=BUILD/(top+'.v');stat=BUILD/(top+'_stat.json');ys=BUILD/(top+'.ys')
        constr=BUILD/(top+'_abc.constr')
        constr.write_text('set_driving_cell BUF_X1\nset_load 5.0\n')
        abc=f'abc -fast -liberty {LIB.as_posix()} -constr {constr.as_posix()} -D 10000'
        if top=='flex_stream_banked':
            # ABC map can leave a dangling node on this router network;
            # cleanup preserves observable logic and lets buffer handle it.
            abc_script=BUILD/(top+'_abc.script')
            abc_script.write_text('strash; dretime; retime -o -D 10000; map -D 10000; cleanup; buffer; upsize -D 10000; dnsize -D 10000; stime -p;\n')
            abc=f'abc -liberty {LIB.as_posix()} -constr {constr.as_posix()} -script {abc_script.as_posix()}'
        ys.write_text('\n'.join([
            'read_verilog -sv -I'+(ROOT/'hdl/proto').as_posix()+' '+' '.join((ROOT/s).as_posix() for s in SOURCES),
            f'hierarchy -check -top {top}',f'synth -flatten -noabc -top {top}',
            f'dfflibmap -liberty {LIB.as_posix()}',
            abc,
            'clean',f'tee -q -o {stat.as_posix()} stat -liberty {LIB.as_posix()} -json',
            f'write_verilog -noattr -noexpr {net.as_posix()}']))
        if args.sta_only:
            assert net.exists() and stat.exists()
            assert all((ROOT/s).stat().st_mtime<=net.stat().st_mtime for s in [*SOURCES,'hdl/proto/mont_reduce16_functions.vh']), 'RTL newer than netlist'
        else:
            checked([args.yosys,'-Q','-l',BUILD/(top+'_live.log'),'-s',ys],BUILD/(top+'_synth.log'))
        module=next(iter(json.loads(stat.read_text())['modules'].values()))
        cells={c:n for c,n in module['num_cells_by_type'].items() if c!='$scopeinfo'}
        assert all(not c.startswith('$') for c in cells),cells
        # OpenSTA 2019 accepts a gate netlist subset: export binary constants
        # and simple assignment LHS, removing unused Yosys public debug aliases.
        sta_net=BUILD/(top+'_sta.v');export=BUILD/(top+'_export.ys')
        export_stat=BUILD/(top+'_export_stat.json')
        export.write_text('\n'.join([
            f'read_liberty -lib {LIB.as_posix()}',f'read_verilog {net.as_posix()}',
            f'hierarchy -top {top}','clean -purge',
            f'tee -q -o {export_stat.as_posix()} stat -json {top}',
            f'write_verilog -noattr -noexpr -nohex -nodec -simple-lhs {sta_net.as_posix()}']))
        if not (args.sta_only and sta_net.exists() and export_stat.exists() and sta_net.stat().st_mtime>=net.stat().st_mtime):
            checked([args.yosys,'-Q','-s',export],BUILD/(top+'_export.log'))
        exported=json.loads(export_stat.read_text())['modules']['\\'+top]['num_cells_by_type']
        assert {c:n for c,n in exported.items() if c!='$scopeinfo'}==cells, 'export changed physical cells'
        tcl=BUILD/(top+'.tcl')
        tcl.write_text('\n'.join([
            f'read_liberty {LIB.as_posix()}',f'read_verilog {sta_net.as_posix()}',f'link_design {top}',
            'create_clock -name core_clk -period 10.0 [get_ports clk]',
            'set_clock_uncertainty 0.1 [get_clocks core_clk]',
            'set signal_inputs [get_ports {in_valid ntt width* ntt_mode* profile inverse tag* data* twiddle* out_ready}]',
            'set_input_delay 0.2 -clock core_clk $signal_inputs',
            'set_output_delay 0.2 -clock core_clk [all_outputs]',
            'set_driving_cell -lib_cell BUF_X1 -pin Z $signal_inputs',
            # Liberty capacitance is fF: 5 = 0.005 pF.
            'set_load 5.0 [all_outputs]',
            'set_false_path -from [get_ports rst]',
            'check_setup -verbose',
            'puts {BEGIN_REG_TO_REG}',
            'report_checks -from [all_registers -clock_pins] -to [all_registers -data_pins] -path_delay max -group_count 1 -digits 4',
            'puts {END_REG_TO_REG}',
            'puts {BEGIN_OVERALL}',
            'report_checks -path_delay max -group_count 1 -digits 4',
            'report_worst_slack -digits 4','puts {END_OVERALL}',
            'report_check_types -max_transition -all_violators',
            'exit']))
        output=checked([args.sta,'-no_init','-exit',tcl],BUILD/(top+'_sta.log'))
        rr=output.split('BEGIN_REG_TO_REG\n',1)[1].split('END_REG_TO_REG',1)[0]
        overall=output.split('BEGIN_OVERALL\n',1)[1].split('END_OVERALL',1)[0]
        def parse_report(text):
            arrival=re.search(r'(-?\d+\.\d+)\s+data arrival time',text)
            slack=re.search(r'(-?\d+\.\d+)\s+slack \((?:MET|VIOLATED)\)',text)
            assert arrival and slack,text
            return {'data_arrival_ns':float(arrival[1]),'slack_ns':float(slack[1]),
                    'startpoint':re.search(r'Startpoint: (.+)',text)[1],
                    'endpoint':re.search(r'Endpoint: (.+)',text)[1]}
        row={'top':top,'cell_area_um2':module['area'],'cells':sum(cells.values()),
             'ff_cells':sum(n for c,n in cells.items() if c.startswith(('DFF','SDFF'))),
             'cell_types':cells,'reg_to_reg':parse_report(rr),'overall':parse_report(overall),
             'seconds':round(time.monotonic()-start,1),
             'rtl_sha256':hashes([*SOURCES,'hdl/proto/mont_reduce16_functions.vh']),
             'netlist_sha256':hashlib.sha256(net.read_bytes()).hexdigest(),
             'sta_netlist_sha256':hashlib.sha256(sta_net.read_bytes()).hexdigest()}
        (BUILD/(top+'_result.json')).write_text(json.dumps(row,indent=2)+'\n')
        print(json.dumps({k:v for k,v in row.items() if k!='cell_types'}),flush=True)
        return row
    if args.top and not args.collect:
        one(args.top)
        return
    if args.collect:
        rows=[]
        for top in TOPS:
            row=json.loads((BUILD/(top+'_result.json')).read_text())
            check_hashes(row['rtl_sha256'])
            assert hashlib.sha256((BUILD/(top+'.v')).read_bytes()).hexdigest()==row['netlist_sha256']
            assert hashlib.sha256((BUILD/(top+'_sta.v')).read_bytes()).hexdigest()==row['sta_netlist_sha256']
            rows.append(row)
    else:
        with ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(one,TOPS))
    routed='flex_stream_banked' in TOPS
    result={'library':'NangateOpenCellLibrary typical 45nm, 1.1V, 25C','dependencies':manifest,
            'mapping':'Yosys synth -flatten -noabc; dfflibmap; ABC fast map at D=10000ps (buffer/upsize/dnsize)'+('; dangling-node cleanup before buffer' if routed else ''),
            'constraints':{'clock_period_ns':10,'clock_uncertainty_ns':.1,'io_delay_ns':.2,'output_load_ff':5,
                           'input_driver':'BUF_X1','reset_false_path':True},
            'synthesis':rows,'source_sha256':hashes([*SOURCES,'hdl/proto/mont_reduce16_functions.vh','scripts/benchmark_stream_sta.py',
                                                     'scripts/bootstrap_stream_sta.py',*(['scripts/benchmark_banked_sta.py'] if routed else [])]),
            'limits':['Cell area only; no SRAM, physical placement, extracted RC, CTS, or power.'+('' if routed else ' No bank gather/scatter in these three tops.'),
                      'Includes FFT limb routing, NTT pack selection, sign control, compact reducers, registered fusion, output, optional queue/CE.'+(' Includes bank gather/scatter RTL.' if routed else ''),
                      'All modes statically active in STA; no runtime mode case analysis.',
                      'Clock is a reference constraint, not a user technology/Fmax target.']}
    RESULT.write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
