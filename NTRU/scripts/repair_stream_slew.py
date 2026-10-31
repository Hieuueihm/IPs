"""Repair mapped-bank-island slew with function-identical cell resizing.

Preserves baseline artifacts. No RTL, arithmetic, pipeline or constraints change.
Run in WSL with the same OpenSTA runtime environment as benchmark_stream_sta.py.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
from arith_experiment_common import ROOT,check_hashes,hashes

BUILD=ROOT/'study/build/stream_slew_repair'
BASE=ROOT/'study/build/stream_sta'
LIB=ROOT/'study/tools/stream_sta/NangateOpenCellLibrary_typical.lib'
STA=ROOT/'study/tools/stream_sta/root/usr/bin/sta'
RESULT=ROOT/'study/results/stream_slew_repair.json'


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def block(text,kind,name):
    match=re.search(r'\b'+kind+r'\s*\(\s*'+re.escape(name)+r'\s*\)\s*\{',text)
    assert match,(kind,name)
    start=match.end();depth=1;quote=False;escape=False;i=start
    while depth:
        ch=text[i]
        if quote:
            if escape:escape=False
            elif ch=='\\':escape=True
            elif ch=='"':quote=False
        elif ch=='"':quote=True
        elif text.startswith('/*',i):i=text.index('*/',i+2)+1
        elif ch=='{':depth+=1
        elif ch=='}':depth-=1
        i+=1
    return text[start:i-1]


def library_cell(lib,name):
    body=block(lib,'cell',name)
    assert not re.search(r'\b(?:ff|latch|statetable)\s*\(',body),name
    pins={}
    for pin in re.findall(r'\bpin\s*\(\s*(\w+)\s*\)\s*\{',body):
        p=block(body,'pin',pin)
        direction=re.search(r'\bdirection\s*:\s*(\w+)',p)[1]
        function=re.search(r'\bfunction\s*:\s*"([^"]+)"',p)
        pins[pin]={'direction':direction,'function':re.sub(r'\s+','',function[1]) if function else None}
    return {'area_um2':float(re.search(r'\barea\s*:\s*([\d.]+)',body)[1]),'logic_signature':pins}


def instance(net,name):
    match=re.search(r'^  (\w+) '+re.escape(name)+r' \(([\s\S]*?)\n  \);',net,re.M)
    assert match,name
    pins=dict(re.findall(r'\.(\w+)\((.*?)\)',match[2]))
    return match,match[1],pins


def sta(net_path,label):
    original=(BASE/'flex_stream_banked.tcl').read_text()
    original_path=(BASE/'flex_stream_banked_sta.v').as_posix()
    assert original.count(original_path)==1
    tcl=original.replace(original_path,net_path.as_posix())
    tcl=tcl.replace('report_check_types -max_transition -all_violators',
                    'puts {BEGIN_SLEW}\nreport_check_types -max_transition -all_violators -digits 4\nputs {END_SLEW}')
    path=BUILD/(label+'.tcl');log_path=BUILD/(label+'.log');path.write_text(tcl)
    start=time.monotonic()
    p=subprocess.run([str(STA),'-no_init','-exit',str(path)],capture_output=True,text=True)
    output=p.stdout+p.stderr;log_path.write_text(output)
    assert not p.returncode and not re.search(r'^Error:',output,re.M),log_path
    report=output.split('BEGIN_SLEW\n',1)[1].split('END_SLEW',1)[0]
    violations=[{'pin':pin,'limit_ns':float(limit),'transition_ns':float(trans),'slack_ns':float(slack)}
                for pin,limit,trans,slack in re.findall(r'^(\S+)\s+([\d.]+)\s+([\d.]+)\s+(-?[\d.]+)\s+\(VIOLATED\)',report,re.M)]
    def timing(marker,end):
        text=output.split(marker+'\n',1)[1].split(end,1)[0]
        return {'data_arrival_ns':float(re.search(r'(-?\d+\.\d+)\s+data arrival time',text)[1]),
                'slack_ns':float(re.search(r'(-?\d+\.\d+)\s+slack \((?:MET|VIOLATED)\)',text)[1]),
                'startpoint':re.search(r'Startpoint: (.+)',text)[1],
                'endpoint':re.search(r'Endpoint: (.+)',text)[1]}
    # Full timing coverage must stay the same as the previously audited baseline.
    warning=re.search(r'Warning: There (?:are|is) (\d+) unconstrained endpoints?',output)
    assert warning and int(warning[1])==64
    assert 'no clock' not in output.lower() and 'combinational loop' not in output.lower()
    result={'label':label,'reg_to_reg':timing('BEGIN_REG_TO_REG','END_REG_TO_REG'),
            'overall':timing('BEGIN_OVERALL','END_OVERALL'),'slew_violating_pins':len(violations),
            'worst_transition_slack_ns':min((v['slack_ns'] for v in violations),default=0),
            'violations':violations,'sta_seconds':round(time.monotonic()-start,1),
            'netlist_sha256':hashlib.sha256(net_path.read_bytes()).hexdigest(),
            'log_sha256':hashlib.sha256(log_path.read_bytes()).hexdigest()}
    print(json.dumps({k:v for k,v in result.items() if k!='violations'}),flush=True)
    return result


def main():
    BUILD.mkdir(parents=True,exist_ok=True)
    previous=json.loads((ROOT/'study/results/banked_stream_sta.json').read_text())
    check_hashes(previous['source_sha256'])
    baseline=previous['synthesis'][0];check_hashes(baseline['rtl_sha256'])
    path=BASE/'flex_stream_banked_sta.v';raw=path.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==baseline['sta_netlist_sha256']
    lib=LIB.read_text()
    assert hashlib.sha256(LIB.read_bytes()).hexdigest()==previous['dependencies']['files'][0]['sha256']
    original=raw.decode();net=original;edits=[];iterations=[];cell_cache={}
    def cell(name):
        if name not in cell_cache:cell_cache[name]=library_cell(lib,name)
        return cell_cache[name]
    # Baseline at the same higher report precision; no constraints are relaxed.
    report=sta(path,'baseline');iterations.append(report)
    for turn in range(1,5):
        if not report['violations']:break
        drivers={}
        for v in report['violations']:
            name,pin=v['pin'].split('/')
            match,kind,pins=instance(net,name)
            if cell(kind)['logic_signature'].get(pin,{}).get('direction')=='output':drivers[name]=kind
        assert drivers,'No directly violating output driver found; inspect fanout before further repair'
        for name,old in sorted(drivers.items()):
            strength=re.search(r'_X(\d+)$',old);assert strength,old
            new=old[:strength.start()]+f'_X{2*int(strength[1])}'
            old_cell,new_cell=cell(old),cell(new)
            assert old_cell['logic_signature']==new_cell['logic_signature'],(old,new)
            match,kind,pins=instance(net,name);assert kind==old
            replacement=match[0].replace(old+' '+name,new+' '+name,1)
            net=net[:match.start()]+replacement+net[match.end():]
            edits.append({'iteration':turn,'instance':name,'old_cell':old,'new_cell':new,
                          'area_delta_um2':new_cell['area_um2']-old_cell['area_um2'],
                          'pin_connections':pins,'logic_signature':old_cell['logic_signature']})
        candidate=BUILD/f'repaired_{turn}.v';candidate.write_text(net)
        report=sta(candidate,f'repaired_{turn}');iterations.append(report)
    assert not report['violations'],'Four resize iterations did not clear slew'
    assert report['overall']['slack_ns']>=0,'Repair regressed setup beyond the reference constraint'
    # Reversing only the recorded cell-type tokens must recover the entire original
    # netlist byte for byte: no connections, constants, registers or logic changed.
    recovered=net
    for edit in reversed(edits):
        match,kind,pins=instance(recovered,edit['instance'])
        assert kind==edit['new_cell'] and pins==edit['pin_connections']
        replacement=match[0].replace(kind+' '+edit['instance'],edit['old_cell']+' '+edit['instance'],1)
        recovered=recovered[:match.start()]+replacement+recovered[match.end():]
    assert recovered==original,'Non-cell-type change detected'
    area_delta=sum(e['area_delta_um2'] for e in edits)
    final={'cell_area_um2':baseline['cell_area_um2']+area_delta,'area_delta_um2':area_delta,
           'area_increase_percent':100*area_delta/baseline['cell_area_um2'],
           'cells':baseline['cells'],'ff_cells':baseline['ff_cells'],**report}
    result={'baseline_cell_area_um2':baseline['cell_area_um2'],'iterations':iterations,'edits':edits,'final':final,
            'equivalence':{'identical_pin_functions':True,'identical_pin_connections':True,
                           'reversing_cell_types_recovers_exact_baseline':True,
                           'scope':'Zero-delay combinational function equivalence of every resized library cell; complete netlist connectivity/constants/registers unchanged.'},
            'constraints':previous['constraints'],'library':previous['library'],
            'source_sha256':hashes(['scripts/repair_stream_slew.py',*baseline['rtl_sha256']]),
            'baseline_result_sha256':hashes(['study/results/banked_stream_sta.json']),
            'limits':['Reference pre-layout cell timing; no SRAM, CTS, placement, extracted RC or power.',
                      'Setup/max-transition checks only; does not establish hold closure or physical signoff.',
                      'Technology-specific mapped-netlist resize; RTL remains technology independent and unchanged.']}
    RESULT.write_text(json.dumps(result,indent=2)+'\n')
    print('PASS: slew cleared; functions and connectivity unchanged; area delta',area_delta,flush=True)


if __name__=='__main__':main()
