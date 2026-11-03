"""Generate independent timing experiments from frozen packed16 + batch RTL."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
B=ROOT/'study/build/a_cg_timing'
OLD=ROOT/'experiments/a_cg_batch'
VARIANTS=('base','host','local','raw','all')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def replace(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)

def host(core):
    core=replace(core,'wire host_write=state==HLOAD || load_accept;','wire host_write=state==HLOAD;')
    core=replace(core,'wire host_read=state==HREAD || read_accept;','wire host_read=state==HREAD;')
    core=replace(core,'wire [1:0] host_sub=(load_accept || read_accept) ? 0 : host_word;','wire [1:0] host_sub=host_word;')
    core=replace(core,'wire [9:0] host_line_sel=load_accept ? load_line : read_accept ? read_line : host_line;','wire [9:0] host_line_sel=host_line;')
    core=replace(core,'wire [127:0] host_data_sel=load_accept ? load_data : host_data;','wire [127:0] host_data_sel=host_data;')
    core=core.replace('host_word<=1; state<=host_submask==0 ? IDLE : HLOAD;','host_word<=0; state<=HLOAD;')
    assert core.count('host_word<=1; state<=host_submask==0 ? HCATCH : HREAD;')==1
    core=core.replace('host_word<=1; state<=host_submask==0 ? HCATCH : HREAD;','host_word<=0; state<=HREAD;')
    core=replace(core,'host_word<=1;state<=host_submask==0 ? HCATCH : HREAD;','host_word<=0;state<=HREAD;')
    core=core.replace('// Burst adapter: accept phase 0 directly on ready/valid. A natural',
        '// Registered host adapter: capture request first, serve phase 0 next. A natural')
    return core

def local(tile):
    # Only public per-tile configuration flops. Leave the arithmetic, memories,
    # request pipeline and clocks free for normal optimization.
    for declaration in ('reg native_r;','reg [1:0] fmt_r;','reg [3:0] shift_r;',
                        'reg  [1:0] md;','reg        dir, mf;'):
        tile=replace(tile,declaration,'(* DONT_TOUCH = "TRUE" *) '+declaration)
    tile=replace(tile,'reg        floor_r, halve_r;',
        'reg floor_r;\n    (* DONT_TOUCH = "TRUE" *) reg halve_r;')
    return tile

def raw(tile):
    tile=replace(tile,'input  wire         ci, bi, split,','input  wire         ci, bi, split, plain,')
    tile=replace(tile,'    assign s = {sqh', '    wire [W-1:0] modular_s = {sqh')
    tile=replace(tile,'    assign d = {dfh','    wire [W-1:0] modular_d = {dfh')
    tile=replace(tile,'    assign co = sum[W];',
        '''    // FFT selects the exact raw sum/difference, before q correction.
    // The existing chains provide both outputs and unchanged carry/borrow.
    assign s = plain ? sum[W-1:0] : modular_s;
    assign d = plain ? {dfh[W-H-1:0],dfl[H-1:0]} : modular_d;
    assign co = sum[W];''')
    tile=replace(tile,'.q(mf ? 32\'d0 : ((dir ? rq_slot : slot_t) ? q1 : q0)), .ci(as_ci), .bi(as_bi), .split(mp),',
        '.q((dir ? rq_slot : slot_t) ? q1 : q0), .ci(as_ci), .bi(as_bi), .split(mp), .plain(mf),')
    return tile

def main():
    previous=json.loads((ROOT/'study/results/a_cg_batch.json').read_text(encoding='utf-8'))
    for p,h in previous['sha256'].items():
        if p.endswith(('.sv','.v','synthesized.dcp')):assert sha(ROOT/p)==h,('Frozen source changed',p)
    for p,h in previous['production_sha256'].items():assert sha(ROOT/p)==h
    inputs={p.relative_to(ROOT).as_posix():sha(p) for p in (OLD/'rtl').glob('*') if p.suffix in ('.sv','.v')}
    core=(OLD/'rtl/a_cg_fast.sv').read_text();tile=(OLD/'rtl/tile_a.sv').read_text()
    B.mkdir(parents=True,exist_ok=True)
    record=B/'baseline_hashes.json'
    state=dict(production=previous['production_sha256'],baseline=inputs)
    if record.exists():assert json.loads(record.read_text())==state
    else:record.write_text(json.dumps(state,indent=2)+'\n')
    for v in VARIANTS:
        out=HERE/v/'rtl';out.mkdir(parents=True,exist_ok=True)
        c=host(core) if v in ('host','all') else core
        t=local(tile) if v in ('local','all') else tile
        t=raw(t) if v in ('raw','all') else t
        (out/'a_cg_fast.sv').write_text(c)
        (out/'tile_a.sv').write_text(t)
        shutil.copy2(OLD/'rtl/mul_ss.v',out/'mul_ss.v')
        (B/v).mkdir(exist_ok=True)
    shutil.copy2(OLD/'main.cpp',HERE/'main.cpp')
    shutil.copy2(OLD/'tb_four_state.sv',HERE/'tb_four_state.sv')
    # The application bridge reuses identical frozen live C inputs/expected
    # fixtures; new RTL supplies the replacement outputs.
    app=(OLD/'application.py').read_text().replace("ROOT/'study/build/a_cg_batch'","ROOT/'study/build/a_cg_timing/all'")
    app=app.replace("sys.path.insert(0,str(Path(__file__).resolve().parent));import build\n    cg=build.__dict__.get('cg')",'import shutil')
    app=app.replace("stem=f'app_N{n}';build.pack(cases,cg,speed,stem)",
        "stem=f'app_N{n}';shutil.copy2(ROOT/'study/build/a_cg_batch'/(stem+'.bin'),BUILD/(stem+'.bin'))")
    app=app.replace('/experiments/a_cg_batch/application.py','/experiments/a_cg_timing/application.py')
    (HERE/'application.py').write_text(app)
    app_host=app.replace('study/build/a_cg_timing/all','study/build/a_cg_timing/host')
    app_host=app_host.replace('/experiments/a_cg_timing/application.py','/experiments/a_cg_timing/application_host.py')
    (HERE/'application_host.py').write_text(app_host)
    print('Generated',', '.join(VARIANTS),'from frozen packed16+batch RTL')

if __name__=='__main__':main()
