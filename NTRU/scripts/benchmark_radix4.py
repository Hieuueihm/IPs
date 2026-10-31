"""Compare full radix4-factor CT/GS with paired radix2 using the selected reducer."""
import argparse
import importlib.util
import json
from random import Random
from arith_experiment_common import ROOT,run,hashes,check_hashes,synthesize

BUILD=ROOT/'study/build/radix4_compare'
RESULT=ROOT/'study/results/radix4_compare.json'
CHOICE=ROOT/'study/results/reducer_compare.json'
WRAPPERS='hdl/proto/radix4_compare_tops.sv'
SOURCES=['hdl/mul_ss.v','hdl/proto/flex_reduce_cluster.sv','hdl/proto/flex_radix4_factor.sv',WRAPPERS]
INCLUDE='hdl/proto/mont_reduce16_functions.vh'
TB='sim/src/tb_radix4_compare.sv'
TOPS=['radix2_shared3','radix2_shared4','radix4_shared4','radix2_pair4','radix4_pair4',
      'radix4_pair_q12289','radix4_pair_q3329','radix2_pair_q12289','radix2_pair_q3329',
      'radix4_shared_epoch','radix4_pair_epoch','radix4_pair_epoch_q12289','radix4_pair_epoch_q3329']
EPOCH_TB='sim/src/tb_radix4_epoch.sv'

def wrappers(implementation):
    ports='''input clk,rst,in_valid,input [1:0] mode,input profile,inverse,
input [15:0] tag,input [127:0] data,input [63:0] twiddle,
output out_valid,output [1:0] out_mode,output out_profile,out_inverse,
output [15:0] out_tag,output [127:0] result'''
    text=f'// Generated from reducer_compare.json selection; REDUCE_IMPL={implementation}.\n'
    text+='module radix2_delay #(parameter integer FIXED_MODE=-1,FIXED_PROFILE=-1)(\n'+ports.replace('output ','output reg ')+');\n'
    text+='''wire v,q,iv;wire [1:0] m;wire [15:0] t;wire [127:0] y;
'''
    text+=f'''flex_reduce_cluster #(.REDUCE_IMPL({implementation}),.FIXED_MODE(FIXED_MODE),.FIXED_PROFILE(FIXED_PROFILE)) u(
 .clk(clk),.rst(rst),.in_valid(in_valid),.mode(mode),.profile(profile),.inverse(inverse),
 .tag(tag),.data(data),.twiddle(twiddle),.out_valid(v),.out_mode(m),
 .out_profile(q),.out_inverse(iv),.out_tag(t),.result(y));
always @(posedge clk) begin
 out_valid<=!rst&&v;out_mode<=m;out_profile<=q;out_inverse<=iv;out_tag<=t;result<=y;
end
endmodule
'''
    definitions=[('radix2_shared3',f'flex_reduce_cluster #(.REDUCE_IMPL({implementation}))'),
                 ('radix2_shared4','radix2_delay'),
                 ('radix4_shared4',f'flex_radix4_factor #(.REDUCE_IMPL({implementation}))'),
                 ('radix2_pair4','radix2_delay #(.FIXED_MODE(1))'),
                 ('radix4_pair4',f'flex_radix4_factor #(.REDUCE_IMPL({implementation}),.FIXED_MODE(1))'),
                 ('radix4_pair_q12289',f'flex_radix4_factor #(.REDUCE_IMPL({implementation}),.FIXED_MODE(1),.FIXED_PROFILE(0))'),
                 ('radix4_pair_q3329',f'flex_radix4_factor #(.REDUCE_IMPL({implementation}),.FIXED_MODE(1),.FIXED_PROFILE(1))'),
                 ('radix2_pair_q12289','radix2_delay #(.FIXED_MODE(1),.FIXED_PROFILE(0))'),
                 ('radix2_pair_q3329','radix2_delay #(.FIXED_MODE(1),.FIXED_PROFILE(1))')]
    for top,extra in [('radix4_shared_epoch',''),('radix4_pair_epoch',',.FIXED_MODE(1)'),
                      ('radix4_pair_epoch_q12289',',.FIXED_MODE(1),.FIXED_PROFILE(0)'),
                      ('radix4_pair_epoch_q3329',',.FIXED_MODE(1),.FIXED_PROFILE(1)')]:
        definitions.append((top,f'flex_radix4_factor #(.REDUCE_IMPL({implementation}),.SHARE_CONSTANT(1){extra})'))
    for top,definition in definitions:text+=f'module {top}(\n{ports});\n{definition} u(.*);\nendmodule\n'
    (ROOT/WRAPPERS).write_text(text)

