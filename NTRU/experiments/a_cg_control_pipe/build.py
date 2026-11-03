"""Keep the routed control prototype intact; decouple its config sequencer."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
PREV=ROOT/'experiments/a_cg_control'
B=ROOT/'study/build/a_cg_control_pipe'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rep(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)

def main():
    old=json.loads((PREV/'manifest.json').read_text())
    for p,h in old['source_sha256'].items():assert sha(ROOT/p)==h
    (HERE/'rtl').mkdir(parents=True,exist_ok=True);B.mkdir(parents=True,exist_ok=True)
    core=(PREV/'rtl/a_cg_fast.sv').read_text()
    core=rep(core,'RUN=8, HPREP=9, CFG0=10, CFG1=11, CFG2=12, CFG3=13, CFG4=14;', 'RUN=8, HPREP=9;')
    core=rep(core,'    reg [3:0] state;', '''    reg [3:0] state;
    // Config has a private fixed-latency valid pipeline. It does not add states
    // or feedback decoders to the butterfly/host FSM.
    reg [4:0] cfg_pipe;
    wire cfg_pending=|cfg_pipe;
    wire cfg_accept=state==IDLE && !cfg_pending && cfg_valid;
    always @(posedge clk)
        if(rst)cfg_pipe<=0;
        else cfg_pipe<={cfg_pipe[3:0],cfg_accept};''')
    core=rep(core,'wire reset_launch=state==IDLE && start && !cfg_valid;',
        'wire reset_launch=state==IDLE && !cfg_pending && start && !cfg_valid;')
    core=rep(core,'assign cfg_ready = state==IDLE;', 'assign cfg_ready = state==IDLE && !cfg_pending;')
    core=rep(core,'assign load_ready = state==IDLE && configured && !cfg_valid;',
        'assign load_ready = state==IDLE && !cfg_pending && configured && !cfg_valid;')
    core=rep(core,'assign read_ready = (state==IDLE || state==HCATCH) && configured && !cfg_valid && !load_valid;',
        'assign read_ready = (state==IDLE || state==HCATCH) && !cfg_pending && configured && !cfg_valid && !load_valid;')
    core=rep(core,'            if (state==IDLE) begin', '            if (state==IDLE && !cfg_pending) begin')
    core=rep(core,'if (root_we && state==IDLE && root_dest[t])',
        'if (root_we && state==IDLE && !cfg_pending && root_dest[t])')
    core=rep(core,'roots_valid<=0;desc_valid<=0;error<=0;state<=CFG0;',
        'roots_valid<=0;desc_valid<=0;error<=0;')
    for i in range(5):
        expected=2 if i==4 else 1
        assert core.count('state==CFG'+str(i))==expected
        core=core.replace('state==CFG'+str(i),'cfg_pipe['+str(i)+']')
    for i in range(1,5):core=rep(core,'                state<=CFG'+str(i)+';\n','')
    core=rep(core,'configured<=!cfg_bad_q;error<=cfg_bad_q;state<=IDLE;',
        'configured<=!cfg_bad_q;error<=cfg_bad_q;')
    assert 'CFG0' not in core and 'CFG4' not in core.replace('after CFG4','after final config stage')
    (HERE/'rtl/a_cg_fast.sv').write_text(core)
    for name in ('tile_a.sv','mul_ss.v'):shutil.copy2(PREV/'rtl'/name,HERE/'rtl'/name)
    for name in ('main.cpp','tb_four_state.sv','application.py','run_sim.ps1','synth.tcl','validate.py','implement.tcl','report.py','README.md'):
        text=(PREV/name).read_text().replace('a_cg_control','a_cg_control_pipe')
        if name=='README.md':text+='\nThe five configuration setup steps now use a private valid pipeline. The core\nFSM retains only the original IDLE/host/compute states; setup latency stays five clocks.\n'
        (HERE/name).write_text(text)
    old['source_sha256']={p.relative_to(ROOT).as_posix():sha(p) for p in (HERE/'rtl').glob('*')}
    old['routed_control_parent']='experiments/a_cg_control/manifest.json'
    old['routed_control_parent_sha256']=sha(PREV/'manifest.json')
    (HERE/'manifest.json').write_text(json.dumps(old,indent=2)+'\n')
    print('Separate config valid pipeline generated; compute FSM and five setup clocks retained.')

if __name__=='__main__':main()