def simulate():
    spec=importlib.util.spec_from_file_location('reference',ROOT/'scripts/prototype_ntt_cluster.py')
    ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref);ref.BUILD=BUILD
    original,cases,counts,groups=ref.generate()
    rng=Random(20261026);records=[];excluded=0
    for idx,(mode,profile,inverse,data,roots,expected) in enumerate(original):
        q=(12289,3329)[profile];imag=(1479,1729)[profile]
        if mode==1:
            w=[((roots>>(16*k))&65535)*pow(65536,-1,q)%q for k in range(3)]
            common,u,v=w
            c=q-imag if inverse else imag
            if common!=u*u%q or v!=c*u%q:
                excluded+=1;continue
            factored=ref.pack([pow(u,k,q)*65536%q for k in (1,2,3)])
        else:factored=roots
        records.append((mode,profile,inverse,data,roots,factored,expected,idx))
    for iteration in range(512):
        for profile,q in enumerate((12289,3329)):
            for inverse in (False,True):
                c=(1479,1729)[profile];c=q-c if inverse else c
                u=[1,q-1,2,q//2][iteration] if iteration<4 else rng.randrange(1,q)
                a=[rng.randrange(q) for _ in range(4)]
                if iteration<4:a=[0,1,q-1,q//2]
                data=ref.pack(a)
                paired_roots=ref.pack([v*65536%q for v in (u*u%q,u,c*u%q)])
                factor_roots=ref.pack([pow(u,k,q)*65536%q for k in (1,2,3)])
                expected=ref.oracle(1,profile,inverse,data,paired_roots)
                records.append((1,profile,inverse,data,paired_roots,factor_roots,expected,None))
    rng.shuffle(records)
    path=BUILD/'radix4_vectors.txt'
    with path.open('w') as f:
        for mode,profile,inverse,data,pr,fr,expected,_ in records:
            f.write(f'{mode:x} {profile:x} {int(inverse):x} {data:032x} {pr:016x} {fr:016x} {expected:032x}\n')
    exe=BUILD/'sim.vvp'
    run(['iverilog','-g2012','-I',ROOT/'hdl/proto','-s','tb_radix4_compare','-o',exe,
         *[ROOT/s for s in SOURCES],ROOT/TB])
    actual=BUILD/'actual.txt'
    r=run(['vvp',exe,f'+vectors={path.as_posix()}',f'+actual={actual.as_posix()}'],capture_output=True,text=True)
    (BUILD/'simulation.log').write_text(r.stdout+r.stderr,encoding='utf-8');print(r.stdout,flush=True)
    outputs={int(i):int(p,16) for i,p in (line.split() for line in actual.read_text().splitlines())}
    assert len(outputs)==len(records)
    for idx,rec in enumerate(records):assert outputs[idx]==rec[-2]
    idmap={rec[-1]:idx for idx,rec in enumerate(records) if rec[-1] is not None}
    for group in groups:
        products=[]
        for partial in group['products']:
            acc=0
            for old_idx,i,j,a,b in partial:
                p=ref.signed(outputs[idmap[old_idx]],64)
                if i<3 and a>>31:p+=ref.signed(b,32)*(1<<32)
                if j<3 and b>>31:p+=ref.signed(a,32)*(1<<32)
                if i<3 and j<3 and a>>31 and b>>31:p+=1<<64
                acc+=p<<(32*(i+j))
            products.append(((acc+(1<<63))>>64)% (1<<128))
        p0,p1,p2=products
        assert (p0-p1)% (1<<128)==group['re']
        assert (p2-p0-p1)% (1<<128)==group['im']
    # Same vectors grouped into stable profile/direction epochs. Modes can
    # still alternate inside each epoch. Testbench drains before each change.
    epoch=sorted(records,key=lambda r:(r[1],r[2]))
    epoch_path=BUILD/'epoch_vectors.txt'
    with epoch_path.open('w') as f:
        for mode,profile,inverse,data,pr,fr,expected,_ in epoch:
            f.write(f'{mode:x} {profile:x} {int(inverse):x} {data:032x} {pr:016x} {fr:016x} {expected:032x}\n')
    epoch_exe=BUILD/'epoch.vvp'
    run(['iverilog','-g2012','-I',ROOT/'hdl/proto','-s','tb_radix4_epoch','-o',epoch_exe,
         *[ROOT/s for s in SOURCES],ROOT/EPOCH_TB])
    epoch_result=run(['vvp',epoch_exe,f'+vectors={epoch_path.as_posix()}'],capture_output=True,text=True)
    (BUILD/'epoch_simulation.log').write_text(epoch_result.stdout+epoch_result.stderr,encoding='utf-8')
    print(epoch_result.stdout,flush=True)
    return {'transactions':len(records),'configurations':9,'epoch_transactions':len(epoch),'epoch_configurations':4,
            'mismatches':0,'transform_traces':len(cases),
            'excluded_non_ntt_root_unit_vectors':excluded,'added_factor_root_vectors':2048,
            'r8_composed_complex_products':len(groups),
            'scope':'All four shared modes; mode1 is restricted to actual adjacent-NTT-layer twiddle relations. No INTT normalization inside core.'}

def report(sim,rows,choice):
    result={'simulation':sim,'synthesis':rows,'selected_reducer':choice,
            'source_sha256':hashes([*SOURCES,INCLUDE,TB,EPOCH_TB]),
            'limits':['Same function and II1; paired baseline has 3 or 4 edges, factor has 4 edges.',
                      'NTT-pair-only factor prunes the fourth multiplier; full shared factor retains four for FFT/independent NTT.',
                      'Mixed CT/GS tops include both fixed-root paths. Epoch tops share one and require drain on profile/direction change.',
                      'Generic GE/depth, not target timing, power, energy or whole-transform speedup.',
                      'No shared compressor FFT/reduction fabric is implemented by this comparison.']}
    RESULT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    lines=['# Radix4 factor vs paired radix2','',f'Selected reducer: **{choice["name"]}**.',
           '',f'Simulation: `{json.dumps(sim)}`','',
           '| Top | Comb GE | FF bits | Total GE | Gate depth |','|---|---:|---:|---:|---:|']
    for r in rows:lines.append(f'| {r["top"]} | {r["comb_ge"]} | {r["ff"]} | {r["total_ge"]} | {r["depth_cells"]} |')
    if rows:
        by_top={r['top']:r for r in rows}
        comparisons=[]
        for base,candidate in (('radix2_shared3','radix4_shared4'),('radix2_shared4','radix4_shared4'),
                               ('radix2_pair4','radix4_pair4'),('radix2_pair_q12289','radix4_pair_q12289'),
                               ('radix2_pair_q3329','radix4_pair_q3329'),
                               ('radix2_shared4','radix4_shared_epoch'),('radix2_pair4','radix4_pair_epoch'),
                               ('radix2_pair_q12289','radix4_pair_epoch_q12289'),('radix2_pair_q3329','radix4_pair_epoch_q3329')):
            ratio=by_top[candidate]['total_ge']/by_top[base]['total_ge']
            comparisons.append({'baseline':base,'candidate':candidate,'total_ge_ratio':ratio})
            lines+=['',f'{candidate} / {base}: {ratio:.4f}× total GE ({(ratio-1)*100:+.2f}%).']
        result['area_comparisons']=comparisons
    lines+=['','Limits','']+['- '+s for s in result['limits']]
    RESULT.with_suffix('.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    RESULT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synth',action='store_true');parser.add_argument('--synth-only',action='store_true');parser.add_argument('--yosys')
    args=parser.parse_args();BUILD.mkdir(parents=True,exist_ok=True)
    reducer=json.loads(CHOICE.read_text(encoding='utf-8'))
    check_hashes(reducer['source_sha256']);choice=reducer['selection']
    if args.synth_only:
        previous=json.loads(RESULT.read_text(encoding='utf-8'));check_hashes(previous['source_sha256'])
        assert previous['selected_reducer']==choice,'reducer selection changed'
        sim=previous['simulation']
    else:
        wrappers(choice['implementation']);sim=simulate();report(sim,[],choice)
    if args.synth or args.synth_only:report(sim,synthesize(BUILD,SOURCES,TOPS,args.yosys),choice)

if __name__=='__main__':main()
